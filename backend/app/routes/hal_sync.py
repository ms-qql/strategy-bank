from fastapi import APIRouter

from ..services.hal_sync import sync_all_drafts_to_hal

router = APIRouter(prefix="/hal", tags=["hal"])


@router.post("/sync-all")
def hal_sync_all() -> dict:
    return sync_all_drafts_to_hal()
