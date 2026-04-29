import logging
from typing import Optional

from google import genai
from google.genai import types

from app.config import settings

logger = logging.getLogger(__name__)

# 初始化 Gemini 客戶端（新 SDK：google-genai）
_client = genai.Client(api_key=settings.gemini_api_key)

# Gemini 2.5 Flash 模型名稱
MODEL_NAME = "gemini-2.5-flash"

SYSTEM_PROMPT = """你是 Stock-Bot，一個友善、專業的投資助理 LINE Bot。

你的能力：
1. 回答使用者的一般問題與聊天
2. 解說股票、投資相關知識
3. 查詢使用者指定的股票即時股價（系統會自動處理查詢）

行為準則：
- 使用繁體中文回覆（除非使用者用其他語言）
- 保持友善、簡潔，避免過度冗長
- **直接回答問題，不要反問或要求確認**
- 不提供具體買賣建議，僅提供資訊參考
- 不確定的資訊請明確說明「我不確定」
- 回覆盡量控制在 200 字以內

重要：如果使用者問股票相關問題（如股價、漲跌、收盤），請直接說明系統會自動查詢，
不要說「我來幫您查詢」然後反問，直接給出有用的回應。
"""


def _build_history(history: list[dict]) -> list[types.Content]:
    """將儲存格式轉換為 google-genai Content 物件"""
    contents = []
    for item in history:
        role = item["role"]
        text = item["parts"][0]["text"] if item.get("parts") else ""
        contents.append(types.Content(
            role=role,
            parts=[types.Part(text=text)],
        ))
    return contents


def _serialize_history(contents: list[types.Content]) -> list[dict]:
    """將 google-genai Content 物件序列化為可儲存的 dict"""
    result = []
    for content in contents:
        result.append({
            "role": content.role,
            "parts": [{"text": part.text} for part in content.parts if hasattr(part, "text")],
        })
    return result


def chat(
    history: list[dict],
    user_message: str,
) -> tuple[str, list[dict]]:
    """
    送出單輪對話至 Gemini，回傳回覆文字與更新後的歷史。

    Args:
        history: 過去的對話歷史（dict 格式，{role, parts}）
        user_message: 使用者這輪的訊息

    Returns:
        (reply_text, updated_history)
    """
    # 組合完整對話內容：歷史 + 新訊息
    contents = _build_history(history)
    contents.append(types.Content(
        role="user",
        parts=[types.Part(text=user_message)],
    ))

    try:
        response = _client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
            ),
        )
        reply_text = response.text

        # 更新歷史：加入 model 回覆
        contents.append(types.Content(
            role="model",
            parts=[types.Part(text=reply_text)],
        ))

        updated_history = _serialize_history(contents)
        return reply_text, updated_history

    except Exception as e:
        logger.error("Gemini API error: %s", e)
        raise RuntimeError("AI 服務暫時無法使用，請稍後再試。")


def classify_intent(text: str) -> Optional[str]:
    """
    使用 Gemini 對模糊訊息進行意圖分類，回傳股票代號或 None。
    僅在 Regex 無法辨識時呼叫（備援機制）。

    Returns:
        股票代號字串（如 "AAPL"、"2330"）或 None（非股票查詢）
    """
    prompt = f"""你是一個意圖分類器。請分析以下訊息，判斷使用者是否想查詢某支股票的股價。

訊息：「{text}」

若是股票查詢，請只回覆股票代號（如 AAPL 或 2330），不要加任何說明。
若不是股票查詢，請只回覆「NONE」。"""

    try:
        response = _client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )
        result = response.text.strip().upper()
        if result == "NONE" or not result:
            return None
        if len(result) <= 10:
            return result
        return None
    except Exception as e:
        logger.warning("Gemini intent classification failed: %s", e)
        return None
