"""
Profiles missing values and timestamp gaps in the cold-storage sensor files.

Reads the extracted raw and preprocessed CSV files (the originals are never
modified), compares both versions and overview.csv, and writes:
  docs/dataset/sensor_missing_values_report.md
  docs/dataset/sensor_missing_values_report.csv
  docs/dataset/sensor_missing_values_comparison.csv

Usage (from the repo root):
    python scripts/profile_missing_values.py
"""

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SENSOR_DIR = REPO_ROOT / "data" / "raw" / "sensor_data"
RAW_DIR = SENSOR_DIR / "raw_unzipped"
PRE_DIR = SENSOR_DIR / "pre_unzipped"
OVERVIEW = SENSOR_DIR / "overview.csv"
OUT_DIR = REPO_ROOT / "docs" / "dataset"

INTERVAL_S = 5
SENSORS = [f"SENSOR{n:02d}" for n in range(1, 10)]
REPORTED_MISSING = 966  # value reported in the task for preprocessed SENSOR01

# Row counts printed by ingestion/load_sensor_readings.py when the raw files were loaded
LOADED_ROWS = {
    "SENSOR01": 156019, "SENSOR02": 156980, "SENSOR03": 84450,
    "SENSOR04": 151248, "SENSOR05": 31146, "SENSOR06": 156887,
    "SENSOR07": 156885, "SENSOR08": 156863, "SENSOR09": 32717,
}


def find_file(folder, name):
    for p in folder.rglob("*"):
        if p.is_file() and p.name.lower() == name.lower():
            return p
    return None


def load_sensor(path):
    """Read one sensor file. Returns (dataframe, number of repeated header lines)."""
    df = pd.read_csv(
        path, sep=";", header=None, dtype=str, keep_default_na=False,
        usecols=[0, 1, 2, 3], names=["date", "time", "temp", "hum"],
        encoding="utf-8-sig", skip_blank_lines=True,
    ).fillna("")
    header_mask = df["date"].str.strip().str.lower() == "date"
    header_lines = int(header_mask.sum())
    df = df[~header_mask].reset_index(drop=True)
    df["ts"] = pd.to_datetime(
        df["date"].str.strip() + " " + df["time"].str.strip(),
        format="%d.%m.%Y %H:%M:%S", errors="coerce",
    )
    for col in ("temp", "hum"):
        text = df[col].str.strip().str.replace(",", ".", regex=False)
        num = pd.to_numeric(text, errors="coerce")
        bad = (num.isna() | np.isinf(num)) & (text != "")
        df[f"{col}_num"] = num.where(np.isfinite(num))
        df[f"{col}_bad"] = bad
        df[f"{col}_missing"] = (text == "") | bad
    return df, header_lines


