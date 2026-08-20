import asyncio
from typing import Optional, Dict
from src.domain.ports import IAnalysisRepository
from src.domain.ai_models import HandAnalysis, HandAnalysisFeedback

class InMemoryAnalysisRepository(IAnalysisRepository):
    """
    A simple in-memory repository for development and testing.
    Since the methods are async but we use an in-memory dict, 
    we just return directly, occasionally sleeping to simulate I/O.
    """
    def __init__(self):
        self._analyses: Dict[str, HandAnalysis] = {}
        self._feedbacks: Dict[str, HandAnalysisFeedback] = {}
        
    async def save_analysis(self, analysis: HandAnalysis) -> None:
        await asyncio.sleep(0.01) # Simulate IO
        self._analyses[analysis.hand_id] = analysis
        print(f"[InMemory] Saved analysis for hand {analysis.hand_id} (ID: {analysis.id})")
        
    async def save_feedback(self, feedback: HandAnalysisFeedback) -> None:
        await asyncio.sleep(0.01) # Simulate IO
        self._feedbacks[feedback.id] = feedback
        print(f"[InMemory] Saved feedback {feedback.is_useful} for analysis {feedback.analysis_id}")
        
    async def get_analysis(self, hand_id: str) -> Optional[HandAnalysis]:
        await asyncio.sleep(0.01) # Simulate IO
        return self._analyses.get(hand_id)
