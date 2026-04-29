import pytest
from app.services.intent_classifier import classify, Intent


@pytest.mark.parametrize("text, expected_intent, expected_symbol", [
    # 台股純代號
    ("2330", Intent.STOCK_QUERY, "2330"),
    ("00878", Intent.STOCK_QUERY, "00878"),
    # 中文名稱
    ("台積電股價", Intent.STOCK_QUERY, "台積電"),
    ("鴻海", Intent.STOCK_QUERY, "鴻海"),
    # 美股純代號
    ("AAPL", Intent.STOCK_QUERY, "AAPL"),
    ("TSLA", Intent.STOCK_QUERY, "TSLA"),
    # 關鍵字 + 代號
    ("2330 現在漲跌多少", Intent.STOCK_QUERY, "2330"),
    # 一般聊天（應為 CHAT，Gemini 備援可能仍辨識為 STOCK，視情況調整）
    ("你好", Intent.CHAT, None),
    ("今天天氣如何", Intent.CHAT, None),
])
def test_classify(text, expected_intent, expected_symbol):
    result = classify(text)
    assert result.intent == expected_intent
    if expected_symbol:
        assert result.symbol == expected_symbol
