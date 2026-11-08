"""Load the pipeline outputs into a DuckDB warehouse: one file, one command.

    python src/load_warehouse.py            # --root . ; run src/run_pipeline.py first

Reads : data/cleaned/segment_clean_py.csv, quarantine_readings.csv, segment_summary_py.csv
        data/raw/dataset.csv       (the authors' segment features, the benchmark)
        logs/MANIFEST.json         (checksums of the outputs of the latest pipeline run)
Writes: data/curated/opssat.duckdb (rebuilt from scratch every time, so a load is repeatable)

Only outputs of a LOGGED run are loaded: every file must match its checksum in MANIFEST.json,
and raw = loaded readings + loaded quarantined rows must still add up (the Chapter 2 accounting).
Tables and views are described in docs/warehouse.md.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

import rules as r
from run_pipeline import sha256_of

WAREHOUSE = Path("data") / "curated" / "opssat.duckdb"
MAGNETOMETERS = ("CADC0872", "CADC0873", "CADC0874")  # the other channels are photodiodes

QUARANTINE_COLUMNS = ["segment", "timestamp", "channel", "value", "sampling", "anomaly", "train",
                      "value_imputed", "is_zero", "class", "reason", "source_file"]

SCHEMA = """
CREATE TABLE dim_channel (
    channel     VARCHAR PRIMARY KEY,
    sensor_type VARCHAR NOT NULL
);
CREATE TABLE dim_segment (
    segment  INTEGER PRIMARY KEY,
    channel  VARCHAR NOT NULL REFERENCES dim_channel (channel),
    sampling INTEGER NOT NULL,
    anomaly  INTEGER NOT NULL,
    train    INTEGER NOT NULL,
    class    VARCHAR NOT NULL
);
CREATE TABLE fact_reading (
    reading_id    INTEGER PRIMARY KEY,
    segment       INTEGER NOT NULL REFERENCES dim_segment (segment),
    "timestamp"   TIMESTAMPTZ NOT NULL,
    value         DOUBLE NOT NULL,
    value_imputed TINYINT NOT NULL,
    is_zero       TINYINT NOT NULL,
    source_file   VARCHAR NOT NULL
);
CREATE TABLE quarantine_reading (
    quarantine_id INTEGER PRIMARY KEY,
    segment       INTEGER,
    "timestamp"   TIMESTAMPTZ,
    channel       VARCHAR,
    value         DOUBLE,
    sampling      INTEGER,
    anomaly       INTEGER,
    train         INTEGER,
    value_imputed TINYINT,
    is_zero       TINYINT,
    class         VARCHAR,
    reason        VARCHAR NOT NULL,
    source_file   VARCHAR
);
CREATE TABLE segment_summary (
    segment       INTEGER PRIMARY KEY REFERENCES dim_segment (segment),
    n_readings    INTEGER NOT NULL,
    timestamp_min TIMESTAMPTZ,
    timestamp_max TIMESTAMPTZ,
    mean_value    DOUBLE,
    n_zero        INTEGER NOT NULL,
    n_imputed     INTEGER NOT NULL,
    len_diff      DOUBLE,
    dur_diff      DOUBLE,
    mean_diff     DOUBLE,
    mean_ok       TINYINT,
    attr_ok       TINYINT
);
CREATE TABLE load_log (
    table_name VARCHAR PRIMARY KEY,
    row_count  BIGINT NOT NULL,
    source     VARCHAR NOT NULL,
    sha256     VARCHAR,
    run_id     VARCHAR,
    code       VARCHAR,
    loaded_at  TIMESTAMPTZ NOT NULL
);
"""

VIEWS = """
CREATE VIEW v_reading AS
SELECT f.reading_id, f.segment, f."timestamp", f.value, f.value_imputed, f.is_zero,
       s.channel, c.sensor_type, s.sampling, s.anomaly, s.train, s.class
FROM fact_reading f
JOIN dim_segment s ON s.segment = f.segment
JOIN dim_channel c ON c.channel = s.channel;

