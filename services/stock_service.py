from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable

from utils.logger import get_logger


logger = get_logger(__name__)


@dataclass(slots=True)
class StockQuote:
    ticker: str
    price: float | None = None
    previous_close: float | None = None
    change: float | None = None
    change_percent: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    market_state: str | None = None
    pre_market_price: float | None = None
    after_hours_price: float | None = None
    currency: str = "USD"
    error: str | None = None

    @property
    def data_available(self) -> bool:
        return self.price is not None


class StockService:
    """Fetches quote data through a provider that can be replaced later."""

    def __init__(self, provider: str = "yfinance") -> None:
        if provider != "yfinance":
            raise ValueError("Only the yfinance provider is implemented in v1.")
        self.provider = provider
        self._yf: Any | None = None
        self._provider_error: str | None = None
        self._provider_error_logged = False
        try:
            self._yf = self._load_yfinance()
        except RuntimeError as exc:
            self._provider_error = str(exc)

    def fetch_many(self, tickers: Iterable[str]) -> dict[str, StockQuote]:
        symbols = [str(ticker).upper() for ticker in tickers]
        if self._provider_error:
            if not self._provider_error_logged:
                logger.error(self._provider_error)
                self._provider_error_logged = True
            return {
                symbol: StockQuote(ticker=symbol, error=self._provider_error)
                for symbol in symbols
            }

        quotes: dict[str, StockQuote] = {}
        for symbol in symbols:
            quotes[symbol] = self.fetch_quote(symbol)
        return quotes

    def fetch_quote(self, ticker: str) -> StockQuote:
        try:
            return self._fetch_yfinance_quote(ticker)
        except Exception as exc:
            logger.exception("Failed to fetch data for %s", ticker)
            return StockQuote(ticker=ticker, error=str(exc))

    def _fetch_yfinance_quote(self, ticker: str) -> StockQuote:
        yf = self._yf or self._load_yfinance()
        ticker_obj = yf.Ticker(ticker)

        fast_info = self._safe_mapping(getattr(ticker_obj, "fast_info", {}))
        history = self._get_history(ticker_obj)
        info = self._get_info(ticker_obj)

        hist_latest = self._history_value(history, -1, "Close")
        hist_prev = self._history_value(history, -2, "Close")
        hist_high = self._history_value(history, -1, "High")
        hist_low = self._history_value(history, -1, "Low")

        price = self._first_number(
            fast_info.get("last_price"),
            info.get("currentPrice"),
            info.get("regularMarketPrice"),
            info.get("postMarketPrice"),
            info.get("preMarketPrice"),
            hist_latest,
        )
        previous_close = self._first_number(
            fast_info.get("previous_close"),
            info.get("regularMarketPreviousClose"),
            info.get("previousClose"),
            hist_prev,
        )
        day_high = self._first_number(
            fast_info.get("day_high"),
            info.get("regularMarketDayHigh"),
            info.get("dayHigh"),
            hist_high,
            price,
        )
        day_low = self._first_number(
            fast_info.get("day_low"),
            info.get("regularMarketDayLow"),
            info.get("dayLow"),
            hist_low,
            price,
        )

        change = None
        change_percent = None
        if price is not None and previous_close not in (None, 0):
            change = price - previous_close
            change_percent = (change / previous_close) * 100

        error = None if price is not None else "Latest price unavailable from yfinance."

        return StockQuote(
            ticker=ticker,
            price=price,
            previous_close=previous_close,
            change=change,
            change_percent=change_percent,
            day_high=day_high,
            day_low=day_low,
            market_state=self._first_text(info.get("marketState"), info.get("quoteType")),
            pre_market_price=self._first_number(info.get("preMarketPrice")),
            after_hours_price=self._first_number(info.get("postMarketPrice")),
            currency=self._first_text(info.get("currency"), fast_info.get("currency")) or "USD",
            error=error,
        )

    @staticmethod
    def _load_yfinance() -> Any:
        try:
            import yfinance as yf
        except ImportError as exc:
            raise RuntimeError(
                "yfinance is not installed. Run: pip install -r requirements.txt"
            ) from exc
        return yf

    @staticmethod
    def _get_history(ticker_obj: Any) -> Any:
        try:
            return ticker_obj.history(period="5d", interval="1d", auto_adjust=False)
        except Exception as exc:
            logger.warning("Could not fetch daily history: %s", exc)
            return None

    @staticmethod
    def _get_info(ticker_obj: Any) -> dict[str, Any]:
        try:
            if hasattr(ticker_obj, "get_info"):
                data = ticker_obj.get_info()
            else:
                data = getattr(ticker_obj, "info", {})
        except Exception as exc:
            logger.warning("Could not fetch extended quote info: %s", exc)
            return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _safe_mapping(value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        try:
            return dict(value)
        except Exception:
            return {}

    @staticmethod
    def _history_value(history: Any, row_index: int, column: str) -> float | None:
        try:
            if history is None or history.empty:
                return None
            if len(history) < abs(row_index):
                return None
            value = history.iloc[row_index].get(column)
        except Exception:
            return None
        return StockService._to_number(value)

    @staticmethod
    def _first_number(*values: Any) -> float | None:
        for value in values:
            number = StockService._to_number(value)
            if number is not None:
                return number
        return None

    @staticmethod
    def _first_text(*values: Any) -> str | None:
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return None

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
