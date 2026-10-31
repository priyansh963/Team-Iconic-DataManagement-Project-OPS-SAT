# Data dictionary (draft)

Status: names below come from the paper. They are NOT verified against the files. Replace with measured types, null counts and ranges once the files are profiled.

## segments.csv (telemetry points)

| Column | Meaning (per paper) | Type in file | Nulls | Notes |
|---|---|---|---|---|
| timestamp | Time of the reading, ISO date format | TODO | TODO | |
| channel | Telemetry channel name | TODO | TODO | 9 channels documented |
| value | Acquired signal value | TODO | TODO | |
| label | Ground-truth annotation | TODO | TODO | |
| segment | Consecutive segment number | TODO | TODO | Join key to dataset.csv (to be verified) |
| sampling | Sampling rate of the segment | TODO | TODO | |
| train | Whether the segment is in the training set | TODO | TODO | See O-005 |

## dataset.csv (one row of features per segment)

Per the paper, 18 handcrafted features: mean, std, skew, kurtosis, var, n_peaks, duration, len, len_weighted, gaps_squared,
var_div_duration, var_div_len, smooth10_n_peaks, smooth20_n_peaks, diff_peaks, diff2_peaks, diff_var, diff2_var,
plus the label, train flag and segment/channel identifiers. Exact column names: TODO after profiling.
