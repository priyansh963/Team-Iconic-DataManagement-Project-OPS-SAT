# Data layers

Nothing in these folders except this file, `.gitkeep` and `raw/CHECKSUMS.sha256`
is committed to Git. The data is reproduced from the public source, not stored here.
The only copy of the raw files in the repo is the one embedded in `tableau/opssat-cleaning-flow.tflx` (decision D-006).

| Folder | Contents | Rule |
|---|---|---|
| `raw/` | Original files exactly as downloaded from Zenodo | Never edited, never re-saved in Excel. Treat as read-only. |
| `staging/` | First standardised copy (types, names, parsed timestamps) | Regenerable. No values changed. |
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
