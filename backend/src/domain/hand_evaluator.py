from treys import Card, Evaluator
from typing import List

class HandEvaluator:
    """
    Adapter for the treys poker evaluation library.
    Evaluates GGPoker formatted cards into human-readable hand strengths.
    """
    def __init__(self):
        self.evaluator = Evaluator()

    def evaluate_street(self, hero_cards_str: str, board_cards_list: List[str]) -> str:
        """
        hero_cards_str: e.g. "Jh Ad"
        board_cards_list: e.g. ["Qh", "8c", "4h"]
        Returns a string describing the hand strength, e.g., "Pair", "High Card"
        """
        if not hero_cards_str:
            return "Unknown"
            
        try:
            hero_str_list = hero_cards_str.strip().split()
            # Convert GGPoker format ("Ts", "Ah") to Treys Card integers
            hero_cards = [Card.new(c) for c in hero_str_list]

            if not board_cards_list:
                return "Pre-Flop"

            board_cards = [Card.new(c) for c in board_cards_list]
            
            # Treys requires at least 3 board cards
            if len(board_cards) < 3:
                return "Pre-Flop"
                
            rank = self.evaluator.evaluate(board_cards, hero_cards)
            class_int = self.evaluator.get_rank_class(rank)
            class_str = self.evaluator.class_to_string(class_int)
            
            return class_str
        except Exception as e:
            # Fallback for parsing errors
            print(f"[HandEvaluator] Error evaluating {hero_cards_str} + {board_cards_list}: {e}")
            return "Unknown"
