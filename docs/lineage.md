# Data lineage

Sources: docs/decisions.md, docs/cleaning_log.md, data/raw/CHECKSUMS.sha256, data/staging/CHECKSUMS.sha256. Anything not confirmed in those files is marked "to confirm".

## Overview

Zenodo record -> data/raw -> data/staging (synthetic nulls) -> data/cleaned (Python pipeline or Tableau Prep) -> data/curated (DuckDB warehouse)

| Step | Input | Process | Output | Owner | Evidence |
|---|---|---|---|---|---|
| 1. Source | Zenodo record 10.5281/zenodo.15108715 (Ruszczak et al., Sci Data 12, 710, 2025) | Manual download | segments.csv, dataset.csv | Team | Licence CC BY 4.0 plus bundled MIT notice (F-6) |
| 2. Raw | Downloaded files | None. Never modified (D-008) | data/raw/segments.csv (303,493 rows), data/raw/dataset.csv (2,123 rows) | Priyansh | Verified with data/raw/CHECKSUMS.sha256 (both OK) |
| 3. Staging | data/raw/segments.csv | src/inject_nulls.py, seed 42. SYNTHETIC nulls (D-008) | data/staging/segments_injected.csv, injection_log.csv | Priyansh | data/staging/CHECKSUMS.sha256 (both OK). 19,212 rows with at least one null |
| 4. Cleaned (Prep) | Original segments.csv and dataset.csv | Tableau Prep flow tableau/opssat-cleaning-flow.tflx, log entries 1-9 | segment_clean.csv (303,493 rows, 9 fields), segment_summary.csv (2,123 rows, 33 fields) | Flow built by Priyansh per log; assigned owner Kalaivani | Prep outputs are generated, not stored in Git. Parity with Python checked by counts only, not row by row |
| 5. Cleaned (Python) | segments_injected.csv | `src/run_pipeline.py` with rules R1-R6, V1, R7a and R7b (`src/rules.py`, `src/cleaning.py`). Nothing is deleted: 303,493 = 301,976 clean + 1,517 quarantined + 0 deleted | Clean readings, `quarantine_readings.csv` (reason "missing timestamp"), segment summary, `logs/run_log.txt`, `logs/MANIFEST.json` | Priyansh | Cleaning log entries 18-22. Input SHA-256 recorded in `logs/MANIFEST.json`. 53 tests pass |
| 6. Curated | Pipeline outputs | `src/load_warehouse.py` (about 3 seconds). Generated, not in Git (`docs/warehouse.md`) | `data/curated/opssat.duckdb`: 7 tables and 3 views, including `load_log` with row counts, checksums and run id | Priyansh | `tests/test_warehouse.py` (10 tests). Contract: `docs/data_contract.yaml` (24 checks pass) |

## Known gaps

- Prep entries 1-9 were run on the original file. The repairs of the injected nulls (entries 18-22) are made and logged by the Python pipeline; the Prep flow for the injected file has been compared with Python by counts only.
- Prep steps and Python functions are linked in the cleaning log (columns "Prep step" and "Python function"), but no row-by-row comparison of the two outputs exists yet.
- Prep writes timestamps as DD-MM-YYYY HH:MM:SS without milliseconds and with a UTF-8 BOM (log entry 9), so the cleaned files differ in format from the raw ones.
- dataset.csv is derived from segments.csv by the authors (parent/child), and is used as the benchmark.
- The warehouse is built and tested, but its owner is still unassigned (O-011). It is loaded from the checksummed injected file through the pipeline outputs.