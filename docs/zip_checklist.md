# Final ZIP checklist

Source: README.md (deadlines and ZIP contents). Items not confirmed in the repository files are marked "to confirm".

## Upload

| What | Value |
|---|---|
| Where | Moodle |
| Deadline | Monday 16 Nov 2026, 11:00 PM |
| ZIP name | `DM_Project_Group<Nr>.zip` (group number: to confirm, O-007) |
| Uploaded by | The group lead (who is the group lead: to confirm) |
| Internal target | All members push their parts by Fri 13 Nov 2026, so assembly can start |

## Contents of the ZIP

| # | Item | Responsible | Where it comes from | Status |
|---|---|---|---|---|
| 1 | Slides | to confirm | `reports/` (Anirudh has a branch `anirudh-slides`) | to confirm |
| 2 | Report PDF | Shruthi (assembly) | Parts from all members, see "Report parts" below | not started |
| 3 | `.tflx` Tableau Prep flow | Kalaivani | `tableau/opssat-cleaning-flow.tflx` (already in `main`) | file exists, review to confirm |
| 4 | Notebook / code | Priyansh | `src/`, `notebooks/`, `requirements.txt` | in progress (branch `priyansh-pipeline`) |
| 5 | GitHub link | Priyansh (owner of the repo) | https://github.com/priyansh963/Team-Iconic-DataManagement-Project-OPS-SAT (private: check that the examiner can open it, to confirm) | to confirm |

## Report parts

| Part | Owner | Source file | Status |
|---|---|---|---|
| Dataset, source, licence, metadata, FAIR score | Aditya | `docs/metadata.json` | to confirm |
| Profiling and quality findings | Anirudh | `reports/`, `docs/cleaning_log.md` | in `main` |
| Tableau Prep flow description | Kalaivani | `tableau/`, `docs/cleaning_log.md` | to confirm |
| Reproducible pipeline and rerun instructions | Priyansh | `src/`, `README.md` | in progress |
| Data dictionary | Shruthi | `docs/data_dictionary.md` | done, in `main` |
| Roles | Shruthi | `docs/roles.md` | done, in `main` |
| Lineage | Shruthi | `docs/lineage.md` | done, in `main` |
| AI risks | Shruthi | `docs/ai_risks.md` | done, in `main` |
| Reflection (who did what) | Every member, own row | `docs/reflection.md` | to confirm |

## Checks before zipping

- [ ] Every member's work is merged into `main` (pull requests closed)
- [ ] `git pull` on `main`, so the ZIP is built from the latest version
- [ ] Synthetic nulls are labelled SYNTHETIC in slides and report (D-008)
- [ ] No problem is described in the report unless it was measured (see `docs/decisions.md`)
- [ ] The authors are credited, the record is cited (10.5281/zenodo.15108715), and the KP Labs MIT notice is kept
- [ ] `docs/cleaning_log.md`: the Python function column is filled (it said "TODO (P5)")
- [ ] `docs/reflection.md`: every member's row is filled in, and Priyansh is no longer listed as "Tableau Prep"
- [ ] The `.tflx` opens in Tableau Prep
- [ ] ZIP name is exactly `DM_Project_Group<Nr>.zip` with the real group number
- [ ] ZIP contains slides, report PDF, `.tflx`, notebook/code and the GitHub link
- [ ] Uploaded to Moodle before Mon 16 Nov, 11:00 PM

## Open points

- Group number and presentation date (O-007)
- Who is the group lead and uploads the ZIP
- Data warehouse owner (O-011)
- The presentation: 15 minutes, every member presents (date: to confirm)