
import re
from pathlib import Path

import numpy as np
import pandas as pd

from profile_sensor_data import (
    RAW_DIR,
    PRE_DIR,
    RAW_HEADER,
    PRE_HEADER,
    read_sensor_file,
    read_overview,
)

from profile_household_cold_chain import (
    ROOT,
    EXPECTED,
    T_COLS,
    RH_COLS,
    FILE_PATTERN,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

OUT_DIR = REPO_ROOT / "docs" / "dataset"
OUT_DIR.mkdir(parents=True, exist_ok=True)

EXPECTED_SENSORS = {
    f"SENSOR{i:02d}" for i in range(1, 10)
}

EXPECTED_FRIDGES = {
    f"{i:03d}" for i in range(1, 124)
}

records = []
identity_issues = []


def outside_range(values, low, high):
    return int(((values < low) | (values > high)).sum().sum())


def non_finite(values):
    return int(values.isin([np.inf, -np.inf]).sum().sum())


def check_sensor_files():

    datasets = [
        ("sensor_raw", RAW_DIR, RAW_HEADER, r"(SENSOR\d{2})\.csv"),
        (
            "sensor_preprocessed",
            PRE_DIR,
            PRE_HEADER,
            r"(SENSOR\d{2})_preprocessed\.csv",
        ),
    ]

    for dataset, folder, header, pattern in datasets:

        found_ids = []

        for path in sorted(folder.iterdir()):

            if not path.is_file() or path.suffix.lower() != ".csv":
                continue

            match = re.fullmatch(pattern, path.name, re.IGNORECASE)

            if not match:
                identity_issues.append(
                    f"{dataset}: unexpected filename {path.name}"
                )
                continue

            sensor_id = match.group(1).upper()
            found_ids.append(sensor_id)

            df, info, header_ok = read_sensor_file(path, header)

            valid_ts = df["ts"].dropna()
            steps = valid_ts.diff().dt.total_seconds().dropna()

            records.append({
                "dataset": dataset,
                "device_id": sensor_id,
                "source_file": path.name,
                "rows": len(df),
                "header_ok": header_ok,
                "duplicate_records": int(df.duplicated().sum()),
                "duplicate_time_keys": int(valid_ts.duplicated().sum()),
                "invalid_time_keys": int(df["ts"].isna().sum()),
                "non_increasing_steps": int((steps <= 0).sum()),
                "unexpected_intervals": int((steps != 5).sum()),
                "missing_cells": info["empty_cells"],
                "non_numeric_cells": info["non_numeric_cells"],
                "non_finite_cells": non_finite(df[["temp", "hum"]]),
                "repeated_header_rows": info["repeated_header_rows"],
                "temperature_min": df["temp"].min(),
                "temperature_max": df["temp"].max(),
                "temperature_outside_screen": outside_range(
                    df["temp"], -50, 80
                ),
                "humidity_min": df["hum"].min(),
                "humidity_max": df["hum"].max(),
                "humidity_outside_range": outside_range(
                    df["hum"], 0, 100
                ),
                "temperature_unit": "C",
                "humidity_unit": "%",
                "time_unit": "seconds",
                "expected_interval": 5,
            })

        missing = EXPECTED_SENSORS - set(found_ids)
        unexpected = set(found_ids) - EXPECTED_SENSORS

        if missing:
            identity_issues.append(f"{dataset}: missing IDs {sorted(missing)}")

        if unexpected:
            identity_issues.append(
                f"{dataset}: unexpected IDs {sorted(unexpected)}"
            )

        if len(found_ids) != len(set(found_ids)):
            identity_issues.append(f"{dataset}: duplicate sensor IDs")

        print(f"{dataset}: {len(found_ids)} files checked")

    overview_ids = set(read_overview())

    if overview_ids != EXPECTED_SENSORS:
        identity_issues.append(
            f"Overview ID mismatch: {sorted(overview_ids)}"
        )

    print("Overview IDs:", sorted(overview_ids))


def check_household_files():

    first = next(ROOT.rglob("001_1D.txt"), None)

    if first is None:
        raise FileNotFoundError("Household measurement folder not found")

    found_ids = []

    for path in sorted(first.parent.glob("*.txt")):

        match = FILE_PATTERN.fullmatch(path.name)

        if not match:
            identity_issues.append(
                f"Household: unexpected filename {path.name}"
            )
            continue

        fridge_id, fridge_type = match.groups()
        found_ids.append(fridge_id)

        if fridge_type not in {"1D", "2DT", "2DB"}:
            identity_issues.append(
                f"Invalid fridge type: {path.name}"
            )

        df = pd.read_csv(
            path,
            sep="\t",
            dtype=str,
            keep_default_na=False,
            encoding="utf-8-sig",
        )

        df.columns = df.columns.str.strip()

        if list(df.columns) != EXPECTED:
            identity_issues.append(
                f"Household header mismatch: {path.name}"
            )
            continue

        stripped = df.apply(lambda col: col.str.strip())
        numeric = stripped.apply(pd.to_numeric, errors="coerce")

        empty = stripped.eq("")
        bad_numeric = numeric.isna() & ~empty

        valid_time = numeric["Time"].replace(
            [np.inf, -np.inf], np.nan
        ).dropna()

        steps = valid_time.diff().dropna()

        temperatures = numeric[T_COLS + ["TP"]]
        humidity = numeric[RH_COLS]

        records.append({
            "dataset": "household",
            "device_id": fridge_id,
            "fridge_type": fridge_type,
            "source_file": path.name,
            "rows": len(df),
            "header_ok": True,
            "duplicate_records": int(numeric.duplicated().sum()),
            "duplicate_time_keys": int(valid_time.duplicated().sum()),
            "invalid_time_keys": int(len(df) - len(valid_time)),
            "non_increasing_steps": int((steps <= 0).sum()),
            "unexpected_intervals": int((~np.isclose(steps, 5)).sum()),
            "missing_cells": int(empty.sum().sum()),
            "non_numeric_cells": int(bad_numeric.sum().sum()),
            "non_finite_cells": non_finite(numeric),
            "repeated_header_rows": 0,
            "temperature_min": temperatures.min().min(),
            "temperature_max": temperatures.max().max(),
            "temperature_outside_screen": outside_range(
                temperatures, -30, 70
            ),
            "humidity_min": humidity.min().min(),
            "humidity_max": humidity.max().max(),
            "humidity_outside_range": outside_range(
                humidity, 0, 100
            ),
            "temperature_unit": "C",
            "humidity_unit": "%",
            "time_unit": "minutes",
            "expected_interval": 5,
        })

    missing = EXPECTED_FRIDGES - set(found_ids)
    unexpected = set(found_ids) - EXPECTED_FRIDGES

    if missing:
        identity_issues.append(
            f"Household missing IDs: {sorted(missing)}"
        )

    if unexpected:
        identity_issues.append(
            f"Household unexpected IDs: {sorted(unexpected)}"
        )

    if len(found_ids) != len(set(found_ids)):
        identity_issues.append("Household duplicate refrigerator IDs")

    print(f"Household: {len(found_ids)} files checked")


def main():

    print("=== AtmoSync Dataset Quality Validation ===")

    check_sensor_files()
    check_household_files()

    report = pd.DataFrame(records)

    output = OUT_DIR / "dataset_quality_report.csv"
    report.to_csv(output, index=False)

    metrics = [
        "rows",
        "duplicate_records",
        "duplicate_time_keys",
        "invalid_time_keys",
        "non_increasing_steps",
        "unexpected_intervals",
        "missing_cells",
        "non_numeric_cells",
        "non_finite_cells",
        "repeated_header_rows",
        "temperature_outside_screen",
        "humidity_outside_range",
    ]

    print("\n=== Quality Summary ===")
    print(report.groupby("dataset")[metrics].sum().T.to_string())

    print("\n=== Temperature and Humidity Ranges ===")
    print(
        report.groupby("dataset").agg(
            temperature_min=("temperature_min", "min"),
            temperature_max=("temperature_max", "max"),
            humidity_min=("humidity_min", "min"),
            humidity_max=("humidity_max", "max"),
        ).to_string()
    )

    print("\n=== Identity and Header Issues ===")

    header_issues = report.loc[
        ~report["header_ok"], "source_file"
    ].tolist()

    issues = identity_issues + [
        f"Header mismatch: {name}" for name in header_issues
    ]

    if issues:
        for issue in issues:
            print(issue)
    else:
        print("No identity or header issues detected.")

    print("\n=== Unit and Screening Notes ===")
    print("Raw sensor units: C and % from source headers.")
    print("Preprocessed units: inferred from raw-data comparison.")
    print("Household units: C, % and elapsed minutes from README.")
    print("Sensor temperature screen: -50 to 80 C (provisional).")
    print("Household screen: -30 to 70 C (documented logger range).")
    print("Duplicates counted after parsing and normalization.")
    print("Screening limits are not food-safety thresholds.")
    print("No source records modified, deleted or imputed.")

    print(f"\nReport saved to: {output}")


if __name__ == "__main__":
    main()
