"""Tests for src/cleaning.py. All fixtures are tiny, hand-made and SYNTHETIC.

Green tests (R1, R2, R3, R6) were written with the code. Red tests (R4, R5, R7) are the
specification of the functions marked TODO(Priyansh): make them pass.
"""
import numpy as np
import pandas as pd
import pytest

import cleaning as c

NA = pd.NA


def readings(**cols):
    return pd.DataFrame(cols)


# ------------------------------------------------------------------ R1
def test_r1_removes_label_and_keeps_rows():
    df = readings(segment=[1, 1], label=["anomaly", "anomaly"], value=[1.0, 2.0])
    out = c.remove_label(df)
    assert "label" not in out.columns
    assert len(out) == len(df)
    assert list(out.columns) == ["segment", "value"]
    assert "label" in df.columns  # input is not modified


# ------------------------------------------------------------------ R2
def test_r2_flags_missing_values_only():
    df = readings(value=[1.0, np.nan, 3.0])
    out = c.flag_missing_value(df)
    assert out["value_imputed"].tolist() == [0, 1, 0]
    assert out["value"].isna().tolist() == [False, True, False]  # value untouched
    assert "value_imputed" not in df.columns


# ------------------------------------------------------------------ R3
def test_r3_quarantines_rows_without_timestamp():
    ts = pd.to_datetime(["2022-06-01T00:00:00Z", None, "2022-06-01T00:00:02Z"])
    df = readings(segment=[1, 1, 1], timestamp=ts, value=[1.0, 2.0, 3.0])
    clean, quarantined = c.quarantine_missing_timestamp(df)
    assert clean["value"].tolist() == [1.0, 3.0]
    assert clean["timestamp"].notna().all()
    assert quarantined["value"].tolist() == [2.0]
    assert quarantined["reason"].tolist() == ["missing timestamp"]


def test_r3_row_counts_add_up():
    ts = pd.to_datetime(["2022-06-01T00:00:00Z", None, None, "2022-06-01T00:00:03Z"])
    df = readings(timestamp=ts, value=[1.0, 2.0, 3.0, 4.0])
    clean, quarantined = c.quarantine_missing_timestamp(df)
    assert len(clean) + len(quarantined) == len(df)


def test_r3_nothing_to_quarantine():
    ts = pd.to_datetime(["2022-06-01T00:00:00Z", "2022-06-01T00:00:01Z"])
    df = readings(timestamp=ts, value=[1.0, 2.0])
    clean, quarantined = c.quarantine_missing_timestamp(df)
    assert len(clean) == 2
    assert len(quarantined) == 0


# ------------------------------------------------------------------ R6
def test_r6_adds_flags():
    df = readings(value=[0.0, 0.5, 0.0], anomaly=[1, 1, 0])
    out = c.add_flags(df)
    assert out["is_zero"].tolist() == [1, 0, 1]
    assert out["class"].tolist() == ["anomaly", "anomaly", "nominal"]
    assert len(out) == 3


# ------------------------------------------------------------------ R4  (YOURS)
def test_r4_recovers_text_and_number_columns():
    df = readings(
        segment=[1, 1, 1, 2, 2, 2],
        channel=pd.array(["A", NA, "A", "B", "B", NA], dtype="string"),
        anomaly=pd.array([1, NA, 1, 0, 0, NA], dtype="Int64"),
        sampling=pd.array([1, 1, NA, 5, NA, 5], dtype="Int64"),
        train=pd.array([NA, 0, 0, 1, 1, 1], dtype="Int64"),
    )
    out = c.recover_segment_constants(df)
    assert out["channel"].tolist() == ["A", "A", "A", "B", "B", "B"]
    assert out["anomaly"].tolist() == [1, 1, 1, 0, 0, 0]
    assert out["sampling"].tolist() == [1, 1, 1, 5, 5, 5]
    assert out["train"].tolist() == [0, 0, 0, 1, 1, 1]


def test_r4_keeps_row_count_and_other_columns():
    df = readings(
        segment=[1, 1],
        channel=pd.array(["A", NA], dtype="string"),
        value=[1.5, 2.5],
    )
    out = c.recover_segment_constants(df, columns=("channel",))
    assert len(out) == len(df)
    assert out["value"].tolist() == [1.5, 2.5]


