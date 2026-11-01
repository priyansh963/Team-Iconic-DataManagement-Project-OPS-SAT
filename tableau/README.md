# Tableau Prep

- `*.tflx` is the packaged flow and is committed (graded deliverable).
- Save a screenshot of each flow step in `tableau/screenshots/` with the step number in the name
  (for example `step3_calculated_fields.png`), including row counts before and after.
- Keep one flow file name stable (`opssat-cleaning-flow.tflx`) and describe changes in `docs/cleaning_log.md`.
- The `.tflx` embeds unmodified copies of the two input CSVs (about 2.2 MB, decision D-006). Their checksums are in `data/raw/CHECKSUMS.sha256`.
- The flow, in order: inputs `segments` and `dataset`; Clean 1 (remove `label`, add `is_zero`, `class`); Aggregate 1 (one row per segment); Clean 2 on `dataset`; Join 1 (full outer on `segment`); Clean 3 (parity checks); Clean 4 (drop the five duplicate `-1` identifier fields); outputs `data/cleaned/segment_clean.csv` and `data/cleaned/segment_summary.csv`.
- To run it on your machine, open the `.tflx` in Tableau Prep Builder, set each Output to a path inside your clone, and click Run Flow. Expect 303,494 lines (with header) and 2,124 lines.
- Output notes: Prep writes timestamps as `DD-MM-YYYY HH:MM:SS` without milliseconds and adds a UTF-8 byte-order mark. In Python use `encoding="utf-8-sig"`.
- The editable `.tfl` is ignored by Git (it holds absolute paths of one machine).
- `.hyper` extracts are ignored.
