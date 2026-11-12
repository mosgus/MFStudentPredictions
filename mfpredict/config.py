import re

SHEET_NAME = "Predictions"
LAST_COL = "Last (family) name"
FIRST_COL = "First (given) name"
GROUP_COL = "Group"

# CONTROL is a synthetic "no change" baseline (its predictions are the anchor prices),
# not a competitor. When True, CONTROL is excluded from rank/leaderboard winners and
# from the standings heatmap, but still shown for reference. Set False to restore the
# old behavior of ranking CONTROL alongside everyone.
EXCLUDE_BENCHMARK_FROM_RANKS = True

# Show CONTROL in the rank heatmap for reference, even when EXCLUDE_BENCHMARK_FROM_RANKS
# excludes it from Total_Rank_Score/winner in STEP 6. When shown, ranks for EVERYONE in
# this chart switch to the full-field scale (full_rankings_df) so CONTROL's numbers sit
# on the same scale as everyone else's -- mixing a competitor-only rank scale with a
# full-field one for just CONTROL's row would misrepresent relative standing.
INCLUDE_CONTROL_IN_HEATMAP = True

CAT_COLORS = ["#2a78d6", "#eb6834", "#1baf7a"]  # blue, orange, aqua
SEQ_COLOR = "#2a78d6"  # single-hue sequential (histograms)

TICKER_MAP = {
    "S&P 500 Index": "^GSPC",
    "MSCI World Index Developed Markets": "^990100-USD-STRD",  # MSCI World, Standard (price) index
    "MSCI EM Index Emerging Markets": "^891800-USD-STRD",      # MSCI EM, Standard (price) index
    "1 oz Gold": "GC=F",                                       # COMEX gold futures, front month (spot proxy)
    "1 Bitcoin": "BTC-USD",
    "1 barrel of WTI crude oil": "CL=F",                       # NYMEX WTI futures, front month
    "JPY USD exchange rate": "JPY=X",                          # yen per 1 USD
    "US 10-year rate": "^TNX",                                 # already quoted in percent, no scaling needed
}

YAHOO_HOSTS = ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]
MAX_ATTEMPTS_PER_HOST = 3
RETRY_BACKOFF_SECONDS = [1, 2]

_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

ANCHOR_RE = re.compile(r"currently\s*[\$Y]?([\d,]+\.?\d*)\s*%?\)", re.IGNORECASE)

PII_COLUMNS = ("Email Address", "Your NetID")
