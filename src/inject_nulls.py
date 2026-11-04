"""Inject synthetic missing values into OPSSAT-AD segments.csv for the cleaning demo.

WHY: the real dataset has no nulls (measured, docs/decisions.md F-series). The course
professor asked for injected nulls so the Tableau Prep cleaning steps have something to
fix. Everything this script produces is SYNTHETIC and must be labelled as such in
slides, report and data dictionary. data/raw/ is never modified.

Input : data/raw/segments.csv                (unchanged original)
Output: data/staging/segments_injected.csv   (same columns, some cells blanked)
        data/staging/injection_log.csv       (ground truth: row, segment, column, original)

Reproducible: fixed seed, fixed rates, text copied cell for cell (no float re-formatting).
Usage : python src/inject_nulls.py [--seed 42]
"""
import argparse
import csv
import random
from pathlib import Path

# column -> share of rows blanked. Designed so each column needs a different decision:
#   value     -> measurement lost; can only be estimated        (impute + flag)
#   channel, sampling, anomaly, train -> constant per segment   (recover from the segment)
#   timestamp -> cannot be recovered cleanly                    (drop the row)
RATES = {
    "value": 0.02,
    "channel": 0.01,
    "sampling": 0.01,
    "anomaly": 0.01,
    "train": 0.01,
    "timestamp": 0.005,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--root", default=".", help="repo root")
    a = ap.parse_args()
    root = Path(a.root)
    src = root / "data" / "raw" / "segments.csv"
    out = root / "data" / "staging" / "segments_injected.csv"
    log = root / "data" / "staging" / "injection_log.csv"
    out.parent.mkdir(parents=True, exist_ok=True)

    with open(src, newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r)
        rows = list(r)
    col = {c: i for i, c in enumerate(header)}
    assert all(c in col for c in RATES), "unexpected header: %s" % header
    n = len(rows)

    rng = random.Random(a.seed)  # one RNG, columns visited in a fixed order
    picks = {c: set(rng.sample(range(n), round(n * p))) for c, p in RATES.items()}

    with open(log, "w", newline="", encoding="utf-8") as lf:
        lw = csv.writer(lf)
        lw.writerow(["row", "segment", "column", "original"])
        for c in RATES:
            for i in sorted(picks[c]):
                lw.writerow([i, rows[i][col["segment"]], c, rows[i][col[c]]])
                rows[i][col[c]] = ""

    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)

    print("rows:", n, "seed:", a.seed)
    for c in RATES:
        print("  %-10s blanked %6d (%.2f%%)" % (c, len(picks[c]), 100 * len(picks[c]) / n))
    anyrow = set().union(*picks.values())
    print("  rows with at least one null:", len(anyrow))


if __name__ == "__main__":
    main()
