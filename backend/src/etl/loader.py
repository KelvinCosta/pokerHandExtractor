import os
import polars as pl
from typing import Iterator
from itertools import islice
from src.domain.models import HandContext, ActionType
from src.parser.summary_parser import TournamentSummary

class HandLoader:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _parse_game_type(self, source_file: str, game_info: str, hand_id: str) -> str:
        name = source_file.lower()
        if "rushandcash" in name or hand_id.startswith("RC"):
            return "Rush & Cash"
        if "spin&gold" in name:
            return "Spin & Gold"
        if "mystery battle royale" in name or "mbr" in name:
            return "Mystery Battle Royale"
        if "tournament" in name or "bounty" in name or "freeroll" in name or "step" in name:
            return "Tournament"
        if "tournament" in game_info.lower():
            return "Tournament"
        return "Regular Cash"

    def process_and_save(self, hands_iterator: Iterator[HandContext], batch_size: int = 10000) -> int:
        total_processed = 0
        import time
        run_id = int(time.time() * 1000)
        batch_index = 1
        
        while True:
            batch = list(islice(hands_iterator, batch_size))
            if not batch:
                break
                
            dict_batch = []
            for hand in batch:
                # 1. Calculando Lucro Líquido do Hero
                hero_collected = sum(a.amount for a in hand.actions if a.player == hand.player_nickname and a.action_type == ActionType.COLLECT)
                hero_invested = sum(a.invested_amount for a in hand.actions if a.player == hand.player_nickname and a.action_type not in (ActionType.COLLECT, ActionType.FOLD))
                hero_net_profit = round(hero_collected - hero_invested, 2)
                
                # 2. Extraindo Posição e Flags Pré-Flop
                preflop_actions = [a for a in hand.actions if (hasattr(a.street, "name") and a.street.name == "PRE_FLOP" or str(a.street) == "PRE_FLOP")]
                
                # VPIP, PFR, 3Bet
                hero_vpip = any(a.player == hand.player_nickname and a.action_type in (ActionType.CALL, ActionType.RAISE) for a in preflop_actions)
                hero_pfr = any(a.player == hand.player_nickname and a.action_type == ActionType.RAISE for a in preflop_actions)
                
                # 3Bet heuristic: Was it the 2nd raise or more on preflop?
                raises_before_hero = 0
                hero_3bet = False
                for a in preflop_actions:
                    if a.action_type == ActionType.RAISE:
                        if a.player == hand.player_nickname and raises_before_hero >= 1:
                            hero_3bet = True
                            break
                        if a.player != hand.player_nickname:
                            raises_before_hero += 1

                # Inferindo posição (Ordem de primeira ação pré-flop)
                # Ordem esperada: SB, BB, UTG, MP, CO, BTN
                seen_players = []
                for a in preflop_actions:
                    if a.player not in seen_players:
                        seen_players.append(a.player)
                
                hero_position = "Unknown"
                if hand.player_nickname in seen_players:
                    idx = seen_players.index(hand.player_nickname)
                    total_players = len(seen_players)
                    if idx == 0: hero_position = "SB"
                    elif idx == 1: hero_position = "BB"
                    elif idx == total_players - 1: hero_position = "BTN"
                    elif idx == total_players - 2: hero_position = "CO"
                    elif idx == 2 and total_players > 4: hero_position = "UTG"
                    else: hero_position = "MP"

                dict_batch.append({
                    "hand_id": hand.hand_id,
                    "date": hand.timestamp,
                    "source_file": hand.source_file,
                    "game_info": hand.game_info,
                    "game_type": self._parse_game_type(hand.source_file, hand.game_info, hand.hand_id),
                    "stake_level": hand.stake_level,
                    "platform": hand.platform,
                    "player_nickname": hand.player_nickname,
                    "hero_net_profit": hero_net_profit,
                    "hero_position": hero_position,
                    "hero_vpip": hero_vpip,
                    "hero_pfr": hero_pfr,
                    "hero_3bet": hero_3bet,
                    "current_pot": hand.current_pot, 

                    "total_pot_final": hand.total_pot,
                    "rake": hand.rake,
                    "jackpot": hand.jackpot,
                    "bingo": hand.bingo,
                    "fortune": hand.fortune,
                    "tax": hand.tax,
                    "actions": [
                        {
                            "player": a.player,
                            "action_type": a.action_type.name if hasattr(a.action_type, "name") else str(a.action_type),
                            "street": a.street.name if hasattr(a.street, "name") else str(a.street),
                            "amount": a.amount,
                            "is_all_in": a.is_all_in,
                            "invested_amount": a.invested_amount,
                            "pot_odds": a.pot_odds
                        }
                        for a in hand.actions
                    ],
                    "board_cards": list(hand.board_cards),
                    "board_str": " ".join(hand.board_cards),
                    "player_cards": [{"player": p, "cards": c} for p, c in hand.player_cards.items()],
                    "hero_cards": hand.player_cards.get(hand.player_nickname, ""),
                    "lista_vencedores": [a.player for a in hand.actions if a.action_type == ActionType.COLLECT],
                    "hero_ganhou": any(a.player == hand.player_nickname and a.action_type == ActionType.COLLECT for a in hand.actions),
                    "hero_flop_pot_odds": max([a.pot_odds for a in hand.actions if a.player == hand.player_nickname and (hasattr(a.street, "name") and a.street.name == "FLOP" or str(a.street) == "FLOP")] + [0.0]),
                    "hero_turn_pot_odds": max([a.pot_odds for a in hand.actions if a.player == hand.player_nickname and (hasattr(a.street, "name") and a.street.name == "TURN" or str(a.street) == "TURN")] + [0.0]),
                    "hero_river_pot_odds": max([a.pot_odds for a in hand.actions if a.player == hand.player_nickname and (hasattr(a.street, "name") and a.street.name == "RIVER" or str(a.street) == "RIVER")] + [0.0])
                })
            
            df = pl.DataFrame(dict_batch)
            
            # Cast explícito para garantir que listas vazias não sejam inferidas como List(Null)
            df = df.with_columns(pl.col("board_cards").cast(pl.List(pl.String)))

            flop_suits_count = (
                pl.col("board_cards").list.slice(0, 3)
                .list.eval(pl.element().str.slice(1, 1))
                .list.unique()
                .list.len()
            )

            flop_values_count = (
                pl.col("board_cards").list.slice(0, 3)
                .list.eval(pl.element().str.slice(0, 1))
                .list.unique()
                .list.len()
            )

            df = df.with_columns(
                pl.when(pl.col("board_cards").list.len() >= 3)
                .then(
                    pl.when(flop_suits_count == 1).then(pl.lit("Monotone"))
                    .when(flop_suits_count == 2).then(pl.lit("Two-Tone"))
                    .when(flop_suits_count == 3).then(pl.lit("Rainbow"))
                    .otherwise(pl.lit(None, dtype=pl.String))
                )
                .otherwise(pl.lit(None, dtype=pl.String))
                .alias("flop_suit_type"),

                pl.when(pl.col("board_cards").list.len() >= 3)
                .then(
                    pl.when(flop_values_count == 3).then(pl.lit("Unpaired"))
                    .when(flop_values_count == 2).then(pl.lit("Paired"))
                    .when(flop_values_count == 1).then(pl.lit("Trips"))
                    .otherwise(pl.lit(None, dtype=pl.String))
                )
                .otherwise(pl.lit(None, dtype=pl.String))
                .alias("flop_pair_type")
            )
            
            output_file = os.path.join(self.output_dir, f"hands_part_{run_id}_{batch_index}.parquet")
            df.write_parquet(output_file, compression="zstd")
            print(f"✅ Partição {batch_index:04d} salva: {output_file} ({df.height} mãos)")
            
            total_processed += df.height
            batch_index += 1
            
        print(f"📊 Carga completa! Total de mãos particionadas: {total_processed}")
        return total_processed

    def save_summaries(self, summaries: list[TournamentSummary]):
        if not summaries:
            return
            
        file_path = os.path.join(self.output_dir, "tournaments.parquet")
        
        dict_batch = [s.model_dump() for s in summaries]
        new_df = pl.DataFrame(dict_batch)
        
        if os.path.exists(file_path):
            existing_df = pl.read_parquet(file_path)
            # Combinar e remover duplicatas pelo tournament_id
            df = pl.concat([existing_df, new_df]).unique(subset=["tournament_id"], keep="last")
        else:
            df = new_df
            
        df.write_parquet(file_path, compression="zstd")
        print(f"✅ Torneios atualizados: {len(summaries)} novos sumários salvos no Datalake (Total: {df.height})")