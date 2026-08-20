from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

@dataclass(frozen=True, slots=True)
class HandAnalysis:
    id: str # UUID for this specific analysis run
    hand_id: str
    agent_version: str # e.g., "v1.0-gpt4o-zeroshot"
    raw_analysis: str
    created_at: datetime
    
@dataclass(frozen=True, slots=True)
class HandAnalysisFeedback:
    id: str # UUID for this feedback record
    analysis_id: str
    is_useful: bool
    comments: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
