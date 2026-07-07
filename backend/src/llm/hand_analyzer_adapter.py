from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from src.domain.ports import IHandAnalyzer
from src.domain.models import HandContext
from src.domain.ai_models import HandAnalysis

class LlmPromptAnalyzer(IHandAnalyzer):
    def __init__(self, model_name: str = "llama3"):
        self.model_name = model_name
        self.llm = ChatOllama(model=model_name, temperature=0.2)
        self.prompt = PromptTemplate.from_template(
            "Você é um jogador profissional de poker experiente analisando um histórico de mão. "
            "Seja direto e objetivo. Indique o principal erro ou acerto do 'Hero' nesta mão.\n\n"
            "MÃO:\n{hand_history}\n\n"
            "ANÁLISE:"
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

    def _format_hand(self, hand: HandContext) -> str:
        out = f"Hand #{hand.hand_id} ({hand.game_info or 'Cash Game'})\n"
        out += f"Date: {hand.timestamp}\n"
        out += f"Final Pot: {hand.total_pot}\n\n"
        
        grouped = {}
        for act in hand.actions:
            street = act.street.name.upper()
            if street == "PRE_FLOP":
                street = "PREFLOP"
            if street not in grouped:
                grouped[street] = []
            grouped[street].append(act)
            
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
                    out += f"{line}{is_all_in}\n"
                out += "\n"
        
        villains_with_cards = {p: c for p, c in hand.player_cards.items() if p != hand.player_nickname and c}
        if villains_with_cards:
            out += "--- SHOWDOWN ---\n"
            for p, c in villains_with_cards.items():
                out += f"{p} shows [{c}]\n"
            out += "\n"
            
        return out.strip()
