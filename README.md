# Fall 2026 Market Predictions — Scoring & Visualization

This project takes a spreadsheet of student market predictions (S&P 500,
gold, Bitcoin, etc.), grabs the real current prices from Yahoo Finance, and
produces a weekly leaderboard — who's closest, who's winning, and some charts
to go with it. It runs once a week, by hand, for the whole semester.

You do **not** need to know how to code to run this. You do need Python and
Jupyter installed once (see Setup below), and then it's "open the notebook,
click Run All."

---

## Directory structure

```
MFStudentPredictions/
├── README.md                                    <- you are here
├── requirements.txt                              <- list of Python packages needed
├── sorted_predictions.ipynb                      <- THE notebook — run this every week
├── compile_results_pdf.py                        <- optional helper: bundles this week's
│                                                     charts into one PDF
├── Fall 2026 Market Predictions (Responses).xlsx  <- the input: raw survey responses
│
├── results/                                      <- this week's output lands here
│   ├── full_leaderboard_YYYY-MM-DD.csv
│   ├── rank_standings_YYYY-MM-DD.csv
│   ├── prediction_error_heatmap_YYYY-MM-DD.png
│   ├── rank_heatmap_YYYY-MM-DD.png
│   ├── prediction_distributions_YYYY-MM-DD.png
│   ├── winner_vs_control_vs_actual_YYYY-MM-DD.png
│   └── results_YYYY-MM-DD.pdf                    <- made by compile_results_pdf.py
│
├── old_results/                                  <- every previous week's output gets
│                                                     moved here automatically when you
│                                                     run the notebook again
│
├── changes.md                                    <- history of what's changed and why
│                                                     (for whoever maintains this)
├── idea.md                                       <- backlog of ideas not yet built
└── contracts/                                    <- specs used to implement past changes
```

---

## Setup (one-time)

1. **Install Python 3.10+** if you don't have it already (from python.org, or
   via Anaconda).
2. **Install Jupyter** if you don't have it: `pip install jupyter` (or use
   Jupyter through Anaconda/PyCharm/VS Code — any of those work).
3. **Install the packages this notebook needs.** Open a terminal in this
   folder and run:

   ```
   pip install -r requirements.txt
   ```

   This installs everything listed in `requirements.txt`:

   | Package | What it's for |
   |---|---|
   | `pandas` | Reading the spreadsheet and doing all the table math |
   | `numpy` | Number crunching underneath pandas |
   | `matplotlib`, `seaborn` | Drawing the charts |
   | `pytz` | Knowing whether US markets are currently open |
   | `openpyxl` | Lets pandas read `.xlsx` Excel files |
   | `Pillow` | Image handling, used by the PDF-compiling script |
   | `pypdf` | Combining images into a PDF, used by the PDF-compiling script |

You only need to do this setup once per computer.

---

## Running it (every week)

1. Make sure the survey responses spreadsheet,
   **`Fall 2026 Market Predictions (Responses).xlsx`**, is up to date in this
   folder.
2. Open `sorted_predictions.ipynb` in Jupyter (or in PyCharm/VS Code's
   notebook viewer).
3. Run every cell top to bottom — in Jupyter's menu this is usually
   **Run → Run All Cells** (or **Kernel → Restart & Run All**, which is safer
   since it starts from a clean slate).
4. Watch for printed warnings as it runs (in plain red/yellow-ish text in the
   output) — they call out things like a price that couldn't be fetched, or a
   blank/broken survey row. These aren't necessarily errors, but they're worth
   reading.
5. When it finishes, check the `results/` folder for this week's charts and
   spreadsheets (see "What gets saved" below).
6. *(Optional)* Run `python compile_results_pdf.py` from a terminal in this
   folder to bundle this week's charts into a single PDF, handy for emailing
   or printing.

**Heads up — if the notebook ever produces results in an unexpected folder:**
the notebook decides where to save its output using a hard-coded folder path
set near the top (a variable called `BASE_DIR`), not automatically based on
where you double-clicked the file from. Right now that path points at
`/Users/gunnarbalch/PycharmProjects/Jupyter/Student Predictions`, a different
folder than this one (`MFStudentPredictions`). If you've moved this project
and `results/`/`old_results/` stop updating where you expect, that hard-coded
path is why — it needs to be updated to point at wherever this project
actually lives. I didn't change it since that's a code edit, not a docs
change — flagging it here so it doesn't look mysterious later.

---

## What the notebook actually does, step by step

Read top to bottom, the notebook is organized into clearly labeled sections:

1. **Config** — the one place to flip a few on/off switches, e.g. whether the
   `CONTROL` benchmark counts as a "competitor" for ranking purposes.
