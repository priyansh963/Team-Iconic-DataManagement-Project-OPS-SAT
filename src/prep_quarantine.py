"""Tableau Prep Script step: the rows that were set aside, each with a `reason`.

In Prep:  + > Script  >  connect to TabPy  >  file src/prep_quarantine.py  >  function quarantined_readings
Put it on a second branch from the same input, then write it to the quarantine output.
Setup notes: docs/prep_script.md.

Numbers travel as decimals here because quarantined rows can still have blanks.
"""
import os
import sys

import pandas as pd

_src = os.environ.get("OPSSAT_SRC")
if _src and _src not in sys.path:
    sys.path.insert(0, _src)

import prep_script as core  # noqa: E402

try:  # inside Tableau Prep these helpers exist
    prep_string, prep_decimal, prep_datetime
except NameError:  # on our own computer and in tests: empty typed columns
    def prep_string(): return pd.Series(dtype="object")
    def prep_decimal(): return pd.Series(dtype="float64")
    def prep_datetime(): return pd.Series(dtype="datetime64[ns]")


def quarantined_readings(df):
    return core.quarantine_table(df)


def get_output_schema():
    return pd.DataFrame({
        "channel": prep_string(),
        "timestamp": prep_datetime(),
        "value": prep_decimal(),
        "sampling": prep_decimal(),
        "anomaly": prep_decimal(),
        "train": prep_decimal(),
        "segment": prep_decimal(),
        "value_imputed": prep_decimal(),
        "is_zero": prep_decimal(),
        "class": prep_string(),
        "reason": prep_string(),
    })
