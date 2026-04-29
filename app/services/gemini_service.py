import logging
from collections import defaultdict

from app.adapters import gemini_adapter
from app.config import settings

logger = logging.getLogger(__name__)

# 記憶體內 session store: userId → 對話歷史（Gemini Content 格式）
_session_store: dict[str, list[dict]] = defaultdict(list)


def chat(user_id: str, text: str) -> str:
    """
    執行多輪 AI 對話。

    Args:
        user_id: LINE 使用者 ID（用於隔離 session）
        text: 使用者訊息

    Returns:
        Gemini 回覆文字
    """
    history = _session_store[user_id]

    reply, updated_history = gemini_adapter.chat(history, text)

    # 控制歷史長度（每輪 = user + model 各 1 條，故 * 2）
    max_items = settings.session_max_history * 2
    _session_store[user_id] = updated_history[-max_items:]

    logger.info(
        "GeminiService: user=%s... history_len=%d",
        user_id[:6],
        len(_session_store[user_id]),
    )
    return reply


def clear_session(user_id: str) -> None:
    """清除指定使用者的對話歷史"""
    _session_store.pop(user_id, None)
    logger.info("Session cleared for user=%s...", user_id[:6])
