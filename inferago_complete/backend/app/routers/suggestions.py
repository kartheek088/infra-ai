from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.suggestions import generate_suggestions

router = APIRouter(prefix="/api/suggestions", tags=["Suggestions"])


@router.get("/{workflow_id}")
async def get_suggestions(workflow_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    suggestions = await generate_suggestions(workflow_id, db)
    return [{"type": s.type, "impact": s.impact, "title": s.title,
             "description": s.description, "estimated_saving": s.estimated_saving,
             "action": s.action} for s in suggestions]
