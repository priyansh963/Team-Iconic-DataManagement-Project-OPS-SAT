import numpy as np
import pandas as pd

IDENTIFIER_COLUMNS = ("channel", "sampling", "anomaly", "train")


# ---------------------------------------------------------------- R1
def remove_label(df: pd.DataFrame, column: str = "label") -> pd.DataFrame:
    """R1: drop the constant, misleading `label` column (finding F-1).

    Needs  : `column` to exist.
    Changes: removes that one column.
    Rows   : never changes the row count.
    Mirrors: Prep Clean 1, Remove Fields.
    """
    return df.drop(columns=[column])


# ---------------------------------------------------------------- R2
def flag_missing_value(
    df: pd.DataFrame, value_col: str = "value", flag_col: str = "value_imputed"
) -> pd.DataFrame:
    """R2: add `value_imputed` = 1 where `value` is missing, else 0.

    Must run BEFORE R5, otherwise the information is lost.
    Needs  : `value_col`.   Changes: adds one column.   Rows: unchanged.
    Mirrors: Prep calculated field IF ISNULL([value]) THEN 1 ELSE 0 END.
    """
    out = df.copy()
    out[flag_col] = out[value_col].isna().astype("int8")
    return out


# ---------------------------------------------------------------- R3
def quarantine_missing_timestamp(
    df: pd.DataFrame,
    timestamp_col: str = "timestamp",
    reason_col: str = "reason",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """R3: set aside rows without a timestamp, with a reason (fail safely).

    A missing time cannot be recovered cleanly, so these rows must not continue.
    They are not deleted: they are returned in a second table with a `reason`.
    Needs  : `timestamp_col`.
    Returns: (clean, quarantined). len(clean) + len(quarantined) == len(df).
    Rows   : fewer in `clean` (injected v1: 303,493 -> 301,976 clean + 1,517 quarantined).
    Mirrors: Prep filter NOT ISNULL([timestamp]) + a second output for the removed rows.
    """
    missing = df[timestamp_col].isna()
    clean = df.loc[~missing].reset_index(drop=True)
    quarantined = df.loc[missing].copy()
    quarantined[reason_col] = "missing timestamp"
    return clean, quarantined.reset_index(drop=True)


# ---------------------------------------------------------------- R4
def recover_segment_constants(
    df: pd.DataFrame,
    columns: list[str,] = list(IDENTIFIER_COLUMNS),
    by: str = "segment",
) -> pd.DataFrame:
    """R4: fill blanks in `columns` using the other rows of the same segment.

    These fields are constant inside a segment, so a blank can be recovered exactly.
    Needs  : `by` and every column in `columns`.
    Changes: only blank cells in `columns`.
    Rows   : never changes the row count.
    Mirrors: Prep calculated fields with {FIXED [segment] : MIN/MAX(...)}.
    """
    filler = df.groupby(by=by)[columns].transform("first")
    return df.fillna(filler)


# ---------------------------------------------------------------- R5
def impute_value(
    df: pd.DataFrame,
    value_col: str = "value",
    by: str = "segment",
    method: str = "mean",
) -> pd.DataFrame:
    """R5: estimate blank `value` cells from the same segment.

    method="mean" must match Prep (segment average). Interpolation is optional later.
    Needs  : `value_col`, `by`.   Changes: only blank cells in `value_col`.
    Rows   : unchanged.
    Mirrors: Prep IFNULL([value], {FIXED [segment] : AVG([value])}).
    """
    if method in ("mean", "median"):
        imputer = df.groupby(by=by)[value_col].transform(method)
    else:
        raise ValueError(f"Can't impute with {method}")
    return df.fillna({value_col: imputer})


# ---------------------------------------------------------------- R6
def add_flags(
    df: pd.DataFrame,
    value_col: str = "value",
    anomaly_col: str = "anomaly",
) -> pd.DataFrame:
    """R6: add `is_zero` (1 if value == 0) and `class` ("anomaly" / "nominal").

    Zeros are flagged, never deleted: in photodiode channels they can be real.
    Run after R4 and R5, so `anomaly` and `value` have no blanks left.
    Changes: adds two columns.   Rows: unchanged.
    Mirrors: Prep calculated fields is_zero and class.
    """
    out = df.copy()
    out["is_zero"] = (out[value_col] == 0).astype("int8")
    out["class"] = np.where(out[anomaly_col] == 1, "anomaly", "nominal")
    return out


# ---------------------------------------------------------------- R7
def summarise_segments(df: pd.DataFrame) -> pd.DataFrame:
    """R7a: one row per segment.

    Output columns: segment, channel, anomaly, train, sampling, n_readings,
    timestamp_min, timestamp_max, mean_value, n_zero, n_imputed.
    Mirrors: Prep Aggregate 1.

    TODO(Priyansh): implement. Tests: test_r7_summarise_* in tests/test_cleaning.py.
    """
    raise NotImplementedError("R7a")


def compare_with_authors(summary: pd.DataFrame, authors: pd.DataFrame) -> pd.DataFrame:
    """R7b: compare our summary with the authors' dataset.csv, per segment.

    Output: one row per segment with len_diff, dur_diff, mean_diff, mean_ok, attr_ok.
      len_diff  = n_readings - len
      dur_diff  = (timestamp_max - timestamp_min in seconds) - duration
      mean_diff = |mean_value - mean|
      mean_ok   = 1 if mean_diff < 1e-12 else 0
      attr_ok   = 1 if channel, anomaly, train and sampling all match, else 0
    Mirrors: Prep Join 1 (full outer on segment) + Clean 3 parity checks.

    TODO(Priyansh): implement. Tests: test_r7_compare_* in tests/test_cleaning.py.
    """
    raise NotImplementedError("R7b")
