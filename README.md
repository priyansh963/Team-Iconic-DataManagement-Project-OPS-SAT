# Beyond Earth: a FAIR, AI-ready spacecraft telemetry data product (ESA OPS-SAT)

Group exam project for *Data Management* (Prof. Dr. Mehrdad Jalali), SRH University of Applied Sciences Heidelberg.

**Question every group answers:** *Can this data be trusted, reused and fed into an AI model, and how do we prove it?*

**Our dataset:** OPSSAT-AD, real telemetry from the ESA OPS-SAT CubeSat with expert anomaly labels
(Ruszczak, Kotowski, Evans, Nalepa; *Scientific Data* 12, 710, 2025, https://doi.org/10.1038/s41597-025-05035-3).

## Status

Early setup. Nothing below has been checked against the real files yet. See `docs/decisions.md` for what is verified and what is still open.

## Deadlines

| What | When |
|---|---|
| Moodle upload (ZIP with slides, report PDF, `.tflx`, notebook/code, GitHub link) | Monday 16 Nov 2026, 11:00 PM |
| Presentation (15 min, every member presents) | TODO: confirm date |

ZIP name: `DM_Project_Group<Nr>.zip`, uploaded by the group lead.

## Source data

- Zenodo record used: https://zenodo.org/records/15108715 (version and licence: TODO, see `data/README.md`)
- The original files are **not** stored in this repo. Download them into `data/raw/` and record checksums.

## Repository layout

```
data/        raw -> staging -> cleaned -> curated (contents not committed, see data/README.md)
src/         reusable Python functions (load, validate, profile, clean, KPIs, export)
notebooks/   profiling and the Python vs Tableau Prep parity check
tests/       checks that the functions behave
tableau/     the .tflx flow and step screenshots
docs/        decisions, cleaning log, data dictionary, metadata, reflection
reports/     slides and report PDF
```

## Setup

```
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

## Working agreement

- Everyone pushes their own work, each under their own name (`git config user.name` and `user.email` set on your machine). Git history is our evidence for "who did what".
- Never commit directly to `main`. Work on your own branch (for example `p3-profiling`, `p4-tableau`, `p5-pipeline`) and merge by pull request.
- Run `git pull` before you start and before you push. Keep commits small, with clear messages.
- Only the owner of a file edits it. The `.tflx` flow is a binary file that Git cannot merge, so only P4 changes it.
- Every assumption and decision goes into `docs/decisions.md` with a date and an owner.
- Never edit files in `data/raw/`. Never describe a data problem in a slide or the report unless it was measured in the files.

## Licence

Our code: MIT (`LICENSE`). The OPSSAT-AD data keeps its own licence and must be credited to its authors;
any change we make to it must be described. Check the licence on the Zenodo record before redistributing any data.
