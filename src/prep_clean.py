"""Tableau Prep Script step: the readings that passed every rule.

In Prep:  + > Script  >  connect to TabPy  >  file src/prep_clean.py  >  function clean_readings
Put it on the main branch of the flow, right after the input. Setup notes: docs/prep_script.md.

The rules live in src/prep_script.py (and cleaning.py, rules.py). This file only hands Prep the
table and describes the columns that come back.
"""
import os
import sys

import pandas as pd

# TabPy must find cleaning.py, rules.py and prep_script.py: start TabPy with OPSSAT_SRC set to
# the repo's src folder (or with that folder on PYTHONPATH).
_src = os.environ.get("OPSSAT_SRC")
if _src and _src not in sys.path:
    sys.path.insert(0, _src)

import prep_script as core  # noqa: E402

try:  # inside Tableau Prep these helpers exist
    prep_string, prep_decimal, prep_int, prep_datetime
except NameError:  # on our own computer and in tests: empty typed columns
    def prep_string(): return pd.Series(dtype="object")
    def prep_decimal(): return pd.Series(dtype="float64")
    def prep_int(): return pd.Series(dtype="int64")
    def prep_datetime(): return pd.Series(dtype="datetime64[ns]")


def clean_readings(df):
    return core.clean_table(df)


def get_output_schema():
    return pd.DataFrame({
        "channel": prep_string(),
        "timestamp": prep_datetime(),
        "value": prep_decimal(),
        "sampling": prep_int(),
        "anomaly": prep_int(),
        "train": prep_int(),
        "segment": prep_int(),
        "value_imputed": prep_int(),
        "is_zero": prep_int(),
        "class": prep_string(),
    })
