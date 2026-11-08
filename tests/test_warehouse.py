"""The warehouse must hold exactly what the pipeline produced, and refuse anything it cannot trust.

Uses a tiny SYNTHETIC input, so it always runs, with or without the real data.
"""
import json
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

import load_warehouse as lw

SRC = Path(__file__).resolve().parents[1] / "src"

SEGMENTS = """channel,timestamp,value,label,sampling,anomaly,segment,train
CADC0872,2022-06-01T00:00:00.000Z,1.0,anomaly,1,1,1,1
CADC0872,2022-06-01T00:00:01.000Z,,anomaly,1,1,1,1
CADC0872,2022-06-01T00:00:02.000Z,3.0,anomaly,,1,1,1
CADC0872,,4.0,anomaly,1,1,1,1
,2022-06-01T00:00:04.000Z,5.0,anomaly,1,1,1,1
CADC0884,2022-06-01T01:00:00.000Z,10.0,anomaly,5,0,2,0
CADC0884,2022-06-01T01:00:05.000Z,20.0,anomaly,5,,2,0
CADC0884,2022-06-01T01:00:10.000Z,30.0,anomaly,5,0,2,0
CADC0886,2022-06-01T02:00:00.000Z,7.0,anomaly,5,0,3,0
CADC0886,2022-06-01T02:00:05.000Z,8.0,anomaly,5,0,3,0
NOPE,2022-06-01T02:00:10.000Z,9.0,anomaly,5,0,3,0
"""
NO_QUARANTINE = """channel,timestamp,value,label,sampling,anomaly,segment,train
CADC0884,2022-06-01T01:00:00.000Z,10.0,anomaly,5,0,2,0
CADC0884,2022-06-01T01:00:05.000Z,20.0,anomaly,5,0,2,0
"""
AUTHORS = """segment,anomaly,train,channel,sampling,duration,len,mean
1,1,1,CADC0872,1,4,5,3.25
2,0,0,CADC0884,5,10,3,20.0
3,0,0,CADC0886,5,10,3,8.0
"""
TABLES = ["dim_channel", "dim_segment", "fact_reading", "quarantine_reading",
          "segment_summary", "segment_features"]


AUTHORS_SEGMENT_2 = """segment,anomaly,train,channel,sampling,duration,len,mean
2,0,0,CADC0884,5,5,2,15.0
"""


def make_project(root: Path, segments: str, authors: str = AUTHORS) -> Path:
    (root / "data" / "staging").mkdir(parents=True)
    (root / "data" / "raw").mkdir(parents=True)
    (root / "data" / "staging" / "segments_injected.csv").write_text(segments, newline="\n")
    (root / "data" / "raw" / "dataset.csv").write_text(authors, newline="\n")
    return root


def run(script: str, root: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SRC / script), "--root", str(root)],
                          capture_output=True, text=True)


@pytest.fixture
def project(tmp_path):
    root = make_project(tmp_path, SEGMENTS)
    assert run("run_pipeline.py", root).returncode == 0
    return root


@pytest.fixture
def loaded(project):
    done = run("load_warehouse.py", project)
    assert done.returncode == 0, done.stdout + done.stderr
    return project


def connect(root: Path, read_only=True):
    return duckdb.connect(str(root / lw.WAREHOUSE), read_only=read_only)


def test_tables_hold_what_the_pipeline_logged(loaded):
    counts = json.loads((loaded / "logs" / "MANIFEST.json").read_text())["counts"]
    con = connect(loaded)
    n = lambda t: con.execute("SELECT count(*) FROM %s" % t).fetchone()[0]
    assert n("fact_reading") == counts["clean"]
    assert n("quarantine_reading") == counts["quarantined"]
    assert n("fact_reading") + n("quarantine_reading") == counts["raw"]
    assert n("dim_segment") == n("segment_summary") == 3
    assert n("dim_channel") == 9


def test_quarantined_rows_keep_their_reason(loaded):
    reasons = {row[0] for row in connect(loaded).execute(
        "SELECT reason FROM quarantine_reading").fetchall()}
    assert "missing timestamp" in reasons
    assert len(reasons) == 2


def test_views_answer_the_ml_and_overview_questions(loaded):
    con = connect(loaded)
    assert con.execute("SELECT count(*) FROM ml_training_set").fetchone()[0] == 3
    assert con.execute("SELECT count(*) FROM v_reading").fetchone()[0] == \
        con.execute("SELECT count(*) FROM fact_reading").fetchone()[0]
    columns = [d[0] for d in con.execute("SELECT * FROM ml_training_set LIMIT 1").description]
    assert columns[:8] == ["segment", "channel", "sampling", "anomaly", "train", "class",
                           "n_readings", "n_imputed"]
    assert con.execute("SELECT count(*) FROM v_channel_overview").fetchone()[0] == 9
    assert con.execute("SELECT sum(imputed_values) FROM v_channel_overview").fetchone()[0] == \
        con.execute("SELECT sum(value_imputed) FROM fact_reading").fetchone()[0]


def test_a_reading_for_an_unknown_segment_is_refused(loaded):
    con = connect(loaded, read_only=False)
    with pytest.raises(duckdb.Error):
        con.execute("INSERT INTO fact_reading VALUES (999, -5, '2022-01-01', 1.0, 0, 0, 'x')")


def test_load_log_names_the_run_it_came_from(loaded):
    manifest = json.loads((loaded / "logs" / "MANIFEST.json").read_text())
    rows = connect(loaded).execute("SELECT DISTINCT run_id FROM load_log").fetchall()
    assert rows == [(manifest["run_id"],)]


def test_loading_twice_gives_the_same_content(loaded):
    def content():
        con = connect(loaded)
        out = {t: con.execute("SELECT * FROM %s ORDER BY 1" % t).fetchall() for t in TABLES}
        con.close()
        return out
    first = content()
    assert run("load_warehouse.py", loaded).returncode == 0
    assert content() == first


def test_stops_without_a_manifest(project):
    (project / "logs" / "MANIFEST.json").unlink()
    with pytest.raises(lw.WarehouseStop, match="MANIFEST"):
        lw.read_inputs(project)


def test_stops_when_an_output_changed_after_the_run(project):
    with open(project / "data" / "cleaned" / "segment_clean_py.csv", "a", newline="\n") as f:
        f.write("tampered\n")
    done = run("load_warehouse.py", project)
    assert done.returncode != 0 and "changed after the pipeline run" in (done.stdout + done.stderr)
    assert not (project / lw.WAREHOUSE).exists()


def test_stops_when_the_run_did_not_reach_the_summary(tmp_path):
    root = make_project(tmp_path, SEGMENTS)
    assert subprocess.run([sys.executable, str(SRC / "run_pipeline.py"), "--root", str(root),
                           "--upto", "R3"], capture_output=True).returncode == 0
    with pytest.raises(lw.WarehouseStop):
        lw.read_inputs(root)


def test_a_run_without_quarantined_rows_loads_an_empty_quarantine_table(tmp_path):
    root = make_project(tmp_path, NO_QUARANTINE, AUTHORS_SEGMENT_2)
    assert run("run_pipeline.py", root).returncode == 0
    done = run("load_warehouse.py", root)
    assert done.returncode == 0, done.stdout + done.stderr
    assert connect(root).execute("SELECT count(*) FROM quarantine_reading").fetchone()[0] == 0
