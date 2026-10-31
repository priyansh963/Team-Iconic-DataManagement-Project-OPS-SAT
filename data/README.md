# Data layers

Nothing in these folders except this file, `.gitkeep` and `raw/CHECKSUMS.sha256`
is committed to Git. The data is reproduced from the public source, not stored here.

| Folder | Contents | Rule |
|---|---|---|
| `raw/` | Original files exactly as downloaded from Zenodo | Never edited, never re-saved in Excel. Treat as read-only. |
| `staging/` | First standardised copy (types, names, parsed timestamps) | Regenerable. No values changed. |
| `cleaned/` | After cleaning and validation | Every change recorded in `docs/cleaning_log.md`. |
| `curated/` | Integrated, documented, AI-ready tables | Only published after the licence is confirmed. |

## Source (to be confirmed)

- Zenodo record from the project brief: https://zenodo.org/records/15108715
- Exact version used: TODO
- Licence shown on the record page: TODO
- Files, sizes and SHA-256 checksums: record them in `raw/CHECKSUMS.sha256` after download.
