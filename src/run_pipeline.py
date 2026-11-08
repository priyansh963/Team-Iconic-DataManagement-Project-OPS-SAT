"""Run the repair pipeline on the injected readings and write the cleaned outputs.

    python src/run_pipeline.py                  # full run
    python src/run_pipeline.py --upto R3        # stop after a rule (handy while developing)

Validation (src/rules.py): the input is checked first (STOP if the structure is wrong), and
after R6 every row is checked (QUARANTINE rows that break a rule, with the reason).

Reads : data/staging/segments_injected.csv (synthetic nulls, see data/README.md)
        data/raw/dataset.csv               (authors' summary table, the benchmark)
Writes: data/cleaned/segment_clean_py.csv        one row per reading (with source_file)
        data/cleaned/quarantine_readings.csv     rows set aside, each with a reason
        data/cleaned/segment_summary_py.csv      one row per segment, with parity checks
        data/cleaned/pipeline_step_log.csv       rows and fields before/after each rule
"""
import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import cleaning as c
import rules as r

CSV = {"index": False, "lineterminator": "\n"}  # LF everywhere, so checksums match on Windows and Mac

DTYPES = {
    "channel": "string",
    "label": "string",
    "sampling": "Int64",
    "anomaly": "Int64",
    "train": "Int64",
    "segment": "int64",
}


def load_readings(path: Path) -> pd.DataFrame:
    """Blank cells become missing values; timestamps are parsed as UTC.

    Adds `source_file` (the file name) so every row, also a quarantined one, can be traced back.
    """
    df = pd.read_csv(path, dtype=DTYPES, parse_dates=["timestamp"])
    df["source_file"] = path.name
    return df


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


def sha256_of(path: Path) -> str:
    """Fingerprint of a file. Same bytes give the same text, always."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git_state(root: Path) -> str:
    """Short commit id of the code that ran, plus '(uncommitted changes)' if the tree is dirty."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root, capture_output=True, text=True, check=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--", "src", "tests"],
            cwd=root, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return commit + (" (uncommitted changes)" if dirty else "")
    except Exception:
        return "unknown (git not available)"


def write_run_log(root, run_id, code_state, input_path, last, log_df, n_raw, n_clean,
                  n_quarantined, outputs) -> None:
    """Append one readable block per run to logs/run_log.txt (never overwrite: that is the history)."""
    lines = [
        "=== run %s ===" % run_id,
        "code       : git %s" % code_state,
        "stopped at : R%d" % last,
        "input      : %s  sha256 %s" % (input_path.relative_to(root).as_posix(), sha256_of(input_path)),
    ]
    for row in log_df.itertuples(index=False):
        lines.append(
            "%-4s %-28s rows %7d -> %-7d quarantined %5d  deleted %d"
            % (row.rule, row.function, row.rows_before, row.rows_after, row.rows_quarantined, 0)
        )
    lines.append(
        "accounting : %d raw = %d clean + %d quarantined + 0 deleted  OK" % (n_raw, n_clean, n_quarantined)
    )
    for out in outputs:
        lines.append("output     : %s  sha256 %s" % (out.relative_to(root).as_posix(), sha256_of(out)))
    log_dir = root / "logs"
    log_dir.mkdir(exist_ok=True)
    with open(log_dir / "run_log.txt", "a", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n\n")


def write_manifest(root, run_id, code_state, input_path, outputs, counts) -> None:
    """Overwrite logs/MANIFEST.json: a machine-readable description of the latest run."""
    manifest = {
        "run_id": run_id,
        "code": code_state,
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "input": {"path": input_path.relative_to(root).as_posix(), "sha256": sha256_of(input_path)},
        "counts": counts,
        "outputs": {o.relative_to(root).as_posix(): sha256_of(o) for o in outputs},
    }
    (root / "logs").mkdir(exist_ok=True)
    (root / "logs" / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

def stop_run(root: Path, run_id: str, code_state: str, reason: str) -> None:
    """End the run with an error, and write the stop to the run log (a failed run is history too)."""
    log_dir = root / "logs"
    log_dir.mkdir(exist_ok=True)
    with open(log_dir / "run_log.txt", "a", encoding="utf-8", newline="\n") as f:
        f.write("=== run %s ===\ncode       : git %s\nSTOPPED    : %s\n\n" % (run_id, code_state, reason))
    sys.exit("STOP: %s" % reason)


# (rule, rank, function, returns (clean, quarantined)?). --upto Rn runs every step with rank <= n.
READING_STEPS = [
    ("R1", 1, c.remove_label, False),
    ("R2", 2, c.flag_missing_value, False),
    ("R3", 3, c.quarantine_missing_timestamp, True),
    ("R4", 4, c.recover_segment_constants, False),
    ("R5", 5, c.impute_value, False),
    ("R6", 6, c.add_flags, False),
    ("V1", 6, r.quarantine_invalid_rows, True),  # row validation, right after the repairs
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="repo root")
    ap.add_argument("--upto", default="R7", help="last rule to run, R1..R7")
    a = ap.parse_args()
    root = Path(a.root)
    last = int(a.upto.lstrip("Rr"))

    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    code_state = git_state(root)
    input_path = root / "data" / "staging" / "segments_injected.csv"
    df = load_readings(input_path)
    try:
        r.validate_input(df)
    except r.PipelineStop as err:
        stop_run(root, run_id, code_state, str(err))
    n_raw = len(df)
    log: list = []
    quarantine: list = []
    print("start: %d rows, %d fields" % (n_raw, df.shape[1]))

    for rule, rank, fn, splits in READING_STEPS:
        if rank > last:
            break
        try:
            if splits:
                df = apply_split_step(log, quarantine, rule, fn, df)
            else:
                df = apply_step(log, rule, fn, df)
        except r.PipelineStop as err:
            stop_run(root, run_id, code_state, "%s: %s" % (rule, err))

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
            out_dir / "segment_summary_py.csv", **CSV
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
        q = pd.concat(quarantine, ignore_index=True)
        q = q[[col for col in q.columns if col != "reason"] + ["reason"]]  # reason last
        q.to_csv(out_dir / "quarantine_readings.csv", **CSV)
    # Accounting check (Chapter 2): raw = clean + quarantined + deleted. We delete nothing.
    if n_raw != len(df) + n_quarantined:
        stop_run(root, run_id, code_state,
                 "ACCOUNTING FAILED: %d raw != %d clean + %d quarantined" % (n_raw, len(df), n_quarantined))
    print("accounting: %d raw = %d clean + %d quarantined + 0 deleted" % (n_raw, len(df), n_quarantined))

    df.to_csv(out_dir / "segment_clean_py.csv", **CSV)
    log_df = pd.DataFrame(log)
    log_df.to_csv(out_dir / "pipeline_step_log.csv", **CSV)
    print(log_df.to_string(index=False))

    # History: one block per run in logs/run_log.txt, latest run in logs/MANIFEST.json.
    outputs = [out_dir / "segment_clean_py.csv"]
    if quarantine:
        outputs.append(out_dir / "quarantine_readings.csv")
    if last >= 7:
        outputs.append(out_dir / "segment_summary_py.csv")
    write_run_log(root, run_id, code_state, input_path, last, log_df, n_raw, len(df), n_quarantined, outputs)
    write_manifest(
        root, run_id, code_state, input_path, outputs,
        {"raw": n_raw, "clean": len(df), "quarantined": n_quarantined, "deleted": 0},
    )
    print("logged run %s -> logs/run_log.txt, logs/MANIFEST.json" % run_id)


if __name__ == "__main__":
    sys.exit(main())