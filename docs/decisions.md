# Decisions, assumptions and open issues

Rule: if it was not measured in the files, it goes in "Unverified", not in a slide.
Format: ID | date | owner | text.

## Decisions

| ID | Date | Owner | Decision | Why |
|---|---|---|---|---|
| D-001 | 2026-11-01 | Priyansh | Raw data files are not committed as files in `data/raw/`; the README points to the Zenodo version and we record checksums. Exception: see D-006. | Large CSVs suit Git badly. The licence is now confirmed (CC BY 4.0 on the record, MIT in the bundled LICENSE). |
| D-002 | 2026-11-01 | Priyansh | `.tflx` is committed; `.hyper` extracts are ignored. | The flow is a graded deliverable. |
| D-003 | 2026-11-01 | Priyansh | Python pipeline will be standalone functions, not a Tableau Prep Script step. | The Script step needs a TabPy setup, which is a risk close to the deadline. Allowed by the brief. |
| D-004 | 2026-11-01 | Priyansh | Every member pushes their own work on a personal branch and merges by pull request; nobody commits directly to `main`. | Avoids overwriting each other, and Git history shows who did what for the reflection section. |
| D-005 | 2026-11-01 | Priyansh | `actual_baseline/` (KP Labs code and licence) stays unmodified as third-party reference. Our own work goes in `src/` and `notebooks/`. | Keeps provenance clean. The upstream notebooks read `data/segments.csv`, our files live in `data/raw/`, so we copy and adapt rather than edit them. |
| D-006 | 2026-11-01 | Priyansh | The committed packaged flow `tableau/opssat-cleaning-flow.tflx` (2.2 MB) embeds unmodified copies of `segments.csv` and `dataset.csv`. We accept this. The embedded files are identified by the checksums in `data/raw/CHECKSUMS.sha256` (md5 and sha256 of the Zenodo files). | Tableau packages input data into a `.tflx`. Committing it lets anyone open and run the flow without setup, which supports the reproducibility criterion. Redistribution is allowed by CC BY 4.0 and MIT if we credit the authors, cite the version DOI and keep the KP Labs notice (README and `data/README.md` do). Cost is small (2.2 MB compressed). |
| D-007 | 2026-11-01 | Priyansh | The flow file keeps Prep's name `opssat-cleaning-flow` (hyphens). Output files are `data/cleaned/segment_clean.csv` (reading level, 303,493 rows, 9 fields) and `data/cleaned/segment_summary.csv` (one row per segment, 2,123 rows, 33 fields). The editable `.tfl` stays out of Git. | Matches what Prep produced, so docs and files agree. Names in the docs were changed to match. |

## Documented in the paper (NOT yet checked against the files)

- Source: Ruszczak et al., Scientific Data 12, 710 (2025). Paper licence is CC BY 4.0.
- Two files on Zenodo: `segments.csv` (telemetry points) and `dataset.csv` (18 features per segment).
- `segments.csv` columns per the paper: `timestamp` (ISO date), `channel`, `value`, `label`, `segment`, `sampling`, `train`.
- 2,123 segments, 9 channels (3 magnetometer, 6 photodiode), 434 anomalous (about 20%).
- Documented quality problems: data gaps, artefacts, sampling-frequency changes, zero values, amplitude variations.

## Seen in the Zenodo preview (2026-11-01, first rows only, NOT yet measured in the full files)

- Record page preview for 15108715 lists two files: `segments.csv` and `dataset.csv`. `dataset.csv` is 507.6 kB; the Files header shows 19.5 MB in total, so `segments.csv` is roughly 19 MB (inferred, confirm after download).
- `segments.csv` columns as displayed: channel, timestamp, value, label, sampling, anomaly, segment, train. The paper does not list an `anomaly` column, so the paper and the file differ here.
- `timestamp` looks like ISO 8601 UTC with milliseconds and a Z suffix (example: 2022-06-01T23:42:54.000Z), one reading per second in the first rows.
- `label` shows the text "anomaly" while `anomaly` shows 1 on the same rows. Check whether the two always agree.
- `dataset.csv` columns as displayed: segment, anomaly, train, channel, sampling, duration, len, mean, and more to the right. It repeats segment, anomaly, train, channel and sampling, which gives us consistency checks between the two tables.
- A licence text was open next to the browser: "MIT License for OPS-SAT Dataset, Copyright (c) 2024 KP Labs", covering "software, data and associated documentation files". It is the `LICENSE` file bundled in the Zenodo record itself (confirmed by checksum).

## Measured on the downloaded files (2026-11-01)

