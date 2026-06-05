from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from services.portfolio_service import PortfolioAnalysis
from services.stock_service import StockQuote
from utils.formatter import (
    format_change,
    format_percent,
    format_price,
    format_shares,
    format_supports,
    format_thb,
)


class ReportService:
    def __init__(self, timezone_name: str = "Asia/Bangkok") -> None:
        self.timezone_name = timezone_name
        self.timezone = self._resolve_timezone(timezone_name)

    def build_daily_report(
        self,
        analyses: list[PortfolioAnalysis],
        market_quotes: dict[str, StockQuote],
    ) -> str:
        now = datetime.now(self.timezone)
        lines: list[str] = [
            "Daily Stock Watchlist",
            f"Date: {now:%Y-%m-%d}",
            f"Time: {now:%H:%M} {self._timezone_label(now)}",
            "",
            "Market Summary:",
            f"QQQ / Tech sentiment: {self._sentiment(market_quotes.get('QQQ'))}",
            f"Semiconductor sentiment: {self._sentiment(market_quotes.get('SMH'))}",
            f"Cash strategy: {self._cash_strategy(analyses)}",
            "",
            "--------------------",
        ]

        for analysis in analyses:
            lines.extend(self._stock_block(analysis))
            lines.append("--------------------")

        lines.extend(self._portfolio_view(analyses))
        return "\n".join(lines).strip()

    def build_failure_report(self, reason: str) -> str:
        now = datetime.now(self.timezone)
        return "\n".join(
            [
                "Daily Stock Watchlist",
                f"Date: {now:%Y-%m-%d}",
                f"Time: {now:%H:%M} {self._timezone_label(now)}",
                "",
                "Report failed.",
                reason,
                "Check logs, yfinance availability, and network access.",
            ]
        )

    def _stock_block(self, analysis: PortfolioAnalysis) -> list[str]:
        quote = analysis.quote
        if not quote.data_available:
            return [
                f"{analysis.ticker}: Data Unavailable",
                "Status: Data Unavailable",
                f"Action: {analysis.action}",
                f"Note: {analysis.note or 'N/A'}",
            ]

        lines = [
            (
                f"{analysis.ticker}: {format_price(quote.price)} "
                f"({format_percent(quote.change_percent, signed=True)} / {format_change(quote.change)})"
            ),
            (
                f"Prev: {format_price(quote.previous_close)} | "
                f"Range: {format_price(quote.day_low)}-{format_price(quote.day_high)} | "
                f"Mkt: {quote.market_state or 'N/A'}"
            ),
            (
                f"Avg Cost: {format_price(analysis.avg_cost)} | "
                f"Shares: {format_shares(analysis.estimated_shares)} est"
            ),
            f"P/L: {self._pnl_line(analysis)} | Position: {format_thb(analysis.position_thb)}",
            f"Support: {format_supports(analysis.support_levels)}",
            f"Nearest: {self._nearest_support_line(analysis)}",
        ]

        extended = self._extended_hours_line(quote)
        if extended:
            lines.append(extended)

        lines.extend(
            [
                f"Status: {analysis.status}",
                f"Action: {analysis.action}",
                f"Note: {analysis.note or 'N/A'}",
            ]
        )
        return lines

    @staticmethod
    def _pnl_line(analysis: PortfolioAnalysis) -> str:
        parts = [
            format_percent(analysis.pnl_percent, signed=True),
            format_price(analysis.pnl_usd, signed=True),
            format_thb(analysis.pnl_thb, signed=True),
        ]
        available = [part for part in parts if part != "N/A"]
        return " / ".join(available) if available else "N/A"

    @staticmethod
    def _nearest_support_line(analysis: PortfolioAnalysis) -> str:
        if analysis.nearest_support is None:
            return "N/A"
        distance = format_percent(analysis.support_distance_percent, signed=True)
        return f"{format_price(analysis.nearest_support)} ({distance}, {analysis.support_state})"

    @staticmethod
    def _extended_hours_line(quote: StockQuote) -> str | None:
        parts: list[str] = []
        if quote.pre_market_price is not None:
            parts.append(f"Pre-market {format_price(quote.pre_market_price)}")
        if quote.after_hours_price is not None:
            parts.append(f"After-hours {format_price(quote.after_hours_price)}")
        if not parts:
            return None
        return "Extended: " + " / ".join(parts)

    @staticmethod
    def _sentiment(quote: StockQuote | None) -> str:
        if quote is None or quote.change_percent is None:
            return "Unavailable"
        if quote.change_percent >= 1:
            return "Strong"
        if quote.change_percent >= 0:
            return "Stable"
        if quote.change_percent > -1:
            return "Soft"
        if quote.change_percent > -3:
            return "Weak"
        return "Under pressure"

    @staticmethod
    def _cash_strategy(analyses: list[PortfolioAnalysis]) -> str:
        statuses = {item.status for item in analyses}
        if "Deep Sell-off" in statuses or "Breakdown Risk" in statuses:
            return "Do not use all cash in one day."
        if "Near Support" in statuses or "Watch" in statuses:
            return "Scale in slowly and keep cash for deeper support."
        return "Hold cash for planned support zones."

    @staticmethod
    def _portfolio_view(analyses: list[PortfolioAnalysis]) -> list[str]:
        lines = ["Portfolio View:"]
        if any(item.status in {"Deep Sell-off", "Breakdown Risk"} for item in analyses):
            lines.append("- Some positions are under pressure; avoid adding too frequently.")
        if any(item.ticker in {"MU", "NVDA", "ANET"} for item in analyses):
            lines.append("- AI and semiconductor stocks can be volatile.")

        ticker_notes = 0
        for item in analyses:
            if ticker_notes >= 4:
                break
            if item.status == "Deep Sell-off":
                lines.append(f"- {item.ticker} is in heavy sell-off mode; avoid panic decisions.")
                ticker_notes += 1
            elif item.status == "Breakdown Risk":
                lines.append(f"- {item.ticker} broke below a nearby support zone; wait for confirmation.")
                ticker_notes += 1
            elif item.status == "Near Support":
                lines.append(f"- {item.ticker} is close to support; watch before scaling in.")
                ticker_notes += 1

        lines.append("- Keep some cash for deeper support zones.")
        return lines

    @staticmethod
    def _resolve_timezone(timezone_name: str) -> ZoneInfo:
        try:
            return ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            return ZoneInfo("Asia/Bangkok")

    @staticmethod
    def _timezone_label(now: datetime) -> str:
        if getattr(now.tzinfo, "key", "") == "Asia/Bangkok":
            return "ICT"
        return now.tzname() or "ICT"
