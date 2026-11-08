# Warehouse (DuckDB)

One file, `data/curated/opssat.duckdb`, built from the pipeline outputs with one command.
It is generated, so it is not in Git (same rule as the data). Rebuild it any time.

```
python src/run_pipeline.py        # clean the data, write the log and the manifest
python src/load_warehouse.py      # load the outputs into the warehouse (about 3 seconds)
```

## Where it sits

```
raw -> staging -> [ Python pipeline / Tableau Prep ] -> cleaned -> [ load_warehouse.py ] -> curated (DuckDB)
```

Cleaning stays in the pipeline. The warehouse is where the cleaned data is kept, queried and shared.

## Tables

| Table | One row per | Holds |
|---|---|---|
| `fact_reading` | clean reading | segment, timestamp, value, `value_imputed`, `is_zero`, `source_file` |
| `quarantine_reading` | quarantined row | the row as it was, plus `reason` |
| `dim_segment` | segment | channel, sampling, anomaly, train, class |
| `dim_channel` | channel | sensor type (magnetometer or photodiode) |
| `segment_summary` | segment | our summary and the parity checks against the authors (`mean_ok`, `attr_ok`, ...) |
| `segment_features` | segment | the authors' `dataset.csv` features (the benchmark, as published) |
| `load_log` | loaded table | row count, source file, checksum, run id and code version of the pipeline run |

Keys are enforced: a reading cannot point to a segment that does not exist, a segment cannot
point to an unknown channel.

## Views

| View | For |
|---|---|
| `ml_training_set` | the ML engineer: one row per segment, the authors' features plus `class`, `n_readings` and `n_imputed` |
| `v_reading` | analysts: every reading with its channel, sensor type, anomaly and train flags |
| `v_channel_overview` | a first look: segments, readings, imputed values and anomaly segments per channel |

`ml_training_set` takes its features from the authors' file, which was computed on the original
data, not on our repaired readings. `n_imputed` shows how much of a segment we had to repair, so
weak segments can be filtered out.

## Using it

```python
import duckdb
con = duckdb.connect("data/curated/opssat.duckdb", read_only=True)
train = con.sql("SELECT * FROM ml_training_set WHERE train = 1 AND n_imputed = 0").df()
```

Many people can read the file at the same time (`read_only=True`). Only one can write, and the
loader needs the file closed. It deletes and rebuilds the file on every load.

## What the loader refuses

| Situation | Reaction |
|---|---|
| No `logs/MANIFEST.json`, or the run stopped before the summary (R7) | STOP |
| An output file changed after the pipeline logged it (checksum differs) | STOP |
| Loaded rows differ from the run's counts, or raw != readings + quarantined | STOP, nothing is kept |

So the warehouse only ever holds outputs of a logged run, and its `load_log` says which run.

## Sharing across the team

- ML engineer: reads `ml_training_set` from Python.
- Analysts and Tableau: SQL on the views, or an export. Tableau needs an extra driver for DuckDB.
- Governance: `load_log` and the schema describe what is loaded and from where.
- Everyone gets the same database by running the two commands above on the same raw data
  (checked with the checksums). The file can also be passed around in a shared folder.

## Limits

DuckDB is a file, not a server: one writer at a time, no user accounts, no network access.
That is enough for this project. At company scale the same tables would move to a server
warehouse (for example Postgres, BigQuery or Snowflake) with little change to the SQL.