- `dataset.csv`: 507,550 bytes, 2,123 data rows (matches the 2,123 segments in the paper), 23 columns: segment, anomaly, train, channel, sampling plus the 18 features named in the paper.
- `segments.csv`: 18,987,091 bytes, 303,493 data rows (line count minus header; assumes no line breaks inside fields), 8 columns: channel, timestamp, value, label, sampling, anomaly, segment, train.
- `dataset.csv` MD5 equals the value shown on the Zenodo record. `segments.csv` MD5 not yet compared with Zenodo.
- Files use LF line endings.

## Measured findings from the full-file audit (2026-11-01, stdlib Python over both CSVs)

Relational structure
- Both files hold exactly the same 2,123 segment ids: 0 orphans in either direction, no duplicate ids in `dataset.csv`.
- `channel`, `sampling`, `anomaly` and `train` agree between the two files for every segment, and are constant inside every segment of `segments.csv`.
- `dataset.len` equals the point count and `dataset.duration` equals last minus first timestamp for all 2,123 segments.
- The upstream notebook `dataset_generator.ipynb` shows `dataset.csv` is computed from `segments.csv` (group by segment, take the first row's `anomaly`, `train`, `channel`, `sampling`). So the pair is parent (points) and child (derived per-segment summary), and the data confirms the derivation is consistent. We describe it that way and never as two independent tables.

- Reproduced inside Tableau Prep (Aggregate + full outer Join + Clean 3): 2,123 matched, 0 unmatched either side; reading count and duration match `dataset.csv` for every segment; channel, anomaly, train and sampling agree for every segment; mean value agrees within 1e-12. This covers 3 of the 18 features (len, duration, mean), not the other 15.

Date column
- All 303,493 timestamps match the ISO 8601 form `YYYY-MM-DDTHH:MM:SS.mmmZ`. No duplicate timestamps and no out-of-order timestamps inside any segment.

Counts that settle earlier doubts
- `train` is 1 for 1,594 segments (1,273 nominal + 321 anomalous) and 0 for 529 (416 + 113). This matches the paper's Table 1. The paper's running text says 1,494 training segments, which is a typo relative to its own table and the file (O-005).
- 434 of 2,123 segments are anomalous (20.4%). 100,264 of 303,493 point rows (33.0%) belong to anomalous segments.
- 9 channels, very uneven: CADC0873 has 593 segments, CADC0886 only 11 and CADC0890 only 14. `sampling` takes two values, 1 and 5 (seconds between readings).

Quality findings (real, measured)
- F-1 `label` in `segments.csv` contains the single value "anomaly" on all 303,493 rows, including the 203,229 rows where `anomaly` = 0. The column is constant and contradicts the real flag. Anyone using `label` as the target gets nonsense. `anomaly` is the usable target (answers O-009).
- F-2 Sampling is not regular in 151 of 2,123 segments: `gaps_squared` differs from the value expected for perfectly regular spacing. 149 segments contain a gap longer than their sampling step, the largest being 130 s. No gap reaches 24 h.
- F-3 46,671 rows (15.4%) have value exactly 0: 13,535 in anomalous rows (13.5% of those) and 33,136 in nominal rows (16.3%). Zeros are not specific to anomalies. Whether they are faults or legitimate readings must be judged per channel.
- F-4 `gaps_squared` does not measure gaps only. In the generator it is the sum of squared time differences over all consecutive readings, so a perfectly regular segment gets (len - 1) x sampling^2 (verified: 1,972 of 2,123 segments match this exactly; segment 1 has len 280 and gaps_squared 279). The paper describes it as the squared number of missing points. Consequence: the feature is largely a function of segment length and sampling, which is an AI-readiness risk.
- F-5 No empty cells and no non-numeric or NaN values in either file.

- F-7 Timestamps: 86,016 distinct values for 303,493 rows, because the 9 channels are recorded at the same moments. This is NOT duplication: all 303,493 (channel, timestamp) pairs are unique, and no pair appears in more than one segment.
- F-8 Time coverage is very uneven. Range 2022-01-04 to 2022-06-02. Rows per month: January 39,210; February 6,151; March, April and May none; June 258,132 (85.1% of all rows). The authors selected "interesting" fragments, so this is a property of the selection, and it limits what the data can claim about long-term behaviour.
- F-9 Train and test are interleaved in time. For every channel the training and test segments cover the same time span (the authors split by stratified random sampling). No point appears twice, so there is no row-level overlap, but neighbouring segments can sit on both sides of the split. Leakage risk to test, not proven.
- F-10 Channels live on different scales. Magnetometer channels CADC0872/0873/0874 range about -1e-4 to 1e-4. Photodiode channels CADC0884/0886/0888/0890/0892/0894 range from exactly 0 up to about 1.57. Raw values cannot be pooled without per-channel scaling.
- F-3 refinement: the zeros sit mostly in the photodiode channels. Zero share per channel: CADC0894 46.7%, CADC0892 36.1%, CADC0888 33.1%, CADC0886 31.6%, CADC0890 21.1%, CADC0884 15.1%, against 3.0-3.5% for the three magnetometer channels. The photodiode minimum is exactly 0, so zeros may be a physical floor and not a fault. Decide per channel, never delete blindly.

Honest assessment: structurally the data is very clean (no nulls, no duplicates, no orphans). The real problems are signal-level (irregular sampling, zeros, heterogeneous sampling rate, strong channel imbalance) and documentation-level (constant `label`, `gaps_squared` definition, the 1,494 typo). The cleaning story must be built on these, and must not invent defects.

Licence
- The record's own metadata (Zenodo API, read 2026-11-01) states `"license": {"id": "cc-by-4.0"}`.
- `actual_baseline/LICENSE` is "MIT License for OPS-SAT Dataset, Copyright (c) 2024 KP Labs", covering "software, data and associated documentation files". That text is what was open in the editor. Copies must keep that copyright notice. The Zenodo record's own licence field is still not confirmed (O-002).

- F-6 Two licence statements in one record: the metadata says CC BY 4.0, the bundled LICENSE file says MIT (KP Labs, 2024, covering software, data and documentation). Both are open and both require credit, so they do not conflict in practice. We comply with both: credit the authors and cite the record, state what we changed, keep the KP Labs copyright and MIT notice with any copied code or data. The inconsistency itself is a FAIR reusability finding for the original dataset (R1.1: one clear licence in the metadata).
- Record contents: the Zenodo record bundles the code with the data. All six files (including `actual_baseline/*`) match the record's sizes and MD5 checksums exactly. `segments.csv` MD5 72f109630abb933a386106897a631188 equals Zenodo's.
- Record creator field lists only Bogdan Ruszczak; Kotowski, Evans and Nalepa appear as contributors. The paper lists all four as authors. Cite per the paper and the record.

Upstream example notebook, small catch
- `modeling_examples.ipynb`, last cell fits an Isolation Forest on the unscaled `X_train` but predicts on the scaled `X_test2`. Only matters if we reuse that cell.

## Unverified / open

| ID | Question | How to settle it | Owner | Status |
|---|---|---|---|---|
| O-001 | Which Zenodo version and files? | API metadata | Priyansh | answered: version DOI 10.5281/zenodo.15108715, latest version of concept 10.5281/zenodo.12588358, six files (segments.csv, dataset.csv, LICENSE, dataset_generator.ipynb, modeling_examples.ipynb, requirements.txt). No human-readable version label was visible in the metadata we saw. |
| O-002 | Licence of the record | API metadata `license` | Priyansh | answered: CC BY 4.0 in the record metadata, plus a bundled MIT LICENSE file (see F-6). The web page did not show it prominently. |
| O-003 | Does Prep parse `timestamp` as a date-time, and are there invalid or duplicate timestamps? Format looks ISO 8601 in the preview. | Prep profile pane | Priyansh | partly answered: Prep auto-detected `timestamp` as Date & Time on import (no manual conversion needed). Checked segment 261 against the raw file: Prep shows 03:09:58 for raw 2022-06-02T03:09:58.000Z, so no time-zone shift; Prep displays dates as dd/mm/yyyy. Null count after parsing still to read in a Clean step. |
| O-004 | Do the two files form a defensible related-tables pair? `dataset.csv` is derived from `segments.csv`, so we describe it honestly as parent (points) and child (per-segment summary), joined on the segment id. Does every segment match? | Join in Prep, count unmatched | Priyansh | answered: see findings, derived parent/child, no orphans |
| O-005 | Training-set size: the paper text says 1,494 but Table 1 sums to 1,594 (1,273 + 321). Which does the file contain? | Count `train` values | Priyansh | answered: file has 1,594; paper text typo |
| O-006 | Can Prep compute the time difference between consecutive rows (sampling gaps)? If not, gap analysis moves to Python. | Test on real data | Priyansh | open |
| O-007 | Presentation date and group number. | Ask the course | Priyansh | open |
| O-008 | May other groups pick OPSSAT-AD? | Ask the course | Priyansh | open |
| O-009 | `label` (text) and `anomaly` (0/1) in `segments.csv`: do they always agree? | Cross-tab in Prep | Priyansh | answered: `label` is constant, use `anomaly` |
| O-010 | Do `channel`, `anomaly`, `train` and `sampling` agree per `segment` between the two files, and does each `segment` appear exactly once in `dataset.csv`? | Join and compare in Prep | Priyansh | answered: all consistent |