def profile(sensor, version, path, df, header_lines):
    n = len(df)
    valid = df.dropna(subset=["ts"]).sort_values("ts")
    uniq = valid["ts"].drop_duplicates()
    diffs = uniq.diff().dropna().dt.total_seconds()
    first, last = uniq.min(), uniq.max()
    expected_slots = int((last - first).total_seconds() // INTERVAL_S) + 1
    off_grid = int((((uniq - first).dt.total_seconds()) % INTERVAL_S != 0).sum())
    gaps = diffs[diffs > INTERVAL_S]
    if len(gaps):
        idx = gaps.idxmax()
        largest = float(gaps.max())
        gap_start = uniq.shift(1).loc[idx].strftime("%Y-%m-%d %H:%M:%S")
        gap_end = uniq.loc[idx].strftime("%Y-%m-%d %H:%M:%S")
    else:
        largest, gap_start, gap_end = 0.0, "", ""
    return {
        "sensor": sensor,
        "version": version,
        "file": path.name,
        "records": n,
        "header_lines_skipped": header_lines,
        "bad_timestamps": n - len(valid),
        "duplicate_timestamps": int(valid["ts"].duplicated().sum()),
        "temp_missing": int(df["temp_missing"].sum()),
        "temp_missing_pct": round(100 * int(df["temp_missing"].sum()) / n, 3),
        "temp_non_numeric": int(df["temp_bad"].sum()),
        "hum_missing": int(df["hum_missing"].sum()),
        "hum_missing_pct": round(100 * int(df["hum_missing"].sum()) / n, 3),
        "hum_non_numeric": int(df["hum_bad"].sum()),
        "both_missing": int((df["temp_missing"] & df["hum_missing"]).sum()),
        "first_reading": first.strftime("%Y-%m-%d %H:%M:%S"),
        "last_reading": last.strftime("%Y-%m-%d %H:%M:%S"),
        "expected_slots": expected_slots,
        "missing_slots": expected_slots - len(uniq),
        "gap_count": int(len(gaps)),
        "gap_missing_slots": int(round((gaps / INTERVAL_S - 1).sum())),
        "largest_gap_s": largest,
        "largest_gap_start": gap_start,
        "largest_gap_end": gap_end,
        "intervals_exactly_5s_pct": round(100 * float((diffs == INTERVAL_S).mean()), 3) if len(diffs) else 0.0,
        "off_grid_timestamps": off_grid,
    }


def compare(sensor, raw_df, pre_df):
    keep = ["ts", "temp_num", "hum_num"]
    r = raw_df.dropna(subset=["ts"]).drop_duplicates("ts")[keep]
    p = pre_df.dropna(subset=["ts"]).drop_duplicates("ts")[keep]
    m = r.merge(p, on="ts", how="outer", suffixes=("_raw", "_pre"), indicator=True)
    both = m[m["_merge"] == "both"]
    pre_only = m[m["_merge"] == "right_only"]
    raw_only = m[m["_merge"] == "left_only"]
    t_diff = (both["temp_num_raw"] - both["temp_num_pre"]).abs()
    h_diff = (both["hum_num_raw"] - both["hum_num_pre"]).abs()
    empty = int((pre_only["temp_num_pre"].isna() & pre_only["hum_num_pre"].isna()).sum())
    return {
        "sensor": sensor,
        "raw_records": len(raw_df),
        "pre_records": len(pre_df),
        "timestamps_in_both": len(both),
        "pre_only_rows": len(pre_only),
        "pre_only_fully_empty": empty,
        "pre_only_with_values": len(pre_only) - empty,
        "raw_only_rows": len(raw_only),
        "raw_temp_present_pre_missing": int((both["temp_num_raw"].notna() & both["temp_num_pre"].isna()).sum()),
        "raw_hum_present_pre_missing": int((both["hum_num_raw"].notna() & both["hum_num_pre"].isna()).sum()),
        "pre_temp_present_raw_missing": int((both["temp_num_raw"].isna() & both["temp_num_pre"].notna()).sum()),
        "max_abs_temp_diff": round(float(t_diff.max()), 4) if t_diff.notna().any() else 0.0,
        "max_abs_hum_diff": round(float(h_diff.max()), 4) if h_diff.notna().any() else 0.0,
    }


def read_overview():
    if not OVERVIEW.exists():
        return {}
    ov = pd.read_csv(OVERVIEW, sep=";", header=None, dtype=str,
                     keep_default_na=False, encoding="utf-8-sig").fillna("")
    labels = ov[0].str.strip().str.lower()
    names_row = ov[labels == "sensor"]
    length_row = ov[labels == "length"]
    if names_row.empty or length_row.empty:
        return {}
    names, values = names_row.iloc[0].tolist(), length_row.iloc[0].tolist()
    result = {}
    for name, val in zip(names[1:], values[1:]):
        if name.strip() and val.strip().isdigit():
            result[name.strip()] = int(val.strip())
    return result


def md_table(frame):
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in row) + " |")
    return "\n".join(lines)


QUALITY_COLS = ["sensor", "records", "header_lines_skipped", "bad_timestamps", "duplicate_timestamps",
                "temp_missing", "temp_missing_pct", "hum_missing", "hum_missing_pct", "both_missing",
                "temp_non_numeric", "hum_non_numeric"]
TIMING_COLS = ["sensor", "first_reading", "last_reading", "expected_slots", "missing_slots", "gap_count",
               "largest_gap_s", "largest_gap_start", "largest_gap_end", "intervals_exactly_5s_pct",
               "off_grid_timestamps"]
