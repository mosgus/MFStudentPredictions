"""Test chart rendering and PDF generation."""

import io
from pathlib import Path

import matplotlib.pyplot
import pypdf
import pytest

from mfpredict.loading import read_input_file, prepare_participants
from mfpredict.scoring import score
from mfpredict.charts import render_all_charts
from mfpredict.pdf import pngs_to_pdf


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


@pytest.fixture
def score_result():
    """Fixture: load and score the test data."""
    fixture_path = FIXTURES_DIR / "predictions_2026-11-11.xlsx"
    with open(fixture_path, "rb") as f:
        data = f.read()

    raw_df, _ = read_input_file(data, "predictions_2026-11-11.xlsx")
    prepared = prepare_participants(raw_df)
    return score(prepared, FIXTURE_PRICES)


def test_render_all_charts(score_result):
    """Test that all 4 charts are rendered and are valid PNGs."""
    assets = score_result.scored_assets

    charts = render_all_charts(score_result, assets, FIXTURE_PRICES)

    # Should have 4 charts
    assert len(charts) == 4

    # Check order (notebook order: VIS 1, 2, 3, 4)
    expected_keys = [
        "prediction_error_heatmap",
        "rank_heatmap",
        "prediction_distributions",
        "winner_vs_control_vs_actual",
    ]

    assert [c.key for c in charts] == expected_keys

    # Each PNG should be non-empty and start with PNG magic bytes
    for chart in charts:
        assert len(chart.png) > 0, f"Chart {chart.key} has empty PNG"
        assert chart.png.startswith(b"\x89PNG"), f"Chart {chart.key} doesn't start with PNG magic bytes"


def test_pngs_to_pdf(score_result):
    """Test PDF generation from PNG bytes."""
    assets = score_result.scored_assets

    charts = render_all_charts(score_result, assets, FIXTURE_PRICES)
    pngs = [c.png for c in charts]

    # Generate PDF
    pdf_bytes = pngs_to_pdf(pngs)

    # Check that PDF starts with magic bytes
    assert pdf_bytes.startswith(b"%PDF"), "PDF doesn't start with magic bytes"

    # Check page count
    reader = pypdf.PdfReader(io.BytesIO(pngs_to_pdf(pngs)))
    assert len(reader.pages) == 4, f"Expected 4 pages, got {len(reader.pages)}"


def test_no_pyplot_figures_created(score_result):
    """Test that no pyplot figures are created (figures should use Figure, not pyplot)."""
    assets = score_result.scored_assets

    # Render all charts
    render_all_charts(score_result, assets, FIXTURE_PRICES)

    # Check that pyplot has no figures
    assert len(matplotlib.pyplot.get_fignums()) == 0, \
        "pyplot.get_fignums() is not empty - figures were created with pyplot instead of Figure"
