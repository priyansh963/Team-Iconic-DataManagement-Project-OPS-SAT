# Data dictionary (draft)

Status: names below come from the paper and the Zenodo preview (first rows only). They are NOT verified against the files. Replace with measured types, null counts and ranges once the files are profiled.

## segments.csv (telemetry points)

| Column | Meaning (per paper) | Type in file | Nulls | Notes |
|---|---|---|---|---|
| timestamp | Time of the reading, ISO 8601 UTC, ms precision | text matching YYYY-MM-DDTHH:MM:SS.mmmZ (all rows) | 0 | Parse to date-time in Prep |
| channel | Telemetry channel name | TODO | TODO | 9 channels documented |
| value | Acquired signal value | decimal, 0 non-numeric | 0 | Scale differs by channel: magnetometers about +-1e-4, photodiodes 0 to about 1.57. 46,671 rows (15.4%) are exactly 0, mostly photodiode channels |
| label | Text. MEASURED: the value is "anomaly" on every row, including rows where `anomaly` = 0 | text | 0 | Constant and misleading, do not use as target |
| anomaly | 0/1 flag, the usable ground truth (33.0% of rows are 1) | 0/1 | 0 | Not in the paper's column list |
| segment | Consecutive segment number | TODO | TODO | Join key to dataset.csv (to be verified) |
| sampling | Seconds between readings in the segment | 1 or 5 | 0 | Constant inside each segment |
| train | 1 = training set, 0 = test set (1,594 / 529 segments) | 0/1 | 0 | Constant inside each segment |

## dataset.csv (one row of features per segment)

Per the paper, 18 handcrafted features: mean, std, skew, kurtosis, var, n_peaks, duration, len, len_weighted, gaps_squared,
var_div_duration, var_div_len, smooth10_n_peaks, smooth20_n_peaks, diff_peaks, diff2_peaks, diff_var, diff2_var,
plus the label, train flag and segment/channel identifiers. Exact column names: TODO after profiling.
