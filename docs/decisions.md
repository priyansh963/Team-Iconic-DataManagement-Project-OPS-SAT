# Decisions, assumptions and open issues

Rule: if it was not measured in the files, it goes in "Unverified", not in a slide.
Format: ID | date | owner | text.

## Decisions

| ID | Date | Owner | Decision | Why |
|---|---|---|---|---|
| D-001 | 2026-11-01 | Priyansh | Raw data is not committed; the README points to the Zenodo version and we record checksums. | Large CSVs suit Git badly, and the licence is not confirmed yet. |
| D-002 | 2026-11-01 | Priyansh | `.tflx` is committed; `.hyper` extracts are ignored. | The flow is a graded deliverable. |
| D-003 | 2026-11-01 | Priyansh | Python pipeline will be standalone functions, not a Tableau Prep Script step. | The Script step needs a TabPy setup, which is a risk close to the deadline. Allowed by the brief. |
| D-004 | 2026-11-01 | Priyansh | Every member pushes their own work on a personal branch and merges by pull request; nobody commits directly to `main`. | Avoids overwriting each other, and Git history shows who did what for the reflection section. |

## Documented in the paper (NOT yet checked against the files)

- Source: Ruszczak et al., Scientific Data 12, 710 (2025). Paper licence is CC BY 4.0.
- Two files on Zenodo: `segments.csv` (telemetry points) and `dataset.csv` (18 features per segment).
- `segments.csv` columns per the paper: `timestamp` (ISO date), `channel`, `value`, `label`, `segment`, `sampling`, `train`.
- 2,123 segments, 9 channels (3 magnetometer, 6 photodiode), 434 anomalous (about 20%).
- Documented quality problems: data gaps, artefacts, sampling-frequency changes, zero values, amplitude variations.

## Unverified / open

| ID | Question | How to settle it | Owner | Status |
|---|---|---|---|---|
| O-001 | Which Zenodo version do we use (v1 has a "newer version" banner), and what are the exact files and sizes? | Read the record page, screenshot it | Priyansh | open |
| O-002 | What licence is stated on the Zenodo record itself (not the paper)? | Record page | Priyansh | open |
| O-003 | Is `timestamp` a real date-time and parsed correctly? | Prep profile pane | Priyansh | open |
| O-004 | Do the two files form a defensible related-tables pair? `dataset.csv` is derived from `segments.csv`, so we describe it honestly as parent (points) and child (per-segment summary), joined on the segment id. Does every segment match? | Join in Prep, count unmatched | Priyansh | open |
| O-005 | Training-set size: the paper text says 1,494 but Table 1 sums to 1,594 (1,273 + 321). Which does the file contain? | Count `train` values | Priyansh | open |
| O-006 | Can Prep compute the time difference between consecutive rows (sampling gaps)? If not, gap analysis moves to Python. | Test on real data | Priyansh | open |
| O-007 | Presentation date and group number. | Ask the course | Priyansh | open |
| O-008 | May other groups pick OPSSAT-AD? | Ask the course | Priyansh | open |
