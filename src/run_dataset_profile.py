"""Profile data/raw/dataset.csv and save the result to reports/dataset_summary.json."""
import json
from pathlib import Path

import profiling as p

ROOT = Path(__file__).resolve().parent.parent
df = p.load_segments(ROOT / "data" / "raw" / "dataset.csv")
summary = p.profile_dataset_summary(df)
out = ROOT / "reports" / "dataset_summary.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, default=str)
print("Saved", out)