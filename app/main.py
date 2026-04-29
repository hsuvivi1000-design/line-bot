import logging
import logging.config

from fastapi import FastAPI

from app.routers import health, webhook
from app.config import settings

logger = logging.getLogger(__name__)

# --- 日誌設定 ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# --- FastAPI 應用 ---
app = FastAPI(
    title="Stock-Bot",
    description="LINE Bot powered by Gemini 2.5 Flash with real-time stock price lookup",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)

# --- 路由掛載 ---
app.include_router(health.router, tags=["Health"])
app.include_router(webhook.router, tags=["LINE Webhook"])


@app.on_event("startup")
async def on_startup():
    secret_preview = settings.line_channel_secret[:6] if settings.line_channel_secret else "EMPTY"
    logger.info("=== Stock-Bot Started ===")
    logger.info("LINE_CHANNEL_SECRET: %s... (len=%d)", secret_preview, len(settings.line_channel_secret))