-- One row per segment for the ML engineer: the authors' features, plus how much of the
-- segment we had to repair (n_imputed) so weak segments can be filtered out.
CREATE VIEW ml_training_set AS
SELECT s.segment, s.channel, s.sampling, s.anomaly, s.train, s.class,
       m.n_readings, m.n_imputed,
       f.* EXCLUDE (segment, anomaly, train, channel, sampling)
FROM dim_segment s
JOIN segment_features f ON f.segment = s.segment
JOIN segment_summary m ON m.segment = s.segment;

CREATE VIEW v_channel_overview AS
SELECT c.channel, c.sensor_type,
       count(s.segment)                      AS segments,
       CAST(coalesce(sum(m.n_readings), 0) AS BIGINT) AS readings,
       CAST(coalesce(sum(m.n_imputed), 0) AS BIGINT)  AS imputed_values,
       CAST(coalesce(sum(s.anomaly), 0) AS BIGINT)    AS anomaly_segments
FROM dim_channel c
LEFT JOIN dim_segment s ON s.channel = c.channel
LEFT JOIN segment_summary m ON m.segment = s.segment
GROUP BY c.channel, c.sensor_type
ORDER BY c.channel;
"""


class WarehouseStop(RuntimeError):
    """The load must not go on (missing file, changed file, numbers that do not add up)."""


def verify_against_manifest(root: Path, files: list[Path]) -> dict:
    """Return the manifest of the latest run, after checking every file we load against it."""
    path = root / "logs" / "MANIFEST.json"
    if not path.exists():
        raise WarehouseStop("logs/MANIFEST.json not found: run src/run_pipeline.py first")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for f in files:
        rel = f.relative_to(root).as_posix()
        if not f.exists():
            raise WarehouseStop("%s not found: run src/run_pipeline.py first" % rel)
        if rel not in manifest["outputs"]:
            raise WarehouseStop("%s is not in the manifest: run the full pipeline (R1 to R7)" % rel)
        if sha256_of(f) != manifest["outputs"][rel]:
            raise WarehouseStop("%s changed after the pipeline run logged it: run it again" % rel)
    return manifest


def read_inputs(root: Path) -> tuple[dict, dict]:
    """Read every input table. Returns (tables, manifest)."""
    cleaned = root / "data" / "cleaned"
    clean_path = cleaned / "segment_clean_py.csv"
    summary_path = cleaned / "segment_summary_py.csv"
    quarantine_path = cleaned / "quarantine_readings.csv"
    needed = [clean_path, summary_path]
    has_quarantine = quarantine_path.exists()
    if has_quarantine:
        needed.append(quarantine_path)
    manifest = verify_against_manifest(root, needed)
    if not has_quarantine and manifest["counts"]["quarantined"] != 0:
        raise WarehouseStop("quarantine_readings.csv is missing but the run quarantined rows")

    tables = {
        "clean": pd.read_csv(clean_path, parse_dates=["timestamp"]),
        "summary": pd.read_csv(summary_path, parse_dates=["timestamp_min", "timestamp_max"]),
        "quarantine": (pd.read_csv(quarantine_path, parse_dates=["timestamp"])
                       if has_quarantine else pd.DataFrame(columns=QUARANTINE_COLUMNS)),
        "features": pd.read_csv(root / "data" / "raw" / "dataset.csv"),
    }
    if tables["features"]["segment"].duplicated().any():
        raise WarehouseStop("dataset.csv has a segment more than once")
    return tables, manifest


def build(con: duckdb.DuckDBPyConnection, tables: dict) -> None:
    """Create the tables, fill them (parents first, so the foreign keys hold), then the views."""
    con.execute(SCHEMA)
    summary, clean = tables["summary"], tables["clean"]

    channels = pd.DataFrame({"channel": list(r.CHANNELS)})
    channels["sensor_type"] = ["magnetometer" if c in MAGNETOMETERS else "photodiode"
                               for c in channels["channel"]]
    segments = summary[["segment", "channel", "sampling", "anomaly", "train"]].copy()
    segments["class"] = ["anomaly" if a == 1 else "nominal" for a in segments["anomaly"]]  # as in R6
    fact = clean[["segment", "timestamp", "value", "value_imputed", "is_zero", "source_file"]].copy()
    fact.insert(0, "reading_id", range(1, len(fact) + 1))
    quarantine = tables["quarantine"].reindex(columns=QUARANTINE_COLUMNS)
    quarantine.insert(0, "quarantine_id", range(1, len(quarantine) + 1))
    parity = summary.drop(columns=["channel", "anomaly", "train", "sampling"])
    for col in ("len_diff", "dur_diff", "mean_diff"):
        parity[col] = pd.to_numeric(parity[col]).astype("float64")

    for name, frame in (("dim_channel", channels), ("dim_segment", segments),
                        ("fact_reading", fact), ("quarantine_reading", quarantine),
                        ("segment_summary", parity)):
        con.register("incoming", frame)
        columns = ", ".join('"%s"' % c for c in frame.columns)
        con.execute('INSERT INTO %s (%s) SELECT %s FROM incoming' % (name, columns, columns))
        con.unregister("incoming")
    con.register("incoming", tables["features"])
    con.execute("CREATE TABLE segment_features AS SELECT * FROM incoming")
    con.unregister("incoming")
    con.execute(VIEWS)


def check_and_log(con: duckdb.DuckDBPyConnection, root: Path, manifest: dict) -> dict:
    """Accounting inside the warehouse, then one load_log row per table."""
    count = lambda t: con.execute("SELECT count(*) FROM %s" % t).fetchone()[0]
    counts = manifest["counts"]
    n_fact, n_quarantine = count("fact_reading"), count("quarantine_reading")
    if n_fact != counts["clean"] or n_quarantine != counts["quarantined"]:
        raise WarehouseStop("loaded %d readings and %d quarantined rows, the run logged %d and %d"
                            % (n_fact, n_quarantine, counts["clean"], counts["quarantined"]))
    if counts["raw"] != n_fact + n_quarantine:
        raise WarehouseStop("ACCOUNTING FAILED: %d raw != %d readings + %d quarantined"
                            % (counts["raw"], n_fact, n_quarantine))
    sources = {
        "fact_reading": "data/cleaned/segment_clean_py.csv",
        "quarantine_reading": "data/cleaned/quarantine_readings.csv",
        "segment_summary": "data/cleaned/segment_summary_py.csv",
        "dim_segment": "data/cleaned/segment_summary_py.csv",
        "segment_features": "data/raw/dataset.csv",
        "dim_channel": "src/rules.py (CHANNELS)",
    }
    now = datetime.now(timezone.utc)
    for table, source in sources.items():
        file_hash = manifest["outputs"].get(source) or (
            sha256_of(root / source) if (root / source).exists() else None)
        con.execute("INSERT INTO load_log VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [table, count(table), source, file_hash, manifest["run_id"], manifest["code"], now])
    return {"raw": counts["raw"], "readings": n_fact, "quarantined": n_quarantine}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="repo root")
    a = ap.parse_args()
    root = Path(a.root)
    try:
        tables, manifest = read_inputs(root)
        target = root / WAREHOUSE
        target.parent.mkdir(parents=True, exist_ok=True)
        for leftover in (target, Path(str(target) + ".wal")):
            leftover.unlink(missing_ok=True)
        con = duckdb.connect(str(target))
        try:
            build(con, tables)
            totals = check_and_log(con, root, manifest)
            overview = con.execute("SELECT * FROM v_channel_overview").df()
        finally:
            con.close()
    except WarehouseStop as err:
        sys.exit("STOP: %s" % err)
    print("accounting: %(raw)d raw = %(readings)d readings + %(quarantined)d quarantined" % totals)
    print(overview.to_string(index=False))
    print("warehouse written: %s" % WAREHOUSE.as_posix())


if __name__ == "__main__":
    sys.exit(main())
