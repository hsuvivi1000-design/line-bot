import logging

from app.adapters import yfinance_adapter

logger = logging.getLogger(__name__)


def query(symbol_raw: str) -> str:
    """
    查詢股票報價並回傳格式化字串。

    Args:
        symbol_raw: 原始輸入（如 "2330"、"台積電"、"AAPL"）

    Returns:
        格式化的股價訊息字串
    """
    try:
        quote = yfinance_adapter.get_quote(symbol_raw)
        return quote.format_message()
    except ValueError as e:
        logger.warning("StockService query failed for '%s': %s", symbol_raw, e)
        return f"⚠️ 找不到「{symbol_raw}」的股票資訊，請確認代號是否正確。\n\n範例：台積電、2330、AAPL、TSLA"
    except Exception as e:
        logger.error("Unexpected error querying '%s': %s", symbol_raw, e)
        return "⚠️ 股價查詢服務暫時無法使用，請稍後再試。"
