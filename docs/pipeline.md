# Reproducible repair pipeline (Python)

Owner: Priyansh. Code: `src/cleaning.py` (repair rules), `src/rules.py` (validation), `src/run_pipeline.py` (runner).
The rules mirror the Tableau Prep flow `opssat-cleaning-flow` step by step, so the two can be compared (see `docs/cleaning_log.md`).
Field meanings are in `docs/data_dictionary.md`, not repeated here.

## How to rerun

Prerequisites: the injected file exists (see `data/README.md`, section "Injected working data (SYNTHETIC)"), and `data/raw/dataset.csv` exists (the authors' summary table, used as the benchmark).

Windows (PowerShell, from the repo root, virtual environment active):

```powershell
python -m pip install -r requirements.txt
python -m pytest tests -q          # all tests must pass
python src/run_pipeline.py
```

Mac: the same with `python3`.

Useful option: `python src/run_pipeline.py --upto R3` stops after a rule (R1 to R7).

Expected result on the injected v1 file (seed 42):

```
accounting: 303493 raw = 301976 clean + 1517 quarantined + 0 deleted
parity vs authors: len_diff != 0 in 869 segments, dur_diff != 0 in 26, mean_ok = 0 in 1639, attr_ok = 0 in 0 (of 2123)
```

## Inputs and outputs

| File | What | In Git? |
|---|---|---|
| `data/staging/segments_injected.csv` | input: readings with SYNTHETIC nulls | no, generated (checksum in `data/staging/CHECKSUMS.sha256`) |
| `data/raw/dataset.csv` | input: authors' summary table, benchmark | no, downloaded from Zenodo |
| `data/cleaned/segment_clean_py.csv` | one row per clean reading, with `source_file` | no, regenerated |
| `data/cleaned/quarantine_readings.csv` | rows set aside, each with a `reason` | no, regenerated |
| `data/cleaned/segment_summary_py.csv` | one row per segment, with the parity checks against the authors | no, regenerated |
| `data/cleaned/pipeline_step_log.csv` | rows and fields before and after each rule | no, regenerated |
| `logs/run_log.txt` | one readable block per run, appended, never overwritten | yes (official runs only) |
| `logs/MANIFEST.json` | the latest run: code version, input and output checksums, counts, Python and pandas versions | yes (official runs only) |

All CSV outputs use Unix line endings (`\n`), so the checksums are the same on Windows and Mac.

## Rules (the contract with the Prep flow)

| Rule | Function | What it does | Reaction |
|---|---|---|---|
| R1 | `remove_label` | removes the constant, misleading `label` column | fix |
| R2 | `flag_missing_value` | adds `value_imputed` = 1 where `value` is blank (before R5) | flag |
| R3 | `quarantine_missing_timestamp` | rows without a timestamp cannot be placed in time | quarantine, reason "missing timestamp" |
| R4 | `recover_segment_constants` | fills blank channel, sampling, anomaly, train from the same segment | fix |
| R5 | `impute_value` | fills blank `value` with the segment mean (matches Prep) | fix, flagged by R2 |
| R6 | `add_flags` | adds `is_zero` and `class` | derive |
| V1 | `quarantine_invalid_rows` | checks every row against `src/rules.py` | quarantine, reason names the rule |
| R7a | `summarise_segments` | one row per segment | derive |
| R7b | `compare_with_authors` | compares with the authors' `dataset.csv` | check |

Order matters: R2 before R5 (otherwise the information about which values were blank is lost), R3 before R4.

## Stop or quarantine (policy)

| Situation | Reaction | Where | Why |
|---|---|---|---|
| Input has no rows | **STOP** | `validate_input` | nothing to repair |
| A required column is missing or has the wrong type | **STOP** | `validate_input` | the rules cannot run on a different structure |
| Raw rows != clean + quarantined + deleted | **STOP** | runner, accounting check | rows were lost without a record |
| A rule fails with an unexpected error | **STOP** | Python | the clean output is written only after all rules finish, so no half-finished result appears |
| Row has no timestamp | **QUARANTINE** | R3 | the time cannot be recovered cleanly |
| Row still has a blank after repairs (for example a segment with no known channel) | **QUARANTINE** | V1 | R4 never invents a value |
| Channel not one of the 9 known, sampling not 1 or 5, anomaly or train not 0 or 1, value not finite | **QUARANTINE** | V1 | the row is wrong, the rest of the table is fine |
| Row differs from the majority value of its segment in channel, sampling, anomaly or train | **QUARANTINE** | V1 (custom check) | these are constant per segment, so one odd row is an error |
| Two rows share segment + timestamp | **QUARANTINE** both | V1 | we cannot tell which one is right |
| Blank `value` | **FLAG** (`value_imputed`) and fix | R2, R5 | a measurement is lost, the estimate must stay visible |
| Constant `label` column | **FIX** (remove) | R1 | it carries no information |
| Anything | **DELETE** | nothing is deleted | raw = clean + quarantined + deleted, and deleted is always 0 |

A run that stops at one of the checks above (structure or accounting) ends with an error message and writes a `STOPPED` block into `logs/run_log.txt`, so it is part of the history too.

## Reproducibility

- Same input, same output: `tests/test_pipeline_determinism.py` runs the whole pipeline twice on a tiny synthetic input and compares every output file byte for byte.
- The run log records, for every run: the Git commit (with a warning if `src` or `tests` have uncommitted changes), the input checksum, rows in and out of each rule, the accounting line and the checksum of each output.
- Exact package versions: `requirements-lock.txt` (created with `pip freeze` in the project environment).
- Data versions are marked with Git tags (`injected-v1`, `pipeline-v1`), created on `main` after the pipeline pull request is merged.

## Known finding

`mean_ok = 0` in 1639 segments: 869 lost rows to the quarantine, and 770 lost no rows but had a blank `value` that R5 filled. Imputing with the segment mean keeps the table complete but cannot restore the lost measurement, so the segment mean moves. `injection_log.csv` keeps the original values, so the size of this error can be measured.
