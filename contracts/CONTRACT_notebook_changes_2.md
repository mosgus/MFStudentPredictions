# Implementation contract #2: `sorted_predictions.ipynb`

Hand this whole file to the implementing agent as the prompt. This follows
`DONE_CONTRACT_notebook_changes.md`, which is already implemented and verified — do
not redo any of it.

---

## Context

`/Users/gunnarbalch/PycharmProjects/Jupyter/Student Predictions/sorted_predictions.ipynb`
scores student market predictions against live Yahoo Finance prices. It is run
once a week by hand for the whole semester.

Three domain facts drive these changes:

1. **The `CONTROL` row is a synthetic benchmark**, not a competitor. Its
   predictions are literally the anchor prices baked into the survey column
   headers (`S&P 500 Index (currently 7666)` -> CONTROL predicted `7666`). It
   represents "what if you just predicted no change." It is already excluded
   from rankings via `EXCLUDE_BENCHMARK_FROM_RANKS`.
2. **All eight assets must be scored every week.** The owner does not want a
   run that quietly scores 7 of 8. A price that cannot be fetched should stop
   the run, not shrink the scoring set.
3. **Skipping an asset currently helps you.** `Average_APE` uses
   `mean(axis=1)` and rank-sum uses `sum(axis=1)`; both skip NaN, so a
   participant who answers 6 of 8 is scored over 6 and gets a *lower* (better)
   rank total than someone who answered all 8. There are zero partial
   submissions in the sheet today, so this is latent, not active — but it must
   be closed before it fires.

## Ground rules

- Edit the notebook **in place**. Use `NotebookEdit` if available; otherwise
  edit the `.ipynb` JSON carefully and preserve valid JSON structure.
- **Do not modify** `Fall 2026 Market Predictions (Responses).xlsx`. Not even to
  delete the known stray blank row — the STEP 2 blank-row guard handles it
  deliberately and the owner wants it kept.
- **Do not implement anything from `idea.md`.** That is a deferred backlog. In
  particular: no `results/` history, no date-stamped output folders, no
  `prices.csv` persistence, no `yfinance` dependency, no data-quality preflight
  against the `Raw data for class` sheet. Out of scope.
- No new third-party dependencies (stdlib + numpy/pandas/matplotlib/seaborn).
- Must run cleanly top-to-bottom. No cell reordering. Prefer editing existing
  cells over adding new ones.
- Keep existing style: `# --- STEP N: ... ---` banners, `snake_case`.
- Clear outputs on cells you modify; do not fabricate outputs.

---

## Change E — `DROP_FAILED_ASSETS` flag: fail the run instead of dropping

Contract #1 made a failed fetch drop the asset from scoring. That was correct
versus the old anchor-fallback bug, but the owner would rather re-run an hour
later than publish a 7-asset leaderboard.

- **Cell 2 (config):** add `DROP_FAILED_ASSETS = False`, with a comment
  explaining that `False` aborts the run on any unfetchable asset (re-run
  later), and `True` restores contract #1's behavior of dropping it — an escape
  hatch for a genuinely delisted ticker when results are needed the same day.
- **Cell 7:** after the retry/mirror ladder and the existing dropped-assets
  banner, if `dropped_assets` is non-empty **and** `DROP_FAILED_ASSETS` is
  `False`, raise a `RuntimeError` naming the assets and stating that the run was
  aborted so no partial-coverage leaderboard is produced. Point the reader at
  `DROP_FAILED_ASSETS = True` and the existing manual-override line as the two
  ways to proceed anyway.
- Print the banner **before** raising, so the user sees which assets failed.
- Leave the whole drop path intact and working for `DROP_FAILED_ASSETS = True`,
  including the `scored_assets` logic and `RuntimeError` guard in cell 8.

## Change F — Close the partial-submission loophole

- **Cell 2 (config):** add `MISSING_ANSWER_POLICY = "worst"`. Two valid values:
  - `"worst"` (default) — a missing answer scores the worst APE observed on
    that asset among everyone who did answer it. Makes skipping strictly worse
    than any real guess, so the incentive to skip disappears.
  - `"median"` — a missing answer is scored as if the participant had predicted
    the class median for that asset. Lands them mid-pack; neutral rather than
    punitive.

  Raise a `ValueError` on any other value.

- **Cell 8 (STEP 4)** is where this happens, and the order matters:
  1. Build `results_df` with the `_Pred` columns exactly as now.
  2. Compute `results_df["N_Answered"]` = count of non-null `_Pred` columns,
     **before** any imputation.
  3. For each scored asset, compute APE as now.
  4. Apply the policy per asset:
     - `"worst"`: `results_df[ape_col] = results_df[ape_col].fillna(results_df[ape_col].max())`
       (the max is over answerers, since NaNs are excluded from `max()`).
     - `"median"`: compute a parallel scored prediction
       `pred.fillna(pred.median())` and derive the APE from that.
  5. Then compute `Average_APE`.

  **Leave the raw `_Pred` columns untouched (still NaN) under both policies.**
  Under `"median"`, hold the filled values in a separate `_PredScored` column.
  Cells 10, 11, 14 and 15 must keep reading the raw `_Pred` columns so the
  charts show only real human answers — never a synthetic imputed value in a
  distribution plot or an error heatmap.

- **Cell 12 (STEP 6):** no imputation logic needed. Because APEs are imputed in
  cell 8, ranks derive from them automatically — under `"worst"` non-answerers
  tie at last place on that asset, under `"median"` they land mid-pack. Verify
  this rather than adding a second mechanism; the two metrics must agree on how
  a blank is treated.

