
from pathlib import Path

import pandas as pd

from profile_sensor_data import (
    PRE_DIR,
    PRE_HEADER,
    read_sensor_file,
)

from profile_household_cold_chain import (
    ROOT,
    EXPECTED,
    FILE_PATTERN,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

OUT_DIR = REPO_ROOT / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE_SIZE = 100


def generate_sensor_sample():

    samples = []

    for path in sorted(PRE_DIR.glob("*_preprocessed.csv")):

        sensor_id = path.stem.split("_")[0].upper()

        df, info, header_ok = read_sensor_file(
            path, PRE_HEADER
        )

        if not header_ok:
            raise ValueError(f"Unexpected header: {path.name}")

        df = df.rename(columns={
            "ts": "timestamp",
            "temp": "temperature_c",
            "hum": "humidity_pct",
        })

        df["source_row"] = df.index + 1

        df = df.sort_values("timestamp")

        df["sensor_id"] = sensor_id
        df["source_file"] = path.name
        df["source_type"] = "historical_sensor"

        df["temperature_missing"] = (
            df["temperature_c"].isna()
        )

        df["humidity_missing"] = (
            df["humidity_pct"].isna()
        )

        df["quality_status"] = "OBSERVED"

        missing = (
            df["temperature_missing"]
            | df["humidity_missing"]
        )

        df.loc[missing, "quality_status"] = (
            "MISSING_MEASUREMENT"
        )

        df["interval_seconds"] = (
            df["timestamp"].diff().dt.total_seconds()
        )

        sample = pd.concat([
            df.head(SAMPLE_SIZE),
            df.loc[missing].head(SAMPLE_SIZE),
        ])

        sample = sample.drop_duplicates(
            subset=["source_row"]
        )

        sample = sample.sort_values("timestamp")

        samples.append(sample)

        print(
            f"{sensor_id}: "
            f"source={len(df)}, "
            f"sample={len(sample)}, "
            f"missing rows="
            f"{sample['quality_status'].eq('MISSING_MEASUREMENT').sum()}"
        )

    result = pd.concat(samples, ignore_index=True)

    output = OUT_DIR / "sensor_pilot_sample.csv"

    result.to_csv(output, index=False)

    print(f"\nSensor sample rows: {len(result)}")
    print(f"Sensor IDs: {result['sensor_id'].nunique()}")
    print(f"Saved: {output}")

    return result


def generate_household_sample():

    first = next(ROOT.rglob("001_1D.txt"), None)

    if first is None:
        raise FileNotFoundError(
            "Household dataset folder not found"
        )

    samples = []

    for path in sorted(first.parent.glob("*.txt")):

        match = FILE_PATTERN.fullmatch(path.name)

        if not match:
            continue

        fridge_id, fridge_type = match.groups()

        df = pd.read_csv(
            path,
            sep="\t",
            dtype=str,
            keep_default_na=False,
            encoding="utf-8-sig",
        )

        df.columns = df.columns.str.strip()

        if list(df.columns) != EXPECTED:
            raise ValueError(
                f"Unexpected header: {path.name}"
            )

        df = df.apply(
            lambda col: pd.to_numeric(
                col.str.strip(),
                errors="coerce",
            )
        )

        df["source_row"] = df.index + 1

        df = df.rename(columns={
            "Time": "elapsed_minutes",
            "T_AMB": "t_amb_c",
            "T_MS": "t_ms_c",
            "T_TS": "t_ts_c",
            "T_VD": "t_vd_c",
            "T_DS": "t_ds_c",
            "T_FC": "t_fc_c",
            "RH_AMB": "rh_amb_pct",
            "RH_MS": "rh_ms_pct",
            "RH_TS": "rh_ts_pct",
            "RH_VD": "rh_vd_pct",
            "RH_DS": "rh_ds_pct",
            "RH_FC": "rh_fc_pct",
            "TP": "product_temperature_c",
        })

        df["fridge_id"] = f"FRIDGE{fridge_id}"
        df["fridge_type"] = fridge_type
        df["source_file"] = path.name
        df["source_type"] = "household_reference"

        df = df.sort_values("elapsed_minutes")

        df["interval_minutes"] = (
            df["elapsed_minutes"].diff()
        )

        samples.append(df.head(SAMPLE_SIZE))

    result = pd.concat(samples, ignore_index=True)

    output = OUT_DIR / "household_pilot_sample.csv"

    result.to_csv(output, index=False)

    print(f"\nHousehold sample rows: {len(result)}")
    print(f"Refrigerator IDs: {result['fridge_id'].nunique()}")
    print(f"Saved: {output}")

    return result


def main():

    print("=== AtmoSync Cleaned Pilot Samples ===")

    sensor = generate_sensor_sample()
    household = generate_household_sample()

    print("\n=== Sample Validation ===")

    print(
        "Sensor duplicate keys:",
        sensor.duplicated(
            ["sensor_id", "timestamp"]
        ).sum()
    )

    print(
        "Household duplicate keys:",
        household.duplicated(
            ["fridge_id", "elapsed_minutes"]
        ).sum()
    )

    print(
        "Sensor missing temperature:",
        sensor["temperature_c"].isna().sum()
    )

    print(
        "Sensor missing humidity:",
        sensor["humidity_pct"].isna().sum()
    )

    print("No imputation performed.")
    print("Original datasets unchanged.")
    print("Pilot sample generation completed.")


if __name__ == "__main__":
    main()
