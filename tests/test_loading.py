"""Test data loading, validation, and sample file generation."""

from pathlib import Path

import pandas as pd
import pytest

from mfpredict.loading import (
    read_input_file, prepare_participants, make_sample_download,
    InputFormatError, PII_COLUMNS
)
from mfpredict.config import LAST_COL, FIRST_COL


FIXTURES_DIR = Path(__file__).parent / "fixtures"
INPUT_FILE = Path(__file__).parent.parent / "Fall 2026 Market Predictions (Responses).xlsx"


def test_missing_last_col():
    """Test error when LAST_COL is missing."""
    df = pd.DataFrame({
        "Email": ["test@example.com"],
        "First (given) name": ["John"],
        "S&P 500 Index (currently 7666)": [7700],
    })

    with pytest.raises(InputFormatError) as exc_info:
        prepare_participants(df)

    assert "Last (family) name" in str(exc_info.value)
    assert "Missing required column" in str(exc_info.value)


def test_missing_first_col():
    """Test error when FIRST_COL is missing."""
    df = pd.DataFrame({
        "Email": ["test@example.com"],
        "Last (family) name": ["Doe"],
        "S&P 500 Index (currently 7666)": [7700],
    })

    with pytest.raises(InputFormatError) as exc_info:
        prepare_participants(df)

    assert "First (given) name" in str(exc_info.value)


def test_no_asset_columns():
    """Test error when no asset columns (matching 'currently') are found."""
    df = pd.DataFrame({
        "Email": ["test@example.com"],
        "Last (family) name": ["Doe"],
        "First (given) name": ["John"],
        "Timestamp": ["2026-01-01"],
    })

    with pytest.raises(InputFormatError) as exc_info:
        prepare_participants(df)

    assert "No asset columns found" in str(exc_info.value)
    assert "(currently" in str(exc_info.value)


def test_unknown_asset_label():
    """Test that unknown asset labels generate a warning but don't error."""
    df = pd.DataFrame({
        "Last (family) name": ["Doe"],
        "First (given) name": ["John"],
        "Unknown Asset (currently 100)": [110],
    })

    # Should not raise an error, just warn
    prepared = prepare_participants(df)
    assert prepared is not None
    assert any("Unknown Asset" in w for w in prepared.warnings)


def test_ignored_columns_in_info():
    """Test that non-asset columns are listed in info."""
    df = pd.DataFrame({
        "Email Address": ["test@example.com"],
        "Last (family) name": ["Doe"],
        "First (given) name": ["John"],
        "Reasoning": ["Some reason"],
        "S&P 500 Index (currently 7666)": [7700],
    })

    prepared = prepare_participants(df)

    # Should have info about ignored columns
    assert any("Ignored columns" in msg for msg in prepared.info)


def test_numeric_coercion_warning():
    """Test warning when a cell can't be coerced to numeric."""
    df = pd.DataFrame({
        "Email Address": ["test@example.com"],
        "Last (family) name": ["Doe"],
        "First (given) name": ["John"],
        "S&P 500 Index (currently 7666)": ["7,600-8,100"],
        "1 oz Gold (currently $4,440)": [4500.0],
    })

    prepared = prepare_participants(df)

    # Should have a warning about the coercion
    coercion_warnings = [w for w in prepared.warnings if "7,600-8,100" in w and "John Doe" in w]
    assert len(coercion_warnings) == 1


def test_blank_row_warning():
    """Test warning when a row has no predictions."""
    df = pd.DataFrame({
        "Email Address": ["test1@example.com", "test2@example.com"],
        "Last (family) name": ["Doe", "Smith"],
        "First (given) name": ["John", "Jane"],
        "S&P 500 Index (currently 7666)": [7700.0, None],
    })

    prepared = prepare_participants(df)

    # Jane Smith's row is all NaN, should be dropped with a warning
    assert "Row 3" in str(prepared.warnings)  # DataFrame index 1 = row 3
    assert len(prepared.df) == 1  # Only John Doe remains
    assert prepared.df.index[0] == 0
    assert prepared.df.iloc[0]["Person"] == "John Doe"


def test_zero_rows_remaining_error():
    """Test error when all rows are blank."""
    df = pd.DataFrame({
        "Email Address": ["test@example.com"],
        "Last (family) name": ["Doe"],
        "First (given) name": ["John"],
        "S&P 500 Index (currently 7666)": [None],
    })

    with pytest.raises(InputFormatError) as exc_info:
        prepare_participants(df)

    assert "No valid rows remain" in str(exc_info.value)


def test_read_excel_with_predictions_sheet():
    """Test reading Excel with 'Predictions' sheet."""
    fixture_path = FIXTURES_DIR / "predictions_2026-11-11.xlsx"
    with open(fixture_path, "rb") as f:
        data = f.read()

    raw_df, source_desc = read_input_file(data, "predictions_2026-11-11.xlsx")

    assert source_desc == "sheet 'Predictions'"
    assert len(raw_df) > 0


def test_read_csv():
    """Test reading CSV file."""
    fixture_path = FIXTURES_DIR / "predictions_2026-11-11.csv"
    with open(fixture_path, "rb") as f:
        data = f.read()

    raw_df, source_desc = read_input_file(data, "predictions_2026-11-11.csv")

    assert source_desc == "CSV"
    assert len(raw_df) > 0


def test_read_unsupported_format():
    """Test error on unsupported file format."""
    with pytest.raises(InputFormatError) as exc_info:
        read_input_file(b"dummy", "test.txt")

    assert "Unsupported file format" in str(exc_info.value)
    assert ".txt" in str(exc_info.value)


def test_make_sample_download_no_pii():
    """Test that sample download has no PII columns."""
    sample_bytes = make_sample_download(INPUT_FILE)

    sample_df = pd.read_excel(sample_bytes, sheet_name="Predictions")

    for pii_col in PII_COLUMNS:
        assert pii_col not in sample_df.columns, f"PII column '{pii_col}' found in sample"


def test_make_sample_download_only_one_sheet():
    """Test that sample download has only the Predictions sheet."""
    sample_bytes = make_sample_download(INPUT_FILE)

    # Read all sheet names
    xl_file = pd.ExcelFile(sample_bytes)
    assert len(xl_file.sheet_names) == 1
    assert xl_file.sheet_names[0] == "Predictions"


def test_make_sample_download_no_pii_in_real_file():
    """Test that real file is never re-served with PII in prepared data."""
    with open(INPUT_FILE, "rb") as f:
        data = f.read()

    raw_df, _ = read_input_file(data, "Fall 2026 Market Predictions (Responses).xlsx")
    prepared = prepare_participants(raw_df)

    # Check that no PII appears in warnings or info
    all_messages = prepared.warnings + prepared.info
    for pii_col in PII_COLUMNS:
        for msg in all_messages:
            assert pii_col not in msg, f"PII column name '{pii_col}' found in message: {msg}"
