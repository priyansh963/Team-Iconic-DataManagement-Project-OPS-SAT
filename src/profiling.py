"""Reusable profiling checks for OPSSAT-AD (one function per check).

Every function takes a pandas DataFrame and returns a DataFrame or dict,
so Priyansh can reuse them in the pipeline and we can save results to reports/.
"""
from pathlib import Path
import pandas as pd


def load_segments(path):
    """Load a CSV with every column as text, so nothing is silently converted.

    Blank cells become NaN (missing). Types are decided later, on purpose.
    """
    return pd.read_csv(Path(path), dtype=str, keep_default_na=False, na_values=[""])


def shape_and_dtypes(df):
    """Rows, columns and column names. dtype is 'object' (text) after load_segments."""
    return {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "column_names": list(df.columns),
    }


def nulls_per_column(df):
    """Count and percent of missing cells per column."""
    n = len(df)
    counts = df.isna().sum()
    out = pd.DataFrame({"nulls": counts, "percent": (counts / n * 100).round(3)})
    out["rows"] = n
    return out

def value_stats_per_channel(df):
    """Min, max, mean, zero count and zero share of `value`, per channel.

    `value` is text after load_segments, so it is converted here.
    Cells that are not blank but do not convert to a number are counted
    separately as `non_numeric` (blank cells are already counted as nulls).
    Rows with a blank `channel` are grouped under the label '(missing)'.
    """
    work = pd.DataFrame({
        "channel": df["channel"].fillna("(missing)"),
        "raw": df["value"],
        "num": pd.to_numeric(df["value"], errors="coerce"),
    })
    work["non_numeric"] = work["raw"].notna() & work["num"].isna()
    work["is_zero"] = work["num"] == 0

    g = work.groupby("channel")
    out = pd.DataFrame({
        "rows": g.size(),
        "null_value": g["raw"].apply(lambda s: int(s.isna().sum())),
        "non_numeric": g["non_numeric"].sum().astype(int),
        "min": g["num"].min(),
        "max": g["num"].max(),
        "mean": g["num"].mean(),
        "zeros": g["is_zero"].sum().astype(int),
    })
    out["zero_pct_of_valid"] = (
        out["zeros"] / (out["rows"] - out["null_value"] - out["non_numeric"]) * 100
    ).round(2)
    return out

PLACEHOLDERS = ["na", "n/a", "nan", "null", "none", "-", "?", "", "unknown", "missing"]


def rows_with_any_null(df):
    """Number of rows with at least one missing cell."""
    return int(df.isna().any(axis=1).sum())


def distinct_values(df, cols):
    """Distinct values (including missing) with counts, for low-cardinality columns."""
    return {c: df[c].value_counts(dropna=False).to_dict() for c in cols}


def placeholder_text(df):
    """Count cells that hold placeholder text instead of being truly empty."""
    out = {}
    for c in df.columns:
        s = df[c].dropna().astype(str).str.strip().str.lower()
        out[c] = int(s.isin(PLACEHOLDERS).sum())
    return out


def duplicate_rows(df):
    """Full-row duplicates and duplicate (segment, timestamp) pairs."""
    with_ts = df.dropna(subset=["timestamp"])
    return {
        "full_row_duplicates": int(df.duplicated().sum()),
        "segment_timestamp_duplicates": int(with_ts.duplicated(["segment", "timestamp"]).sum()),
    }


def constant_within_segment(df, cols):
    """For each column: do segments hold one value only (missing cells ignored)?"""
    g = df.groupby("segment")
    size = g.size()
    rows = {}
    for c in cols:
        nun = g[c].nunique(dropna=True)
        rows[c] = {
            "segments": int(len(size)),
            "with_more_than_one_value": int((nun > 1).sum()),
            "with_all_cells_missing": int((nun == 0).sum()),
            "with_some_cells_missing": int((g[c].count() < size).sum()),
        }
    return pd.DataFrame(rows).T


def timestamp_issues(df, fmt="%Y-%m-%dT%H:%M:%S.%fZ"):
    """Missing, unparseable, out-of-order and irregularly spaced timestamps.

    Gaps are measured only between rows that are neighbours in the file and both
    have a timestamp, so blanked timestamps do not create fake gaps.
    """
    raw = df["timestamp"]
    ts = pd.to_datetime(raw, format=fmt, errors="coerce")
    missing = int(raw.isna().sum())
    unparseable = int((raw.notna() & ts.isna()).sum())
    work = pd.DataFrame({"segment": df["segment"], "ts": ts})
    work["diff"] = work.groupby("segment")["ts"].diff().dt.total_seconds()
    valid = work.dropna(subset=["diff"]).copy()
    mode = valid.groupby("segment")["diff"].agg(lambda s: s.mode().iloc[0])
    valid = valid.join(mode.rename("mode"), on="segment")
    irregular = valid["diff"] != valid["mode"]
    bigger = valid["diff"] > valid["mode"]
    return {
        "missing": missing,
        "unparseable": unparseable,
        "steps_measured": int(len(valid)),
        "backwards_steps": int((valid["diff"] < 0).sum()),
        "zero_steps": int((valid["diff"] == 0).sum()),
        "steps_different_from_segment_mode": int(irregular.sum()),
        "segments_with_irregular_step": int(valid.loc[irregular, "segment"].nunique()),
        "segments_with_gap_larger_than_mode": int(valid.loc[bigger, "segment"].nunique()),
        "largest_step_seconds": float(valid["diff"].max()),
        "earliest": str(ts.min()),
        "latest": str(ts.max()),
    }


def _row_and_segment_counts(df, col):
    row = df[col].value_counts(dropna=False).to_dict()
    seg = df.groupby("segment")[col].first().value_counts(dropna=False).to_dict()
    return {"rows": row, "segments": seg}


def class_balance(df):
    """`anomaly` counts at row level and at segment level."""
    return _row_and_segment_counts(df, "anomaly")


def train_test_split(df):
    """`train` counts at row level and at segment level."""
    return _row_and_segment_counts(df, "train")


def print_part_a(path):
    """Run every Part A check on one file and print the results."""
    df = load_segments(path)
    print("== shape ==")
    print(shape_and_dtypes(df))
    print("== nulls per column ==")
    print(nulls_per_column(df).to_string())
    print("== rows with at least one null ==")
    print(rows_with_any_null(df))
    print("== placeholder text ==")
    print(placeholder_text(df))
    print("== distinct values ==")
    print(distinct_values(df, ["label", "sampling", "anomaly", "train", "channel"]))
    print("== value per channel ==")
    print(value_stats_per_channel(df).to_string())
    print("== duplicates ==")
    print(duplicate_rows(df))
    print("== constant within segment ==")
    print(constant_within_segment(df, ["channel", "sampling", "anomaly", "train"]).to_string())
    print("== timestamps ==")
    print(timestamp_issues(df))
    print("== class balance (anomaly) ==")
    print(class_balance(df))
    print("== train/test split ==")
    print(train_test_split(df))