COMPARE_COLS = ["sensor", "raw_records", "pre_records", "timestamps_in_both", "pre_only_rows",
                "pre_only_fully_empty", "pre_only_with_values", "raw_only_rows",
                "raw_temp_present_pre_missing", "raw_hum_present_pre_missing",
                "pre_temp_present_raw_missing", "max_abs_temp_diff", "max_abs_hum_diff"]
OVERVIEW_COLS = ["sensor", "overview_length", "raw_records", "raw_minus_overview", "raw_matches_loader"]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    overview = read_overview()
    profiles, comps = [], []

    for s in SENSORS:
        raw_path = find_file(RAW_DIR, f"{s}.CSV")
        pre_path = find_file(PRE_DIR, f"{s}_preprocessed.csv")
        if raw_path is None or pre_path is None:
            raise SystemExit(f"File missing for {s}: raw={raw_path}, preprocessed={pre_path}")
        raw_df, raw_h = load_sensor(raw_path)
        pre_df, pre_h = load_sensor(pre_path)
        profiles.append(profile(s, "raw", raw_path, raw_df, raw_h))
        profiles.append(profile(s, "preprocessed", pre_path, pre_df, pre_h))
        comp = compare(s, raw_df, pre_df)
        comp["overview_length"] = overview.get(s)
        comp["raw_minus_overview"] = (comp["raw_records"] - overview[s]) if s in overview else None
        comp["raw_matches_loader"] = "yes" if comp["raw_records"] == LOADED_ROWS.get(s) else "NO"
        comps.append(comp)
        print(f"{s} done")

    prof = pd.DataFrame(profiles)
    comp = pd.DataFrame(comps)
    prof.to_csv(OUT_DIR / "sensor_missing_values_report.csv", index=False)
    comp.to_csv(OUT_DIR / "sensor_missing_values_comparison.csv", index=False)

    raw_p = prof[prof["version"] == "raw"].reset_index(drop=True)
    pre_p = prof[prof["version"] == "preprocessed"].reset_index(drop=True)

    s1_pre = pre_p[pre_p["sensor"] == "SENSOR01"].iloc[0]
    s1_raw = raw_p[raw_p["sensor"] == "SENSOR01"].iloc[0]
    confirmed = (int(s1_pre["temp_missing"]) == REPORTED_MISSING
                 and int(s1_pre["hum_missing"]) == REPORTED_MISSING)
    verdict = "CONFIRMED" if confirmed else "DIFFERENT FROM THE REPORTED VALUE"

    verification = [
        f"- Reported: {REPORTED_MISSING} missing values in each field of the preprocessed SENSOR01 file.",
        f"- Found in preprocessed SENSOR01: temperature {int(s1_pre['temp_missing'])}, "
        f"humidity {int(s1_pre['hum_missing'])}, rows with both missing {int(s1_pre['both_missing'])} "
        f"(of {int(s1_pre['records'])} rows). Result: {verdict}.",
        f"- Raw SENSOR01: {int(s1_raw['temp_missing'])} missing temperature and "
        f"{int(s1_raw['hum_missing'])} missing humidity values; {int(s1_raw['missing_slots'])} missing 5-second "
        f"slots in {int(s1_raw['gap_count'])} gap(s); largest gap {s1_raw['largest_gap_s']:.0f} s "
        f"from {s1_raw['largest_gap_start']} to {s1_raw['largest_gap_end']}.",
    ]
    if int(s1_pre["temp_missing"]) == int(s1_raw["missing_slots"]) + int(s1_raw["temp_missing"]):
        verification.append(
            "- The preprocessed missing count equals the missing 5-second slots of the raw file plus its empty "
            "values: the preprocessed file shows the raw gap(s) as empty rows.")

    findings = [
        f"- Raw files with missing temperature or humidity values: {int(((raw_p['temp_missing'] > 0) | (raw_p['hum_missing'] > 0)).sum())} of 9 "
        f"(temperature {int(raw_p['temp_missing'].sum())}, humidity {int(raw_p['hum_missing'].sum())} in total).",
        f"- Preprocessed files with missing values: {int(((pre_p['temp_missing'] > 0) | (pre_p['hum_missing'] > 0)).sum())} of 9 "
        f"(temperature {int(pre_p['temp_missing'].sum())}, humidity {int(pre_p['hum_missing'].sum())} in total).",
        f"- Raw files with timestamp gaps: {int((raw_p['gap_count'] > 0).sum())} of 9; "
        f"missing 5-second slots in total {int(raw_p['missing_slots'].sum())}; "
        f"largest gap {raw_p['largest_gap_s'].max():.0f} s ({raw_p.loc[raw_p['largest_gap_s'].idxmax(), 'sensor']}).",
        f"- Duplicate timestamps in raw files: {int(raw_p['duplicate_timestamps'].sum())}; in preprocessed files: {int(pre_p['duplicate_timestamps'].sum())}.",
        f"- Repeated header lines inside raw files: {int(raw_p['header_lines_skipped'].sum()) - 9} "
        f"(each file has one header line at the top, extra ones are skipped).",
        f"- Preprocessed rows without a raw counterpart: {int(comp['pre_only_rows'].sum())} "
        f"(fully empty: {int(comp['pre_only_fully_empty'].sum())}, with values: {int(comp['pre_only_with_values'].sum())}).",
        f"- Raw rows missing from the preprocessed files: {int(comp['raw_only_rows'].sum())}.",
    ]
    if overview:
        diff = comp["raw_minus_overview"].dropna()
        findings.append(
            f"- overview.csv Length differs from the raw record count for {int((diff != 0).sum())} of {len(diff)} sensors "
            f"(raw files contain {int(diff.sum())} rows more in total than the overview lists).")

    report = [
        "# Sensor Missing-Value and Timestamp-Gap Report",
        "",
        f"Generated by scripts/profile_missing_values.py on {date.today():%d %B %Y} from the extracted files in data/raw/sensor_data (extracted copies, not committed).",
        "Expected sampling interval: 5 seconds. Raw and preprocessed files are profiled independently, then compared.",
        "",
        "## 1. Reported value check (preprocessed SENSOR01)",
        *verification,
        "",
        "## 2. Findings",
        *findings,
        "",
        "## 3. Raw files: records and missing values",
        md_table(raw_p[QUALITY_COLS]),
        "",
        "## 4. Raw files: timestamp coverage and gaps",
        md_table(raw_p[TIMING_COLS]),
        "",
        "## 5. Preprocessed files: records and missing values",
        md_table(pre_p[QUALITY_COLS]),
        "",
        "## 6. Preprocessed files: timestamp coverage and gaps",
        md_table(pre_p[TIMING_COLS]),
        "",
        "## 7. Raw versus preprocessed (matched on sensor and timestamp)",
        md_table(comp[COMPARE_COLS]),
        "",
        "## 8. overview.csv Length versus raw record count",
        md_table(comp[OVERVIEW_COLS]),
        "",
        "## 9. Missing-data policy measures (section 7 of the proposed policy)",
        "- Records removed by this analysis: 0. Values imputed: 0. No file was changed, so the counts before and after are identical.",
        "- Missing values are counted separately for temperature and humidity; missing time slots are counted separately from empty values.",
        "- A missing slot is an expected 5-second timestamp without a row between the first and last reading of a file.",
        "",
        "## 10. Limits",
        "- Missing slots assume readings on a regular 5-second grid; off_grid_timestamps lists readings that are not on it.",
        "- Values compared between raw and preprocessed files can differ by rounding (raw uses two decimals, preprocessed one).",
    ]
    (OUT_DIR / "sensor_missing_values_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    show = ["sensor", "records", "temp_missing", "hum_missing", "both_missing", "missing_slots", "gap_count", "largest_gap_s"]
    print("\nRAW\n" + raw_p[show].to_string(index=False))
    print("\nPREPROCESSED\n" + pre_p[show].to_string(index=False))
    print("\nVERIFICATION\n" + "\n".join(verification))
    print("\nFINDINGS\n" + "\n".join(findings))
    print(f"\nReport written to {OUT_DIR / 'sensor_missing_values_report.md'}")


if __name__ == "__main__":
    main()