"""
Profiles all household refrigerator files (123 expected).

Checks header, row counts, time step, empty cells, non-numeric cells,
humidity range and value ranges. Writes docs/design/household_file_profile.csv.

Usage (from the repo root):
    python scripts/profile_household_cold_chain.py
"""

import re
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT = REPO_ROOT / "data" / "raw" / "household_cold_chain" / "unzipped"
OUT_FILE = REPO_ROOT / "docs" / "design" / "household_file_profile.csv"

EXPECTED = ["Time", "T_AMB", "T_MS", "T_TS", "T_VD", "T_DS", "T_FC",
            "RH_AMB", "RH_MS", "RH_TS", "RH_VD", "RH_DS", "RH_FC", "TP"]
T_COLS = ["T_AMB", "T_MS", "T_TS", "T_VD", "T_DS", "T_FC"]
RH_COLS = ["RH_AMB", "RH_MS", "RH_TS", "RH_VD", "RH_DS", "RH_FC"]
FILE_PATTERN = re.compile(r"^(\d{3})_(.+)\.txt$")


def main():
    first = next(ROOT.rglob("001_1D.txt"), None)
    if first is None:
        raise SystemExit(f"001_1D.txt not found under {ROOT}")
    data_dir = first.parent
    files = sorted(p for p in data_dir.glob("*.txt") if FILE_PATTERN.match(p.name))

    rows = []
    col_min, col_max = {}, {}

    for path in files:
        number, ftype = FILE_PATTERN.match(path.name).groups()
        df = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False, encoding="utf-8-sig")
        df.columns = [c.strip() for c in df.columns]
        header_ok = list(df.columns) == EXPECTED
        record = {"file": path.name, "fridge_number": int(number), "fridge_type": ftype,
                  "data_rows": len(df), "header_ok": header_ok}

        if not header_ok:
            record["note"] = f"header differs: {list(df.columns)}"
            rows.append(record)
            continue

        stripped = df.apply(lambda s: s.str.strip())
        numeric = stripped.apply(pd.to_numeric, errors="coerce")
        empty = stripped == ""
        bad_text = numeric.isna() & ~empty
        time = numeric["Time"].dropna()
        steps = sorted(set(time.diff().dropna().round(3)))

        record.update({
            "time_start": time.min(),
            "time_end": time.max(),
            "time_steps": ";".join(str(s) for s in steps),
            "empty_cells": int(empty.sum().sum()),
            "non_numeric_cells": int(bad_text.sum().sum()),
            "humidity_cells_outside_0_100": int(((numeric[RH_COLS] < 0) | (numeric[RH_COLS] > 100)).sum().sum()),
            "temp_min": numeric[T_COLS].min().min(),
            "temp_max": numeric[T_COLS].max().max(),
            "rh_min": numeric[RH_COLS].min().min(),
            "rh_max": numeric[RH_COLS].max().max(),
            "tp_min": numeric["TP"].min(),
            "tp_max": numeric["TP"].max(),
            "tp_constant": bool(numeric["TP"].nunique() <= 1),
        })
        rows.append(record)

        for c in EXPECTED[1:]:
            col_min[c] = min(col_min.get(c, float("inf")), numeric[c].min())
            col_max[c] = max(col_max.get(c, float("-inf")), numeric[c].max())

    profile = pd.DataFrame(rows)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    profile.to_csv(OUT_FILE, index=False)

    ok = profile[profile["header_ok"]]
    print(f"Data folder: {data_dir}")
    print(f"Files: {len(profile)} | header matches expected: {len(ok)}")
    print("Files per type:")
    print(profile["fridge_type"].value_counts().to_string())
    print(f"Data rows per file: min {profile['data_rows'].min()}, "
          f"median {profile['data_rows'].median():.0f}, max {profile['data_rows'].max()}")
    print("Time steps seen (minutes):", sorted(set(";".join(ok["time_steps"].astype(str)).split(";"))))
    print("Empty cells (all files):", int(ok["empty_cells"].sum()))
    print("Non-numeric cells (all files):", int(ok["non_numeric_cells"].sum()))
    print("Files with humidity outside 0-100:", int((ok["humidity_cells_outside_0_100"] > 0).sum()))
    print("Files where TP never changes:", int(ok["tp_constant"].sum()))
    print("Overall min / max per column:")
    for c in EXPECTED[1:]:
        print(f"  {c}: {col_min.get(c)} to {col_max.get(c)}")
    print(f"Full profile written to {OUT_FILE}")


if __name__ == "__main__":
    main()