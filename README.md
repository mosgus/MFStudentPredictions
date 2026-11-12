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
├── app.py                                        <- Streamlit web app entrypoint
├── sorted_predictions.ipynb                      <- THE notebook — run this every week
├── compile_results_pdf.py                        <- optional helper: bundles this week's
│                                                     charts into one PDF
├── Fall 2026 Market Predictions (Responses).xlsx  <- the input: raw survey responses
│
├── mfpredict/                                    <- Python package with core scoring logic
│   ├── __init__.py
│   ├── config.py                                 <- constants
│   ├── loading.py                                <- file parsing and validation
│   ├── prices.py                                 <- Yahoo Finance price fetching
│   ├── scoring.py                                <- APE, rankings, winners
│   ├── charts.py                                 <- matplotlib figure rendering
│   └── pdf.py                                    <- PNG to PDF conversion
│
├── .streamlit/                                   <- Streamlit configuration
│   └── config.toml
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
├── tests/                                        <- pytest test suite
│   ├── test_parity.py                            <- S1 parity tests
│   ├── test_loading.py                           <- S1 loading tests
│   ├── test_charts_pdf.py                        <- S1 charts/PDF tests
│   ├── test_prices.py                            <- S1 price fetching tests
│   ├── test_app.py                               <- S2 app tests
│   └── fixtures/                                 <- test data
│       ├── predictions_2026-11-11.xlsx
│       ├── predictions_2026-11-11.csv
│       ├── full_leaderboard_2026-11-11.csv
│       └── rank_standings_2026-11-11.csv
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

---

## Web app (alternative: interactive scoring without the notebook)

Instead of running the notebook by hand, you can use the **Streamlit web app**
to interactively upload files and generate charts in your browser.

### Run locally

1. Install dependencies (same as the notebook setup):
   ```
   pip install -r requirements.txt
   ```
2. Start the app:
   ```
   streamlit run app.py
   ```
   This opens the app in your default browser at `http://localhost:8501`.

### Features

- **Download the sample file** (`Fall 2026 Market Predictions (Responses).xlsx`)
  with a single click — the download strips out student email addresses and
  NetIDs (PII) to keep responses private.
- **Upload your own file** (optional `.xlsx` or `.csv`) to score a different
  set of predictions. Uploads are **never stored**; they're validated and
  processed in your session only.
- **Validate input immediately** before scoring — see any format errors or
  warnings right away.
- **Generate charts on demand** with one click. Prices are fetched live from
  Yahoo Finance and cached for 5 minutes to avoid hitting the API too often.
- **Download charts individually** as PNG images, or all at once as a PDF.

### Deploy on Streamlit Community Cloud

To make the app publicly accessible (e.g., for sharing with students or for
use in class):

1. Push this repository to GitHub (`main` branch).
2. Go to [Streamlit Community Cloud](https://streamlit.io/cloud) and sign in
   with your GitHub account.
3. Click "New app," select this repository, set the main file to `app.py`, and
   deploy.

The app will be live at a URL like `https://yourname-predictions.streamlit.app`.

### Updating the sample file

To update the sample data the app offers for download:

1. Replace `Fall 2026 Market Predictions (Responses).xlsx` with a new file
   (same filename).
2. Push to GitHub.
3. The web app picks up the new file on the next page load.

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
