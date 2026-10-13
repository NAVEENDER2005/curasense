from fastapi import APIRouter, Depends

from app.analytics import compute_summary
from app.dependencies import get_pool

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def summary(pool=Depends(get_pool)):
    return await compute_summary(pool)
