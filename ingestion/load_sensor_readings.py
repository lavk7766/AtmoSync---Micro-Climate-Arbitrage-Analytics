"""
Loads the real sensor readings (9 sensors) into ATMOSYNC.RAW.RAW_SENSOR_READINGS.

The raw files are loaded as received, one row per reading. A header line that is
repeated inside a file holds no reading and is skipped. The preprocessed files are
not loaded: their values are identical to the raw values (see docs/design).
Cutting the data to the common time window is done later in dbt.

Where the table columns come from:
  SENSOR_ID      <- the file name, e.g. SENSOR01.CSV -> SENSOR01
  READING_TS     <- Date + Time (DD.MM.YYYY HH:MM:SS, no time zone in the source)
  TEMPERATURE_C  <- Temperature (C)
  HUMIDITY_PCT   <- Humidity (%)
  SOURCE_FILE    <- the file name
  LOADED_AT      <- filled by Snowflake (column default)

The table is fully reloaded on each run, as one transaction. If the loaded row
count does not match the rows read from the files, the load is rolled back.

Before the first run, unzip data/raw/sensor_data/Raw.zip into
data/raw/sensor_data/raw_unzipped/ (that folder is not in Git).

Usage (from the repo root):
    python ingestion/load_sensor_readings.py --dry-run   # read and check only
    python ingestion/load_sensor_readings.py             # read, check and load
"""

import argparse
import os
import re
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw" / "sensor_data" / "raw_unzipped"

TABLE = "ATMOSYNC.RAW.RAW_SENSOR_READINGS"
EXPECTED_FILES = 9
EXPECTED_READINGS = 1_083_195   # verified with scripts/profile_sensor_data.py
RAW_HEADER = ["Date", "Time", "Temperature (C)", "Humidity (%)"]
DATE_FORMAT = "%d.%m.%Y %H:%M:%S"
FILE_PATTERN = re.compile(r"^(SENSOR\d{2})\.CSV$", re.IGNORECASE)
BATCH = 5000


def read_sensor_file(path):
    """Return a dict with the readings of one file and its check counts."""
    df = pd.read_csv(path, sep=";", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    if [c.strip() for c in df.columns] != RAW_HEADER:
        raise ValueError(f"{path.name}: unexpected header {list(df.columns)}")
    df.columns = ["date", "time", "temp", "hum"]
    df = df.apply(lambda s: s.str.strip())

    repeated_header = df["date"].str.lower() == "date"
    skipped = int(repeated_header.sum())
    df = df[~repeated_header].reset_index(drop=True)

    ts = pd.to_datetime(df["date"] + " " + df["time"], format=DATE_FORMAT, errors="coerce")
    bad_ts = int(ts.isna().sum())
    if bad_ts:
        raise ValueError(f"{path.name}: {bad_ts} unreadable timestamps")

    temp = pd.to_numeric(df["temp"], errors="coerce")
    hum = pd.to_numeric(df["hum"], errors="coerce")
    readings = pd.DataFrame({
        "ts_text": ts.dt.strftime("%Y-%m-%d %H:%M:%S"),
        "temp": temp,
        "hum": hum,
    })
    return {
        "sensor_id": path.stem.upper(),
        "source_file": path.name,
        "readings": readings,
        "header_lines_skipped": skipped,
        "empty_or_non_numeric_cells": int(temp.isna().sum() + hum.isna().sum()),
        "first": ts.min(),
        "last": ts.max(),
    }


def read_all():
    files = sorted(p for p in RAW_DIR.glob("*.CSV") if FILE_PATTERN.match(p.name))
    if not files:
        raise SystemExit(f"No SENSORnn.CSV files found in {RAW_DIR}\n"
                         "Unzip Raw.zip into the 'raw_unzipped' folder first.")
    return [read_sensor_file(p) for p in files]


def batches(sensor):
    """Yield lists of rows (tuples) for one sensor. Empty values become NULL."""
    df = sensor["readings"]
    for i in range(0, len(df), BATCH):
        part = df.iloc[i:i + BATCH]
        temps = part["temp"].astype(object).where(part["temp"].notna(), None)
        hums = part["hum"].astype(object).where(part["hum"].notna(), None)
        n = len(part)
        yield list(zip([sensor["sensor_id"]] * n, part["ts_text"], temps, hums,
                       [sensor["source_file"]] * n))


def load(sensors, total):
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
        sql = (f"INSERT INTO {TABLE} "
               "(SENSOR_ID, READING_TS, TEMPERATURE_C, HUMIDITY_PCT, SOURCE_FILE) "
               "VALUES (%s, %s, %s, %s, %s)")
        done = 0
        for sensor in sensors:
            for rows in batches(sensor):
                cur.executemany(sql, rows)
                done += len(rows)
            print(f"  {sensor['sensor_id']}: loaded ({done} of {total} rows so far)")
        cur.execute(f"SELECT COUNT(*) FROM {TABLE}")
        count = cur.fetchone()[0]
        if count != total:
            raise RuntimeError(f"Row count mismatch: read {total}, table has {count}")
        conn.commit()
        return count
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Load real sensor readings")
    parser.add_argument("--dry-run", action="store_true", help="read and check only, do not load")
    args = parser.parse_args()

    sensors = read_all()
    total = sum(len(s["readings"]) for s in sensors)

    print(f"Files found: {len(sensors)} (expected {EXPECTED_FILES})")
    for s in sensors:
        print(f"  {s['sensor_id']}: {len(s['readings'])} readings, "
              f"{s['first']} to {s['last']}, "
              f"repeated header lines skipped: {s['header_lines_skipped']}")
    print(f"Total readings to load: {total} (expected {EXPECTED_READINGS})")
    print("Repeated header lines skipped:", sum(s["header_lines_skipped"] for s in sensors))
    print("Empty or non-numeric temperature/humidity cells (loaded as NULL):",
          sum(s["empty_or_non_numeric_cells"] for s in sensors))

    matches = len(sensors) == EXPECTED_FILES and total == EXPECTED_READINGS
    if args.dry_run:
        print("Counts match the verified profile." if matches else "WARNING: counts differ from the verified profile.")
        print("Dry run: nothing loaded.")
        return 0

    if not matches:
        raise SystemExit("Refusing to load: counts differ from the verified profile. "
                         "Run the dry run and check the numbers first.")

    count = load(sensors, total)
    print(f"Loaded {count} rows into {TABLE}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())