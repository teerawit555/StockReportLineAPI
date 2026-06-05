from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args: object, **_kwargs: object) -> bool:
        return False

from services.line_service import LineService
from services.fx_service import FxService
from services.portfolio_service import PortfolioService
from services.report_service import ReportService
from services.stock_service import StockQuote, StockService
from utils.logger import get_logger, setup_logging


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = ROOT_DIR / "config" / "watchlist.json"
MARKET_TICKERS = ("QQQ", "SMH")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send a daily US stock watchlist report to LINE."
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to watchlist JSON config.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the report instead of sending it to LINE.",
    )
    parser.add_argument(
        "--test-line",
        action="store_true",
        help="Send a small LINE test message and exit.",
    )
    parser.add_argument(
        "--mock-data",
        action="store_true",
        help="Use local sample quotes for offline dry-run verification.",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        help="Logging level: DEBUG, INFO, WARNING, ERROR.",
    )
    return parser.parse_args()


def load_watchlist(config_path: str | Path) -> dict[str, dict[str, Any]]:
    path = Path(config_path)
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict) or not data:
        raise ValueError("Watchlist config must be a non-empty JSON object.")

    normalized: dict[str, dict[str, Any]] = {}
    for ticker, settings in data.items():
        if not isinstance(settings, dict):
            raise ValueError(f"Watchlist settings for {ticker} must be an object.")
        normalized[str(ticker).upper()] = settings
    return normalized


def send_or_print(
    report: str,
    dry_run: bool,
    logger_name: str = __name__,
    label: str = "report",
) -> bool:
    logger = get_logger(logger_name)
    if dry_run:
        print(f"[DRY RUN] LINE sending is disabled. Generated {label} follows.")
        print("=" * 60)
        print(report)
        print("=" * 60)
        print(f"[DRY RUN] {label.capitalize()} length: {len(report):,} characters.")
        return True

    try:
        line_service = LineService.from_env()
        sent = line_service.push_message(report)
    except ValueError as exc:
        logger.error("Unable to send LINE %s: %s", label, exc)
        print(f"{label.capitalize()} send failed: {exc}")
        return False
    except Exception:
        logger.exception("Unable to send LINE %s.", label)
        print(f"{label.capitalize()} send failed. Check LINE environment variables and logs.")
        return False

    if sent:
        logger.info("LINE %s sent successfully.", label)
        print(f"LINE {label} sent successfully.")
    else:
        print(f"LINE {label} send failed. Check logs for details.")
    return sent


def build_mock_quotes() -> tuple[dict[str, StockQuote], dict[str, StockQuote]]:
    quotes = {
        "MU": StockQuote(
            ticker="MU",
            price=902,
            previous_close=986,
            change=-84,
            change_percent=-8.5,
            day_low=900,
            day_high=960,
            market_state="CLOSED",
        ),
        "NVDA": StockQuote(
            ticker="NVDA",
            price=208.10,
            previous_close=218.57,
            change=-10.47,
            change_percent=-4.8,
            day_low=205,
            day_high=214,
            market_state="CLOSED",
        ),
        "GOOGL": StockQuote(
            ticker="GOOGL",
            price=369.50,
            previous_close=367.66,
            change=1.84,
            change_percent=0.5,
            day_low=364,
            day_high=371,
            market_state="CLOSED",
        ),
        "RKLB": StockQuote(
            ticker="RKLB",
            price=104.25,
            previous_close=106.20,
            change=-1.95,
            change_percent=-1.8,
            day_low=103.80,
            day_high=107.10,
            market_state="CLOSED",
        ),
        "ANET": StockQuote(
            ticker="ANET",
            price=154.25,
            previous_close=153.25,
            change=1.00,
            change_percent=0.7,
            day_low=151.30,
            day_high=155.10,
            market_state="CLOSED",
        ),
        "AAPL": StockQuote(
            ticker="AAPL",
            price=188.00,
            previous_close=191.20,
            change=-3.20,
            change_percent=-1.7,
            day_low=187.50,
            day_high=190.90,
            market_state="CLOSED",
        ),
        "VOO": StockQuote(
            ticker="VOO",
            price=552.00,
            previous_close=550.25,
            change=1.75,
            change_percent=0.3,
            day_low=548.80,
            day_high=553.40,
            market_state="CLOSED",
        ),
    }
    market_quotes = {
        "QQQ": StockQuote(
            ticker="QQQ",
            price=510,
            previous_close=520,
            change=-10,
            change_percent=-1.9,
        ),
        "SMH": StockQuote(
            ticker="SMH",
            price=245,
            previous_close=253,
            change=-8,
            change_percent=-3.2,
        ),
    }
    return quotes, market_quotes


def main() -> int:
    load_dotenv(ROOT_DIR / ".env")
    args = parse_args()
    setup_logging(args.log_level)
    logger = get_logger(__name__)

    timezone_name = os.getenv("TIMEZONE", "Asia/Bangkok").strip() or "Asia/Bangkok"

    if args.mock_data and not args.dry_run:
        print("--mock-data is only allowed with --dry-run so fake data is never sent to LINE.")
        return 1

    if args.test_line:
        logger.info("Running LINE test mode. Stock data will not be fetched.")
        message = "LINE stock report bot test message. Stock data was not fetched."
        if send_or_print(message, args.dry_run, label="test message"):
            return 0
        return 1

    try:
        watchlist = load_watchlist(args.config)
        usd_thb_rate = FxService().get_usd_thb_rate()
    except Exception as exc:
        logger.exception("Failed to load configuration.")
        if args.dry_run:
            print(f"Configuration error: {exc}")
            return 1
        failure_report = ReportService(timezone_name).build_failure_report(
            f"Configuration error: {exc}"
        )
        send_or_print(failure_report, dry_run=False)
        return 1

    if usd_thb_rate is None:
        logger.warning(
            "USD_THB_RATE is not set. Share estimates and THB P/L will be unavailable."
        )
        if args.dry_run:
            print("[DRY RUN] USD_THB_RATE is not set; THB P/L fields will show N/A.")

    portfolio_service = PortfolioService(usd_thb_rate=usd_thb_rate)
    report_service = ReportService(timezone_name=timezone_name)

    if args.mock_data:
        logger.info("Using mock data for dry-run verification.")
        quotes, market_quotes = build_mock_quotes()
    else:
        stock_service = StockService()
        logger.info("Fetching stock data for %s", ", ".join(watchlist.keys()))
        quotes = stock_service.fetch_many(watchlist.keys())

        logger.info("Fetching market summary data for %s", ", ".join(MARKET_TICKERS))
        market_quotes = stock_service.fetch_many(MARKET_TICKERS)

    analyses = portfolio_service.analyze_watchlist(watchlist, quotes)
    all_data_failed = all(item.status == "Data Unavailable" for item in analyses)

    if all_data_failed:
        report = report_service.build_failure_report(
            "No market data could be fetched for the configured watchlist."
        )
    else:
        report = report_service.build_daily_report(analyses, market_quotes)

    if send_or_print(report, args.dry_run):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
