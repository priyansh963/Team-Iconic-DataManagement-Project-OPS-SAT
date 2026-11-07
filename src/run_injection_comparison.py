"""Compare the measured profile of segments_injected.csv with injection_log.csv.

Usage (from the project root):  python src/run_injection_comparison.py
Writes reports/injection_comparison.csv.
"""
from pathlib import Path

import profiling as p

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
INJECTED = ROOT / "data" / "staging" / "segments_injected.csv"
LOG = ROOT / "data" / "staging" / "injection_log.csv"

if __name__ == "__main__":
    REPORTS.mkdir(exist_ok=True)
    df = p.load_segments(INJECTED)
    result = p.compare_with_injection_log(df, LOG)
    result.to_csv(REPORTS / "injection_comparison.csv")
    print(result.to_string())
    print("Duplicate log entries:", result.attrs["duplicate_log_entries"])
    print("Saved to", REPORTS / "injection_comparison.csv")