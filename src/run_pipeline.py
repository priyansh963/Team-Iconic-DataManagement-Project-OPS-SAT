"""Run the repair pipeline on the injected readings and write the cleaned outputs.

    python src/run_pipeline.py                  # full run
    python src/run_pipeline.py --upto R3        # stop after a rule (handy while developing)

Reads : data/staging/segments_injected.csv (synthetic nulls, see data/README.md)
        data/raw/dataset.csv               (authors' summary table, the benchmark)
Writes: data/cleaned/segment_clean_py.csv        one row per reading
        data/cleaned/quarantine_readings.csv     rows set aside, each with a reason
        data/cleaned/segment_summary_py.csv      one row per segment, with parity checks
        data/cleaned/pipeline_step_log.csv       rows and fields before/after each rule
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

import cleaning as c

DTYPES = {
    "channel": "string",
    "label": "string",
    "sampling": "Int64",
    "anomaly": "Int64",
    "train": "Int64",
    "segment": "int64",
}


def load_readings(path: Path) -> pd.DataFrame:
    """Blank cells become missing values; timestamps are parsed as UTC."""
    return pd.read_csv(path, dtype=DTYPES, parse_dates=["timestamp"])


def apply_step(log: list, rule: str, fn, df: pd.DataFrame, *args, **kwargs) -> pd.DataFrame:
    """Run one rule and record rows and fields before and after (for docs/cleaning_log.md)."""
    out = fn(df, *args, **kwargs)
    log.append(
        {
            "rule": rule,
            "function": fn.__name__,
            "rows_before": len(df),
            "fields_before": df.shape[1],
            "rows_after": len(out),
            "fields_after": out.shape[1],
            "rows_quarantined": 0,
        }
    )
    return out


def apply_split_step(
    log: list, quarantine: list, rule: str, fn, df: pd.DataFrame, *args, **kwargs
) -> pd.DataFrame:
    """Run a rule that returns (clean, quarantined). Keep the quarantined rows for the output."""
    clean, quarantined = fn(df, *args, **kwargs)
    quarantine.append(quarantined)
    log.append(
        {
            "rule": rule,
            "function": fn.__name__,
            "rows_before": len(df),
            "fields_before": df.shape[1],
            "rows_after": len(clean),
            "fields_after": clean.shape[1],
            "rows_quarantined": len(quarantined),
        }
    )
    return clean


# (rule, function, returns (clean, quarantined)?)
READING_STEPS = [
    ("R1", c.remove_label, False),
    ("R2", c.flag_missing_value, False),
    ("R3", c.quarantine_missing_timestamp, True),
    ("R4", c.recover_segment_constants, False),
    ("R5", c.impute_value, False),
    ("R6", c.add_flags, False),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="repo root")
    ap.add_argument("--upto", default="R7", help="last rule to run, R1..R7")
    a = ap.parse_args()
    root = Path(a.root)
    last = int(a.upto.lstrip("Rr"))

    df = load_readings(root / "data" / "staging" / "segments_injected.csv")
    n_raw = len(df)
    log: list = []
    quarantine: list = []
    print("start: %d rows, %d fields" % (n_raw, df.shape[1]))

    for rule, fn, splits in READING_STEPS:
        if int(rule[1:]) > last:
            break
        if splits:
            df = apply_split_step(log, quarantine, rule, fn, df)
        else:
            df = apply_step(log, rule, fn, df)

    out_dir = root / "data" / "cleaned"
    out_dir.mkdir(parents=True, exist_ok=True)

    if last >= 7:
        authors = pd.read_csv(root / "data" / "raw" / "dataset.csv")
        summary = apply_step(log, "R7a", c.summarise_segments, df)
        checks = c.compare_with_authors(summary, authors)
        log.append(
            {
                "rule": "R7b", "function": "compare_with_authors",
                "rows_before": len(summary), "fields_before": summary.shape[1],
                "rows_after": len(checks), "fields_after": checks.shape[1],
                "rows_quarantined": 0,
            }
        )
        summary.merge(checks, on="segment").to_csv(
            out_dir / "segment_summary_py.csv", index=False
        )
        print(
            "parity vs authors: len_diff != 0 in %d segments, dur_diff != 0 in %d, "
            "mean_ok = 0 in %d, attr_ok = 0 in %d (of %d)"
            % (
                (checks["len_diff"] != 0).sum(), (checks["dur_diff"] != 0).sum(),
                (checks["mean_ok"] == 0).sum(), (checks["attr_ok"] == 0).sum(), len(checks),
            )
        )

    n_quarantined = sum(len(q) for q in quarantine)
    if quarantine:
        pd.concat(quarantine, ignore_index=True).to_csv(
            out_dir / "quarantine_readings.csv", index=False
        )
    # Accounting check (Chapter 2): raw = clean + quarantined + deleted. We delete nothing.
    if n_raw != len(df) + n_quarantined:
        sys.exit("ACCOUNTING FAILED: %d raw != %d clean + %d quarantined" % (n_raw, len(df), n_quarantined))
    print("accounting: %d raw = %d clean + %d quarantined + 0 deleted" % (n_raw, len(df), n_quarantined))

    df.to_csv(out_dir / "segment_clean_py.csv", index=False)
    log_df = pd.DataFrame(log)
    log_df.to_csv(out_dir / "pipeline_step_log.csv", index=False)
    print(log_df.to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())