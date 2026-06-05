from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from services.stock_service import StockQuote


@dataclass(slots=True)
class PortfolioAnalysis:
    ticker: str
    quote: StockQuote
    support_levels: list[float]
    avg_cost: float | None
    position_thb: float | None
    priority: str
    note: str
    estimated_shares: float | None
    pnl_percent: float | None
    pnl_usd: float | None
    pnl_thb: float | None
    nearest_support: float | None
    support_distance_percent: float | None
    support_state: str
    status: str
    action: str


class PortfolioService:
    def __init__(self, usd_thb_rate: float | None) -> None:
        self.usd_thb_rate = usd_thb_rate

    def analyze_watchlist(
        self,
        watchlist: dict[str, dict[str, Any]],
        quotes: dict[str, StockQuote],
    ) -> list[PortfolioAnalysis]:
        analyses: list[PortfolioAnalysis] = []
        for ticker, settings in watchlist.items():
            quote = quotes.get(ticker, StockQuote(ticker=ticker, error="Quote missing."))
            analyses.append(self.analyze_position(ticker, settings, quote))
        return analyses

    def analyze_position(
        self,
        ticker: str,
        settings: dict[str, Any],
        quote: StockQuote,
    ) -> PortfolioAnalysis:
        support_levels = self._number_list(settings.get("support", []))
        avg_cost = self._positive_or_none(settings.get("avg_cost"))
        position_thb = self._positive_or_none(settings.get("position_thb"))
        priority = str(settings.get("priority", "medium")).strip().lower() or "medium"
        note = str(settings.get("note", "")).strip()

        shares = self._estimate_shares(position_thb, avg_cost)
        pnl_percent = None
        pnl_usd = None
        pnl_thb = None

        if quote.price is not None and avg_cost:
            pnl_percent = ((quote.price - avg_cost) / avg_cost) * 100
            if shares is not None:
                pnl_usd = shares * (quote.price - avg_cost)
                if self.usd_thb_rate:
                    pnl_thb = pnl_usd * self.usd_thb_rate

        nearest_support = self._nearest_support(quote.price, support_levels)
        support_distance_percent = None
        support_state = "unavailable"
        if quote.price is not None and nearest_support:
            support_distance_percent = ((quote.price - nearest_support) / nearest_support) * 100
            support_state = self._support_state(support_distance_percent)

        status = self._status(quote, support_distance_percent)
        action = self._action(status, nearest_support)

        return PortfolioAnalysis(
            ticker=ticker,
            quote=quote,
            support_levels=support_levels,
            avg_cost=avg_cost,
            position_thb=position_thb,
            priority=priority,
            note=note,
            estimated_shares=shares,
            pnl_percent=pnl_percent,
            pnl_usd=pnl_usd,
            pnl_thb=pnl_thb,
            nearest_support=nearest_support,
            support_distance_percent=support_distance_percent,
            support_state=support_state,
            status=status,
            action=action,
        )

    def _estimate_shares(
        self,
        position_thb: float | None,
        avg_cost: float | None,
    ) -> float | None:
        if not position_thb or not avg_cost or not self.usd_thb_rate:
            return None
        return (position_thb / self.usd_thb_rate) / avg_cost

    @staticmethod
    def _nearest_support(price: float | None, support_levels: list[float]) -> float | None:
        if price is None or not support_levels:
            return None
        return min(support_levels, key=lambda level: abs(price - level))

    @staticmethod
    def _support_state(distance_percent: float) -> str:
        if distance_percent >= 2:
            return "above support"
        if distance_percent >= 0:
            return "near support"
        return "below support"

    @staticmethod
    def _status(quote: StockQuote, support_distance_percent: float | None) -> str:
        if not quote.data_available:
            return "Data Unavailable"
        if quote.change_percent is not None and quote.change_percent <= -7:
            return "Deep Sell-off"
        if support_distance_percent is not None:
            if support_distance_percent < -2:
                return "Breakdown Risk"
            if 0 <= support_distance_percent <= 2:
                return "Near Support"
            if support_distance_percent < 0:
                return "Watch"
        if quote.change_percent is not None and quote.change_percent > 0:
            return "Strong"
        return "Normal"

    @staticmethod
    def _action(status: str, nearest_support: float | None) -> str:
        if status == "Data Unavailable":
            return "Check the data source before making decisions."
        if status == "Deep Sell-off":
            return "High volatility today. Avoid panic selling and do not average down too quickly."
        if status == "Breakdown Risk":
            return "Do not average down too quickly. Keep cash for deeper support."
        if status == "Near Support":
            if nearest_support:
                return f"Near support, wait for confirmation around ${nearest_support:.2f}."
            return "Near support, wait for confirmation."
        if status == "Watch":
            return "Watch for scale-in, but wait for confirmation."
        if status == "Strong":
            return "Hold / no need to chase."
        return "Hold / no need to chase. Keep cash for planned support zones."

    @staticmethod
    def _number_list(values: Any) -> list[float]:
        if not isinstance(values, list):
            return []
        numbers: list[float] = []
        for value in values:
            number = PortfolioService._to_number(value)
            if number is not None:
                numbers.append(number)
        return numbers

    @staticmethod
    def _positive_or_none(value: Any) -> float | None:
        number = PortfolioService._to_number(value)
        if number is None or number <= 0:
            return None
        return number

    @staticmethod
    def _to_number(value: Any) -> float | None:
        if value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if math.isnan(number) or math.isinf(number):
            return None
        return number
