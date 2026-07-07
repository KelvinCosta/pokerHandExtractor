from abc import ABC, abstractmethod
from typing import Optional
from src.domain.models import HandContext
from src.domain.ai_models import HandAnalysis, HandAnalysisFeedback

class IHandAnalyzer(ABC):
    @abstractmethod
    async def analyze(self, hand: HandContext) -> HandAnalysis:
        """
        Analyzes a poker hand and returns a raw analysis.
        This method will invoke the underlying AI API.
        Note: The returned HandAnalysis should not have an ID yet, as the Use Case will assign it.
        Or, depending on design, the Adapter could assign it. 
        We will let the Use Case assign the UUID.
        """
        pass

class IAnalysisRepository(ABC):
    @abstractmethod
    async def save_analysis(self, analysis: HandAnalysis) -> None:
        """Saves a new HandAnalysis record."""
        pass
        
    @abstractmethod
    async def save_feedback(self, feedback: HandAnalysisFeedback) -> None:
        """Saves a new HandAnalysisFeedback record."""
        pass
        
    @abstractmethod
    async def get_analysis(self, hand_id: str) -> Optional[HandAnalysis]:
        """Retrieves the latest analysis for a given hand."""
        pass
