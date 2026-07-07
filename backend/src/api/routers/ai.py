from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import os
import polars as pl

from src.core.use_cases.analyze_hand import AnalyzeHandUseCase, ProvideFeedbackUseCase
from src.llm.hand_analyzer_adapter import LlmPromptAnalyzer
from src.database.analysis_repository import SQLiteAnalysisRepository
from src.api.dependencies import _load_user_datalake, get_current_user
from src.database.models import User
from src.domain.models import HandContext

router = APIRouter(prefix="/api/ai", tags=["AI Analysis"])

# Simple dependency injection for the MVP
# In a real app with proper DI, we'd use FastAPI Depends or a DI container
repository = SQLiteAnalysisRepository()
analyzer = LlmPromptAnalyzer(model_name="llama3")

class AnalysisFeedbackRequest(BaseModel):
    is_useful: bool
    comments: Optional[str] = None

@router.post("/analyze/{hand_id}")
async def analyze_hand(hand_id: str, current_user: User = Depends(get_current_user)):
    silver_bucket = os.getenv("S3_SILVER_BUCKET", "poker-silver")
    cache_entry = _load_user_datalake(current_user.id, silver_bucket)
    df = cache_entry.get("df_hands")
    
    if df is None or df.height == 0:
        raise HTTPException(status_code=404, detail="No data available")
        
    hand_df = df.filter(pl.col("hand_id") == hand_id)
    if hand_df.height == 0:
        raise HTTPException(status_code=404, detail="Hand not found")
        
    hand_dict = hand_df.to_dicts()[0]
    
    # Garantir serialização da data
    if "data_limpa" in hand_dict and hand_dict["data_limpa"]:
        hand_dict["data_limpa"] = str(hand_dict["data_limpa"])
        
    # Map raw dictionary to Domain HandContext
    # We only map the fields necessary for the Analyzer Adapter to format the hand
    from src.domain.models import Action, ActionType, Street

    mapped_actions = []
    for act in hand_dict.get("actions", []):
        street_str = act.get("street", "PREFLOP").upper()
        if street_str == "PRE_FLOP": street_str = "PREFLOP"
        try:
            street_enum = Street[street_str]
        except KeyError:
            street_enum = Street.PRE_FLOP
            
        action_type_str = act.get("action_type", "CHECK").upper()
        try:
            action_type_enum = ActionType[action_type_str]
        except KeyError:
            action_type_enum = ActionType.CHECK
            
        mapped_actions.append(Action(
            player=act.get("player", ""),
            action_type=action_type_enum,
            street=street_enum,
            amount=act.get("amount", 0.0),
            is_all_in=act.get("is_all_in", False)
        ))

    player_cards = {}
    for p in hand_dict.get("player_cards", []):
        if "player" in p and "cards" in p:
            player_cards[p["player"]] = p["cards"]

    import ast
    starting_stacks = {}
    player_seats = {}
    button_seat = 0
    try:
        ss_raw = hand_dict.get("starting_stacks", "{}")
        if isinstance(ss_raw, str):
            starting_stacks = ast.literal_eval(ss_raw)
        elif isinstance(ss_raw, dict):
            starting_stacks = ss_raw
            
        ps_raw = hand_dict.get("player_seats", "{}")
        if isinstance(ps_raw, str):
            player_seats = ast.literal_eval(ps_raw)
        elif isinstance(ps_raw, dict):
            player_seats = ps_raw
            
        button_seat = int(hand_dict.get("button_seat", 0))
    except Exception:
        pass

    hand_context = HandContext(
        hand_id=hand_dict.get("hand_id", hand_id),
        timestamp=hand_dict.get("data_limpa", ""),
        game_info=hand_dict.get("game_type", ""),
        actions=tuple(mapped_actions),
        board_cards=tuple(hand_dict.get("board_cards", [])),
        player_cards=player_cards,
        player_nickname=hand_dict.get("player_nickname", "Hero"),
        total_pot=hand_dict.get("total_pot_final", 0.0),
        starting_stacks=starting_stacks,
        player_seats=player_seats,
        button_seat=button_seat
    )
    
    # 3. Run the orchestrator
    use_case = AnalyzeHandUseCase(analyzer, repository)
    analysis = await use_case.execute(hand_context)
    
    return {
        "analysis_id": analysis.id,
        "raw_analysis": analysis.raw_analysis,
        "agent_version": analysis.agent_version
    }

@router.post("/feedback")
async def provide_feedback(request: AnalysisFeedbackRequest):
    use_case = ProvideFeedbackUseCase(repository)
    # Temporary: using a fake analysis_id if not provided just for testing
    feedback = await use_case.execute(
        analysis_id="fake-id", # In reality, we'd pass this from the UI request
        is_useful=request.is_useful,
        comments=request.comments
    )
    return {"status": "success", "feedback_id": feedback.id}
