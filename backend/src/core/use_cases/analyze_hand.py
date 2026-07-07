from dataclasses import replace
import uuid
from typing import Optional

from src.domain.ports import IHandAnalyzer, IAnalysisRepository
from src.domain.models import HandContext
from src.domain.ai_models import HandAnalysis, HandAnalysisFeedback
from datetime import datetime

class AnalyzeHandUseCase:
    def __init__(self, analyzer: IHandAnalyzer, repository: IAnalysisRepository):
        self.analyzer = analyzer
        self.repository = repository
        
    async def execute(self, hand: HandContext) -> HandAnalysis:
        # Check if we already have an analysis for this hand
        existing_analysis = await self.repository.get_analysis(hand.hand_id)
        if existing_analysis:
            return existing_analysis
            
        # Generate the analysis from the AI adapter.
        # The adapter returns a raw HandAnalysis (without an ID or properly set timestamps).
        # We ensure the Domain Entity gets a proper UUID and timestamp here.
        
        raw_analysis = await self.analyzer.analyze(hand)
        
        # Inject UUID and current time to guarantee uniqueness
        analysis = replace(
            raw_analysis,
            id=str(uuid.uuid4()),
            created_at=datetime.utcnow()
        )
        
        # Append-only persistence (non-blocking)
        await self.repository.save_analysis(analysis)
        
        return analysis


class ProvideFeedbackUseCase:
    def __init__(self, repository: IAnalysisRepository):
        self.repository = repository
        
    async def execute(self, analysis_id: str, is_useful: bool, comments: Optional[str] = None) -> HandAnalysisFeedback:
        feedback = HandAnalysisFeedback(
            id=str(uuid.uuid4()),
            analysis_id=analysis_id,
            is_useful=is_useful,
            comments=comments,
            created_at=datetime.utcnow()
        )
        
        # Append-only persistence (non-blocking)
        await self.repository.save_feedback(feedback)
        
        return feedback
