"""Run the repair rules inside Tableau Prep's Script step, or on their own.

This file is a second way to run the SAME rules. src/run_pipeline.py is not changed and stays
the reference: it writes every output, the run log and the manifest.

Same functions, same order as run_pipeline.py:  R1 -> R2 -> R3 -> R4 -> R5 -> R6 -> V1.

Tableau Prep gives a Script step ONE table and takes ONE table back, and each script file has one
get_output_schema(). So the flow has two Script steps, one per branch:

    src/prep_clean.py        clean_readings        the readings that passed every rule
    src/prep_quarantine.py   quarantined_readings  the rows set aside, each with a `reason`

Both call run_rules() below, so they can never disagree with each other or with run_pipeline.py.

On its own (no Prep, no TabPy):
    python src/prep_script.py            # --root . ; reads data/staging/segments_injected.csv
writes data/cleaned/prep_script_clean.csv and data/cleaned/prep_script_quarantine.csv.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

import cleaning as c
import rules as r

CSV = {"index": False, "lineterminator": "\n"}  # LF everywhere, same as run_pipeline.py

REQUIRED = ("channel", "timestamp", "value", "sampling", "anomaly", "train", "segment")
CLEAN_COLUMNS = ["channel", "timestamp", "value", "sampling", "anomaly", "train", "segment",
                 "value_imputed", "is_zero", "class"]
QUARANTINE_COLUMNS = CLEAN_COLUMNS + ["reason"]
WHOLE_NUMBERS = ("sampling", "anomaly", "train", "segment", "value_imputed", "is_zero")
QUARANTINE_NUMBERS = ("value",) + WHOLE_NUMBERS  # may hold blanks, so they travel as decimals


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Give Prep's table the same types run_pipeline.py gets from read_csv.

    Prep may send timestamps without a time zone and whole numbers with blanks as decimals.
    Timestamps are read as UTC, like in run_pipeline.py.
    """
    out = df.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True)
    for col in ("sampling", "anomaly", "train"):
        out[col] = pd.to_numeric(out[col]).astype("Int64")
    out["segment"] = pd.to_numeric(out["segment"]).astype("int64")
    out["value"] = pd.to_numeric(out["value"]).astype("float64")
    out["channel"] = out["channel"].astype("string")
    if "label" in out.columns:
        out["label"] = out["label"].astype("string")
    return out


def run_rules(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply every rule in order. Returns (clean, quarantined); nothing is deleted.

    Raises r.PipelineStop when the table itself is broken (STOP, as in run_pipeline.py).
    """
    missing = [col for col in REQUIRED if col not in df.columns]
    if missing:
        raise r.PipelineStop("missing column(s): %s" % ", ".join(missing))
    n_raw = len(df)
    df = prepare(df)
    r.validate_input(df)
    if "label" in df.columns:
        df = c.remove_label(df)                              # R1
    df = c.flag_missing_value(df)                            # R2
    df, no_time = c.quarantine_missing_timestamp(df)         # R3
    df = c.recover_segment_constants(df)                     # R4
    df = c.impute_value(df)                                  # R5
    df = c.add_flags(df)                                     # R6
    df, invalid = r.quarantine_invalid_rows(df)              # V1
    quarantined = pd.concat([no_time, invalid], ignore_index=True)
    if n_raw != len(df) + len(quarantined):
        raise r.PipelineStop(
            "ACCOUNTING FAILED: %d raw != %d clean + %d quarantined" % (n_raw, len(df), len(quarantined))
        )
    return df, quarantined


def _plain(df: pd.DataFrame, decimals: tuple = ()) -> pd.DataFrame:
    """Plain pandas types that Prep (through TabPy) can send back.

    UTC timestamps lose their time zone, whole numbers become int64 (or float64 where `decimals`
    says blanks are possible), text becomes plain Python strings with None for blanks.
    """
    out = df.reset_index(drop=True).copy()
    for col in out.columns:
        s = out[col]
        if isinstance(s.dtype, pd.DatetimeTZDtype):
            out[col] = s.dt.tz_convert("UTC").dt.tz_localize(None)
        elif col in decimals or col == "value":
            out[col] = pd.to_numeric(s).astype("float64")
        elif col in WHOLE_NUMBERS:
            out[col] = s.astype("int64")
        elif not pd.api.types.is_datetime64_any_dtype(s):
            out[col] = s.astype(object).where(s.notna(), None)
    return out


def clean_table(df: pd.DataFrame) -> pd.DataFrame:
    """The readings that passed every rule (what Prep's flow continues with)."""
    clean, _ = run_rules(df)
    return _plain(clean.reindex(columns=CLEAN_COLUMNS))


def quarantine_table(df: pd.DataFrame) -> pd.DataFrame:
    """The rows that were set aside, each with a `reason` (what the quarantine output gets)."""
    _, quarantined = run_rules(df)
    return _plain(quarantined.reindex(columns=QUARANTINE_COLUMNS), decimals=QUARANTINE_NUMBERS)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="repo root")
    a = ap.parse_args()
    root = Path(a.root)
    df = pd.read_csv(root / "data" / "staging" / "segments_injected.csv")
    clean, quarantined = clean_table(df), quarantine_table(df)
    out_dir = root / "data" / "cleaned"
    out_dir.mkdir(parents=True, exist_ok=True)
    clean.to_csv(out_dir / "prep_script_clean.csv", **CSV)
    quarantined.to_csv(out_dir / "prep_script_quarantine.csv", **CSV)
    print("accounting: %d raw = %d clean + %d quarantined + 0 deleted"
          % (len(df), len(clean), len(quarantined)))


if __name__ == "__main__":
    sys.exit(main())
