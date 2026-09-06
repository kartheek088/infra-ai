from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.core.security import verify_password
from app.core.utils import to_uuid


async def get_user_by_email(email: str, db: AsyncSession) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(user_id: str, db: AsyncSession) -> User | None:
    result = await db.execute(select(User).where(User.id == to_uuid(user_id)))
    return result.scalar_one_or_none()


async def authenticate_user(email: str, password: str, db: AsyncSession) -> User | None:
    user = await get_user_by_email(email, db)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user
