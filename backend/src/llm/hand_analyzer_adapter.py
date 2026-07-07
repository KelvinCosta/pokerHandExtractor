from langchain_ollama import ChatOllama
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate
)
from src.domain.ports import IHandAnalyzer
from src.domain.models import HandContext
from src.domain.ai_models import HandAnalysis
from src.domain.hand_evaluator import HandEvaluator

class LlmPromptAnalyzer(IHandAnalyzer):
    def __init__(self, model_name: str = "llama3"):
        self.model_name = model_name
        self.llm = ChatOllama(model=model_name, temperature=0.2, num_ctx=1024, num_predict=512)
        
        system_template = """Você é um Arquiteto de Software e Jogador Profissional de Poker de High Stakes, especialista em GTO (Game Theory Optimal).

A sua missão é analisar históricos de mãos. Você NUNCA deve dar conselhos genéricos. Seja estrito, matemático e encontre vazamentos (leaks).

<regras_inquebraveis>
1. PROIBIDO USAR FRASES GENÉRICAS: Nunca diga "isso é suspeito", "isso é razoável", "não tem informação". Fale de Ranges e Equidade.
2. CITE A FORÇA DA MÃO: O sistema (Python) já calculou a Força da Mão (Hero Strength) para você no log. Use EXATAMENTE essa força na sua análise. NÃO INVENTE MÃOS.
3. Seja AGRESSIVO nas críticas. Se o Hero pagou apostas grandes com "High Card" ou mãos fracas, chame a jogada de "Fish" ou "Doação de fichas".
4. Leia a 'Relative Position' no bloco [GTO METRICS].
5. Valores de aposta já estão calculados em BIG BLINDS (BBs).
6. A ação "BLIND" é uma aposta obrigatória. NUNCA critique um BLIND.
7. Identifique os Atores: "Hero" é o jogador analisado. NÃO INVENTE AÇÕES.
8. Se SPR <= 1 no Flop, o Hero está COMMITADO. Nunca sugira fold ou apostar pequeno.
9. VOCÊ DEVE RESPONDER EM PORTUGUÊS (PT-BR). QUALQUER RESPOSTA EM INGLÊS SERÁ DESCARTADA.
</regras_inquebraveis>

FORMATO DE SAÍDA EXIGIDO:
**DIAGNÓSTICO PRÉ-FLOP:** [Análise severa da entrada]
**DIAGNÓSTICO PÓS-FLOP:** [Análise linha a linha das apostas e equidade]
**VEREDICTO ARQUITETURAL:** [Qual foi o erro principal? Qual botão deveria ter sido clicado?]"""

        human_template = """
MÃO:
{hand_history}
"""
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_template),
            HumanMessagePromptTemplate.from_template(human_template)
        ])

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
        player_map = {hand.player_nickname: "Hero"}
        villain_counter = 1
        for act in hand.actions:
            if act.player not in player_map:
                player_map[act.player] = f"Villain {villain_counter}"
                villain_counter += 1
                
        out = f"Hand #{hand.hand_id} ({hand.game_info or 'Cash Game'})\n"
        out += f"Date: {hand.timestamp}\n"
        
        # Calculate GTO Metrics if available
        eff_stack = self._calculate_effective_stack(hand)
        
        bb = getattr(hand, "stake_level", 0.0)
        if not bb or bb == 0.0:
            posts = [a.amount for a in hand.actions if a.action_type.name in ("POST", "BLIND")]
            if posts:
                bb = max(posts)
        if not bb or bb == 0.0:
            bb = 1.0
            
        eff_stack_bb = round(eff_stack / bb, 1)
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
        total_pot_bb = round(hand.total_pot / bb, 1)
        out += f"Final Pot: {total_pot_bb} BBs\n\n"
        
        hero_cards_val = hand.player_cards.get(hand.player_nickname, "")
        board_cards = hand.board_cards or ()
        
        evaluator = HandEvaluator()
        
        street_order = ["PREFLOP", "FLOP", "TURN", "RIVER"]
        for street in street_order:
            if street in grouped:
                out += f"--- {street} ---\n"
                
                if street == "PREFLOP" and hero_cards_val:
                    out += f"Dealt to Hero [{hero_cards_val}]\n"
                elif street == "FLOP" and len(board_cards) >= 3:
                    current_board = board_cards[:3]
                    strength = evaluator.evaluate_street(hero_cards_val, current_board)
                    out += f"Board [{' '.join(current_board)}] (Hero Strength: {strength})\n"
                elif street == "TURN" and len(board_cards) >= 4:
                    current_board = board_cards[:4]
                    strength = evaluator.evaluate_street(hero_cards_val, current_board)
                    out += f"Board [{' '.join(current_board)}] (Hero Strength: {strength})\n"
                elif street == "RIVER" and len(board_cards) >= 5:
                    current_board = board_cards[:5]
                    strength = evaluator.evaluate_street(hero_cards_val, current_board)
                    out += f"Board [{' '.join(current_board)}] (Hero Strength: {strength})\n"
                
                for act in grouped[street]:
                    is_all_in = " (All-in)" if act.is_all_in else ""
                    mapped_player = player_map.get(act.player, act.player)
                    act_name = act.action_type.name
                    if act_name == "POST":
                        act_name = "BLIND"
                        
                    line = f"{mapped_player}: {act_name}"
                    if act.amount > 0:
                        amt_bb = round(act.amount / bb, 1)
                        line += f" {amt_bb} BBs"
                        
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
                mapped_villain = player_map.get(p, p)
                out += f"{mapped_villain} shows [{c}]\n"
            out += "\n"
            
        return out.strip()
