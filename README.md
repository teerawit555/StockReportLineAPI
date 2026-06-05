# Stock LINE Report Bot

Python automation that sends a concise daily US stock watchlist report to LINE at 07:30 Thailand time.

The bot fetches market data with `yfinance`, compares prices with your support levels, estimates position metrics, labels each ticker, and pushes the final report through the LINE Messaging API.

## Watchlist

Default tickers:

- MU
- NVDA
- GOOGL
- RKLB
- ANET
- AAPL
- VOO

Edit `config/watchlist.json` to change tickers, support levels, average cost, position value in THB, priority, and notes.

## Installation

```bash
cd stock-line-report-bot
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

On macOS or Linux, activate the virtual environment with:

```bash
source .venv/bin/activate
```

## Environment Variables

Create a `.env` file for local runs:

```env
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
USD_THB_RATE=
TIMEZONE=Asia/Bangkok
```

Never commit `.env`. `LINE_CHANNEL_ACCESS_TOKEN` and `LINE_USER_ID` are only needed when sending to LINE.

`USD_THB_RATE` is optional:

- Leave it blank to fetch live USD/THB from yfinance with `USDTHB=X`.
- Set it manually, for example `USD_THB_RATE=36.50`, when you want to force a fixed rate.
- If live FX fetching fails and no manual rate is set, estimated shares and THB P/L show `N/A`.

## Create a LINE Messaging API Token

1. Go to the LINE Developers Console.
2. Create a provider if you do not already have one.
3. Create a Messaging API channel.
4. In the Messaging API settings, issue a long-lived channel access token.
5. Put that token in `LINE_CHANNEL_ACCESS_TOKEN`.
6. Add your bot as a friend in LINE so it can push messages to you.

## Get Your LINE User ID

LINE push messages need a user ID, not your display name.

1. Enable webhooks for the Messaging API channel.
2. Send a message from your LINE account to the bot.
3. Inspect the webhook event payload.
4. Copy `events[0].source.userId` into `LINE_USER_ID`.

For a quick webhook capture, you can temporarily use a request-bin style HTTPS endpoint or a small local webhook exposed with a tunnel. Disable or replace the temporary endpoint after copying the user ID.

## Run Locally

Print the report without sending:

```bash
python main.py --dry-run
```

Print a deterministic offline sample report without fetching market data:

```bash
python main.py --dry-run --mock-data
```

Send the actual report:

```bash
python main.py
```

Send a small LINE test message:

```bash
python main.py --test-line
```

This command does not fetch stock data.

Print the test message instead of sending:

```bash
python main.py --test-line --dry-run
```

## Change Watchlist and Support Levels

Edit `config/watchlist.json`.

Example:

```json
{
  "NVDA": {
    "support": [205, 200, 190],
    "avg_cost": 214,
    "position_thb": 3500,
    "priority": "high",
    "note": "Core AI chip holding"
  }
}
```

Support levels are compared with the latest available price:

- Within 2 percent above support: `Near Support`
- More than 2 percent below nearest support: `Breakdown Risk`
- Down more than 7 percent in one day: `Deep Sell-off`
- Missing quote data: `Data Unavailable`

The action text is intentionally cautious, for example "Hold / no need to chase" or "Do not average down too quickly."

## GitHub Actions Deployment

The workflow is in `.github/workflows/daily_report.yml`.

It runs every day at 00:30 UTC, which is 07:30 Thailand time.

Manual runs are enabled with `workflow_dispatch`.

Add these GitHub Secrets:

- `LINE_CHANNEL_ACCESS_TOKEN`
- `LINE_USER_ID`
- `USD_THB_RATE`
- `TIMEZONE`

Use `Asia/Bangkok` for `TIMEZONE`.

You can also run it manually from the Actions tab with `workflow_dispatch`.

If this project folder is inside a larger repository, GitHub will only detect workflows placed at the repository root. Move or copy `.github/workflows/daily_report.yml` to the repository root and set the workflow command to run from this folder:

```yaml
defaults:
  run:
    working-directory: stock-line-report-bot
```

## Data Source Notes

This first version uses `yfinance` because it is free and simple.

Limitations:

- Free quote data can be delayed.
- Pre-market and after-hours fields are not always available.
- Yahoo Finance can rate-limit or change response behavior.
- Some market status fields may be missing.
- For production-grade reliability, replace `StockService` with Finnhub, Polygon, Alpha Vantage, or Twelve Data.

## Project Structure

```text
stock-line-report-bot/
  main.py
  config/
    watchlist.json
  services/
    stock_service.py
    report_service.py
    line_service.py
    portfolio_service.py
  utils/
    logger.py
    formatter.py
  requirements.txt
  .env.example
  README.md
  .github/
    workflows/
      daily_report.yml
```