def test_r4_does_not_invent_a_value_for_a_fully_blank_segment():
    df = readings(segment=[1, 1], channel=pd.array([NA, NA], dtype="string"))
    out = c.recover_segment_constants(df, columns=("channel",))
    assert out["channel"].isna().all()


# ------------------------------------------------------------------ R5  (YOURS)
def test_r5_fills_blank_with_segment_mean_only():
    df = readings(segment=[1, 1, 1, 2, 2], value=[1.0, np.nan, 3.0, 10.0, 20.0])
    out = c.impute_value(df)
    assert out["value"].tolist() == [1.0, 2.0, 3.0, 10.0, 20.0]
    assert len(out) == len(df)


def test_r5_uses_each_segments_own_mean():
    df = readings(segment=[1, 1, 2, 2], value=[0.0, np.nan, 100.0, np.nan])
    out = c.impute_value(df)
    assert out["value"].tolist() == [0.0, 0.0, 100.0, 100.0]


def test_r5_does_not_modify_its_input():
    df = readings(segment=[1, 1], value=[1.0, np.nan])
    c.impute_value(df)
    assert df["value"].isna().sum() == 1


# ------------------------------------------------------------------ R7  (YOURS)
def _repaired():
    ts = pd.to_datetime(
        [
            "2022-06-01T00:00:00Z", "2022-06-01T00:00:01Z", "2022-06-01T00:00:02Z",
            "2022-06-01T01:00:00Z", "2022-06-01T01:00:05Z",
        ]
    )
    return readings(
        segment=[1, 1, 1, 2, 2],
        channel=["A", "A", "A", "B", "B"],
        anomaly=[1, 1, 1, 0, 0],
        train=[1, 1, 1, 0, 0],
        sampling=[1, 1, 1, 5, 5],
        timestamp=ts,
        value=[0.0, 2.0, 4.0, 10.0, 20.0],
        is_zero=[1, 0, 0, 0, 0],
        value_imputed=[0, 1, 0, 0, 0],
    )


def test_r7_summarise_one_row_per_segment():
    s = c.summarise_segments(_repaired()).set_index("segment")
    assert list(s.index) == [1, 2]
    assert s.loc[1, "n_readings"] == 3
    assert s.loc[2, "n_readings"] == 2
    assert s.loc[1, "mean_value"] == pytest.approx(2.0)
    assert s.loc[2, "mean_value"] == pytest.approx(15.0)
    assert s.loc[1, "n_zero"] == 1
    assert s.loc[1, "n_imputed"] == 1
    assert s.loc[2, "n_imputed"] == 0
    assert s.loc[1, "timestamp_min"] == pd.Timestamp("2022-06-01T00:00:00Z")
    assert s.loc[1, "timestamp_max"] == pd.Timestamp("2022-06-01T00:00:02Z")
    assert s.loc[2, "channel"] == "B"
    assert s.loc[2, "sampling"] == 5


def test_r7_compare_all_match():
    summary = c.summarise_segments(_repaired())
    authors = pd.DataFrame(
        {
            "segment": [1, 2], "len": [3, 2], "duration": [2, 5], "mean": [2.0, 15.0],
            "channel": ["A", "B"], "anomaly": [1, 0], "train": [1, 0], "sampling": [1, 5],
        }
    )
    r = c.compare_with_authors(summary, authors).set_index("segment")
    for col in ("len_diff", "dur_diff"):
        assert (r[col] == 0).all()
    assert (r["mean_ok"] == 1).all()
    assert (r["attr_ok"] == 1).all()


def test_r7_compare_detects_differences():
    summary = c.summarise_segments(_repaired())
    authors = pd.DataFrame(
        {
            "segment": [1, 2], "len": [4, 2], "duration": [2, 5], "mean": [2.5, 15.0],
            "channel": ["A", "X"], "anomaly": [1, 0], "train": [1, 0], "sampling": [1, 5],
        }
    )
    r = c.compare_with_authors(summary, authors).set_index("segment")
    assert r.loc[1, "len_diff"] == -1
    assert r.loc[1, "mean_diff"] == pytest.approx(0.5)
    assert r.loc[1, "mean_ok"] == 0
    assert r.loc[2, "mean_ok"] == 1
    assert r.loc[1, "attr_ok"] == 1
    assert r.loc[2, "attr_ok"] == 0
