# Data lineage

Sources: docs/decisions.md, docs/cleaning_log.md, data/raw/CHECKSUMS.sha256, data/staging/CHECKSUMS.sha256. Anything not confirmed in those files is marked "to confirm".

## Overview

Zenodo record -> data/raw -> data/staging (synthetic nulls) -> data/cleaned -> data/curated

| Step | Input | Process | Output | Owner | Evidence |
|---|---|---|---|---|---|
| 1. Source | Zenodo record 10.5281/zenodo.15108715 (Ruszczak et al., Sci Data 12, 710, 2025) | Manual download | segments.csv, dataset.csv | Team | Licence CC BY 4.0 plus bundled MIT notice (F-6) |
| 2. Raw | Downloaded files | None. Never modified (D-008) | data/raw/segments.csv (303,493 rows), data/raw/dataset.csv (2,123 rows) | Priyansh | Verified with data/raw/CHECKSUMS.sha256 (both OK) |
| 3. Staging | data/raw/segments.csv | src/inject_nulls.py, seed 42. SYNTHETIC nulls (D-008) | data/staging/segments_injected.csv, injection_log.csv | Priyansh | data/staging/CHECKSUMS.sha256 (both OK). 19,212 rows with at least one null |
| 4. Cleaned (Prep) | Original segments.csv and dataset.csv | Tableau Prep flow tableau/opssat-cleaning-flow.tflx, log entries 1-9 | segment_clean.csv (303,493 rows, 9 fields), segment_summary.csv (2,123 rows, 33 fields) | Flow built by Priyansh per log; assigned owner Kalaivani | Outputs are not in the repository (data/cleaned/ is empty after cloning) |
| 5. Cleaned (Python) | segments_injected.csv | Reusable Python functions | to confirm | Priyansh | Cleaning log lists "TODO (P5)" for every step |
| 6. Curated | to confirm | to confirm | data/curated | to confirm | Not started in the files |

## Known gaps

- Prep entries 1-9 were run on the original file, not on segments_injected.csv. Repairs of the injected nulls are announced in the cleaning log but no entries exist yet.
- Python function names are not linked to Prep steps yet, so the parity check cannot be traced.
- Prep writes timestamps as DD-MM-YYYY HH:MM:SS without milliseconds and with a UTF-8 BOM (log entry 9), so the cleaned files differ in format from the raw ones.
- dataset.csv is derived from segments.csv by the authors (parent/child), and is used as the benchmark.
- The data warehouse load is unassigned (O-011). It must use the exact checksummed injected file.