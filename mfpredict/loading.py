from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import load_workbook

from .config import SHEET_NAME, LAST_COL, FIRST_COL, GROUP_COL, ANCHOR_RE, TICKER_MAP, PII_COLUMNS


class InputFormatError(ValueError):
    """Raised with a human-readable message when an input file can't be scored."""
    pass


def read_input_file(data: bytes, filename: str) -> tuple[pd.DataFrame, str]:
    """Parse raw bytes into a DataFrame. Returns (raw_df, source_description)."""
    ext = Path(filename).suffix.lower()

    if ext == ".xlsx":
        try:
            buffer = io.BytesIO(data)
            # First, check what sheets exist
            wb = load_workbook(buffer)
            sheet_names = wb.sheetnames

            # Use SHEET_NAME if it exists, otherwise first sheet
            if SHEET_NAME in sheet_names:
                sheet_to_read = SHEET_NAME
                source_desc = f"sheet '{SHEET_NAME}'"
            else:
                sheet_to_read = sheet_names[0]
                source_desc = f"first sheet '{sheet_to_read}' (no '{SHEET_NAME}' sheet found)"

            buffer.seek(0)
            raw_df = pd.read_excel(buffer, sheet_name=sheet_to_read)
            return raw_df, source_desc
        except Exception as e:
            raise InputFormatError(f"Failed to parse Excel file: {e}")

    elif ext == ".csv":
        try:
            raw_df = pd.read_csv(io.BytesIO(data))
            return raw_df, "CSV"
        except Exception as e:
            raise InputFormatError(f"Failed to parse CSV file: {e}")

    else:
        raise InputFormatError(f"Unsupported file format '{ext}'. Expected .xlsx or .csv.")


def parse_asset_column(col_name: str) -> tuple[str, float | None]:
    """Parse label and anchor price from asset column header."""
    label = col_name.split("(currently", maxsplit=1)[0].strip()
    label = pd.Series([label]).str.replace(r"\([^)]*\)", "", regex=True).iloc[0]
    label = pd.Series([label]).str.replace(r"\s+", " ", regex=True).str.strip().iloc[0]

    m = ANCHOR_RE.search(col_name)
    anchor_price = float(m.group(1).replace(",", "")) if m else None

    return label, anchor_price


@dataclass
class PreparedData:
    df: pd.DataFrame
    asset_raw_cols: list[str]
    asset_info: pd.DataFrame
    person_group: dict[str, str]
    warnings: list[str]
    info: list[str]


