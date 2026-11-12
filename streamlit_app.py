import hashlib
from pathlib import Path

import streamlit as st

from mfpredict.loading import load_and_prepare, make_sample_download, InputFormatError
from mfpredict.prices import fetch_actual_prices, price_table
from mfpredict.scoring import score, ScoringError
from mfpredict.charts import render_all_charts
from mfpredict.pdf import pngs_to_pdf
from mfpredict.config import TICKER_MAP

SAMPLE_FILE = Path(__file__).parent / "Fall 2026 Market Predictions (Responses).xlsx"
PRICE_CACHE_TTL_SECONDS = 300

st.set_page_config(page_title="Market Predictions Leaderboard", layout="wide")

# Cached wrapper for price fetching
@st.cache_data(ttl=PRICE_CACHE_TTL_SECONDS, show_spinner=False)
def _cached_fetch_prices(labels_tuple):
    return fetch_actual_prices(labels_tuple)

def fetch_prices_with_cache(labels):
    result = _cached_fetch_prices(tuple(labels))
    # Don't cache partial/failed results
    if result.dropped_assets:
        _cached_fetch_prices.clear()
    return result

# Cached validation
@st.cache_data
def _validate_input(file_bytes, filename):
    try:
        prepared, source_desc = load_and_prepare(file_bytes, filename)
        return {
            "success": True,
            "prepared": prepared,
            "source_desc": source_desc,
            "warnings": prepared.warnings,
            "info": prepared.info,
        }
    except InputFormatError as e:
        return {
            "success": False,
            "error": str(e),
        }

# --- Page Layout ---

st.title("Fall 2026 Market Predictions — Leaderboard Charts")
st.markdown("Compare student market predictions against live prices from Yahoo Finance.")

# --- Input Section ---

st.header("Input")

# Sample download button
sample_mtime = SAMPLE_FILE.stat().st_mtime if SAMPLE_FILE.exists() else 0

@st.cache_data
def _get_sample_download(mtime_key):
    return make_sample_download(SAMPLE_FILE)

sample_bytes = _get_sample_download(sample_mtime)
st.download_button(
    label="📥 Download sample file",
    data=sample_bytes,
    file_name=f"{SAMPLE_FILE.stem} - sample.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# Format explanation
from mfpredict.config import LAST_COL, FIRST_COL
with st.expander("Expected format", expanded=False):
    st.markdown(f"""
- **Required columns:** `{LAST_COL}` and `{FIRST_COL}`
- **Asset columns:** Each asset is one column header ending in `(currently <price>)`
- **Supported assets:** {', '.join(TICKER_MAP.keys())}
- **Benchmark:** A row with Last name = CONTROL and First name = CONTROL is treated as the no-change baseline
    """)

# File uploader
uploaded_file = st.file_uploader("Upload your own file (optional)", type=["xlsx", "csv"])

# Determine active input
if uploaded_file:
    active_input_bytes = uploaded_file.getvalue()
    active_input_name = uploaded_file.name
else:
    active_input_bytes = SAMPLE_FILE.read_bytes()
    active_input_name = SAMPLE_FILE.name

# Show active input status
input_sha256 = hashlib.sha256(active_input_bytes).hexdigest()

validation_result = _validate_input(active_input_bytes, active_input_name)

# Show validation results
if not validation_result["success"]:
    st.error(f"**Input error:** {validation_result['error']}")
    input_valid = False
else:
    input_valid = True
    prepared = validation_result["prepared"]
    source_desc = validation_result["source_desc"]

    st.info(f"**Using:** {source_desc}")

    if validation_result["warnings"]:
        for warning in validation_result["warnings"]:
            st.warning(warning)

    if validation_result["info"]:
        for info in validation_result["info"]:
            st.info(info)

    n_participants = len(prepared.df)
    n_assets = len(prepared.asset_raw_cols)
    st.success(f"✓ {n_participants} participants, {n_assets} assets")

# --- Generate Section ---

st.header("Generate")
st.caption("Prices are cached for up to 5 minutes.")

if st.button("Generate charts", type="primary", disabled=not input_valid):
    if not input_valid:
        st.error("Please fix the input file first.")
    else:
        with st.spinner("Fetching live prices and building charts…"):
            try:
                prepared = validation_result["prepared"]
                asset_labels = list(prepared.asset_info["label"])

                # Fetch prices
                prices_result = fetch_prices_with_cache(asset_labels)

                # Score
                score_result = score(prepared, prices_result.actual_prices)

                # Render charts - pass all asset labels, not just scored_assets
                charts = render_all_charts(score_result, asset_labels, prices_result.actual_prices)

                # Generate PDF
                chart_pngs = [c.png for c in charts]
                pdf_bytes = pngs_to_pdf(chart_pngs)

                # Store in session state
                st.session_state["results"] = {
                    "input_sha256": input_sha256,
                    "prices": prices_result,
                    "asset_info": prepared.asset_info,
                    "score_messages": score_result.messages,
                    "charts": charts,
                    "pdf": pdf_bytes,
                }

                st.success("✓ Charts generated!")

            except ScoringError as e:
                st.error(f"Scoring error: {e}")
            except Exception as e:
                st.error("Something went wrong generating the charts.")
                with st.expander("Details"):
                    st.exception(e)

# --- Results Section ---

if "results" in st.session_state:
    results = st.session_state["results"]

    # Check if results are still valid for the current input
    if results["input_sha256"] == input_sha256:
        st.header("Results")

        prices = results["prices"]
        asset_info = results["asset_info"]

        # Price timestamp and market status
        status_str = "OPEN" if prices.market_open else "CLOSED"
        time_str = prices.fetched_at.strftime("%H:%M")
        st.subheader(f"Prices as of {time_str} ET (market {status_str})")

        # Price table
        price_df = price_table(asset_info, prices)
        st.dataframe(price_df, width="stretch")

        # Price fetch warnings
        if prices.warnings:
            with st.expander("Price fetch log"):
                for warning in prices.warnings:
                    st.text(warning)

        # Dropped assets warning
        dropped_assets = prices.dropped_assets
        if dropped_assets:
            st.warning(
                f"⚠️ **WARNING:** The following assets could NOT be fetched from Yahoo Finance "
                f"on ANY host after retries, and have been DROPPED from this run's scoring "
                f"entirely (never scored against a stale anchor price):\n\n" +
                "\n".join(f"- {asset}" for asset in dropped_assets) +
                f"\n\nThis run's leaderboard is scored over {len(asset_info) - len(dropped_assets)} "
                f"of {len(asset_info)} assets."
            )

        # Score messages
        for message in results["score_messages"]:
            st.write(message)

        # PDF download
        st.download_button(
            label="📥 Download all charts (PDF)",
            data=results["pdf"],
            file_name=prices.fetched_at.strftime("results_%Y-%m-%d.pdf"),
            mime="application/pdf",
            key="pdf_download",
        )

        # Individual charts
        st.divider()
        for i, chart in enumerate(results["charts"]):
            st.subheader(chart.title)
            st.image(chart.png, width="stretch")
            st.download_button(
                label="📥 Download PNG",
                data=chart.png,
                file_name=prices.fetched_at.strftime(f"{chart.key}_%Y-%m-%d.png"),
                mime="image/png",
                key=f"chart_download_{i}",
            )
    else:
        # Results don't match current input, delete them
        del st.session_state["results"]
