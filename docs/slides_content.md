# Slide content for the profiling and quality role (Anirudh)



Every number below comes from a file in `reports/` or from `docs/cleaning_log.md`.



## Slide 1: Method (what was checked)



**Title:** How we profiled the data



**Files profiled**



- `segments_injected.csv` (working data, with synthetic nulls)

- `segments.csv` (raw)

- `dataset.csv` (the authors' summary table, 2,123 rows, 23 columns)



**Checks (one function each in `src/profiling.py`)**



- rows, columns and data types

- nulls per column (count and %)

- value range and zeros per channel

- duplicates

- `channel`, `sampling`, `anomaly` and `train` constant within each segment

- timestamp problems (missing, irregular spacing)

- class balance of `anomaly` and the train/test split



**Answer-key comparison**



- measured nulls compared cell by cell with `injection_log.csv`



**Reproducible**



- `python src/run_profiling.py`

- `python src/run_dataset_profile.py`

- `python src/run_injection_comparison.py`



Source: `src/profiling.py`, `reports/`





## Slide 2: Findings (real vs synthetic issues)



**Title:** What we found: real vs synthetic issues



**Real issues (raw `segments.csv`)**



- `label` is "anomaly" on all 303,493 rows, while `anomaly` = 0 on 203,229 rows (cleaning log row 14)

- `value` = 0 on 46,671 rows, 40,443 of them in the six photodiode channels (row 14)

- Two value scales: three channels about -1e-4 to 1e-4, six photodiode channels 0 to at most 1.5708 (row 15)

- Irregular sampling: 151 of 2,123 segments have a step that differs from their usual step, largest step 130 s (row 16)

- Uneven time coverage: June has 258,132 rows (85.1%), no rows for March to May (row 17)



**Synthetic issues (injected for the exercise, in `segments_injected.csv`)**



- `value`: 6,070 blank cells

- `channel`, `sampling`, `anomaly`, `train`: 3,035 blank cells each

- `timestamp`: 1,517 blank cells

- 19,212 rows with at least one null

- All injected cells were found (`reports/injection_comparison.csv`)



Source: `docs/cleaning_log.md` rows 10 to 17





## Slide 3: Evidence (counts and chart)



**Title:** Evidence: counts and chart



**Table 1: synthetic nulls found vs the answer key (`segments_injected.csv`)**



| Column | In injection log | Measured nulls |

|---|---|---|

| value | 6,070 | 6,070 |

| channel | 3,035 | 3,035 |

| sampling | 3,035 | 3,035 |

| anomaly | 3,035 | 3,035 |

| train | 3,035 | 3,035 |

| timestamp | 1,517 | 1,517 |

| rows with at least one null | 19,212 | 19,212 |



Source: `reports/injection_comparison.csv`. These nulls are SYNTHETIC, injected for the exercise.



**Table 2: real properties of the data (no injection)**



| Check | Result | Source |

|---|---|---|

| `label` column | "anomaly" on all 303,493 rows | cleaning log row 14 |

| `anomaly` = 0 | 203,229 rows | cleaning log row 14 |

| `value` = 0 | 46,671 rows (15.4%), 40,443 in the six photodiode channels | cleaning log rows 2 and 14 |

| Irregular sampling | 151 of 2,123 segments, largest step 130 s | cleaning log row 16 |

| `dataset.csv` | 2,123 rows, 23 columns, 0 nulls, 2,123 distinct segment ids | `reports/dataset_summary.json` |



**Chart:** `reports/nulls_per_column_injected.png` (missing cells per column in `segments_injected.csv`, synthetic).



Not verified: whether the 18 feature values in `dataset.csv` match the raw points.



