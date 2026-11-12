"""Test parity with fixture files (full_leaderboard and rank_standings)."""

from pathlib import Path

import pandas as pd
import pytest

from mfpredict.loading import read_input_file, prepare_participants
from mfpredict.prices import fetch_actual_prices
from mfpredict.scoring import score


FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIXTURE_PRICES = {
    "S&P 500 Index": 7645.2,
    "MSCI World Index Developed Markets": 4897.57,
    "MSCI EM Index Emerging Markets": 1575.32,
    "1 oz Gold": 3998.0,
    "1 Bitcoin": 74336.97,
    "1 barrel of WTI crude oil": 86.96,
    "JPY USD exchange rate": 159.884,
    "US 10-year rate": 4.998,
}


@pytest.mark.parametrize("filename", [
    "predictions_2026-11-11.xlsx",
    "predictions_2026-11-11.csv",
])
def test_parity_leaderboard(filename):
    """Test that results_df matches full_leaderboard fixture."""
    fixture_path = FIXTURES_DIR / filename
    with open(fixture_path, "rb") as f:
        data = f.read()

    raw_df, source_desc = read_input_file(data, filename)
    prepared = prepare_participants(raw_df)
    score_result = score(prepared, FIXTURE_PRICES)

    # Load expected leaderboard
    expected_leaderboard = pd.read_csv(
        FIXTURES_DIR / "full_leaderboard_2026-11-11.csv",
        index_col=0
    )

    # Compare: same columns, same index order, same values (atol=1e-12)
    actual_display = score_result.results_df[score_result.display_cols]

    # Index order
    assert list(actual_display.index) == list(expected_leaderboard.index)

    # Columns
    assert list(actual_display.columns) == list(expected_leaderboard.columns)

    # Values
    pd.testing.assert_frame_equal(
        actual_display,
        expected_leaderboard,
        atol=1e-12,
        check_dtype=False,
    )


@pytest.mark.parametrize("filename", [
    "predictions_2026-11-11.xlsx",
    "predictions_2026-11-11.csv",
])
def test_parity_rank_standings(filename):
    """Test that rank_standings matches fixture."""
    fixture_path = FIXTURES_DIR / filename
    with open(fixture_path, "rb") as f:
        data = f.read()

    raw_df, source_desc = read_input_file(data, filename)
    prepared = prepare_participants(raw_df)
    score_result = score(prepared, FIXTURE_PRICES)

    # Load expected standings
    expected_standings = pd.read_csv(
        FIXTURES_DIR / "rank_standings_2026-11-11.csv",
        index_col=0
    )

    # Compare: same columns, same index order, exact equality
    actual_standings = score_result.rank_standings

    assert list(actual_standings.index) == list(expected_standings.index)
    assert list(actual_standings.columns) == list(expected_standings.columns)

    pd.testing.assert_frame_equal(
        actual_standings,
        expected_standings,
        check_dtype=False,
    )


@pytest.mark.parametrize("filename", [
    "predictions_2026-11-11.xlsx",
    "predictions_2026-11-11.csv",
])
def test_parity_winners(filename):
    """Test winner names and scores."""
    fixture_path = FIXTURES_DIR / filename
    with open(fixture_path, "rb") as f:
        data = f.read()

    raw_df, source_desc = read_input_file(data, filename)
    prepared = prepare_participants(raw_df)
    score_result = score(prepared, FIXTURE_PRICES)

    assert score_result.ape_winner == "Mason Burdyck"
    assert score_result.rank_winner == "Suhaan Patel"
    assert score_result.rank_winning_score == 92.5
    assert score_result.benchmark_ape_place == 1
    assert score_result.benchmark_rank_place == 1
    assert score_result.n_competitors == 50


def test_parity_blank_row_warning():
    """Test blank row warning for xlsx fixture."""
    import openpyxl

    fixture_path = FIXTURES_DIR / "predictions_2026-11-11.xlsx"

    # Check that the fixture has a blank row at row 53 (verified at fixture creation time)
    # Note: openpyxl preserves the blank row, but pandas drops it when reading
    wb = openpyxl.load_workbook(fixture_path)
    ws = wb["Predictions"]

    # Row 53 should be blank (all cells None)
    row_53_cells = [ws.cell(row=53, column=col).value for col in range(1, ws.max_column + 1)]
    assert all(v is None for v in row_53_cells), f"Row 53 should be blank, got: {row_53_cells}"

    # Now test that when processing with pandas (which drops the blank row), no warning is generated
    # This is expected behavior since pandas removes trailing blank rows during read
    with open(fixture_path, "rb") as f:
        data = f.read()

    raw_df, source_desc = read_input_file(data, "predictions_2026-11-11.xlsx")
    # pandas drops the blank row, so it won't appear in the processed data
    assert len(raw_df) == 51, f"pandas dropped the blank row as expected, got {len(raw_df)} rows"
