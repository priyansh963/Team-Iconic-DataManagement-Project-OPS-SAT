# Tableau Prep

- `*.tflx` is the packaged flow and is committed (graded deliverable).
- Save a screenshot of each flow step in `tableau/screenshots/` with the step number in the name
  (for example `step3_calculated_fields.png`), including row counts before and after.
- Keep one flow file name stable (`opssat-cleaning-flow.tflx`) and describe changes in `docs/cleaning_log.md`.
- The `.tflx` embeds unmodified copies of the two input CSVs (about 2.2 MB, decision D-006). Their checksums are in `data/raw/CHECKSUMS.sha256`.
- The flow, in order: inputs `segments` and `dataset`; Clean 1 (remove `label`, add `is_zero`, `class`); Aggregate 1 (one row per segment); Clean 2 on `dataset`; Join 1 (full outer on `segment`); Clean 3 (parity checks); Clean 4 (drop the five duplicate `-1` identifier fields); outputs `data/cleaned/segment_clean.csv` and `data/cleaned/segment_summary.csv`.
- To run it on your machine, open the `.tflx` in Tableau Prep Builder, set each Output to a path inside your clone, and click Run Flow. Expect 303,494 lines (with header) and 2,124 lines.
- Output notes: Prep writes timestamps as `DD-MM-YYYY HH:MM:SS` without milliseconds and adds a UTF-8 byte-order mark. In Python use `encoding="utf-8-sig"`.
- The editable `.tfl` is ignored by Git (it holds absolute paths of one machine).
- `.hyper` extracts are ignored.

## Flow on the injected data: `opssat-cleaning-flow-injected.tflx`

**The embedded `segments_injected.csv` is SYNTHETIC.** Nulls were injected on purpose (seed 42) into a copy of
`segments.csv`; the real data has no nulls. The second embedded file, `dataset.csv`, is unmodified and is the benchmark.
Checksum of the synthetic file: `data/staging/CHECKSUMS.sha256` (SHA-256 ends in `...e63030`). Embedding it is accepted
under decision D-006; it must stay labelled synthetic wherever it is shown.

The flow follows the same rules as the Python pipeline (`docs/pipeline.md`), so the two outputs can be compared.

Steps, in order:

1. **flag value_imputed**: remove `label`; add `value_imputed = IF ISNULL([value]) THEN 1 ELSE 0 END` (before any imputation).
2. The flow then splits on `timestamp`:
   - **timestamp split clean branch**: filter `NOT ISNULL([timestamp])`; continues to step 3.
   - **timestamp split quarantine branch**: filter `ISNULL([timestamp])`; add `reason = "missing timestamp"` as the last
     column; output `data/cleaned/quarantine_readings_prep.csv`. Rows are quarantined, not dropped.
3. **recover and impute**: per segment, `{FIXED [segment] : ...}` helper fields plus `IFNULL` (Prep does not allow an LOD
   inside `IFNULL`): `channel` MIN, `sampling`/`anomaly`/`train` MAX, `value` AVG; helpers removed afterwards.
4. **flags**: `is_zero`, `class`; output `data/cleaned/segment_clean_injected.csv` (one row per reading).
5. **agg prep** (duplicate `timestamp`) → **aggregate per segment** → **rename aggregates**
   (`n_readings`, `ts_start`, `ts_end`, `mean_value`, `n_zero`, `n_imputed`).
6. **benchmark pass-through** on `dataset` → **join benchmark** (full outer on `segment`).
7. **parity checks**: `len_diff`, `dur_diff`, `mean_diff`, `mean_ok`, `attr_ok`.
8. **drop duplicate ids** (removes the five `-1` columns after the join, no rows); output
   `data/cleaned/segment_summary_injected.csv` (one row per segment).

To run it:

1. Run `python src/inject_nulls.py` and check the checksum above (only needed if you want the file outside the `.tflx`).
2. Open `tableau/opssat-cleaning-flow-injected.tflx` in Tableau Prep Builder.
3. In each of the three Output steps, set the location to `data/cleaned/` inside your clone.
4. Click **Run Flow**.

Expected results (synthetic injected v1 file):

| Output | Rows |
|---|---|
| `segment_clean_injected.csv` | 301,976 |
| `quarantine_readings_prep.csv` | 1,517, all `reason = missing timestamp` |
| `segment_summary_injected.csv` | 2,123 |

301,976 + 1,517 = 303,493 input rows. Sum of `value_imputed` in the clean output: 6,040.
Parity: `len_diff` not 0 in 869 segments, `dur_diff` not 0 in 26, `mean_ok = 0` in 1,639, `attr_ok = 0` in 0.

Outputs are not committed (CSV files are git-ignored). Screenshots of the changed steps:
`step1_flag_value_imputed.png`, `step1b_timestamp_split.png`, `step8b_quarantine_output.png`, `step9_self_check.png`.
