"""Small Lecture 4 smoke test for Yahoo Finance price data."""

import argparse

import yfinance as yf


UNIVERSE = {"AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "JPM", "BAC", "GS"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Yahoo Finance price data.")
    parser.add_argument("ticker", nargs="?", default="AAPL")
    parser.add_argument("--period", default="1mo")
    args = parser.parse_args()
    ticker = args.ticker.upper()
    if ticker not in UNIVERSE:
        raise SystemExit(f"Ticker must be in the approved universe: {sorted(UNIVERSE)}")

    prices = yf.Ticker(ticker).history(period=args.period, auto_adjust=False)
    if prices.empty:
        raise SystemExit(f"Yahoo Finance returned no data for {ticker}.")
    close = prices["Close"]
    print(f"ticker={ticker}")
    print(f"rows={len(close)}")
    print(f"first_date={close.index[0].date()}")
    print(f"last_date={close.index[-1].date()}")
    print(f"latest_close={float(close.iloc[-1]):.4f}")


if __name__ == "__main__":
    main()
