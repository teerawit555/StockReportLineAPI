from __future__ import annotations

import json
import unittest
from pathlib import Path

from main import build_mock_quotes
from services.fx_service import FxService
from services.line_service import LineService
from services.portfolio_service import PortfolioService
from services.report_service import ReportService


class MockReportTest(unittest.TestCase):
    def test_mock_report_contains_expected_labels_and_calculations(self) -> None:
        watchlist = json.loads(Path("config/watchlist.json").read_text(encoding="utf-8"))
        quotes, market_quotes = build_mock_quotes()

        analyses = PortfolioService(usd_thb_rate=36.5).analyze_watchlist(
            watchlist, quotes
        )
        report = ReportService("Asia/Bangkok").build_daily_report(
            analyses, market_quotes
        )

        mu = next(item for item in analyses if item.ticker == "MU")
        self.assertAlmostEqual(mu.estimated_shares or 0, 1000 / 36.5 / 996, places=6)
        self.assertAlmostEqual(mu.pnl_percent or 0, -9.43775, places=4)
        self.assertAlmostEqual(mu.pnl_thb or 0, -94.3775, places=2)
        self.assertEqual(mu.status, "Deep Sell-off")

        googl = next(item for item in analyses if item.ticker == "GOOGL")
        self.assertIsNone(googl.avg_cost)
        self.assertIsNone(googl.pnl_percent)

        self.assertIn("Avg Cost: N/A", report)
        self.assertIn("Status: Near Support", report)
        self.assertIn("Portfolio View:", report)

    def test_line_splitter_keeps_chunks_under_limit(self) -> None:
        text = "\n".join(["A" * 200 for _ in range(100)])
        chunks = LineService._split_message(text)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(
            all(len(chunk) <= LineService.MAX_TEXT_LENGTH for chunk in chunks)
        )

    def test_fx_env_override(self) -> None:
        import os

        original = os.environ.get("USD_THB_RATE")
        os.environ["USD_THB_RATE"] = "36.50"
        try:
            self.assertEqual(FxService().get_usd_thb_rate(), 36.50)
        finally:
            if original is None:
                os.environ.pop("USD_THB_RATE", None)
            else:
                os.environ["USD_THB_RATE"] = original


if __name__ == "__main__":
    unittest.main()
