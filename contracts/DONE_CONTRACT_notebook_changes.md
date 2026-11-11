# Implementation contract: `sorted_predictions.ipynb`

Hand this whole file to the implementing agent as the prompt.

---

## Context

`/Users/gunnarbalch/PycharmProjects/Jupyter/Student Predictions/sorted_predictions.ipynb`
scores student market predictions against live Yahoo Finance prices. It is run
once a week for the whole semester, so failure modes must be loud, not silent.

Key domain fact that drives change A: the `CONTROL` row's predictions are, by
construction, the *anchor* prices embedded in the survey column headers (e.g.
`S&P 500 Index (currently 7666)` -> CONTROL predicted `7666`). CONTROL represents
"what if you just predicted no change." Therefore **falling back to the anchor
price when a fetch fails gives CONTROL a 0.00% APE on that asset and an automatic
win.** That is the bug being fixed.

## Ground rules

- Edit the notebook **in place**. Use `NotebookEdit` if available; otherwise edit
  the `.ipynb` JSON carefully and preserve valid JSON structure.
- **Do not modify** `Fall 2026 Market Predictions (Responses).xlsx`.
- **Do not implement anything from `idea.md`** — that is a deferred backlog.
  Specifically: no `results/` history, no date-stamped output folders, no
  `prices.csv` persistence, no `yfinance` dependency. Out of scope.
- The notebook must run cleanly top-to-bottom with no cell reordering.
- Keep existing style: `# --- STEP N: ... ---` comment banners, `snake_case`,
  no new third-party dependencies (stdlib + numpy/pandas/matplotlib/seaborn only).
- Clear all cell outputs for cells you modify; do not fabricate outputs.

---

## Change A — Tiered price fetch, never fall back to the anchor

**Cell 7** (`# --- FETCH LIVE / LAST-CLOSE PRICES (Yahoo Finance chart API) ---`).

Current behavior: one attempt against `query1.finance.yahoo.com`; on any failure
`ACTUAL_PRICES[label] = anchor` and `price_source[label] = "anchor fallback"`.

Replace with this fallback ladder:

1. **Retry with backoff** — up to 3 attempts against `query1.finance.yahoo.com`,
   sleeping ~1s then ~2s between attempts. Yahoo 429s are usually transient.
2. **Mirror host** — if all query1 attempts fail, try the same path on
   `query2.finance.yahoo.com` (same retry policy). Same API, different host.
3. **Drop the asset** — if every attempt fails, **omit the label from
   `ACTUAL_PRICES` entirely** (do not set it to `None`, do not set it to the
   anchor) and set `price_source[label] = "FETCH FAILED - asset dropped"`.

Rationale for dropping rather than substituting: dropping shrinks the scoring
denominator equally for every participant, so it is fair. Any substituted value
biases the leaderboard toward whoever happened to guess near it.

Also in cell 7:

- If `TICKER_MAP.get(label)` returns `None` (a label/ticker-map mismatch), it
  currently fails **silently** — `fetch_yahoo_price` is never called so no
  warning prints, and it only surfaces as a row in a table the user may scroll
  past. Print an explicit warning naming the unmapped label.
- After the loop, if any asset was dropped, print a prominent multi-line banner
  listing the dropped assets and stating that the leaderboard for this run
  excludes them. Not a one-liner buried in output.
- Keep the `price_check` DataFrame as the last expression of the cell so it still
  renders. Add a `source` value distinguishing which host served the price, e.g.
  `"live (^GSPC via query1)"`.
- Keep the existing commented-out manual-override line at the bottom of the cell.

## Change B — Make downstream cells tolerate a dropped asset

Because a dropped label is now absent from `ACTUAL_PRICES` rather than mapped to
a value, downstream code must key off the assets that actually got a price.

- In **cell 8**, after building `ape_columns`, define
  `scored_assets = [a for a in assets if a in ACTUAL_PRICES]` and use it in place
  of `assets` wherever a *price* is required.
- Keep `assets` as the full list wherever only the *prediction* column is needed
  (the `_Pred` columns still exist for dropped assets and are fine to display).
