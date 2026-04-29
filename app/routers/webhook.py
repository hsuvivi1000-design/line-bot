import base64
import hashlib
import hmac
import logging

from fastapi import APIRouter, HTTPException, Request
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from app.config import settings
from app.handlers.webhook_handler import handle_message

logger = logging.getLogger(__name__)

router = APIRouter()

# LINE SDK Webhook Handler（負責 Signature 驗證與事件派發）
_handler = WebhookHandler(settings.line_channel_secret)


@_handler.add(MessageEvent, message=TextMessageContent)
def on_text_message(event: MessageEvent) -> None:
    handle_message(event)


@router.post("/webhook", summary="LINE Webhook Endpoint")
async def webhook(request: Request) -> dict:
    """
    接收 LINE Platform 推送的事件。
    - 驗證 X-Line-Signature
    - 解析事件並分派至對應 Handler
    - 必須在 5 秒內回傳 HTTP 200
    """
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    body_str = body.decode("utf-8")

    # --- Signature 診斷 ---
    computed = base64.b64encode(
        hmac.new(settings.line_channel_secret.encode(), body, hashlib.sha256).digest()
    ).decode()
    # 寫到檔案，確認程式碼有執行
    with open("debug.log", "a") as f:
        f.write(f"body     : {body_str[:80]}\n")
        f.write(f"recv_sig : {signature}\n")
        f.write(f"calc_sig : {computed}\n")
        f.write(f"match    : {signature == computed}\n---\n")
    print(f"[Webhook] body     : {body_str[:80]}", flush=True)
    print(f"[Webhook] recv_sig : {signature}", flush=True)
    print(f"[Webhook] calc_sig : {computed}", flush=True)
    print(f"[Webhook] match    : {signature == computed}", flush=True)
    # ----------------------

    try:
        _handler.handle(body_str, signature)
    except InvalidSignatureError:
        logger.warning("[Webhook] Signature mismatch → 400")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error("[Webhook] Handler error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"status": "ok"}
