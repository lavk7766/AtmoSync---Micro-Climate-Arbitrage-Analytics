"""
Profiles the real sensor dataset (9 sensors) in data/raw/sensor_data.

Reads the unzipped raw files, the unzipped preprocessed files and overview.csv,
and checks the open points from the data design document:

  1. Row counts: raw readings versus the Length column of overview.csv
     (header lines repeated inside a file are counted separately, not as readings)
  2. Time steps: is every step exactly 5 seconds, are there gaps or duplicates
  3. Preprocessed files: common time grid, empty values, do the values match the raw files
  4. First readings: when does the temperature first drop (a screening threshold is used)

Writes docs/design/sensor_file_profile.csv (one row per sensor).
Nothing is written to Snowflake.

Before the first run, unzip the two zip files into:
  data/raw/sensor_data/raw_unzipped/   (from Raw.zip)
  data/raw/sensor_data/pre_unzipped/   (from Preprocessed.zip)
These folders are not in Git.

Usage (from the repo root):
    python scripts/profile_sensor_data.py
"""

import csv
import re
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SENSOR_DIR = REPO_ROOT / "data" / "raw" / "sensor_data"
RAW_DIR = SENSOR_DIR / "raw_unzipped"
PRE_DIR = SENSOR_DIR / "pre_unzipped"
OVERVIEW = SENSOR_DIR / "overview.csv"
OUT_FILE = REPO_ROOT / "docs" / "design" / "sensor_file_profile.csv"

RAW_HEADER = ["Date", "Time", "Temperature (C)", "Humidity (%)"]
PRE_HEADER = ["Date", "Time", "Temperature", "Humidity"]
DATE_FORMAT = "%d.%m.%Y %H:%M:%S"
STEP_SECONDS = 5
VALUE_TOLERANCE = 0.051      # values have one decimal
COLD_C = 12.0                # screening threshold only, not a safety threshold
RAW_PATTERN = re.compile(r"^(SENSOR\d{2})\.CSV$", re.IGNORECASE)


