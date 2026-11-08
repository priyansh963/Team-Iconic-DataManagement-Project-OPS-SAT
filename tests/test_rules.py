"""Tests for src/rules.py. Tiny, hand-made, SYNTHETIC tables (shape of the data after R6)."""
import pandas as pd
import pytest

import rules as r


def after_repairs(**changes):
    """Four valid readings in two segments, shaped like the table after R6. Override columns with `changes`."""
    cols = dict(
        timestamp=pd.to_datetime(
            ["2022-06-01T00:00:00Z", "2022-06-01T00:00:01Z", "2022-06-01T00:00:02Z", "2022-06-01T00:00:00Z"], utc=True
        ),
        segment=[1, 1, 1, 2],
        channel=pd.array(["CADC0872", "CADC0872", "CADC0872", "CADC0884"], dtype="string"),
        sampling=pd.array([1, 1, 1, 5], dtype="Int64"),
        anomaly=pd.array([1, 1, 1, 0], dtype="Int64"),
        train=pd.array([1, 1, 1, 0], dtype="Int64"),
        value=[1.0, 2.0, 3.0, 4.0],
    )
    cols.update(changes)
    return pd.DataFrame(cols)


def reasons(quarantined):
    return " | ".join(quarantined["reason"])


# ---------------------------------------------------------------- QUARANTINE
def test_valid_table_passes_untouched():
    df = after_repairs()
    clean, quarantined = r.quarantine_invalid_rows(df)
    assert len(clean) == 4
    assert len(quarantined) == 0
    assert "reason" in quarantined.columns


def test_unknown_channel_is_quarantined_with_reason():
    df = after_repairs(channel=pd.array(["CADC0872", "BAD", "CADC0872", "CADC0884"], dtype="string"))
    clean, quarantined = r.quarantine_invalid_rows(df)
    assert quarantined["segment"].tolist() == [1]
    assert "channel: not an allowed value" in reasons(quarantined)
    assert len(clean) == 3


@pytest.mark.parametrize(
    "column, values, text",
    [
        ("anomaly", [1, 1, 2, 0], "anomaly: not an allowed value"),
        ("train", [1, 1, 7, 0], "train: not an allowed value"),
        ("sampling", [1, 1, 3, 5], "sampling: not an allowed value"),
    ],
)
def test_values_outside_the_allowed_set_are_quarantined(column, values, text):
    df = after_repairs(**{column: pd.array(values, dtype="Int64")})
    clean, quarantined = r.quarantine_invalid_rows(df)
    assert len(quarantined) == 1
    assert text in reasons(quarantined)


def test_blank_left_after_repairs_is_quarantined():
    df = after_repairs()
    df.loc[0, "channel"] = pd.NA  # R4 could not recover it
    clean, quarantined = r.quarantine_invalid_rows(df)
    assert len(quarantined) == 1
    assert "channel: not_nullable" in reasons(quarantined)


def test_infinite_value_is_quarantined():
    clean, quarantined = r.quarantine_invalid_rows(after_repairs(value=[1.0, float("inf"), 3.0, 4.0]))
    assert len(quarantined) == 1
    assert "value: value_is_finite" in reasons(quarantined)


def test_duplicate_segment_and_timestamp_quarantines_both_copies():
    df = after_repairs()
    df.loc[3, ["segment"]] = 1  # row 3 now repeats segment 1 at 00:00:00 ...
    df.loc[3, "channel"] = "CADC0872"
    df.loc[3, "sampling"] = 1
    df.loc[3, "anomaly"] = 1
    df.loc[3, "train"] = 1  # ... with identical constants, so only the duplicate rule fires
    clean, quarantined = r.quarantine_invalid_rows(df)
    assert len(quarantined) == 2
    assert "duplicate segment + timestamp" in reasons(quarantined)


def test_one_odd_row_in_a_segment_is_caught_and_the_rest_kept():
    df = after_repairs(sampling=pd.array([1, 5, 1, 5], dtype="Int64"))  # row 1 disagrees with its segment
    clean, quarantined = r.quarantine_invalid_rows(df)
    assert quarantined["segment"].tolist() == [1]
    assert len(quarantined) == 1
    assert "differs from the segment's majority value" in reasons(quarantined)
    assert len(clean) == 3


def test_row_counts_add_up():
    df = after_repairs(anomaly=pd.array([1, 1, 2, 0], dtype="Int64"))
    clean, quarantined = r.quarantine_invalid_rows(df)
    assert len(clean) + len(quarantined) == len(df)


def test_input_table_is_not_modified():
    df = after_repairs(anomaly=pd.array([1, 1, 2, 0], dtype="Int64"))
    before = df.copy()
    r.quarantine_invalid_rows(df)
    pd.testing.assert_frame_equal(df, before)


# ---------------------------------------------------------------------- STOP
def test_valid_input_passes_structure_check():
    r.validate_input(after_repairs())  # no exception


def test_empty_input_stops_the_run():
    with pytest.raises(r.PipelineStop, match="no rows"):
        r.validate_input(after_repairs().iloc[0:0])


def test_missing_column_stops_the_run():
    with pytest.raises(r.PipelineStop, match="structure"):
        r.validate_input(after_repairs().drop(columns=["value"]))


def test_wrong_type_stops_the_run():
    df = after_repairs()
    df["segment"] = df["segment"].astype(str)
    with pytest.raises(r.PipelineStop):
        r.validate_input(df)
