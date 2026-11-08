"""Validation rules for the repair pipeline (pandera).

Two kinds of failure, two different reactions (docs/pipeline.md has the full table):

  STOP       The input itself is wrong: empty, a column missing, a column of the wrong type.
             Nothing sensible can be repaired, so the run ends with a clear message.
             Function: validate_input -> raises PipelineStop.

  QUARANTINE A few rows break a rule after the repairs (R1-R6). The other rows are fine,
             so the bad rows are set aside in a second table with a reason.
             Function: quarantine_invalid_rows -> (clean, quarantined).

Allowed values were measured on the injected v1 file (see docs/decisions.md and
reports/): nine known channels, sampling 1 or 5, anomaly and train 0 or 1.
"""
import numpy as np
import pandas as pd
import pandera.pandas as pa

CHANNELS = (
    "CADC0872", "CADC0873", "CADC0874",  # magnetometer
    "CADC0884", "CADC0886", "CADC0888", "CADC0890", "CADC0892", "CADC0894",  # photodiode
)
SAMPLING_RATES = (1, 5)
BINARY = (0, 1)
CONSTANT_COLUMNS = ("channel", "sampling", "anomaly", "train")


TABLE_LEVEL_REASONS = {
    "matches_segment_majority": "differs from the segment's majority value",
    "multiple_fields_uniqueness": "duplicate segment + timestamp",
}


class PipelineStop(RuntimeError):
    """The input is unusable. The run must end instead of guessing."""


# ------------------------------------------------------------- STOP: structure
INPUT_SCHEMA = pa.DataFrameSchema(
    {
        "timestamp": pa.Column("datetime64[ns, UTC]", nullable=True),
        "channel": pa.Column("string", nullable=True),
        "value": pa.Column("float64", nullable=True),
        "sampling": pa.Column("Int64", nullable=True),
        "anomaly": pa.Column("Int64", nullable=True),
        "train": pa.Column("Int64", nullable=True),
        "segment": pa.Column("int64", nullable=False),
    },
    strict=False,  # extra columns (label, source_file) are fine
)


def validate_input(df: pd.DataFrame) -> None:
    """STOP rule: raise PipelineStop if the table is empty or its structure is wrong."""
    if df.empty:
        raise PipelineStop("input has no rows")
    try:
        INPUT_SCHEMA.validate(df, lazy=True)
    except pa.errors.SchemaErrors as err:
        cases = err.failure_cases[["column", "check", "failure_case"]].head(10)
        raise PipelineStop("input failed structure checks:\n" + cases.to_string(index=False)) from err


# ------------------------------------------------------ QUARANTINE: row values
def _matches_segment_majority(df: pd.DataFrame) -> pd.Series:
    """Custom check: channel, sampling, anomaly and train are constant inside a segment.

    This is the assumption R4 relies on. A row passes if, in each of those columns, it
    holds the segment's most common value (blanks are left to the not-nullable rule).
    A single odd row is caught; the rest of its segment is kept. On an exact tie the
    smaller value counts as the majority (deterministic, and very rare).
    """
    ok = pd.Series(True, index=df.index)
    for col in CONSTANT_COLUMNS:
        majority = df.groupby("segment")[col].transform(
            lambda s: s.mode().iloc[0] if s.notna().any() else pd.NA
        )
        same = (df[col] == majority).fillna(False).astype(bool)
        ok &= same | df[col].isna().astype(bool)
    return ok.astype(bool)


ROW_SCHEMA = pa.DataFrameSchema(
    {
        "timestamp": pa.Column(nullable=False),
        "segment": pa.Column(nullable=False),
        "channel": pa.Column(nullable=False, checks=pa.Check.isin(CHANNELS, name="known_channel")),
        "sampling": pa.Column(nullable=False, checks=pa.Check.isin(SAMPLING_RATES, name="sampling_1_or_5")),
        "anomaly": pa.Column(nullable=False, checks=pa.Check.isin(BINARY, name="anomaly_0_or_1")),
        "train": pa.Column(nullable=False, checks=pa.Check.isin(BINARY, name="train_0_or_1")),
        "value": pa.Column(nullable=False, checks=pa.Check(lambda s: np.isfinite(s), name="value_is_finite")),
    },
    checks=[pa.Check(_matches_segment_majority, name="matches_segment_majority")],
    unique=["segment", "timestamp"],
    report_duplicates="all",  # if two rows share segment + timestamp we cannot tell which is right
    strict=False,
)


def quarantine_invalid_rows(
    df: pd.DataFrame, reason_col: str = "reason"
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """QUARANTINE rule: set aside rows that break a ROW_SCHEMA rule, with the reason.

    Needs  : the columns named in ROW_SCHEMA (otherwise PipelineStop: that is structure).
    Returns: (clean, quarantined). len(clean) + len(quarantined) == len(df).
    The reason lists every rule the row broke, e.g. "known_channel; not_nullable".
    """
    df = df.reset_index(drop=True)
    try:
        ROW_SCHEMA.validate(df, lazy=True)
    except pa.errors.SchemaErrors as err:
        cases = err.failure_cases
        if cases["index"].isna().any():  # a failure that belongs to no row = structural
            raise PipelineStop("row checks failed on the table as a whole:\n" + str(cases.head(10))) from err
        # Table-level checks are reported once per column; give them one readable name.
        check = cases["check"].astype(str).str.replace(r"^isin\(.*\)$", "not an allowed value", regex=True)
        cases = cases.assign(
            why=cases["check"].map(TABLE_LEVEL_REASONS).fillna(cases["column"].astype(str) + ": " + check)
        )
        reasons = cases.groupby("index")["why"].agg(lambda s: "; ".join(sorted(set(s))))
        bad = df.index.isin(reasons.index.astype(int))
        quarantined = df.loc[bad].copy()
        quarantined[reason_col] = "validation: " + reasons.reindex(quarantined.index).astype(str)
        return df.loc[~bad].reset_index(drop=True), quarantined.reset_index(drop=True)
    empty = df.iloc[0:0].copy()
    empty[reason_col] = pd.Series(dtype="string")
    return df, empty
