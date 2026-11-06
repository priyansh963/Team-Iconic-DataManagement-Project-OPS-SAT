# Roles and ownership

Rule (D-004): everyone pushes their own work on a personal branch and merges by pull request. Only the owner of a file edits it. Others propose changes in a pull request comment or a message.

Source: roles from the project brief; files from the Git history (`git log`, 2026-11-04) and `docs/decisions.md`. Anything not visible in the history is marked "to confirm".

| Role | Person | Files they own | Status |
|---|---|---|---|
| Dataset and FAIR | Aditya | `docs/metadata.json` (to confirm) | to confirm |
| Profiling and quality | Anirudh (branch `anirudh`) | to confirm | no commits beyond `main` yet |
| Tableau Prep | Kalaivani (branch `kalaivani`) | to confirm | no commits beyond `main` yet |
| Reproducible pipeline | Priyansh | `src/inject_nulls.py`, `data/staging/` (segments_injected.csv, injection_log.csv, CHECKSUMS.sha256), `data/raw/CHECKSUMS.sha256`, `docs/decisions.md`, repo setup | committed by `priyansh963` |
| Governance and integration | Shruthi (branch `shruthi-cheruku`) | `docs/data_dictionary.md`, `docs/roles.md`, `docs/lineage.md`, `docs/ai_risks.md`, report assembly | in progress |

## Open points

- The Tableau Prep flow `tableau/opssat-cleaning-flow.tflx` and `data/cleaned/` outputs were committed by `priyansh963` (D-002, D-006, D-007). The assigned Tableau Prep owner is Kalaivani. `docs/reflection.md` still lists Priyansh as "Tableau Prep" and needs correcting by its owner.
- Owner of `docs/cleaning_log.md`: to confirm.
- Data warehouse owner: open (O-011, no owner assigned).
- Group number and presentation date: open (O-007).