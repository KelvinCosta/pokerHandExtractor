class PreflopAdvisor:
    """
    Rule-based Pre-flop GTO Advisor.
    Uses simplified tiers to determine GTO actions based on facing action.
    """
    def __init__(self):
        # Extremely simplified GTO representation
        self.tiers = {
            "PREMIUM": {"AA", "KK", "QQ", "AKs"},
            "STRONG": {"JJ", "TT", "AQs", "AKo", "AJs", "KQs"},
            "MARGINAL": {"99", "88", "77", "AQo", "AJo", "KQo", "ATs", "KJs", "QJs", "JTs"},
            "SPECULATIVE": {"66", "55", "44", "33", "22", "T9s", "98s", "87s", "76s", "65s", "54s", "ATo", "KJo", "QJo", "JTo"}
        }

    def get_tier(self, canonical_hand: str) -> str:
        for tier, hands in self.tiers.items():
            if canonical_hand in hands:
                return tier
        return "TRASH"

    def canonicalize(self, hero_cards_str: str) -> str:
        """
        Converts GGPoker cards ("Jh Ad") to canonical form ("AJo")
        """
        if not hero_cards_str:
            return ""
        
        cards = hero_cards_str.strip().split()
        if len(cards) != 2:
            return ""
            
        c1, c2 = cards[0], cards[1]
        r1, s1 = c1[0], c1[1]
        r2, s2 = c2[0], c2[1]
        
        ranks = "23456789TJQKA"
        idx1 = ranks.find(r1.upper())
        idx2 = ranks.find(r2.upper())
        
        if idx1 == -1 or idx2 == -1:
            return ""
            
        suited = "s" if s1.lower() == s2.lower() else "o"
        
        if idx1 > idx2:
            high_rank, low_rank = r1.upper(), r2.upper()
        else:
            high_rank, low_rank = r2.upper(), r1.upper()
            
        if high_rank == low_rank:
            return f"{high_rank}{low_rank}"
        else:
            return f"{high_rank}{low_rank}{suited}"

    def get_preflop_advice(self, hero_cards_str: str, facing_3bet: bool) -> str:
        canonical = self.canonicalize(hero_cards_str)
        if not canonical:
            return ""
            
        tier = self.get_tier(canonical)
        
        if facing_3bet:
            if tier == "PREMIUM":
                return f"O Call/4-Bet na 3-Bet com {canonical} (Premium) foi correto segundo o GTO."
            elif tier == "STRONG":
                return f"O Call na 3-Bet com {canonical} (Forte) é aceitável na maioria das vezes."
            elif tier == "MARGINAL":
                return f"O Open Raise do Hero com {canonical} foi ok, mas dar CALL na 3-Bet com mão Marginal é um ERRO. GTO exige FOLD."
            else:
                return f"Dar CALL na 3-Bet com {canonical} (Fraca) é um erro gravíssimo. GTO exige FOLD."
        
        return ""
