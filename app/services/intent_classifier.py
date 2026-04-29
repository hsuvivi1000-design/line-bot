import re
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.adapters import gemini_adapter

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    STOCK_QUERY = "STOCK_QUERY"
    CHAT = "CHAT"


@dataclass
class ClassificationResult:
    intent: Intent
    symbol: Optional[str] = None  # 僅 STOCK_QUERY 時有值


# --- Regex 規則 ---
# 台股：3~5 位純數字（不用 \b，因為 Python regex 把中文字當 \w 處理）
_TAIWAN_CODE = re.compile(r"(?<!\d)(\d{3,5})(?!\d)")
# 美股：1~5 位純英文大寫（整詞）
_US_CODE = re.compile(r"\b([A-Z]{1,5})\b")
# 中文關鍵字（擴充收盤價、今天、查詢等）
_KEYWORDS = re.compile(
    r"股價|股市|現價|漲跌|漲停|跌停|收盤|收盤價|開盤|成交量"
    r"|今天|明天|本周|本月"
    r"|查詢|報價|報給我|漲跌多少"
    r"|price|stock"
)

# 中文公司名稱（對照表中的 key）
_TW_NAMES = {
    "台積電", "鴻海", "聯發科", "台達電", "富邦金", "國泰金",
    "台塑", "南亞", "中鋼", "台塑化", "廣達", "大立光", "瑞昱",
    "統一", "中華電",
}
_US_NAMES = {
    "蘋果", "特斯拉", "谷歌", "微軟", "亞馬遜", "輝達", "臉書",
}

# ETF 中文名稱對照
_ETF_NAMES: dict[str, str] = {
    "元大台灣50": "0050", "台灣50": "0050",
    "元大高收益": "0056",
    "元大富櫃": "006208",
}

# 排除誤判
_EXCLUDE_NUMBERS = {"1234", "0000", "9999", "110", "119", "911"}


def classify(text: str) -> ClassificationResult:
    """
    兩段式意圖辨識：
    1. Regex 快速比對 → 命中即回傳 STOCK_QUERY
    2. 未命中 → 呼叫 Gemini 分類（備援）
    """
    stripped = text.strip()

    # --- Stage 1: Regex ---

    # ETF 中文名稱對照
    for name, code in _ETF_NAMES.items():
        if name in stripped:
            return ClassificationResult(intent=Intent.STOCK_QUERY, symbol=code)

    # 直接輸入中文公司名稱
    for name in _TW_NAMES | _US_NAMES:
        if name in stripped:
            return ClassificationResult(intent=Intent.STOCK_QUERY, symbol=name)

    # 含股價關鍵字 + 台股代號
    if _KEYWORDS.search(stripped):
        tw_match = _TAIWAN_CODE.search(stripped)
        if tw_match and tw_match.group(1) not in _EXCLUDE_NUMBERS:
            symbol = tw_match.group(1)
            return ClassificationResult(intent=Intent.STOCK_QUERY, symbol=symbol)

        us_match = _US_CODE.search(stripped.upper())
        if us_match:
            symbol = us_match.group(1)
            return ClassificationResult(intent=Intent.STOCK_QUERY, symbol=symbol)

    # 純台股代號輸入（3~5 碼數字，整段訊息）
    tw_full = re.fullmatch(r"\d{3,5}", stripped)
    if tw_full and stripped not in _EXCLUDE_NUMBERS:
        return ClassificationResult(intent=Intent.STOCK_QUERY, symbol=stripped)

    # 純美股代號輸入（1~5 位英文，整段訊息）
    if _US_CODE.fullmatch(stripped.upper()) and len(stripped) <= 5:
        logger.debug("Intent: STOCK_QUERY via pure US code '%s'", stripped.upper())
        return ClassificationResult(intent=Intent.STOCK_QUERY, symbol=stripped.upper())

    # --- Stage 2: Gemini 備援分類 ---
    logger.debug("No regex match, falling back to Gemini classification")
    symbol = gemini_adapter.classify_intent(stripped)
    if symbol:
        return ClassificationResult(intent=Intent.STOCK_QUERY, symbol=symbol)

    return ClassificationResult(intent=Intent.CHAT)
