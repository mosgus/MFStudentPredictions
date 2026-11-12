import json
import time
import urllib.request
import urllib.parse
from dataclasses import dataclass
from datetime import datetime

import pandas as pd
import pytz

from .config import (
    TICKER_MAP, YAHOO_HOSTS, MAX_ATTEMPTS_PER_HOST, RETRY_BACKOFF_SECONDS, _USER_AGENT
)


@dataclass
class PriceResult:
    actual_prices: dict[str, float]
    price_source: dict[str, str]
    dropped_assets: list[str]
    market_open: bool
    fetched_at: datetime
    warnings: list[str]


def _is_market_open() -> bool:
    """Check if US stock market is currently open (9:30 AM - 4 PM ET, weekdays only)."""
    et = pytz.timezone("US/Eastern")
    now = datetime.now(et)
    return now.weekday() < 5 and (9, 30) <= (now.hour, now.minute) < (16, 0)


def _fetch_yahoo_price_once(host: str, ticker: str, timeout: int = 10) -> tuple[float, float, int]:
    """Fetch chart data and return (intraday_price, close_price, timestamp) or raise on failure."""
    url = f"https://{host}/v8/finance/chart/{urllib.parse.quote(ticker)}?range=5d&interval=1d"
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read())

    meta = payload["chart"]["result"][0]["meta"]
    chart = payload["chart"]["result"][0]

    intraday_price = meta["regularMarketPrice"]

    timestamps = chart["timestamp"]
    closes = chart["indicators"]["quote"][0]["close"]
    most_recent_close = closes[-1] if closes[-1] is not None else closes[-2]
    most_recent_timestamp = timestamps[-1]

    return intraday_price, most_recent_close, most_recent_timestamp


def fetch_actual_prices(labels: tuple[str, ...]) -> PriceResult:
    """Fetch live/close prices for given asset labels from Yahoo Finance.

    Retries according to YAHOO_HOSTS and MAX_ATTEMPTS_PER_HOST. Assets that fail
    on all hosts are dropped (never fall back to anchor prices).
    """
    warnings = []
    actual_prices = {}
    price_source = {}
    dropped_assets = []

    market_open = _is_market_open()
    fetched_at = datetime.now(pytz.timezone("US/Eastern"))

    for label in labels:
        ticker = TICKER_MAP.get(label)
        if ticker is None:
            warnings.append(f"No ticker mapped for {label!r} -- asset dropped, no fetch attempted.")
            price_source[label] = "FETCH FAILED - asset dropped"
            dropped_assets.append(label)
            continue

        live_price = None
        host_used = None

        for host in YAHOO_HOSTS:
            for attempt in range(MAX_ATTEMPTS_PER_HOST):
                try:
                    intraday_price, close_price, timestamp = _fetch_yahoo_price_once(host, ticker)
                    live_price = intraday_price if market_open else close_price
                    host_used = host
                    break
                except Exception as e:
                    warnings.append(
                        f"Warning: fetch attempt {attempt + 1}/{MAX_ATTEMPTS_PER_HOST} "
                        f"for {ticker!r} via {host} failed ({e})."
                    )
                    if attempt < MAX_ATTEMPTS_PER_HOST - 1:
                        time.sleep(RETRY_BACKOFF_SECONDS[attempt])

            if live_price is not None:
                break

        if live_price is not None:
            actual_prices[label] = live_price
            price_type = "intraday" if market_open else "close"
            price_source[label] = f"{price_type} ({ticker} via {host_used.split('.')[0]})"
        else:
            price_source[label] = "FETCH FAILED - asset dropped"
            dropped_assets.append(label)

    return PriceResult(
        actual_prices=actual_prices,
        price_source=price_source,
        dropped_assets=dropped_assets,
        market_open=market_open,
        fetched_at=fetched_at,
        warnings=warnings,
    )


def price_table(asset_info: pd.DataFrame, prices: PriceResult) -> pd.DataFrame:
    """Build price check table with columns: label, anchor_price, ticker, actual_price, source."""
    price_check = asset_info[["label", "anchor_price"]].copy()
    price_check["ticker"] = price_check["label"].map(TICKER_MAP)
    price_check["actual_price"] = price_check["label"].map(prices.actual_prices)
    price_check["source"] = price_check["label"].map(prices.price_source)

    return price_check
