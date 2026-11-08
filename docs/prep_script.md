# Running the rules inside Tableau Prep (optional)

`src/run_pipeline.py` is the reference and is unchanged. This is a second way to run the SAME
rules (R1 to R6 and V1), from Tableau Prep's Script step. Both use `cleaning.py` and `rules.py`.

| File | Job |
|---|---|
| `src/prep_script.py` | `run_rules()` applies the rules; also runs on its own: `python src/prep_script.py` |
| `src/prep_clean.py` | Prep Script step, function `clean_readings`: rows that passed every rule |
| `src/prep_quarantine.py` | Prep Script step, function `quarantined_readings`: rows set aside, with `reason` |
| `tests/test_prep_script.py` | proves the same rows as `run_pipeline.py` |

## Why two script files

A Prep Script step takes one table and returns one table, and a script file has one
`get_output_schema()`. So the flow branches after the input: one branch runs `prep_clean.py` and
continues (flags, aggregate, join, parity), the other runs `prep_quarantine.py` and writes the
quarantine output. Both call the same `run_rules()`.

## What is verified, and what is not

- **Verified (tests and a run on the real file):** the script functions give exactly the rows of
  `run_pipeline.py`: 301,976 clean, 1,517 quarantined, same reasons, same values.
- **Not verified (needs Tableau Prep and TabPy, which we could not run here):** the setup below,
  the types Prep accepts back (timestamp, int, decimal) and whether TabPy can import our modules.
  Test on a small sample first. If it fails, the native Prep flow stays as it is.

## Setup (from Prep's documentation, unverified here)

1. In the same Python that will run TabPy: `pip install tabpy pandas pandera` (versions as in
   `requirements-lock.txt`).
2. Set `OPSSAT_SRC` to the full path of the repo's `src` folder, then start `tabpy` in that window.
3. Prep Builder: Help > Settings and Performance > Manage Analytics Extensions Connection:
   TabPy, localhost, port 9004.
4. In the flow: + > Script, pick the file and function from the table above.

## Going back

Nothing existing was changed. The tag `pipeline-v1` is the version before this addition.
