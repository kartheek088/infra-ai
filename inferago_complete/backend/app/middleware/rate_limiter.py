import redis.asyncio as aioredis
from fastapi import Request, HTTPException
from app.core.config import settings

redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def rate_limit(request: Request, limit: int = 100, window: int = 3600):
    client_ip = request.client.host
    key       = f"rate_limit:{client_ip}"
    try:
        count = await redis_client.incr(key)
        if count == 1:
            await redis_client.expire(key, window)
        if count > limit:
            raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Max {limit} requests/hour.")
    except HTTPException:
        raise
    except Exception:
        pass
