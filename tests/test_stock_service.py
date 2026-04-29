from unittest.mock import patch, MagicMock
from datetime import datetime

from app.adapters.yfinance_adapter import resolve_symbol, get_quote
from app.models.stock_quote import StockQuote


def test_resolve_symbol_taiwan_number():
    assert resolve_symbol("2330") == "2330.TW"


def test_resolve_symbol_taiwan_etf():
    assert resolve_symbol("00878") == "00878.TW"


def test_resolve_symbol_us_ticker():
    assert resolve_symbol("AAPL") == "AAPL"


def test_resolve_symbol_chinese_tw():
    assert resolve_symbol("台積電") == "2330.TW"


def test_resolve_symbol_chinese_us():
    assert resolve_symbol("蘋果") == "AAPL"


def test_resolve_symbol_already_suffixed():
    assert resolve_symbol("2330.TW") == "2330.TW"


@patch("app.adapters.yfinance_adapter.yf.Ticker")
def test_get_quote_success(mock_ticker_cls):
    mock_ticker = MagicMock()
    mock_ticker.fast_info.last_price = 980.0
    mock_ticker.fast_info.previous_close = 965.0
    mock_ticker.info = {"shortName": "Taiwan Semiconductor"}
    mock_ticker_cls.return_value = mock_ticker

    quote = get_quote("2330")
    assert quote.symbol == "2330.TW"
    assert quote.price == 980.0
    assert quote.currency == "TWD"
    assert "Taiwan Semiconductor" in quote.name


@patch("app.adapters.yfinance_adapter.yf.Ticker")
def test_get_quote_no_data_raises(mock_ticker_cls):
    import pytest
    mock_ticker = MagicMock()
    mock_ticker.fast_info.last_price = None
    mock_ticker.fast_info.previous_close = None
    mock_ticker_cls.return_value = mock_ticker

    with pytest.raises(ValueError):
        get_quote("INVALID")
