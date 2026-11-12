"""Test price fetching from Yahoo Finance."""

from unittest.mock import patch

import pytest

from mfpredict.prices import fetch_actual_prices
from mfpredict.config import TICKER_MAP, YAHOO_HOSTS, MAX_ATTEMPTS_PER_HOST


def test_price_fetch_all_fail_no_anchor_fallback():
    """Test that when all fetches fail, no anchor values are used."""
    labels = tuple(TICKER_MAP.keys())

    # Mock _fetch_yahoo_price_once to always raise
    with patch("mfpredict.prices._fetch_yahoo_price_once", side_effect=Exception("Network error")):
        with patch("mfpredict.prices.time.sleep"):  # No-op sleep
            result = fetch_actual_prices(labels)

    # All assets should be dropped
    assert len(result.dropped_assets) == len(labels)
    assert len(result.actual_prices) == 0

    # No anchor values should appear anywhere
    # (They would appear in the results if fallback was happening)
    for dropped in result.dropped_assets:
        assert dropped in labels


def test_price_fetch_retry_count():
    """Test that retry logic respects MAX_ATTEMPTS_PER_HOST and YAHOO_HOSTS."""
    labels = tuple(TICKER_MAP.keys())

    call_count = [0]

    def mock_fetch(*args, **kwargs):
        call_count[0] += 1
        raise Exception("Network error")

    with patch("mfpredict.prices._fetch_yahoo_price_once", side_effect=mock_fetch):
        with patch("mfpredict.prices.time.sleep"):
            result = fetch_actual_prices(labels)

    # Expected: len(labels) * len(YAHOO_HOSTS) * MAX_ATTEMPTS_PER_HOST
    expected_calls = len(labels) * len(YAHOO_HOSTS) * MAX_ATTEMPTS_PER_HOST
    assert call_count[0] == expected_calls, \
        f"Expected {expected_calls} calls, got {call_count[0]}"


def test_price_fetch_result_structure():
    """Test the structure of PriceResult."""
    labels = ("S&P 500 Index",)

    with patch("mfpredict.prices._fetch_yahoo_price_once", side_effect=Exception("Error")):
        with patch("mfpredict.prices.time.sleep"):
            result = fetch_actual_prices(labels)

    # Check result has all expected fields
    assert hasattr(result, "actual_prices")
    assert hasattr(result, "price_source")
    assert hasattr(result, "dropped_assets")
    assert hasattr(result, "market_open")
    assert hasattr(result, "fetched_at")
    assert hasattr(result, "warnings")

    # Types
    assert isinstance(result.actual_prices, dict)
    assert isinstance(result.price_source, dict)
    assert isinstance(result.dropped_assets, list)
    assert isinstance(result.market_open, bool)
    assert isinstance(result.warnings, list)


def test_unmapped_label_dropped():
    """Test that labels with no ticker are dropped."""
    labels = ("S&P 500 Index", "Unknown Asset")  # Unknown Asset has no ticker

    with patch("mfpredict.prices.time.sleep"):
        result = fetch_actual_prices(labels)

    # Unknown Asset should be dropped
    assert "Unknown Asset" in result.dropped_assets
    assert result.price_source["Unknown Asset"] == "FETCH FAILED - asset dropped"