- **Cell 10** (signed errors), **cell 14** (distribution plots), **cell 15**
  (winner vs CONTROL vs actual): these already guard on
  `actual_price is not None`, which still works with `.get()` returning `None`
  for an absent key. Verify each still behaves correctly and shows the existing
  "Data Not Available" placeholder rather than erroring or plotting a NaN bar.
- If `scored_assets` is empty, raise a clear `RuntimeError` rather than producing
  an all-NaN leaderboard.

## Change C — `Group` column: CONTROL as a benchmark, not a competitor

Participants are not all students. The pool includes the professor and her
family (surnames `UyHam`, `Travers-UyHam`), possibly the notebook author later,
and the synthetic `CONTROL` row. **Only `CONTROL` is to be excluded from
rankings** — human guests compete normally.

Implement:

- **Cell 2 (config):** add `EXCLUDE_BENCHMARK_FROM_RANKS = True`. Everything
  below must honor this flag; setting it to `False` restores today's behavior of
  ranking CONTROL alongside everyone.
- **Cell 4:** read an optional `Group` column from the sheet. It does not exist
  yet, so:
  - If absent, synthesize it: `"benchmark"` for the CONTROL row, `"student"` for
    everyone else.
  - If present, use it as-is and fill blanks with `"student"`.
  - **Critical:** add `"Group"` to the exclusion list that builds
    `asset_raw_cols`. That list is currently "every column that isn't one of four
    known names," so an unhandled `Group` column would silently be treated as a
    ninth asset.
- **Cell 12 (rank standings):** when `EXCLUDE_BENCHMARK_FROM_RANKS` is true,
  compute per-asset ranks and `Total_Rank_Score` over **non-benchmark rows only**,
  so no student's rank is shifted by CONTROL occupying a slot.
- Report where the benchmark *would* have placed, on both metrics, using
  `(competitor_scores < benchmark_score).sum() + 1`. Print it as a line like:
  `Benchmark (CONTROL) would place 1 of 50 by Average APE, 1 of 50 by rank score.`
  This is the pedagogically interesting number — keep it visible.
- **Cell 8:** keep CONTROL in `results_df` and in the leaderboard table (it is
  useful to see), but make the printed `Winner:` line report the top
  **non-benchmark** participant when the flag is set.
- **Cell 15:** `winner_name = results_df.index[0]` must become the top
  non-benchmark participant, consistent with cell 8. The chart already compares
  winner vs CONTROL vs actual, so a CONTROL "winner" would produce a degenerate
  duplicate-bar chart.
- **Cell 13:** the rank-sorted heatmap should use the same competitor ordering.
  CONTROL may be shown as a final separated row or omitted — implementer's
  choice, but be consistent and label it.

## Change D — Disambiguate the two "Average" columns

Cell 11's leftmost column is `Average APE` (magnitude, colored by bias sign).
Cell 13's leftmost column is labeled `Average` but is the mean **signed** error —
a different quantity under a near-identical name and the same colormap.

Rename cell 13's column to `Avg Signed Error` and update the chart's colorbar
label and title text so the two figures cannot be confused.

---

## Verification before reporting done

1. Run the notebook top to bottom. It must complete with no exceptions.
2. Confirm `price_check` shows all 8 assets sourced live (all 8 tickers were
   verified working on 2026-09-09).
3. **Simulate a failure:** temporarily point one `TICKER_MAP` entry at a bogus
   symbol (e.g. `^NOTAREALTICKER`), re-run, and confirm — the retries happen, the
   query2 mirror is attempted, the asset is dropped, the banner prints, the
   leaderboard is computed over 7 assets, and CONTROL does **not** receive a
   0.00% APE on the dropped asset. Then revert the ticker.
4. Confirm `asset_info` still contains exactly 8 rows after the `Group` column
   handling (i.e. `Group` was not absorbed as an asset).
5. Confirm the `Winner:` line names a student, not CONTROL, and that the
   "would place" line for CONTROL prints.

## Report back

State what changed per cell, paste the actual output of the simulated-failure
run in step 3, and list anything in this contract you could not do and why.
