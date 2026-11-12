from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import numpy as np

from .config import EXCLUDE_BENCHMARK_FROM_RANKS
from .loading import PreparedData


class ScoringError(RuntimeError):
    pass


@dataclass
class ScoreResult:
    results_df: pd.DataFrame
    ape_columns: list[str]
    display_cols: list[str]
    scored_assets: list[str]
    signed_error_df: pd.DataFrame
    competitor_index: list[str]
    rankings_df: pd.DataFrame
    full_rankings_df: pd.DataFrame
    rank_standings: pd.DataFrame
    ape_winner: str
    ape_winning_score: float
    rank_winner: str
    rank_winning_score: float
    benchmark_ape_place: int | None
    benchmark_rank_place: int | None
    n_competitors: int
    messages: list[str]


def score(prepared: PreparedData, actual_prices: dict[str, float],
          exclude_benchmark: bool = EXCLUDE_BENCHMARK_FROM_RANKS) -> ScoreResult:
    """Score participants based on predictions vs actual prices."""
    messages = []
    df = prepared.df.copy()
    person_group = prepared.person_group

    # Map raw column names to labels
    col_to_label = dict(zip(prepared.asset_info["raw_column"], prepared.asset_info["label"]))
    assets = list(prepared.asset_info["label"])

    # Build results table: predictions + APE per asset
    results_df = df.set_index("Person")[prepared.asset_raw_cols].rename(columns=col_to_label)
    results_df = results_df.add_suffix("_Pred")

    ape_columns = []
    scored_assets = []
    for asset in assets:
        actual_price = actual_prices.get(asset)
        if actual_price is None:
            continue
        ape_col = f"{asset}_APE"
        results_df[ape_col] = (results_df[f"{asset}_Pred"] - actual_price).abs() / actual_price
        ape_columns.append(ape_col)
        scored_assets.append(asset)

    if not scored_assets:
        raise ScoringError(
            "No assets have an actual price this run (every ticker fetch failed) -- "
            "cannot compute a leaderboard."
        )

    results_df["Average_APE"] = results_df[ape_columns].mean(axis=1)
    results_df.sort_values("Average_APE", ascending=True, inplace=True)

    # Determine APE winner
    if exclude_benchmark:
        competitors = results_df[[person_group.get(p) != "benchmark" for p in results_df.index]]
    else:
        competitors = results_df

    if len(competitors) == 0:
        raise ScoringError("No competitors remain after filtering.")

    ape_winner = competitors.index[0]
    ape_winning_score = competitors.iloc[0]["Average_APE"]
    messages.append(f"Winner: {ape_winner} with an Average APE of {ape_winning_score:.4%}")

    # Build display columns
    display_cols = ["Average_APE"] + ape_columns

    # Signed errors (for bias direction)
    signed_error_data = {}
    for asset in assets:
        actual_price = actual_prices.get(asset)
        pred_col = f"{asset}_Pred"
        if actual_price is not None and pred_col in results_df.columns:
            signed_error_data[asset] = (results_df[pred_col] - actual_price) / actual_price

    signed_error_df = pd.DataFrame(signed_error_data, index=results_df.index)

    # Rank-based standings
    if exclude_benchmark:
        competitor_index = [p for p in results_df.index if person_group.get(p) != "benchmark"]
    else:
        competitor_index = list(results_df.index)

    rankings_data = {}
    for col in ape_columns:
        asset = col.replace("_APE", "")
        rankings_data[asset] = results_df.loc[competitor_index, col].rank(ascending=True)

    rankings_df = pd.DataFrame(rankings_data, index=competitor_index)

    # Full-field ranks (everyone, including CONTROL) on a single consistent scale
    full_rankings_data = {}
    for col in ape_columns:
        asset = col.replace("_APE", "")
        full_rankings_data[asset] = results_df[col].rank(ascending=True)

    full_rankings_df = pd.DataFrame(full_rankings_data, index=results_df.index)

    rank_standings = rankings_df.copy()
    rank_standings["Total_Rank_Score"] = rank_standings.sum(axis=1)
    rank_standings.sort_values("Total_Rank_Score", ascending=True, inplace=True)

    rank_winner = rank_standings.index[0]
    rank_winning_score = rank_standings.iloc[0]["Total_Rank_Score"]
    messages.append(f"Winner based on Lowest Total Rank Score: {rank_winner} with a score of {rank_winning_score:.0f}")

    # Benchmark placement if CONTROL exists and is excluded
    benchmark_ape_place = None
    benchmark_rank_place = None

    if exclude_benchmark and "CONTROL" in results_df.index:
        benchmark_ape = results_df.loc["CONTROL", "Average_APE"]
        ape_place = (results_df.loc[competitor_index, "Average_APE"] < benchmark_ape).sum() + 1

        full_rank_sums = full_rankings_df.sum(axis=1)
        benchmark_rank_score = full_rank_sums.loc["CONTROL"]
        rank_place = (full_rank_sums.loc[competitor_index] < benchmark_rank_score).sum() + 1

        benchmark_ape_place = ape_place
        benchmark_rank_place = rank_place

        n_competitors = len(competitor_index)
        messages.append(
            f"Benchmark (CONTROL) would place {ape_place} of {n_competitors} by Average APE, "
            f"{rank_place} of {n_competitors} by rank score."
        )
    else:
        n_competitors = len(competitor_index)

    return ScoreResult(
        results_df=results_df,
        ape_columns=ape_columns,
        display_cols=display_cols,
        scored_assets=scored_assets,
        signed_error_df=signed_error_df,
        competitor_index=competitor_index,
        rankings_df=rankings_df,
        full_rankings_df=full_rankings_df,
        rank_standings=rank_standings,
        ape_winner=ape_winner,
        ape_winning_score=ape_winning_score,
        rank_winner=rank_winner,
        rank_winning_score=rank_winning_score,
        benchmark_ape_place=benchmark_ape_place,
        benchmark_rank_place=benchmark_rank_place,
        n_competitors=n_competitors,
        messages=messages,
    )
