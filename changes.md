# Changes from `source files/copy_of_sorted_predictions.py`

This documents every material difference between the original Colab script
(`source files/copy_of_sorted_predictions.py`) and the current
`sorted_predictions.ipynb`, and why each change was made. Ordered roughly by
when the change happened, not by cell order.

---

## 1. Input format: one sheet per asset -> one sheet, header-embedded anchors

**Original:** `Sorted Predictions.xlsx` had one sheet per asset, each with a
`Person` column and one prediction column. The script looped over
`sheets_dict`, built `Person` from a pre-cleaned column, and merged sheets
together.

**Now:** A single sheet (`Predictions` in
`Fall 2026 Market Predictions (Responses).xlsx`), one row per respondent, one
column per asset. `Person` is built from `First (given) name` + `Last (family)
name` (STEP 2). Asset columns are identified by exclusion (everything that
isn't an ID column), and each header embeds an *anchor* price at survey-send
time, e.g. `S&P 500 Index (currently 7666)` (STEP 3 parses this out via
regex).

**Why:** This is just what the new data source (a live Google/Microsoft Form
export) looks like — it's a raw response sheet, not a pre-sorted workbook.

---

## 2. Market prices: manual `input()` prompts -> automated Yahoo Finance fetch

**Original:** `market_prices` was collected by prompting the user once per
asset via `input()`, falling back to the average of all predictions for that
asset if left blank.

**Now (Cell 7, "FETCH LIVE / LAST-CLOSE PRICES"):** `ACTUAL_PRICES` is fetched
automatically from the Yahoo Finance chart API, no manual input, via
`TICKER_MAP`:

| Asset | Ticker | Note |
|---|---|---|
| S&P 500 Index | `^GSPC` | |
| MSCI World Index Developed Markets | `^990100-USD-STRD` | price (not total-return) variant |
| MSCI EM Index Emerging Markets | `^891800-USD-STRD` | price (not total-return) variant |
| 1 oz Gold | `GC=F` | COMEX futures, front month — spot proxy |
| 1 Bitcoin | `BTC-USD` | |
| 1 barrel of WTI crude oil | `CL=F` | NYMEX futures, front month |
| JPY USD exchange rate | `JPY=X` | yen per 1 USD |
| US 10-year rate | `^TNX` | already quoted in percent, no scaling |

Fetch failures are handled by a tiered ladder, not a fallback value:
1. Up to 3 attempts against `query1.finance.yahoo.com`, backing off ~1s then ~2s.
2. If all 3 fail, the same retry policy against the mirror host
   `query2.finance.yahoo.com`.
3. If every attempt on both hosts fails, the asset is **dropped** from
   `ACTUAL_PRICES` entirely — never set to `None`, never set to the anchor
   price — and a banner lists every dropped asset.

**Why:** This notebook runs unattended once a week for the whole semester;
nobody is sitting at a terminal to answer `input()` prompts. Automation was
necessary regardless. The drop-not-fallback behavior is the more important
reason: **`CONTROL`'s predictions are, by construction, the anchor prices**
baked into the survey headers (a "what if you guessed no change" baseline).
The original script's "fall back to a default if blank" pattern, applied
naively to "fall back to the anchor on fetch failure," would hand CONTROL a
free 0.00% APE and an automatic win on any asset whose fetch failed — a
silent, compounding bug in a notebook that runs 15+ times over a semester.
Dropping the asset instead shrinks the scoring denominator equally for
everyone, which is the only failure mode that doesn't bias the outcome.

---

## 3. CONTROL is a benchmark, not a competitor

**Original:** CONTROL (if present in a sheet) was ranked exactly like every
other participant — could literally win.

**Now:** `EXCLUDE_BENCHMARK_FROM_RANKS = True` (Cell 2, config). STEP 2
classifies each row's `Group` as `"benchmark"` (CONTROL) or `"student"`
(everyone else, synthesized if the sheet has no `Group` column yet, trusted
as-is if it does). Effects:
- **STEP 4 / Cell 8:** the printed Winner is the top *non-benchmark*
  participant; CONTROL still appears in the full `results_df` leaderboard for
  reference.
- **STEP 6 / Cell 12:** ranks and `Total_Rank_Score` are computed over
  competitors only, plus a line reporting where CONTROL *would* have placed,
  e.g. `Benchmark (CONTROL) would place 1 of 49 by Average APE, 1 of 49 by
  rank score.`
- **VIZ 2 / Cell 13:** `INCLUDE_CONTROL_IN_HEATMAP = True`, so the rank-sorted
  heatmap *shows* CONTROL for reference on a full-field rank scale (not the
  competitor-only one) — distinct from CONTROL being excluded from
  `Total_Rank_Score`/the printed winner in STEP 6. The subtitle spells out that
  the ranks shown are full-field and may differ by up to 1 from STEP 6's
  `Total_Rank_Score`.
- **VIZ 4 / Cell 15:** the "Winner vs CONTROL vs Actual" chart uses the same
  non-benchmark winner as Cell 8 (previously it would have used whoever was
  first in a CONTROL-inclusive sort — degenerate if CONTROL wins, since it'd
  be CONTROL vs CONTROL).

**Why:** CONTROL representing "no change" is a useful baseline to measure the
class against, but it isn't a person who should be able to "win." This also
gives an ongoing signal (the "would place" line) for whether the class is
collectively beating the naive baseline — arguably more informative than the
raw leaderboard.

---

## 4. Blank/malformed row guard (STEP 2)

**Now:** rows where every asset prediction is blank are detected and dropped
before scoring, with a loud warning naming the row (by email/NetID).

**Why:** A stray Excel autofill row (all-NaN except a numeric `Email Address`)
appeared in the live data mid-semester. `rank_standings.sum(axis=1)` — used
for `Total_Rank_Score` — sums an all-NaN row to `0.0` under pandas' default
`skipna=True` (unlike `.mean()`, which correctly returns `NaN`), so that
garbage row silently "won" the rank-score leaderboard with a perfect score.
The original script had no equivalent guard because its input format
(one clean sheet per asset, hand-curated) made this failure mode unlikely to
ever occur. Not present in the original because the bug didn't exist there —
added here because the new input source (unfiltered form responses) can
produce it.

---

## 5. `RuntimeError` guard on total fetch failure (STEP 4 / Cell 8)

**Now:** if *every* asset fails to fetch (`scored_assets` is empty), the
notebook raises `RuntimeError` instead of silently producing an all-NaN
leaderboard.

**Why:** matches the "failures must be loud, not silent" requirement for an
unattended weekly job — a fully-empty leaderboard should stop the run, not
get emailed out looking like a real (if empty) result.

---

## 6. Output persistence: `results/` folder

**Original:** everything was `display()`'d or `plt.show()`'n in the Colab
session and discarded when it ended.

**Now:** every chart `plt.savefig()`s into `results/` as it's generated;
a final cell writes `full_leaderboard.csv` and `rank_standings.csv`. Before any
of that, the config cell archives whatever's already sitting in `results/`
(the previous run's outputs) into `old_results/` via `shutil.move`, so
`results/` always holds only the latest run's files while older runs survive
in `old_results/`. Every output filename also carries a `DATE_STAMP`
(`YYYY-MM-DD`), so files from different days never collide even inside
`old_results/`. Paths are relative to the current working directory the
notebook is run from (see Cell 2's config comment), not a hardcoded folder.

**Why:** Colab's `/content/` is ephemeral; a local, weekly-run notebook needs
durable output. (Note: multiple weeks' outputs already persist on disk today
via the `old_results/` archive and date-stamped filenames — what's still out
of scope is the *structured* form of that history described in `idea.md` #1:
`results/YYYY-MM-DD/` subfolders, a `results/latest/` convenience copy, and a
long-format `results/history.csv` for rank-over-time charts.)

---

## 7. Missing-data handling made consistent across all four charts

**Original:** only the distribution-plot cell (now VIZ 3) had an
`else: ax.text(..., 'Data Not Available')` branch for a missing asset; the
"winner vs CONTROL vs actual" chart (now VIZ 4) had no such branch, since in
the original script every asset always had a price (manual input never
"failed").

**Now that fetch failures are possible** (see #2), VIZ 4 (Cell 15) got the
same placeholder treatment: if `ACTUAL_PRICES.get(asset)` is `None`, the panel
shows "Data Not Available" instead of silently rendering a two-bar chart
(winner + CONTROL, no Actual bar) with no visual indication anything was
missing.

**Why:** this is a direct consequence of #2 — once fetch failures became a
real, expected runtime path instead of a theoretical one, every chart that
touches `ACTUAL_PRICES` needed to handle a missing entry visibly, not just the
one cell that happened to need it in the original script.

---

## 8. Rank-comparison scale fix (STEP 6 / Cell 12)

**Bug (introduced during the CONTROL-exclusion work in #3, since fixed):**
the "would place ... by rank score" line compared `Total_Rank_Score` (ranked
over competitors only, 49 people) against `benchmark_rank_score` (ranked over
everyone, 50 people) — two different scales. A competitor's competitor-only
rank sum runs systematically lower than their full-field sum, by exactly the
number of assets on which CONTROL beat them. Silent today only because
CONTROL is in 1st place either way; would misreport CONTROL's placement by
several positions once it's mid-pack.

**Fix:** both sides of the comparison now use one full-field ranking
(`full_rank_sums`, ranked over all 50 including CONTROL) — competitors'
placement is read off `full_rank_sums.loc[competitor_index]`, not off the
competitor-only `rank_standings`.

---

## 9. Rank-heatmap label fix (VIZ 2 / Cell 13)

**Bug (introduced during the "Average APE vs signed error" label cleanup,
since fixed):** the leftmost column's text values come from `rankings_plot`
(built from per-asset *ranks*), while its color comes from `sorted_error_df`
(built from per-asset *signed errors*) — two different quantities sharing one
column, by original design (`fmt=".0f"` on rank text, `cmap="RdBu_r"` on error
color). Labeling that column "Avg Signed Error" was accurate for the color
but flatly wrong for the text (which is average *rank*, e.g. `14`, not a
percentage).

**Fix:** column renamed to `"Avg Rank / Signed Err"`, and the chart subtitle
now spells out "leftmost col = Avg Rank (text) / Avg Signed Error (color)."

*(For contrast: the equivalent column in VIZ 1 / Cell 11, "Average APE," has
no such split — both its text and color are derived from the same
APE/signed-error pair for that chart. The two charts' leftmost columns are
different quantities from each other, which is why they're named
differently.)*

---

## 10. Fetch-failure banner arithmetic fix (Cell 7)

**Bug (dormant, since fixed):** the "scored over N of M assets" banner used
`len(TICKER_MAP)` for both N's subtraction and M. An asset with *no* ticker
mapping at all lands in `dropped_assets` but was never a `TICKER_MAP` entry,
which would under-count both numbers. Doesn't fire today (all 8 current
assets are mapped) but would misreport the moment a new asset is added to the
survey without updating `TICKER_MAP`.

**Fix:** both numbers now use `len(asset_info)` — the actual count of assets
in play, independent of how many happen to have tickers.

---

## Not changed (structurally identical to the original)

- APE formula: `|prediction - actual| / actual`.
- Rank formula: `.rank(ascending=True)` per asset (rank 1 = lowest APE), summed
  for `Total_Rank_Score`.
- Signed-error / bias-direction heatmap logic (VIZ 1 / Cell 11): text = APE
  magnitude, color = signed direction — same convention as the original.
- Overall notebook shape: load -> parse -> fetch prices -> build results ->
  leaderboard -> signed errors -> 4 visualizations. No cells reordered.

## Explicitly out of scope (see `idea.md`)

1. The *structured* form of cross-week history: `results/YYYY-MM-DD/`
   subfolders, a `results/latest/` convenience copy, and a long-format
   `results/history.csv` for rank-over-time/bump-chart features (`idea.md`
   #1). Per-run file persistence itself already exists today via
   `old_results/` archiving and date-stamped filenames (see #6 above) — it's
   specifically this structured time-series layer that's deferred.

Persisting `price_check` with a timestamp, caching last-good prices as an
additional fallback tier, switching to `yfinance`, and a data-quality
pre-flight check are also deferred — tracked in `idea.md`, not implemented
here.
