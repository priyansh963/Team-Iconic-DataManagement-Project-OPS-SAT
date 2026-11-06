# AI risks

Question we answer: can this data be trusted, reused and fed into an AI model? Sources: docs/decisions.md (finding IDs F-x, D-x, O-x) and docs/data_dictionary.md. Only problems measured in the files are listed. Anything else is marked "to confirm".

## Risks measured in the data

| ID | Risk | Evidence (measured) | Consequence for AI use | Mitigation |
|---|---|---|---|---|
| R-1 | Wrong target column | `label` is "anomaly" on all 303,493 rows, including 203,229 rows where `anomaly` = 0 (F-1) | A model trained on `label` learns nothing | Use `anomaly` as target. `label` removed in the cleaning flow (log entry 1) |
| R-2 | Zeros of unclear meaning | 46,671 rows (15.4%) are exactly 0. Zero share is 15.1% to 46.7% in photodiode channels against 3.0% to 3.5% in magnetometer channels (F-3) | Deleting them blindly may remove real readings. Keeping them may add noise | Rows kept, flag `is_zero` added (log entry 2). Decide per channel |
| R-3 | Feature largely determined by length and sampling | For 1,972 of 2,123 segments, `gaps_squared` = (len - 1) x sampling^2 (F-4) | The feature carries little gap information and may mislead the model | Document it. Do not describe it as a gap measure |
| R-4 | Very uneven time coverage | 85.1% of rows are from June 2022. March, April and May have no rows (F-8) | Conclusions about long-term behaviour are not supported | State the limit in the report |
| R-5 | Possible leakage between train and test | Training and test segments cover the same time span for every channel (F-9). Leakage is not proven | Test scores may be too optimistic | Report as a risk, not as a fact |
| R-6 | Channels on different scales | Magnetometers about -1e-4 to 1e-4, photodiodes 0 to about 1.57 (F-10) | Raw values cannot be pooled | Scale per channel before modelling |
| R-7 | Strong channel imbalance | CADC0873 has 593 segments, CADC0886 only 11, CADC0890 only 14 | Rare channels are poorly represented | Report per channel. Do not pool blindly |
| R-8 | Class imbalance | 434 of 2,123 segments are anomalous (20.4%). 33.0% of point rows belong to anomalous segments | Accuracy alone is misleading | Use metrics suited to imbalance (to confirm with the team) |
| R-9 | Irregular sampling | 151 of 2,123 segments have irregular sampling. 149 contain a gap longer than their step, largest 130 s (F-2). Two sampling rates: 1 s and 5 s | Models that assume regular spacing may be affected | Gap analysis per segment (O-006 still open) |

## Risks from our own work

| ID | Risk | Evidence | Mitigation |
|---|---|---|---|
| R-10 | Synthetic nulls could be mistaken for real data problems | Nulls in `segments_injected.csv` were injected by `src/inject_nulls.py`, seed 42. The real data has no nulls (F-5, D-008) | Label as SYNTHETIC in every slide, table and the report |
| R-11 | Cleaning was not run on the injected file | Cleaning log entries 1-9 were made on the original file. No repair entries for the injected nulls exist yet | Log the repairs and link them to Python functions |
| R-12 | Prep and Python results cannot be compared yet | Python function column in the cleaning log says "TODO (P5)" on every row | Fill it in before the parity check |
| R-13 | Timestamp format changes in Prep output | Prep writes DD-MM-YYYY HH:MM:SS without milliseconds and with a UTF-8 BOM (log entry 9) | Read with `encoding="utf-8-sig"`. Document the change |

## Legal and reuse risks

| ID | Risk | Evidence | Mitigation |
|---|---|---|---|
| R-14 | Two licence statements in one record | Record metadata says CC BY 4.0. Bundled LICENSE says MIT, KP Labs 2024 (F-6) | Credit the authors, cite the record, state what we changed, keep the KP Labs notice |
| R-15 | Authorship differs between record and paper | The record lists only Ruszczak as creator. The paper lists four authors | Cite per the paper and the record |
| R-16 | Upstream documentation errors | The paper text says 1,494 training segments, the file and Table 1 give 1,594 (O-005). An upstream notebook fits on unscaled data and predicts on scaled data | Do not copy the figure or the cell |

## Open points

- Metrics for imbalanced classes (R-8) are not decided.
- The data warehouse owner is unassigned (O-011).