2. **STEP 1 — Load data**: reads the `Predictions` sheet from the `.xlsx`
   survey file.
3. **STEP 2 — Build the list of participants**: figures out everyone's name,
   drops any completely blank/broken survey row (and prints a warning naming
   it), and identifies which columns are prediction questions vs. just name/
   email/ID fields.
4. **STEP 3 — Parse each question's "anchor" price**: each survey question
   header looks like `S&P 500 Index (currently 7666)` — this step pulls out
   both the clean asset name and that `7666` anchor value, which is also
   `CONTROL`'s stand-in prediction (see below).
5. **Fetch live prices**: pulls each asset's real current price from Yahoo
   Finance. If a fetch fails, it retries a few times, then tries a backup
   Yahoo server, and if it still fails, that one asset is dropped from this
   week's scoring (not silently guessed at) and a loud warning is printed.
6. **STEP 4 — Build the results table**: for every participant and asset,
   computes how far off their prediction was, as a percentage error. Prints
   the "Winner" by average accuracy.
7. **STEP 5 — Signed errors**: same as above, but keeps track of whether each
   person guessed too high or too low (not just how far off), to color the
   first chart.
8. **Visualization 1 — Prediction Error Heatmap**: a table-as-colors view —
   one row per person, one column per asset, colored by whether they guessed
   high (red) or low (blue), with the error size written in each box.
9. **STEP 6 — Rank-based standings**: a second, different way of scoring —
   instead of "how close were you on average," this ranks everyone 1st/2nd/
   3rd/etc. on each asset and adds up the ranks. Rewards being consistently
   decent across all 8 assets over being great at one and bad at the rest.
   Prints its own "Winner."
10. **Visualization 2 — Error Heatmap Sorted by Rank**: same idea as chart 1,
    but ordered by the rank-based standings instead of raw accuracy.
11. **Visualization 3 — Predictions vs Actual**: one small chart per asset
    showing the spread of everyone's guesses as a histogram, with the real
    price and the class average marked.
12. **Visualization 4 — Winner vs CONTROL vs Actual**: a bar chart per asset
    comparing the winner's guess, the `CONTROL` benchmark's guess, and the
    real price side by side.
13. **Save results**: writes the leaderboard and standings tables as `.csv`
    files and saves all four charts as `.png` images into `results/`, with
    today's date in every filename. (Whatever was already sitting in
    `results/` from last time gets moved into `old_results/` automatically
    first, so nothing gets overwritten or lost.)

### What is `CONTROL`?

`CONTROL` is not a real person — it's a built-in "what if you just guessed no
change at all" baseline, using the anchor price from each question as its
"prediction." It's shown in the tables and charts for reference, but it's
excluded from winning and from the real rankings, since it's not a
competitor. Think of it as a sanity-check column, like a thermometer reading
next to a weather forecaster's guesses.

---

## What gets saved, and what each file is

| File | What it is |
|---|---|
| `full_leaderboard_YYYY-MM-DD.csv` | Everyone's per-asset error % and overall average error %, sorted best to worst |
| `rank_standings_YYYY-MM-DD.csv` | Everyone's rank-based score (lower is better), sorted best to worst |
| `prediction_error_heatmap_YYYY-MM-DD.png` | Chart: color-coded grid of everyone's error, by asset |
| `rank_heatmap_YYYY-MM-DD.png` | Same idea, ordered by rank-based standings |
| `prediction_distributions_YYYY-MM-DD.png` | Chart: spread of everyone's guesses per asset vs. the real price |
| `winner_vs_control_vs_actual_YYYY-MM-DD.png` | Chart: winner vs. CONTROL vs. real price, per asset |
| `results_YYYY-MM-DD.pdf` | All of the above charts combined into one PDF (made by running `compile_results_pdf.py` separately — the notebook itself doesn't make this one) |

---

## Good to know

- **This is a living project.** `changes.md` is a running log of what's been
  changed in this notebook over time and why — useful if a number ever looks
  "different than it used to." `idea.md` is a list of improvements someone
  has thought of but not built yet (e.g., keeping a full season-long history
  instead of just last week's results).
- **The notebook has two markdown cells flagged `[RECOVERY NOTE: ...]`.**
  These mark places where some original explanatory text was lost and
  reconstructed from memory rather than the original file — they're
  placeholders, not missing functionality. The code itself is unaffected.
- If you ever see a `RuntimeError` partway through, that's deliberate — it
  means something that should always work (like getting at least one real
  price, or finding at least one valid survey response) didn't, and the
  notebook is refusing to publish a broken or incomplete leaderboard rather
  than silently producing one.
