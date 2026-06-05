from __future__ import annotations

import math
import os
from typing import Any

from utils.logger import get_logger


logger = get_logger(__name__)


class FxService:
    USD_THB_SYMBOL = "USDTHB=X"

    def get_usd_thb_rate(self) -> float | None:
        env_rate = self._rate_from_env()
        if env_rate is not None:
            logger.info("Using USD/THB rate from USD_THB_RATE env var.")
            return env_rate

        rate = self._rate_from_yfinance()
        if rate is not None:
            logger.info("Using live USD/THB rate from yfinance.")
            return rate

        logger.warning("USD/THB rate unavailable. THB P/L fields will show N/A.")
        return None

    @staticmethod
    def _rate_from_env() -> float | None:
        raw_rate = os.getenv("USD_THB_RATE", "").strip()
        if not raw_rate:
            return None

        try:
            rate = float(raw_rate)
        except ValueError as exc:
            raise ValueError("USD_THB_RATE must be a number, for example 36.50.") from exc

        if rate <= 0:
            raise ValueError("USD_THB_RATE must be greater than zero.")
        return rate

    def _rate_from_yfinance(self) -> float | None:
        try:
            import yfinance as yf
        except ImportError:
            logger.warning(
                "yfinance is not installed, so live USD/THB cannot be fetched."
            )
            return None

        try:
            ticker = yf.Ticker(self.USD_THB_SYMBOL)
            fast_info = self._safe_mapping(getattr(ticker, "fast_info", {}))
            history = ticker.history(period="5d", interval="1d", auto_adjust=False)
        except Exception as exc:
            logger.warning("Could not fetch live USD/THB rate: %s", exc)
            return None

        return self._first_number(
            fast_info.get("last_price"),
            fast_info.get("lastPrice"),
            self._history_value(history, -1, "Close"),
        )

    @staticmethod
    def _history_value(history: Any, row_index: int, column: str) -> float | None:
        try:
            if history is None or history.empty:
                return None
            value = history.iloc[row_index].get(column)
        except Exception:
            return None
        return FxService._to_number(value)

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
    def _first_number(*values: Any) -> float | None:
        for value in values:
            number = FxService._to_number(value)
            if number is not None:
                return number
        return None

    @staticmethod
    def _to_number(value: Any) -> float | None:
        if value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if math.isnan(number) or math.isinf(number) or number <= 0:
            return None
        return number
