# Data layers

Nothing in these folders except this file, `.gitkeep`, `raw/CHECKSUMS.sha256` and `staging/CHECKSUMS.sha256`
is committed to Git. The data is reproduced from the public source, not stored here.
The only copy of the raw files in the repo is the one embedded in `tableau/opssat-cleaning-flow.tflx` (decision D-006).

| Folder | Contents | Rule |
|---|---|---|
| `raw/` | Original files exactly as downloaded from Zenodo | Never edited, never re-saved in Excel. Treat as read-only. |
| `staging/` | Working base data for the group: `segments_injected.csv` (synthetic nulls, see below) | Regenerable with `src/inject_nulls.py`. Verify against `staging/CHECKSUMS.sha256`. |
| `cleaned/` | After cleaning and validation | Every change recorded in `docs/cleaning_log.md`. |
| `curated/` | Integrated, documented, AI-ready tables | Only published after the licence is confirmed. |

## Source (to be confirmed)

- Zenodo record from the project brief: https://zenodo.org/records/15108715
- Record: version DOI 10.5281/zenodo.15108715 (concept DOI for all versions: 10.5281/zenodo.12588358). Record created 2025-03-30, original publication date 2024-06-24. The API shows it is the latest version (`is_last: true`).
- Licence in the record metadata (Zenodo API field `license`): CC BY 4.0. The record also bundles a `LICENSE` file saying MIT, Copyright 2024 KP Labs, covering software, data and documentation. See `docs/decisions.md` (F-6).
- Files downloaded 2026-11-01 (measured on the downloaded files):

| File | Size (bytes) | Data rows | MD5 | Matches Zenodo's MD5 |
|---|---|---|---|---|
| `dataset.csv` | 507,550 | 2,123 | 5246fdc5e4630a4cecbf7fb6bc8b795e | yes |
| `segments.csv` | 18,987,091 | 303,493 | 72f109630abb933a386106897a631188 | yes |

- SHA-256 checksums are in `raw/CHECKSUMS.sha256`. Verify a download with:
  `cd data/raw` then `sha256sum -c CHECKSUMS.sha256` (Git Bash) or `certutil -hashfile <file> SHA256` (PowerShell) and compare by eye.

## Injected working data (SYNTHETIC)

The real dataset has no missing values (measured in our audit). On the professor's instruction
we inject synthetic nulls into `segments.csv` only, so the cleaning steps have something to repair.
`dataset.csv` stays exactly as the authors published it and is the benchmark for the parity checks.
Everything below is synthetic and must be labelled as such in slides and report. Decision: D-008.

Create it (from the repo root, needs only the Python standard library):

    python src/inject_nulls.py

This reads `data/raw/segments.csv` (never modified) and writes two files to `data/staging/`:

| File | Content | SHA-256 |
|---|---|---|
| `segments_injected.csv` | Same 303,493 rows and 8 columns as `segments.csv`, with some cells blanked | `352f6ab58aa9eef9db7979dbfa10f5f72457cdd3b7b273e47303554917e63030` |
| `injection_log.csv` | Answer key: `row`, `segment`, `column`, `original` for every blanked cell (19,727) | `cb64461444a641aadd769e70a7ccfda2f07f2b7c6f55d358105d7808043d846b` |

Verify (PowerShell): `certutil -hashfile data\staging\segments_injected.csv SHA256` and compare with the table.
If the hash differs, do not work on that file: check that `data/raw/segments.csv` matches `data/raw/CHECKSUMS.sha256`, then run the script again.

Fixed settings: seed 42, version "injected v1".

| Column | Cells blanked | Share |
|---|---|---|
| `value` | 6,070 | 2% |
| `channel`, `sampling`, `anomaly`, `train` | 3,035 each | 1% each |
| `timestamp` | 1,517 | 0.5% |

19,212 rows have at least one blank cell. The answer key must not be used to hide problems from profiling:
profile `segments_injected.csv` first, then compare your findings with `injection_log.csv`.
