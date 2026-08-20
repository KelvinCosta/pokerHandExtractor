from datetime import datetime
import pytest
from pydantic import ValidationError
from schemas import TimeWindow, GlobalStats, BehavioralTriggers, PlayerStats

def test_time_window_validation():
    window = TimeWindow(
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 1, 31),
        stake_level=2.0
    )
    assert window.stake_level == 2.0

def test_global_stats_validation():
    stats = GlobalStats(
        hands_played=1000,
        win_rate_bb100=5.5,
        profit_bb=55.0,
        vpip=25.0,
        pfr=20.0,
        aggressiveness_factor=2.5,
        all_in_freq=1.0,
        wsd=30.0,
        wwsf=45.0
    )
    assert stats.aggressiveness_factor == 2.5
    assert stats.profit_bb == 55.0

def test_behavioral_triggers_validation():
    # Testa os novos campos adicionados (Milestone 2)
    triggers = BehavioralTriggers(
        recent_trend_vpip=28.0,
        recent_trend_pfr=22.0,
        recent_profit_bb=-15.0,
        recent_aggressiveness_factor=1.8,
        current_losing_streak_sessions=3,
        max_session_downswing_bb=-50.0
    )
    assert triggers.recent_profit_bb == -15.0
    assert triggers.recent_aggressiveness_factor == 1.8
    assert triggers.recent_trend_vpip == 28.0

def test_behavioral_triggers_missing_fields():
    # Garantir que falha se omitir os campos novos obrigatórios
    with pytest.raises(ValidationError):
        BehavioralTriggers(
            recent_trend_vpip=28.0,
            recent_trend_pfr=22.0,
            current_losing_streak_sessions=3,
            max_session_downswing_bb=-50.0
            # Faltando recent_profit_bb e recent_aggressiveness_factor
        )

def test_player_stats_composition():
    stats = PlayerStats(
        player_id="Hero",
        time_window=TimeWindow(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 1, 31),
            stake_level=10.0
        ),
        global_stats=GlobalStats(
            hands_played=500,
            win_rate_bb100=10.0,
            profit_bb=50.0,
            vpip=22.0,
            pfr=18.0,
            aggressiveness_factor=3.0,
            all_in_freq=2.0,
            wsd=28.0,
            wwsf=48.0
        ),
        behavioral_triggers=BehavioralTriggers(
            recent_trend_vpip=24.0,
            recent_trend_pfr=20.0,
            recent_profit_bb=5.0,
            recent_aggressiveness_factor=2.5,
            current_losing_streak_sessions=0,
            max_session_downswing_bb=-20.0
        )
    )
    assert stats.player_id == "Hero"
    assert stats.behavioral_triggers.recent_profit_bb == 5.0
