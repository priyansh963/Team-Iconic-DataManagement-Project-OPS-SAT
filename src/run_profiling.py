"""Run every profiling check and save the results to reports/.

Usage (from the project root):  python src/run_profiling.py
Reads data/staging/segments_injected.csv and data/raw/segments.csv.
Every number on the slides comes from a file this script writes.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import profiling as p

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
FILES = {
    "injected": ROOT / "data" / "staging" / "segments_injected.csv",
    "raw": ROOT / "data" / "raw" / "segments.csv",
}


def run(tag, path):
    df = p.load_segments(path)
    nulls = p.nulls_per_column(df)
    nulls.to_csv(REPORTS / f"{tag}_nulls_per_column.csv")
    p.value_stats_per_channel(df).to_csv(REPORTS / f"{tag}_value_per_channel.csv")
    p.constant_within_segment(
        df, ["channel", "sampling", "anomaly", "train"]
    ).to_csv(REPORTS / f"{tag}_constant_within_segment.csv")

    summary = {
        "file": str(path.relative_to(ROOT)),
        "shape": p.shape_and_dtypes(df),
        "rows_with_any_null": p.rows_with_any_null(df),
        "placeholder_text": p.placeholder_text(df),
        "distinct_values": p.distinct_values(
            df, ["label", "sampling", "anomaly", "train", "channel"]
        ),
        "duplicates": p.duplicate_rows(df),
        "timestamps": p.timestamp_issues(df),
        "class_balance_anomaly": p.class_balance(df),
        "train_test_split": p.train_test_split(df),
    }
    with open(REPORTS / f"{tag}_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    return nulls


def chart(nulls):
    cols = nulls.index.tolist()
    counts = nulls["nulls"].tolist()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(cols, counts, color="#4c72b0")
    ax.bar_label(bars, labels=[f"{c:,}" for c in counts])
    ax.set_title("Missing cells per column in segments_injected.csv (synthetic)")
    ax.set_ylabel("Missing cells")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    fig.savefig(REPORTS / "nulls_per_column_injected.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    REPORTS.mkdir(exist_ok=True)
    results = {tag: run(tag, path) for tag, path in FILES.items()}
    chart(results["injected"])
    print("Saved to", REPORTS)
    for f in sorted(REPORTS.iterdir()):
        print(" ", f.name)