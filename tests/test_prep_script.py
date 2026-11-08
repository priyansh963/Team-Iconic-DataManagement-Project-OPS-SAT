"""The Tableau Prep version must give the same rows as run_pipeline.py.

Uses a tiny SYNTHETIC input, so it always runs, with or without the real data.
"""
import io
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

import prep_clean
import prep_quarantine
import prep_script as core
import rules as r

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
AUTHORS = """segment,anomaly,train,channel,sampling,duration,len,mean
1,1,1,CADC0872,1,4,5,3.25
2,0,0,CADC0884,5,10,3,20.0
3,0,0,CADC0886,5,10,3,8.0
"""


def as_prep_sends_it() -> pd.DataFrame:
    """The table as Tableau Prep hands it to a script: no time zone, blanks in whole numbers as NaN."""
    df = pd.read_csv(io.StringIO(SEGMENTS))
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_localize(None)
    return df


@pytest.fixture
def project(tmp_path):
    (tmp_path / "data" / "staging").mkdir(parents=True)
    (tmp_path / "data" / "raw").mkdir(parents=True)
    (tmp_path / "data" / "staging" / "segments_injected.csv").write_text(SEGMENTS, newline="\n")
    (tmp_path / "data" / "raw" / "dataset.csv").write_text(AUTHORS, newline="\n")
    return tmp_path


def run(script: str, root: Path) -> None:
    done = subprocess.run([sys.executable, str(SRC / script), "--root", str(root)],
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr


def read(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)
    return df.drop(columns=[c for c in ("source_file",) if c in df.columns])


def test_same_clean_rows_as_run_pipeline(project):
    run("run_pipeline.py", project)
    run("prep_script.py", project)
    ref = read(project / "data/cleaned/segment_clean_py.csv")
    got = read(project / "data/cleaned/prep_script_clean.csv")
    for frame in (ref, got):  # same moment, different spelling of the time zone
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True).astype(str)
    common = [c for c in got.columns if c in ref.columns]
    assert len(common) == len(got.columns)
    pd.testing.assert_frame_equal(ref[common], got[common])


def test_same_quarantined_rows_and_reasons_as_run_pipeline(project):
    run("run_pipeline.py", project)
    run("prep_script.py", project)
    ref = read(project / "data/cleaned/quarantine_readings.csv")
    got = read(project / "data/cleaned/prep_script_quarantine.csv")
    assert len(ref) == len(got) == 2
    assert list(ref["reason"]) == list(got["reason"])
    assert list(ref["segment"].astype(float)) == list(got["segment"].astype(float))


def test_accounting_adds_up_with_prep_style_input():
    df = as_prep_sends_it()
    clean, quarantined = core.clean_table(df), core.quarantine_table(df)
    assert len(df) == len(clean) + len(quarantined)
    assert len(quarantined) == 2
    assert "missing timestamp" in set(quarantined["reason"])


def test_clean_table_types_are_plain_and_complete():
    clean = core.clean_table(as_prep_sends_it())
    assert list(clean.columns) == core.CLEAN_COLUMNS
    assert clean["timestamp"].dtype == "datetime64[ns]"          # no time zone
    for col in core.WHOLE_NUMBERS:
        assert clean[col].dtype == "int64", col
    assert clean["value"].dtype == "float64"
    assert not clean.isna().any().any()                           # every blank was repaired
    assert not any(x is pd.NA for col in ("channel", "class") for x in clean[col])


def test_quarantine_table_types_are_plain():
    q = core.quarantine_table(as_prep_sends_it())
    assert list(q.columns) == core.QUARANTINE_COLUMNS
    for col in core.QUARANTINE_NUMBERS:
        assert q[col].dtype == "float64", col
    assert not any(x is pd.NA for col in ("channel", "class", "reason") for x in q[col])


def test_input_table_is_not_modified():
    df = as_prep_sends_it()
    before = df.copy()
    core.clean_table(df)
    pd.testing.assert_frame_equal(df, before)


def test_broken_table_stops():
    with pytest.raises(r.PipelineStop):
        core.clean_table(as_prep_sends_it().drop(columns=["value"]))
    with pytest.raises(r.PipelineStop):
        core.clean_table(as_prep_sends_it().iloc[0:0])


def test_script_files_describe_the_columns_they_return():
    df = as_prep_sends_it()
    assert list(prep_clean.get_output_schema().columns) == list(prep_clean.clean_readings(df).columns)
    assert list(prep_quarantine.get_output_schema().columns) == list(
        prep_quarantine.quarantined_readings(df).columns)
