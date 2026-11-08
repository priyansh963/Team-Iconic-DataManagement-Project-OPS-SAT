# Profiling notes (Anirudh)



Role: profiling and quality. This file describes what was actually delivered. Every number comes from a file in `reports/` or from `docs/cleaning_log.md`.



## Code (src/)



- `src/profiling.py`: one function per check (load, shape and types, nulls per column, value statistics per channel, rows with any null, distinct values, placeholder text, duplicates, constant within segment, timestamp issues, class balance, train/test split, profile of dataset.csv, comparison with the injection log).

- `src/run_profiling.py`: runs the checks on `data/staging/segments_injected.csv` and `data/raw/segments.csv` and writes the results to `reports/`. It also draws the chart of missing cells per column.

- `src/run_dataset_profile.py`: profiles `dataset.csv` and writes `reports/dataset_summary.json`.

- `src/run_injection_comparison.py`: compares the measured nulls with `data/staging/injection_log.csv` and writes `reports/injection_comparison.csv`.



## Results (reports/)



- `injected_*` and `raw_*` tables and JSON summaries: nulls per column, value statistics per channel, constant-within-segment checks, and the summaries for both files.

- `dataset_summary.json`: dataset.csv has 2,123 rows and 23 columns, no nulls, 2,123 distinct segment ids.

- `injection_comparison.csv`: every injected cell in the log (value 6,070; channel, sampling, anomaly and train 3,035 each; timestamp 1,517) is null in segments_injected.csv, and 19,212 rows have at least one null. Nothing was missed.

- `nulls_per_column_injected.png`: chart of missing cells per column in segments_injected.csv (synthetic).



## Real issues on the raw file



See rows 14 to 17 of `docs/cleaning_log.md` (label column, zeros in value, two value scales, irregular sampling, uneven time coverage).



## Not verified



The check that the 18 feature values in dataset.csv match the raw points was not done and is not presented as a finding.



## How to reproduce



From the project root:



&#x20;   python src/run_profiling.py

&#x20;   python src/run_dataset_profile.py

&#x20;   python src/run_injection_comparison.py