def read_sensor_file(path, expected_header):
    """Return (dataframe with ts, temp, hum, empty/non-numeric counts, header_ok)."""
    df = pd.read_csv(path, sep=";", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    header_ok = [c.strip() for c in df.columns] == expected_header
    if df.shape[1] != 4:
        raise ValueError(f"{path.name}: expected 4 columns, found {df.shape[1]}")
    df.columns = ["date", "time", "temp", "hum"]
    df = df.apply(lambda s: s.str.strip())

    # Some files repeat the header line inside the data (logger restart or joined files).
    # These lines hold no reading, so they are counted and removed.
    repeated_header = df["date"].str.lower() == "date"
    repeated_header_rows = int(repeated_header.sum())
    df = df[~repeated_header].reset_index(drop=True)

    ts = pd.to_datetime(df["date"] + " " + df["time"], format=DATE_FORMAT, errors="coerce")
    temp = pd.to_numeric(df["temp"], errors="coerce")
    hum = pd.to_numeric(df["hum"], errors="coerce")
    info = {
        "repeated_header_rows": repeated_header_rows,
        "empty_cells": int((df["temp"] == "").sum() + (df["hum"] == "").sum()),
        "non_numeric_cells": int(((temp.isna()) & (df["temp"] != "")).sum()
                                 + ((hum.isna()) & (df["hum"] != "")).sum()),
    }
    return pd.DataFrame({"ts": ts, "temp": temp, "hum": hum}), info, header_ok


def timing(ts):
    s = ts.dropna()
    d = s.diff().dt.total_seconds().dropna()
    return {
        "rows": len(ts),
        "bad_timestamps": int(ts.isna().sum()),
        "first": s.min(),
        "last": s.max(),
        "duplicate_timestamps": int(s.duplicated().sum()),
        "not_increasing_steps": int((d <= 0).sum()),
        "steps_not_5s": int((d != STEP_SECONDS).sum()),
        "largest_step_s": float(d.max()) if len(d) else float("nan"),
    }


def read_overview():
    """overview.csv has one row per statistic and one column per sensor."""
    csv.field_size_limit(10**8)
    rows = {}
    with open(OVERVIEW, newline="", encoding="utf-8-sig") as f:
        for row in csv.reader(f, delimiter=";"):
            if row:
                rows[row[0].strip()] = row[1:]
    sensors = [s.strip().upper() for s in rows["Sensor"]]
    out = {}
    for i, name in enumerate(sensors):
        def val(label):
            values = rows.get(label, [])
            return values[i].strip() if i < len(values) else ""
        out[name] = {
            "start": pd.to_datetime(val("Start"), errors="coerce"),
            "end": pd.to_datetime(val("End"), errors="coerce"),
            "length": int(val("Length")) if val("Length").isdigit() else None,
        }
    return out


def main():
    raw_files = sorted(p for p in RAW_DIR.glob("*.CSV") if RAW_PATTERN.match(p.name))
    if not raw_files:
        raise SystemExit(f"No SENSORnn.CSV files found in {RAW_DIR}\n"
                         "Unzip Raw.zip into raw_unzipped first.")
    overview = read_overview()

    # Preprocessed files first: they define the common time window
    pre = {}
    for p in raw_files:
        name = p.stem.upper()
        pre_path = PRE_DIR / f"{name}_preprocessed.csv"
        if not pre_path.exists():
            raise SystemExit(f"Missing {pre_path}\nUnzip Preprocessed.zip into pre_unzipped first.")
        pre[name] = read_sensor_file(pre_path, PRE_HEADER)
    window_start = min(v[0]["ts"].min() for v in pre.values())
    window_end = max(v[0]["ts"].max() for v in pre.values())

    records = []
    for path in raw_files:
        name = path.stem.upper()
        raw, raw_info, raw_header_ok = read_sensor_file(path, RAW_HEADER)
        pdf, pre_info, pre_header_ok = pre[name]
        rt, pt = timing(raw["ts"]), timing(pdf["ts"])
        ov = overview.get(name, {})

        in_window = (raw["ts"] >= window_start) & (raw["ts"] <= window_end)
        both_present = pdf["temp"].notna() & pdf["hum"].notna()
        both_missing = pdf["temp"].isna() & pdf["hum"].isna()

        # Do preprocessed values match the raw values at the same timestamp?
        raw_unique = raw.dropna(subset=["ts"]).drop_duplicates("ts")
        merged = pdf[both_present].merge(raw_unique, on="ts", how="left", suffixes=("_pre", "_raw"))
        matched = merged["temp_raw"].notna()
        mismatch = ((merged["temp_pre"] - merged["temp_raw"]).abs() > VALUE_TOLERANCE) | \
                   ((merged["hum_pre"] - merged["hum_raw"]).abs() > VALUE_TOLERANCE)
        raw_in_window_ts = set(raw.loc[in_window, "ts"].dropna())
        pre_value_ts = set(pdf.loc[both_present, "ts"])

        valid_raw = raw.dropna(subset=["ts"])
        cold = valid_raw[valid_raw["temp"] <= COLD_C]
        first_cold = cold["ts"].min() if len(cold) else pd.NaT
        minutes_to_cold = ((first_cold - rt["first"]).total_seconds() / 60) if pd.notna(first_cold) else float("nan")

        records.append({
            "sensor": name,
            "raw_header_ok": raw_header_ok,
            "pre_header_ok": pre_header_ok,
            "raw_repeated_header_rows": raw_info["repeated_header_rows"],
            "raw_rows": rt["rows"],
            "overview_length": ov.get("length"),
            "raw_rows_minus_overview_length": rt["rows"] - ov["length"] if ov.get("length") else None,
            "raw_first": rt["first"], "raw_last": rt["last"],
            "overview_start_matches_raw_first": bool(ov.get("start") == rt["first"]),
            "overview_end_matches_raw_last": bool(ov.get("end") == rt["last"]),
            "raw_rows_before_window": int((raw["ts"] < window_start).sum()),
            "raw_rows_in_window": int(in_window.sum()),
            "raw_rows_after_window": int((raw["ts"] > window_end).sum()),
            "raw_bad_timestamps": rt["bad_timestamps"],
            "raw_duplicate_timestamps": rt["duplicate_timestamps"],
            "raw_not_increasing_steps": rt["not_increasing_steps"],
            "raw_steps_not_5s": rt["steps_not_5s"],
            "raw_largest_step_s": rt["largest_step_s"],
            "raw_empty_cells": raw_info["empty_cells"],
            "raw_non_numeric_cells": raw_info["non_numeric_cells"],
            "raw_temp_min": raw["temp"].min(), "raw_temp_max": raw["temp"].max(),
            "raw_hum_min": raw["hum"].min(), "raw_hum_max": raw["hum"].max(),
            "raw_hum_outside_0_100": int(((raw["hum"] < 0) | (raw["hum"] > 100)).sum()),
            "raw_first_temp": raw["temp"].iloc[0], "raw_first_hum": raw["hum"].iloc[0],
            "raw_minutes_until_temp_le_threshold": minutes_to_cold,
            "pre_rows": pt["rows"],
            "pre_first": pt["first"], "pre_last": pt["last"],
            "pre_steps_not_5s": pt["steps_not_5s"],
            "pre_rows_with_both_values": int(both_present.sum()),
            "pre_rows_both_missing": int(both_missing.sum()),
            "pre_rows_one_value_missing": int((~both_present & ~both_missing).sum()),
            "pre_values_minus_overview_length": int(both_present.sum()) - ov["length"] if ov.get("length") else None,
            "pre_values_found_in_raw": int(matched.sum()),
            "pre_values_not_in_raw": int((~matched).sum()),
            "pre_values_differing_from_raw": int((mismatch & matched).sum()),
            "raw_in_window_not_in_pre_values": len(raw_in_window_ts - pre_value_ts),
        })

    profile = pd.DataFrame(records)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    profile.to_csv(OUT_FILE, index=False)

    print(f"Sensors: {len(profile)} | common window from preprocessed files: {window_start} to {window_end}")
    print(f"Raw headers as expected: {int(profile['raw_header_ok'].sum())}/{len(profile)} | "
          f"preprocessed headers as expected: {int(profile['pre_header_ok'].sum())}/{len(profile)}")
    print("\n1. Raw rows versus overview.csv Length")
    print(profile[["sensor", "raw_rows", "raw_repeated_header_rows", "overview_length",
                   "raw_rows_minus_overview_length", "raw_rows_before_window",
                   "raw_rows_after_window", "raw_bad_timestamps"]].to_string(index=False))
    print("\n2. Time steps in the raw files (expected: only 5 seconds)")
    print(profile[["sensor", "raw_steps_not_5s", "raw_largest_step_s",
                   "raw_duplicate_timestamps", "raw_bad_timestamps"]].to_string(index=False))
    print("\n3. Preprocessed files")
    print(profile[["sensor", "pre_rows", "pre_steps_not_5s", "pre_rows_with_both_values",
                   "pre_rows_both_missing", "pre_values_minus_overview_length",
                   "pre_values_not_in_raw", "pre_values_differing_from_raw"]].to_string(index=False))
    print(f"\n4. Minutes until the first reading at or below {COLD_C} C (screening threshold only)")
    print(profile[["sensor", "raw_first_temp", "raw_first_hum",
                   "raw_minutes_until_temp_le_threshold"]].to_string(index=False))
    print(f"\nFull profile written to {OUT_FILE}")


if __name__ == "__main__":
    main()