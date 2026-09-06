from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.core.deps import get_current_user
from app.core.utils import to_uuid
from app.models.user import User
from app.models.alert import Alert
from app.schemas.alert import AlertCreate, AlertUpdate, AlertResponse

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


@router.post("/", response_model=AlertResponse, status_code=201)
async def create_alert(data: AlertCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    alert = Alert(user_id=current_user.id, **data.model_dump())
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


@router.get("/{workflow_id}", response_model=list[AlertResponse])
async def list_alerts(workflow_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    wf_uuid = to_uuid(workflow_id)
    result = await db.execute(
        select(Alert).where(Alert.workflow_id == wf_uuid, Alert.user_id == current_user.id)
    )
    return result.scalars().all()


@router.patch("/{alert_id}", response_model=AlertResponse)
async def update_alert(alert_id: str, data: AlertUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    alert_uuid = to_uuid(alert_id)
    result = await db.execute(select(Alert).where(Alert.id == alert_uuid, Alert.user_id == current_user.id))
    alert  = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "Alert not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(alert, field, value)
    await db.commit()
    await db.refresh(alert)
    return alert


@router.delete("/{alert_id}", status_code=204)
async def delete_alert(alert_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    alert_uuid = to_uuid(alert_id)
    result = await db.execute(select(Alert).where(Alert.id == alert_uuid, Alert.user_id == current_user.id))
    alert  = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "Alert not found")
    await db.delete(alert)
    await db.commit()
