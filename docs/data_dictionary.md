# Data dictionary

Sources: column names from the file headers (`head`, 2026-11-04); counts and findings (F-x, D-008, O-x) from `docs/decisions.md`; segment range measured on `data/raw/segments.csv`. Units are not stated in the files: "to confirm". "Raw" means the authors' published file. "Injected" means `data/staging/segments_injected.csv`, which is SYNTHETIC (see below).

## segments.csv (telemetry points, 303,493 rows, 8 columns)

| Column | Meaning | Type in file | Nulls in raw | Notes |
|---|---|---|---|---|
| channel | Telemetry channel name | text, e.g. CADC0872 | 0 | 9 channels: CADC0872/0873/0874 (magnetometers), CADC0884/0886/0888/0890/0892/0894 (photodiodes). Strongly imbalanced (CADC0873 has 593 segments, CADC0886 only 11, CADC0890 only 14) |
| timestamp | Time of the reading, ISO 8601 UTC, ms precision | text matching YYYY-MM-DDTHH:MM:SS.mmmZ (all rows) | 0 | Range 2022-01-04 to 2022-06-02. 85.1% of rows are from June (F-8) |
| value | Acquired signal value | decimal, some in scientific notation | 0 | Unit: to confirm. Scale differs by channel: magnetometers about -1e-4 to 1e-4, photodiodes 0 to about 1.57 (F-10). 46,671 rows (15.4%) are exactly 0, mostly photodiode channels (F-3) |
| label | Text | text | 0 | MEASURED: "anomaly" on all 303,493 rows, including rows where `anomaly` = 0. Constant and misleading, do not use as target (F-1) |
| sampling | Seconds between readings in the segment | 1 or 5 | 0 | Constant inside each segment in the raw file |
| anomaly | 0/1 flag, the usable ground truth | 0/1 | 0 | 33.0% of rows belong to anomalous segments. Not in the paper's column list |
| segment | Segment number | integer, 1 to 2123, 2,123 distinct | 0 | Join key to dataset.csv. Same 2,123 ids in both files, 0 orphans (O-010) |
| train | 1 = training set, 0 = test set | 0/1 | 0 | 1,594 training and 529 test segments. Constant inside each segment in the raw file |

## Injected nulls in segments_injected.csv (SYNTHETIC)

Why: the real data has no nulls (F-5) and the professor asked for injected nulls so the cleaning has something to repair (D-008). Created by `src/inject_nulls.py`, seed 42, from the untouched raw file. Only segments.csv gets nulls; dataset.csv and data/raw/ are never modified.

| Column | Blanked cells | Share of 303,493 rows |
|---|---|---|
| value | 6,070 | 2.00% |
| channel | 3,035 | 1.00% |
| sampling | 3,035 | 1.00% |
| anomaly | 3,035 | 1.00% |
| train | 3,035 | 1.00% |
| timestamp | 1,517 | 0.50% |
| label, segment | 0 | 0% |

Rows with at least one null: 19,212. Because blanks are spread over single cells, the raw-file rule "channel, sampling, anomaly and train are constant inside each segment" does not hold row by row in the injected file. Constancy can be used to repair them.

## dataset.csv (one row per segment, 2,123 rows, 23 columns)

Derived from segments.csv by grouping by segment (parent/child, see decisions.md). Untouched by the injection and used as the benchmark. No nulls (F-5). Types and ranges per feature: to confirm.

- Identifiers (5): segment, anomaly, train, channel, sampling
- Features (18, in file order): duration, len, mean, var, std, kurtosis, skew, n_peaks, smooth10_n_peaks, smooth20_n_peaks, diff_peaks, diff2_peaks, diff_var, diff2_var, gaps_squared, len_weighted, var_div_duration, var_div_len

Notes:
- len equals the point count and duration equals last minus first timestamp for all 2,123 segments.
- gaps_squared is not only a gap measure: for a regular segment it equals (len - 1) x sampling^2 (verified for 1,972 of 2,123 segments, F-4). It is largely a function of length and sampling.
- Feature units: to confirm.
