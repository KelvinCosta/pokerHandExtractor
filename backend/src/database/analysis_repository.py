from typing import Optional
from datetime import datetime
from src.domain.ports import IAnalysisRepository
from src.domain.ai_models import HandAnalysis, HandAnalysisFeedback
from src.database.models import HandAnalysisRecord, get_session

class SQLiteAnalysisRepository(IAnalysisRepository):
    async def save_analysis(self, analysis: HandAnalysis) -> None:
        db = get_session()
        try:
            existing = db.query(HandAnalysisRecord).filter(HandAnalysisRecord.hand_id == analysis.hand_id).first()
            if existing:
                existing.raw_analysis = analysis.raw_analysis
                existing.agent_version = analysis.agent_version
                existing.created_at = datetime.utcnow()
            else:
                record = HandAnalysisRecord(
                    id=analysis.id,
                    hand_id=analysis.hand_id,
                    raw_analysis=analysis.raw_analysis,
                    agent_version=analysis.agent_version
                )
                db.add(record)
            db.commit()
        finally:
            db.close()

    async def save_feedback(self, feedback: HandAnalysisFeedback) -> None:
        # Feedback persistency not implemented for SQLite yet
        pass

    async def get_analysis(self, hand_id: str) -> Optional[HandAnalysis]:
        db = get_session()
        try:
            record = db.query(HandAnalysisRecord).filter(HandAnalysisRecord.hand_id == hand_id).first()
            if record:
                return HandAnalysis(
                    id=record.id,
                    hand_id=record.hand_id,
                    raw_analysis=record.raw_analysis,
                    agent_version=record.agent_version,
                    created_at=record.created_at
                )
            return None
        finally:
            db.close()
