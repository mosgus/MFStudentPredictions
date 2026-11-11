# Future Implementation Ideas

Parking lot for improvements to `sorted_predictions.ipynb`. Nothing here is
implemented yet.

---

## 1. Result history / time series (highest value)

**Problem:** `old_results/` archiving and date-stamped (`DATE_STAMP`) filenames
already give per-run file persistence — last week's leaderboard isn't actually
gone, it's sitting in `old_results/` under its own dated filename. What's still
missing is a *structured* history: a per-date folder layout, a convenient
pointer to the latest run, and a single file you can query across weeks to see
whether a student is climbing or sliding — which is the actual point of
running this weekly, and today requires manually opening multiple dated CSVs
to reconstruct.

**Proposal:**
- Write each run to `results/YYYY-MM-DD/` instead of overwriting `results/`.
  Keep a `results/latest/` copy (or symlink) for convenience.
- Append every run to a long-format `results/history.csv`:

  | run_date | person | group | asset | prediction | actual_price | ape | asset_rank | avg_ape | rank_sum | overall_rank |

  Long format, not wide — it survives adding or removing an asset, and it makes
  the charts below trivial.
- Guard against double-appending: if `run_date` already exists in the file,
  replace that day's rows rather than adding duplicates.

**Unlocks:**
- Rank-over-time line chart (bump chart) per student.
- "Biggest mover this week" callout.
- Per-asset actual-price series, so you can show the class how the market moved
  against the distribution of their predictions.
- Reproducibility: you can explain or defend any past week's standings.

---

## 2. Persist the prices used, with a timestamp

`price_check` is displayed in the notebook but never saved. Write it to
`results/YYYY-MM-DD/prices.csv` with a UTC fetch timestamp, the ticker, the
value, and the source.

Without this you can't reproduce a past leaderboard, and you can't tell whether
an odd result came from a bad price or a bad prediction.

---

## 3. Cached last-good price as a fetch fallback

Depends on #2. Once prices are persisted per run, a failed Yahoo fetch can fall
back to the most recent successfully-fetched price instead of dropping the asset
from scoring. Stale by up to a week, but far better than dropping — and
infinitely better than falling back to the survey anchor (which hands CONTROL a
0.00% APE and an automatic win on that asset).

Fallback order once built: retry w/ backoff -> query2 mirror -> cached last-good
price (flag it as stale) -> drop asset with a loud warning.

---

## 4. Switch from raw urllib to `yfinance`

Current implementation hits `query1.finance.yahoo.com/v8/finance/chart/` directly
via `urllib`. Works today, no dependency, fine. But:
- No retry or backoff.
- No handling of the crumb/cookie auth Yahoo has been progressively rolling out
  on unauthenticated endpoints.

`yfinance` handles both. Worth switching if the direct endpoint starts failing.
Low priority while it works.

---

## 5. Consistent as-of timestamps

A uniform intraday-vs-close rule is already implemented: `_is_market_open()`
gates a single choice — intraday price if NYSE is in its 9:30am-4:00pm ET
window, else the most recent daily close — applied identically to all 8
assets, not a per-asset mix. This resolves the original concern (fetching
`^GSPC`'s intraday quote while mixing in a stale close for something else in
the same run).

**Remaining gap:** that NYSE-hours gate is applied even to assets that don't
follow the NYSE calendar — Bitcoin (`BTC-USD`, trades 24/7) and the JPY/USD
rate (trades nearly 24/5 across global sessions). Outside NYSE hours, these
get treated the same as the equity/futures assets and are scored off the most
recent daily close, even though a live/current price would have been
available for them specifically. Worth deciding whether Bitcoin and JPY/USD
should use their own always-open intraday price regardless of NYSE hours,
rather than inheriting the NYSE gate.

---

## 6. Data-quality pre-flight check

Add a cell that runs before scoring and flags likely data-entry problems, so
they get caught before a leaderboard goes out rather than after:
- Cross-check the `Predictions` sheet against `Raw data for class` and report
  any row where the cleaned value doesn't parse back to the raw entry.
- Flag any prediction more than ~3 MADs from the cross-sectional median.
- Flag any prediction implying an absurd move vs. the anchor (e.g. Bitcoin off
  by 10x, a 10-year yield below 2% or above 8%).
- Flag anyone in `Predictions` with no matching row in `Raw data for class`.

Precedent: two order-of-magnitude typos (`7400` for `$74,000`, `1.35` for
`4.35`) put two students in 49th and 50th place in the 2026-09-09 run. Both
would have been caught by any of the checks above.

---

## 7. Range-answer handling rule

Several students submit ranges (`7,600-8,100`, `73000-85000`, `4450-4480`,
`79/80`). These are currently resolved by hand, inconsistently. Pick one rule —
midpoint is the defensible default — and apply it in code when parsing the raw
sheet, rather than during manual cleanup.

---

## 8. Scoring-metric refinements

- **Make rank-sum the headline metric, `Average_APE` the supporting detail.**
  Mean APE is dominated by the highest-dispersion assets: Bitcoin ~10.5% and WTI
  ~9.6% carry roughly 40% of the score, vs. JPY at ~2.9%. Two students with
  identical macro judgment can be separated entirely by a crypto guess. Rank-sum
  already neutralizes this.
- **APE on the 10-year is a percent of a percent.** A 25bp miss scores 5.2% APE,
  comparable to being badly wrong on gold. Rank-based scoring makes this moot;
  if you ever want APE as the primary metric, normalize the rate by
  cross-sectional dispersion or score it in basis points.
- **Cross-sectional z-score** as an alternative third metric: score each asset as
  |error| divided by the standard deviation of errors on that asset. Puts every
  asset on the same footing while preserving magnitude information that pure
  ranks throw away.

---

## 9. Per-student report cards

Once history exists: a one-page PNG or PDF per student showing their eight
predictions vs. the actual path over the semester, their rank trajectory, and
their directional bias (do they systematically over- or under-shoot?). Good
end-of-semester handout, and more instructive than a leaderboard position.

---

## 10. Partial-submission scoring loophole

The blank-row guard (STEP 2) only drops rows with **zero** predictions across
all eight assets. Someone who answers six of eight is scored on those six via
`Average_APE.mean(axis=1)`, which silently drops the two blanks from the
denominator rather than counting them against the participant. A student who
skips their two worst-guess assets (say, Bitcoin and WTI — the highest-
dispersion ones per #8 above) gets a real, if likely unintended, scoring
advantage over someone who answered all eight honestly.

No fix implemented. Options: require all eight answered to be scored at all
(harsh, may disqualify honest partial submitters), or score missing answers as
a fixed worst-case/max-APE penalty rather than excluding them from the mean.
