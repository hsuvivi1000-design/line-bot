from dataclasses import dataclass
from datetime import datetime


@dataclass
class StockQuote:
    symbol: str          # 股票代號，如 "2330.TW"
    name: str            # 股票名稱，如 "Taiwan Semiconductor Manufacturing"
    price: float         # 現價
    change: float        # 漲跌金額
    change_pct: float    # 漲跌百分比
    timestamp: datetime  # 資料時間
    currency: str = "USD"

    def format_message(self) -> str:
        """格式化為 LINE 回覆訊息"""
        arrow = "📈" if self.change >= 0 else "📉"
        sign = "+" if self.change >= 0 else ""
        currency_symbol = "NT$" if self.currency == "TWD" else "$"

        return (
            f"{arrow} {self.name} ({self.symbol})\n"
            f"現價：{currency_symbol}{self.price:,.2f}\n"
            f"漲跌：{sign}{self.change:,.2f} ({sign}{self.change_pct:.2f}%)\n"
            f"更新時間：{self.timestamp.strftime('%Y-%m-%d %H:%M')} (TST)"
        )
