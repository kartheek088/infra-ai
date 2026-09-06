from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.core.deps import get_current_user
from app.core.utils import to_uuid
from app.models.user import User
from app.models.api_key import ApiKey
from app.schemas.api_key import ApiKeyCreate, ApiKeyResponse, ApiKeyListResponse

router = APIRouter(prefix="/api/keys", tags=["API Keys"])


@router.post("/generate", response_model=ApiKeyResponse, status_code=201)
async def generate_key(data: ApiKeyCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    new_key = ApiKey(user_id=current_user.id, key=ApiKey.generate_key(), name=data.name)
    db.add(new_key)
    await db.commit()
    await db.refresh(new_key)
    return new_key


@router.get("/", response_model=list[ApiKeyListResponse])
async def list_keys(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ApiKey).where(ApiKey.user_id == current_user.id).order_by(ApiKey.created_at.desc()))
    keys   = result.scalars().all()
    return [ApiKeyListResponse(id=k.id, name=k.name, key_preview=k.key[:16] + "...",
                               is_active=k.is_active, last_used_at=k.last_used_at,
                               created_at=k.created_at) for k in keys]


@router.delete("/{key_id}", status_code=204)
async def revoke_key(key_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    key_uuid = to_uuid(key_id)
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_uuid, ApiKey.user_id == current_user.id))
    key    = result.scalar_one_or_none()
    if not key:
        raise HTTPException(404, "API key not found")
    key.is_active = False
    await db.commit()
