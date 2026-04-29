import logging
from datetime import datetime

import yfinance as yf

from app.models.stock_quote import StockQuote

logger = logging.getLogger(__name__)

# 台股常用中文名稱 → 代號對照表
TAIWAN_NAME_MAP: dict[str, str] = {
    "台積電": "2330",
    "鴻海": "2317",
    "聯發科": "2454",
    "台達電": "2308",
    "富邦金": "2881",
    "國泰金": "2882",
    "台塑": "1301",
    "南亞": "1303",
    "中鋼": "2002",
    "台塑化": "6505",
    "廣達": "2382",
    "大立光": "3008",
    "瑞昱": "2379",
    "信義房屋": "9940",
    "統一": "1216",
    "中華電": "2412",
}

# 美股常用中文名稱 → 代號對照表
US_NAME_MAP: dict[str, str] = {
    "蘋果": "AAPL",
    "特斯拉": "TSLA",
    "谷歌": "GOOGL",
    "微軟": "MSFT",
    "亞馬遜": "AMZN",
    "輝達": "NVDA",
    "nvidia": "NVDA",
    "meta": "META",
    "臉書": "META",
    "netflix": "NFLX",
}


def resolve_symbol(raw: str) -> str:
    """
    將原始輸入解析為 yfinance 可識別的代號。
    - 4~5 位純數字 → 台股，補 .TW 後綴
    - 中文名稱 → 查對照表
    - 英文字母 → 直接當作美股代號（大寫）
    """
    raw = raw.strip()

    # 中文名稱對照
    if raw in TAIWAN_NAME_MAP:
        return TAIWAN_NAME_MAP[raw] + ".TW"
    if raw.lower() in US_NAME_MAP:
        return US_NAME_MAP[raw.lower()]

    # 台股數字代號（4~5 碼）
    if raw.isdigit() and 4 <= len(raw) <= 5:
        return raw + ".TW"

    # 已帶後綴（.TW / .TWO）
    if raw.upper().endswith((".TW", ".TWO")):
        return raw.upper()

    # 美股英文代號
    return raw.upper()


def get_quote(symbol_raw: str) -> StockQuote:
    """
    查詢股票即時報價。
    Args:
        symbol_raw: 原始使用者輸入（如 "2330"、"AAPL"、"台積電"）
    Returns:
        StockQuote 物件
    Raises:
        ValueError: 找不到該股票或資料不完整
    """
    symbol = resolve_symbol(symbol_raw)
    logger.info("Fetching quote for symbol: %s (raw: %s)", symbol, symbol_raw)

    try:
        ticker = yf.Ticker(symbol)
        fast = ticker.fast_info

        price = fast.last_price
        prev_close = fast.previous_close

        if price is None or prev_close is None:
            raise ValueError(f"No data available for {symbol}")

        change = price - prev_close
        change_pct = (change / prev_close) * 100

        # 幣別判斷：台股為 TWD，其餘預設 USD
        currency = "TWD" if symbol.endswith((".TW", ".TWO")) else "USD"

        # 股票名稱
        name = getattr(fast, "quote_type", None) or symbol
        try:
            info = ticker.info
            name = info.get("shortName") or info.get("longName") or symbol
        except Exception:
            name = symbol

        return StockQuote(
            symbol=symbol,
            name=name,
            price=round(price, 2),
            change=round(change, 2),
            change_pct=round(change_pct, 2),
            timestamp=datetime.now(),
            currency=currency,
        )

    except ValueError:
        raise
    except Exception as e:
        logger.error("yfinance error for %s: %s", symbol, e)
        raise ValueError(f"無法取得 {symbol} 的股價資訊，請確認代號是否正確。")