- **Cell 15:** guard `results_df.loc[winner_name, pred_col]` against NaN, in the
  unlikely case a partial submitter still wins. Skip or placeholder that panel
  rather than plotting a NaN bar.

- Print a warning listing any participant with `N_Answered < len(scored_assets)`
  and stating which policy was applied.

## Change G — Two named winners

The two metrics measure different things and currently disagree (Average APE
favors Daniel Prasad, rank-sum favors Aaron George). Report both as
co-equal, clearly labeled, instead of implying one is *the* winner.

- **Cell 8:** relabel the printed line to
  `Winner - Closest on Average (Average APE): <name> (<score>)`.
- **Cell 12:** relabel to
  `Winner - Most Consistent (Total Rank Score): <name> (<score>)`.
- **Cell 12, at the end:** print a short combined summary block giving both
  winners with a one-line plain-English gloss of each metric:
  - Average APE — rewards raw percentage accuracy; dominated by the
    highest-dispersion assets (Bitcoin and WTI carry roughly 40% of the score).
  - Total Rank Score — rewards placing well across all eight; treats every
    asset equally.

  If the same participant wins both, print a distinct line saying so instead of
  repeating the name twice.
- **Cell 15:** the chart uses the Average APE winner. Update the `suptitle` and
  the bar label to name the metric explicitly (e.g. `"<name> (Avg APE Winner)"`)
  so it can't be read as the sole overall winner.

## Change H — `N_Answered` in the leaderboard, without breaking formatting

`display_cols` is rendered with `.style.format("{:.2%}")` in **cell 8** and
**cell 9**, which applies percent formatting to every column. Adding an integer
count naively would render `8` as `800.00%`.

- Add `N_Answered` to the leaderboard table and to the saved
  `full_leaderboard.csv`.
- Switch both `.style.format(...)` calls to a per-column format dict: `"{:.2%}"`
  for `Average_APE` and every `_APE` column, `"{:.0f}"` for `N_Answered`.

## Change I — Housekeeping

- **Cell 12:** the header comment still says CONTROL's rank score is computed
  "exactly like the old, ungated behavior did." That was made stale by the
  full-field-comparison fix. Rewrite it to match what the code now does.
- **Cell 13:** stop mutating `rankings_df` in place. It currently does
  `rankings_df["Sum_Ranks"] = rankings_df.sum(axis=1)` and then sorts, so
  re-running this one cell without re-running cell 12 folds the previous
  `Sum_Ranks` back into the sum and corrupts the ordering. Compute the sum into
  a local Series and sort a copy; leave `rankings_df` unmodified. This matters
  because tweaking a chart and re-running its cell alone is normal weekly usage.

---

## Verification before reporting done

Do all of these. "Ran without an exception" is not sufficient evidence — check
the actual values and the rendered charts.

1. Normal path: run top to bottom. All 8 assets sourced live, no drops, both
   winner lines print, `N_Answered` shows `8` for everyone as an integer (not
   `800.00%`) in both the cell 8 preview and `results/full_leaderboard.csv`.

2. **Partial-submission test, `"worst"` policy.** Do this **in memory** — add a
   temporary cell right after cell 3 that blanks two predictions for one
   participant (pick someone mid-leaderboard, and blank Bitcoin and WTI, the
   two highest-dispersion assets — the ones most worth skipping). Re-run and
   confirm:
   - `N_Answered` is `6` for that participant, `8` for everyone else.
   - Their Bitcoin and WTI APEs equal the max APE among answerers on those
     assets, and they are tied at last place on both in the rank table.
   - Their standing got **worse**, not better, than it was with all 8 answered.
   - Their raw `_Pred` cells are still NaN: they do not appear in the Bitcoin
     or WTI histograms, and their cells are blank in the signed-error heatmap.
   - The partial-submission warning printed and named them.
   Then **delete the temporary cell**.

3. Repeat step 2 with `MISSING_ANSWER_POLICY = "median"` and confirm the
   participant lands mid-pack on those two assets rather than last, and that
   the raw `_Pred` columns are still NaN (the filled values live only in
   `_PredScored`). Restore the policy to `"worst"`.

4. Set `MISSING_ANSWER_POLICY = "banana"` and confirm a clear `ValueError`.
   Restore.

5. **Fetch-failure test.** Point one `TICKER_MAP` entry at `^NOTAREALTICKER`:
   - With `DROP_FAILED_ASSETS = False`: retries and mirror are attempted, the
     banner prints, then the run aborts with a `RuntimeError`. No leaderboard,
     no CSVs, no charts are produced.
   - With `DROP_FAILED_ASSETS = True`: contract #1 behavior still works — asset
     dropped, banner printed, 7-of-8 leaderboard, cell 14 and cell 15 both show
     the "Data Not Available" placeholder for it.
   Revert the ticker and the flag.

6. **Cell 13 idempotency:** run the notebook top to bottom, then re-run cell 13
   alone three times. The row ordering and the annotated rank numbers must be
   identical every time, and `rankings_df` must not have gained a `Sum_Ranks`
   column.

7. Confirm `asset_info` still has exactly 8 rows and the leaderboard still has
   50 rows (49 competitors + CONTROL) after the blank-row guard.

## Report back

For each of Changes E through I, state what changed and in which cell. Paste
the **actual printed output** of verification steps 2, 4, 5, and 6 — not a
summary of them. For step 2, include the participant's before/after position on
both metrics. List anything you could not do and why.
