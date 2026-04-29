import logging

from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from app.config import settings
from app.services import gemini_service, intent_classifier, stock_service

logger = logging.getLogger(__name__)

# LINE Messaging API 客戶端設定
_line_config = Configuration(access_token=settings.line_channel_access_token)


def handle_message(event: MessageEvent) -> None:
    """
    處理 LINE 文字訊息事件。

    流程：
    1. 取出 userId 與訊息文字
    2. 意圖辨識（Regex → Gemini 備援）
    3. 依意圖呼叫對應 Service
    4. 透過 LINE Reply API 回覆
    """
    if not isinstance(event.message, TextMessageContent):
        return

    user_id: str = event.source.user_id
    text: str = event.message.text.strip()
    reply_token: str = event.reply_token

    logger.info("Message from user=%s... text='%s'", user_id[:6], text[:50])

    # --- 意圖辨識 ---
    result = intent_classifier.classify(text)
    logger.info("Intent: %s, symbol: %s", result.intent, result.symbol)

    # --- 處理 ---
    if result.intent == intent_classifier.Intent.STOCK_QUERY and result.symbol:
        reply_text = stock_service.query(result.symbol)
    else:
        try:
            reply_text = gemini_service.chat(user_id, text)
        except RuntimeError as e:
            reply_text = str(e)

    # --- 回覆 ---
    _reply(reply_token, reply_text)


def _reply(reply_token: str, text: str) -> None:
    """透過 LINE Reply API 送出文字回覆"""
    try:
        with ApiClient(_line_config) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=text)],
                )
            )
    except Exception as e:
        # 寫入檔案方便除錯
        with open("debug.log", "a", encoding="utf-8") as f:
            f.write(f"REPLY ERROR: {e}\n")
        logger.error("Reply error: %s", e)
        raise

