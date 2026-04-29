from datetime import datetime

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", summary="Health Check")
async def health() -> dict:
    """服務健康檢查，供部署平台（Render / UptimeRobot）監控用。"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": "stock-bot",
    }
