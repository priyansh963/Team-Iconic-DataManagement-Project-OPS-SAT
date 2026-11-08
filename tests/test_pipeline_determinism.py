"""Same input, same output: run the whole pipeline twice and compare the files byte for byte.

Uses a tiny SYNTHETIC input so the test always runs, with or without the real data.
"""
import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

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
"""
AUTHORS = """segment,anomaly,train,channel,sampling,duration,len,mean
1,1,1,CADC0872,1,4,5,3.25
2,0,0,CADC0884,5,10,3,20.0
"""
OUTPUTS = [
    "data/cleaned/segment_clean_py.csv",
    "data/cleaned/quarantine_readings.csv",
    "data/cleaned/segment_summary_py.csv",
    "data/cleaned/pipeline_step_log.csv",
]


def run(root: Path) -> None:
    done = subprocess.run(
        [sys.executable, str(SRC / "run_pipeline.py"), "--root", str(root)],
        capture_output=True, text=True,
    )
    assert done.returncode == 0, done.stdout + done.stderr


def fingerprints(root: Path) -> dict:
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in OUTPUTS}


@pytest.fixture
def project(tmp_path):
    (tmp_path / "data" / "staging").mkdir(parents=True)
    (tmp_path / "data" / "raw").mkdir(parents=True)
    (tmp_path / "data" / "staging" / "segments_injected.csv").write_text(SEGMENTS, newline="\n")
    (tmp_path / "data" / "raw" / "dataset.csv").write_text(AUTHORS, newline="\n")
    return tmp_path


def test_two_runs_give_identical_files(project):
    run(project)
    first = fingerprints(project)
    run(project)
    assert fingerprints(project) == first


def test_outputs_use_unix_line_endings(project):
    run(project)
    for name in OUTPUTS:
        assert b"\r" not in (project / name).read_bytes(), name


def test_every_run_adds_a_block_to_the_log(project):
    run(project)
    run(project)
    log = (project / "logs" / "run_log.txt").read_text()
    assert log.count("=== run ") == 2
    assert log.count("accounting :") == 2


def test_accounting_adds_up_and_reasons_are_recorded(project):
    run(project)
    import pandas as pd

    clean = pd.read_csv(project / "data" / "cleaned" / "segment_clean_py.csv")
    quarantined = pd.read_csv(project / "data" / "cleaned" / "quarantine_readings.csv")
    assert len(clean) + len(quarantined) == 8
    assert quarantined["reason"].tolist() == ["missing timestamp"]
    assert set(clean["source_file"]) == {"segments_injected.csv"}


def test_structurally_wrong_input_stops_and_is_logged(project):
    bad = SEGMENTS.replace("channel,timestamp,value,", "channel,timestamp,price,")
    (project / "data" / "staging" / "segments_injected.csv").write_text(bad, newline="\n")
    done = subprocess.run(
        [sys.executable, str(SRC / "run_pipeline.py"), "--root", str(project)],
        capture_output=True, text=True,
    )
    assert done.returncode != 0
    assert "STOPPED" in (project / "logs" / "run_log.txt").read_text()
