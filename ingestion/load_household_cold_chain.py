"""
Loads the household refrigerator files (123 expected) into
ATMOSYNC.RAW.RAW_HOUSEHOLD_FRIDGE_READINGS.

REFERENCE DATA ONLY: these are domestic refrigerator readings. They are used
for exploratory threshold calibration in the simulator and alerts. They are
NOT validated shipping-container safety thresholds.

Where the table columns come from:
  FRIDGE_NUMBER, FRIDGE_TYPE  <- the file name, e.g. 001_1D.txt -> 1, "1D"
  TIME_MINUTES                <- the "Time" column of the file
  T_*, RH_*, TP               <- the same-named columns of the file
  SOURCE_FILE                 <- the file name
  LOADED_AT                   <- filled by Snowflake (column default)

The table is fully reloaded on each run. If the loaded row count does not
match the rows read from the files, the load is rolled back.

Before the first run, unzip data/raw/household_cold_chain/dataverse_files.zip
into data/raw/household_cold_chain/unzipped/ (that folder is not in Git).

Usage (from the repo root):
    python ingestion/load_household_cold_chain.py --dry-run   # read and check only
    python ingestion/load_household_cold_chain.py             # read, check and load
"""

import argparse
import os
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT = REPO_ROOT / "data" / "raw" / "household_cold_chain" / "unzipped"

TABLE = "ATMOSYNC.RAW.RAW_HOUSEHOLD_FRIDGE_READINGS"
EXPECTED_FILES = 123
EXPECTED_HEADER = ["Time", "T_AMB", "T_MS", "T_TS", "T_VD", "T_DS", "T_FC",
                   "RH_AMB", "RH_MS", "RH_TS", "RH_VD", "RH_DS", "RH_FC", "TP"]
FILE_PATTERN = re.compile(r"^(\d{3})_(.+)\.txt$")
BATCH = 1000

INSERT_COLUMNS = (["FRIDGE_NUMBER", "FRIDGE_TYPE", "TIME_MINUTES"]
                  + EXPECTED_HEADER[1:] + ["SOURCE_FILE"])


def read_files():
    """Return (rows, files, rows_per_file). Stops with a clear message on any problem."""
    first = next(ROOT.rglob("001_1D.txt"), None)
    if first is None:
        raise SystemExit(
            f"001_1D.txt not found under {ROOT}\n"
            "Unzip data/raw/household_cold_chain/dataverse_files.zip into the 'unzipped' folder first."
        )
    data_dir = first.parent
    files = sorted(p for p in data_dir.glob("*.txt") if FILE_PATTERN.match(p.name))

    rows = []
    rows_per_file = {}
    for path in files:
        number, fridge_type = FILE_PATTERN.match(path.name).groups()
        df = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False, encoding="utf-8-sig")
        df.columns = [c.strip() for c in df.columns]
        if list(df.columns) != EXPECTED_HEADER:
            raise ValueError(f"{path.name}: unexpected header {list(df.columns)}")

        stripped = df.apply(lambda s: s.str.strip())
        numeric = stripped.apply(pd.to_numeric, errors="coerce")
        bad = int(numeric.isna().sum().sum())
        if bad:
            raise ValueError(f"{path.name}: {bad} empty or non-numeric cells")

        for values in numeric.astype(float).values.tolist():
            rows.append((int(number), fridge_type, *values, path.name))
        rows_per_file[path.name] = len(df)

    return rows, files, rows_per_file


def load(rows):
    # Imported here so --dry-run works without Snowflake settings
    import snowflake.connector
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    conn = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role=os.environ["SNOWFLAKE_ROLE"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        schema=os.environ["SNOWFLAKE_SCHEMA"],
    )
    conn.autocommit(False)
    try:
        cur = conn.cursor()
        cur.execute(f"DELETE FROM {TABLE}")
        sql = (
            f"INSERT INTO {TABLE} ({', '.join(INSERT_COLUMNS)}) "
            f"VALUES ({', '.join(['%s'] * len(INSERT_COLUMNS))})"
        )
        for i in range(0, len(rows), BATCH):
            cur.executemany(sql, rows[i:i + BATCH])
        cur.execute(f"SELECT COUNT(*) FROM {TABLE}")
        count = cur.fetchone()[0]
        if count != len(rows):
            raise RuntimeError(f"Row count mismatch: read {len(rows)}, table has {count}")
        conn.commit()
        return count
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Load household refrigerator reference data")
    parser.add_argument("--dry-run", action="store_true", help="read and check only, do not load")
    args = parser.parse_args()

    rows, files, rows_per_file = read_files()
    counts = sorted(rows_per_file.values())
    types = Counter(FILE_PATTERN.match(p.name).group(2) for p in files)

    print("NOTE: household data is reference data only, not validated container thresholds.")
    print(f"Files found: {len(files)} (expected {EXPECTED_FILES})")
    print("Files per type:", dict(sorted(types.items())))
    print(f"Rows per file: min {counts[0]}, median {statistics.median(counts):.0f}, max {counts[-1]}")
    print(f"Total rows to load: {len(rows)}")

    if args.dry_run:
        print("Dry run: nothing loaded.")
        return 0

    if len(files) != EXPECTED_FILES:
        raise SystemExit(f"Refusing to load: expected {EXPECTED_FILES} files, found {len(files)}.")

    count = load(rows)
    print(f"Loaded {count} rows into {TABLE}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())