def prepare_participants(raw_df: pd.DataFrame) -> PreparedData:
    """Process raw data: validate columns, identify assets, parse labels/anchors."""
    warnings = []
    info = []

    # 1. Check required ID columns exist
    if LAST_COL not in raw_df.columns or FIRST_COL not in raw_df.columns:
        missing = []
        if LAST_COL not in raw_df.columns:
            missing.append(LAST_COL)
        if FIRST_COL not in raw_df.columns:
            missing.append(FIRST_COL)
        raise InputFormatError(
            f"Missing required column(s): {', '.join(missing)}. "
            f"Required columns: {LAST_COL}, {FIRST_COL}"
        )

    # 2. Identify asset columns (headers matching "(currently", case-insensitive)
    asset_raw_cols = []
    ignored_cols = []
    for col in raw_df.columns:
        if col not in (PII_COLUMNS + (LAST_COL, FIRST_COL, GROUP_COL)):
            if "currently" in col.lower():
                asset_raw_cols.append(col)
            else:
                ignored_cols.append(col)

    if not asset_raw_cols:
        raise InputFormatError(
            f"No asset columns found. Expected column headers like "
            f"'S&P 500 Index (currently 7666)' or '1 oz Gold (currently $4,440)'. "
            f"Headers must contain '(currently' pattern."
        )

    if ignored_cols:
        info.append(f"Ignored columns (not assets, not ID): {', '.join(ignored_cols)}")

    # 3. Parse labels and anchors, verify all have tickers
    asset_info_rows = []
    unmapped_labels = []
    for col in asset_raw_cols:
        label, anchor_price = parse_asset_column(col)
        asset_info_rows.append({"raw_column": col, "label": label, "anchor_price": anchor_price})
        if label not in TICKER_MAP:
            unmapped_labels.append(label)

    asset_info_df = pd.DataFrame(asset_info_rows)

    # Warn about unmapped labels (they'll be dropped during scoring, as the notebook does)
    for label in asset_info_df["label"]:
        if label not in TICKER_MAP:
            warnings.append(f"No ticker for asset '{label}' -- will be dropped from scoring")

    df = raw_df.copy()

    # 4. Coerce asset cells to numeric, warn on non-null -> NaN conversions
    for col in asset_raw_cols:
        original = df[col].copy()
        df[col] = pd.to_numeric(df[col], errors="coerce")

        # Find cells that were non-null before coercion but NaN after
        coercion_mask = original.notna() & df[col].isna()
        for idx in df[coercion_mask].index:
            first_name = str(df.loc[idx, FIRST_COL]).strip()
            last_name = str(df.loc[idx, LAST_COL]).strip()
            person_name = f"{first_name} {last_name}"
            asset_label = asset_info_df[asset_info_df["raw_column"] == col]["label"].values[0]
            raw_value = str(original.iloc[idx])
            warnings.append(f"Non-numeric value '{raw_value}' in {person_name}'s {asset_label} prediction (coerced to NaN)")

    # 5. Drop fully blank rows
    blank_mask = df[asset_raw_cols].isna().all(axis=1)
    if blank_mask.any():
        for idx in df[blank_mask].index:
            # Spreadsheet row number (header = row 1, so DataFrame index 0 = row 2)
            row_num = idx + 2
            warnings.append(f"Row {row_num} has no predictions for any asset (blank/malformed submission) -- dropped before scoring")
        df = df[~blank_mask].reset_index(drop=True)

    # 6. Build Person, Group, person_group dict
    last = df[LAST_COL].astype(str).str.strip()
    first = df[FIRST_COL].astype(str).str.strip()

    is_control = (last.str.upper() == "CONTROL") & (first.str.upper() == "CONTROL")
    df["Person"] = np.where(is_control, "CONTROL", first + " " + last)

    if GROUP_COL in raw_df.columns:
        group = df[GROUP_COL].astype(str).str.strip()
        df["Group"] = group.mask(group.eq("") | group.str.lower().eq("nan"), "student")
    else:
        df["Group"] = np.where(is_control, "benchmark", "student")

    person_group = dict(zip(df["Person"], df["Group"]))

    # Check for duplicate names
    dupes = df["Person"][df["Person"].duplicated(keep=False)]
    if not dupes.empty:
        dupe_list = sorted(dupes.unique())
        warnings.append(f"Duplicate person names found: {', '.join(dupe_list)}")

    # 7. Check for zero remaining rows
    if len(df) == 0:
        raise InputFormatError("No valid rows remain after processing (all rows were blank/invalid).")

    return PreparedData(
        df=df,
        asset_raw_cols=asset_raw_cols,
        asset_info=asset_info_df,
        person_group=person_group,
        warnings=warnings,
        info=info,
    )


def load_and_prepare(data: bytes, filename: str) -> tuple[PreparedData, str]:
    """Read file bytes + prepare participants. Returns (PreparedData, source_description)."""
    raw_df, source_desc = read_input_file(data, filename)
    prepared = prepare_participants(raw_df)
    return prepared, source_desc


def make_sample_download(path: Path) -> bytes:
    """Return .xlsx bytes holding only the Predictions sheet, minus PII_COLUMNS."""
    # Read the source file
    raw_df = pd.read_excel(path, sheet_name=SHEET_NAME)

    # Remove PII columns
    cols_to_keep = [c for c in raw_df.columns if c not in PII_COLUMNS]
    sample_df = raw_df[cols_to_keep]

    # Write to BytesIO in xlsx format
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        sample_df.to_excel(writer, sheet_name=SHEET_NAME, index=False)

    buffer.seek(0)
    return buffer.getvalue()
