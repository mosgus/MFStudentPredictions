"""App integration tests focusing on load_and_prepare helper."""

from pathlib import Path

import pytest

from mfpredict.loading import load_and_prepare, InputFormatError


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_load_and_prepare_with_sample():
    """Test load_and_prepare works with the sample file (Fix 1)."""
    sample_file = FIXTURES_DIR.parent.parent / "Fall 2026 Market Predictions (Responses).xlsx"
    sample_bytes = sample_file.read_bytes()

    prepared, source_desc = load_and_prepare(sample_bytes, sample_file.name)

    assert prepared is not None
    assert source_desc == "sheet 'Predictions'"
    assert len(prepared.df) > 0


def test_load_and_prepare_csv_equals_xlsx():
    """Test CSV and XLSX fixtures produce identical results."""
    xlsx_bytes = (FIXTURES_DIR / "predictions_2026-11-11.xlsx").read_bytes()
    csv_bytes = (FIXTURES_DIR / "predictions_2026-11-11.csv").read_bytes()

    xlsx_prepared, _ = load_and_prepare(xlsx_bytes, "test.xlsx")
    csv_prepared, _ = load_and_prepare(csv_bytes, "test.csv")

    # DataFrames should be identical
    import pandas as pd
    pd.testing.assert_frame_equal(
        xlsx_prepared.df.reset_index(drop=True),
        csv_prepared.df.reset_index(drop=True),
    )


def test_load_and_prepare_invalid_format():
    """Test load_and_prepare raises InputFormatError for invalid formats."""
    with pytest.raises(InputFormatError):
        load_and_prepare(b"invalid", "test.txt")


def test_load_and_prepare_with_unmapped_label():
    """Test file with unmapped label loads successfully with warning (R1)."""
    import pandas as pd
    import io

    # Create a fixture with an extra unmapped label
    fixture_path = FIXTURES_DIR / "predictions_2026-11-11.xlsx"
    raw_df = pd.read_excel(fixture_path, sheet_name="Predictions")

    # Add a Silver column
    raw_df["Silver (currently 30)"] = [30.0] * len(raw_df)

    # Write to bytes
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        raw_df.to_excel(writer, sheet_name="Predictions", index=False)
    buffer.seek(0)

    # Load and check for warning (should NOT error)
    prepared, _ = load_and_prepare(buffer.getvalue(), "test.xlsx")

    assert prepared is not None
    assert any("Silver" in w for w in prepared.warnings)
    # Should still have all 9 asset columns (8 original + 1 unmapped)
    assert len(prepared.asset_raw_cols) == 9
