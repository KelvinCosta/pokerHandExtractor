from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from src.domain.ports import IHandAnalyzer
from src.domain.models import HandContext
from src.domain.ai_models import HandAnalysis

class LlmPromptAnalyzer(IHandAnalyzer):
    def __init__(self, model_name: str = "llama3"):
        self.model_name = model_name
        self.llm = ChatOllama(model=model_name, temperature=0.2, num_ctx=2048, num_predict=512)
        self.prompt = PromptTemplate.from_template(
            """
            Você é um Arquiteto de Software e Jogador Profissional de Poker de High Stakes, especialista em GTO (Game Theory Optimal) e estratégias Exploitative para jogos de Micro-Stakes (NL2 e NL5).

            A sua missão é analisar históricos de mãos fornecidos num formato de log de texto.
            Você NUNCA deve dar conselhos genéricos. Você deve ser estrito, matemático e focar em encontrar "vazamentos" (leaks) na lógica do jogador (Hero).

            Siga OBRIGATORIAMENTE este pipeline de processamento para cada mão:

            1. LEITURA DE ESTADO (PRE-FLOP):
            - Analise a posição do Hero. 
            - Foi um Pote Simples (SRP), 3-Bet ou 4-Bet?
            - A mão inicial do Hero justificava a ação? (Ex: Pagar 3-bets fora de posição com mãos marginais como AJo, KTo é um erro grave. Se o Hero fez isso, critique severamente).

            2. AVALIAÇÃO DE TEXTURA (PÓS-FLOP):
            - Calcule mentalmente o tamanho do pote e o SPR (Stack-to-Pot Ratio).
            - Como a mão do Hero se conecta com o Bordo? É Top Pair? Draw? Segundo Par? Lixo?
            - NUNCA chame um Segundo Par de "mão forte" num pote grande.

            3. AUDITORIA DE ERROS COMUNS:
            - Value Owning: O Hero apostou no River com uma mão média quando mãos piores nunca dariam call e mãos melhores nunca foldariam?
            - Passividade Pré-flop: O Hero deu apenas Call com mãos Premium (QQ+, AK, AQs) em vez de aplicar uma 3-bet?
            - Sunk Cost Fallacy: O Hero pagou múltiplas apostas apenas por "esperança" sem as Pot Odds adequadas?

            4. FORMATO DE SAÍDA:
            Gere a análise dividida em:
            - [DIAGNÓSTICO PRÉ-FLOP]: Avaliação severa da decisão de entrada.
            - [DIAGNÓSTICO PÓS-FLOP]: Análise linha a linha das apostas (sizing) e da equidade.
            - [VEREDICTO ARQUITETURAL]: Qual foi o erro principal? Qual botão deveria ter sido clicado (Fold, Call, Raise) e porquê.
            - DIRETRIZ DE SAÍDA: Você deve gerar toda a resposta OBRIGATORIAMENTE em Português do Brasil (pt-BR)
            
            REGRAS MATEMÁTICAS E LÓGICAS INQUEBRÁVEIS (STRICT RULES):
                1. Regra do All-in: Se um jogador aposta All-in e toma Call, a rodada de apostas acaba. Nunca sugira que um jogador faça "Fold" para um "Call".
                2. Regra do SPR (Stack-to-Pot Ratio): Se no Flop a aposta restante do Hero for menor ou igual ao tamanho do pote (SPR <= 1), o Hero está matematicamente COMMITADO. Com Top Pair ou Overpair (ex: AA, KK), a única jogada correta é ir All-in. NUNCA critique um all-in com SPR baixo e NUNCA sugira "apostar pequeno" se o stack restante for minúsculo.
                3. Regra de Ocultação: Com SPR baixo (potes grandes, pouco stack), ocultar informação é irrelevante. O objetivo é realizar equidade.
            MÃO:
            {hand_history}
            ANÁLISE:
            """
        )

        self.chain = self.prompt | self.llm
        
    async def analyze(self, hand: HandContext) -> HandAnalysis:
        # 1. Format the HandContext into a clean string (similar to our Clipboard format)
        hand_history_str = self._format_hand(hand)
        
        # 2. Invoke the LLM chain
        response = await self.chain.ainvoke({"hand_history": hand_history_str})
        
        # 3. Return the raw Analysis Entity (ID and timestamps will be injected by the Use Case)
        return HandAnalysis(
            id="", 
            hand_id=hand.hand_id,
            agent_version=f"{self.model_name}-zeroshot",
            raw_analysis=response.content,
            created_at=None
        )

    def _calculate_effective_stack(self, hand: HandContext) -> float:
        if not hasattr(hand, "starting_stacks") or not hand.starting_stacks:
            return 0.0
        hero_stack = hand.starting_stacks.get(hand.player_nickname, 0.0)
        villain_stacks = [s for p, s in hand.starting_stacks.items() if p != hand.player_nickname]
        if not villain_stacks:
            return hero_stack
        max_villain = max(villain_stacks)
        return min(hero_stack, max_villain)

    def _determine_relative_position(self, hand: HandContext) -> str:
        if not hasattr(hand, "player_seats") or not hand.player_seats:
            return "Unknown"
        hero_seat = hand.player_seats.get(hand.player_nickname, -1)
        btn_seat = getattr(hand, "button_seat", 0)
        if hero_seat == -1 or btn_seat == 0:
            return "Unknown"
        if hero_seat == btn_seat:
            return "In Position (Button)"
        # Simple heuristic for now
        return "Out of Position / Middle Position"

    def _format_hand(self, hand: HandContext) -> str:
        out = f"Hand #{hand.hand_id} ({hand.game_info or 'Cash Game'})\n"
        out += f"Date: {hand.timestamp}\n"
        
        # Calculate GTO Metrics if available
        eff_stack = self._calculate_effective_stack(hand)
        eff_stack_bb = round(eff_stack / hand.stake_level, 1) if hand.stake_level > 0 else 0
        rel_pos = self._determine_relative_position(hand)
        
        out += "\n[GTO METRICS]\n"
        out += f"Effective Stack: {eff_stack_bb} BBs\n"
        out += f"Relative Position: {rel_pos}\n"
        
        # Track running pot for Pot Odds and SPR
        running_pot = 0.0
        flop_pot = 0.0
        
        grouped = {}
        for act in hand.actions:
            street = act.street.name.upper()
            if street == "PRE_FLOP":
                street = "PREFLOP"
            if street not in grouped:
                grouped[street] = []
            grouped[street].append(act)
            
        # Calculate Pot before Flop actions (for SPR)
        for act in grouped.get("PREFLOP", []):
            running_pot += getattr(act, "invested_amount", 0.0)
        flop_pot = running_pot
        
        if flop_pot > 0 and eff_stack > 0:
            spr = round(eff_stack / flop_pot, 2)
            out += f"SPR (Flop): {spr}\n"
            
        out += "\n"
        out += f"Final Pot: {hand.total_pot}\n\n"
        
        hero_cards_val = hand.player_cards.get(hand.player_nickname, "")
        board_cards = hand.board_cards or ()
        
        street_order = ["PREFLOP", "FLOP", "TURN", "RIVER"]
        for street in street_order:
            if street in grouped:
                out += f"--- {street} ---\n"
                
                if street == "PREFLOP" and hero_cards_val:
                    out += f"Dealt to Hero [{hero_cards_val}]\n"
                elif street == "FLOP" and len(board_cards) >= 3:
                    out += f"Board [{' '.join(board_cards[:3])}]\n"
                elif street == "TURN" and len(board_cards) >= 4:
                    out += f"Board [{' '.join(board_cards[:4])}]\n"
                elif street == "RIVER" and len(board_cards) >= 5:
                    out += f"Board [{' '.join(board_cards[:5])}]\n"
                
                for act in grouped[street]:
                    is_all_in = " (All-in)" if act.is_all_in else ""
                    line = f"{act.player}: {act.action_type.name}"
                    if act.amount > 0:
                        line += f" {act.amount}"
                        
                    # Pot odds calculation (very naive approach based on invested amount)
                    invested = getattr(act, "invested_amount", 0.0)
                    running_pot += invested
                    
                    if act.player == hand.player_nickname and act.action_type.name == "CALL" and invested > 0:
                        pot_odds_pct = round((invested / running_pot) * 100, 1) if running_pot > 0 else 0
                        line += f" [Pot Odds: {pot_odds_pct}%]"
                        
                    out += f"{line}{is_all_in}\n"
                out += "\n"
        
        villains_with_cards = {p: c for p, c in hand.player_cards.items() if p != hand.player_nickname and c}
        if villains_with_cards:
            out += "--- SHOWDOWN ---\n"
            for p, c in villains_with_cards.items():
                out += f"{p} shows [{c}]\n"
            out += "\n"
            
        return out.strip()
