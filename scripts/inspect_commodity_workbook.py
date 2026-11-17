
"""
Inspect all five sheets of the World Bank commodity workbook.

AtmoSync - Day 8
17 November 2026
"""

from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]

XLSX = (
    REPO_ROOT
    / "data"
    / "raw"
    / "commodity_prices"
    / "CMO-Historical-Data-Monthly.xlsx"
)

EXPECTED_SHEETS = [
    "Monthly Prices",
    "Monthly Indices",
    "Description",
    "Index Weights",
    "Mismatch Details",
]


def inspect_sheet(workbook, sheet_name):
    print("\n" + "=" * 80)
    print(f"SHEET: {sheet_name}")
    print("=" * 80)

    df = pd.read_excel(
        workbook,
        sheet_name=sheet_name,
        header=None,
        dtype=object
    )

    print(f"Rows: {df.shape[0]}")
    print(f"Columns: {df.shape[1]}")
    print(f"Non-empty cells: {int(df.notna().sum().sum())}")

    print("\nFirst 12 rows (first 8 columns):")
    print(
        df.iloc[:12, :8]
        .fillna("")
        .to_string(index=True, header=False)
    )

    # Identify monthly period rows.
    first_col = df.iloc[:, 0].astype(str).str.strip()

    monthly_mask = first_col.str.fullmatch(
        r"\d{4}M(0[1-9]|1[0-2])"
    )

    monthly_rows = df.loc[monthly_mask]

    if not monthly_rows.empty:
        periods = first_col[monthly_mask]

        dates = pd.to_datetime(
            periods.str.replace("M", "-", regex=False)
            + "-01"
        )

        print("\nMonthly period layout:")
        print(f"Monthly rows: {len(periods)}")
        print(f"First monthly Excel row: {monthly_rows.index[0] + 1}")
        print(f"Start month: {dates.min():%Y-%m}")
        print(f"End month: {dates.max():%Y-%m}")
        print(f"Duplicate months: {dates.duplicated().sum()}")
        print(f"Chronological order: {dates.is_monotonic_increasing}")

    else:
        print("\nNo YYYYMmm periods detected in column A.")

    if sheet_name == "Monthly Prices":
        print("\nCommodity names and units:")

        for col in range(1, df.shape[1]):
            name = df.iloc[4, col]
            unit = df.iloc[5, col]

            print(f"  {col}: {name} | {unit}")

    if sheet_name == "Monthly Indices":
        print("\nHeader and index base information:")
        print(
            df.iloc[:7]
            .fillna("")
            .to_string(index=True, header=False)
        )

    if sheet_name == "Index Weights":
        print("\nIndex weight preview:")
        print(
            df.iloc[:25]
            .fillna("")
            .to_string(index=True, header=False)
        )

    if sheet_name == "Mismatch Details":
        print("\nMismatch details preview:")
        print(
            df.iloc[:25]
            .fillna("")
            .to_string(index=True, header=False)
        )

def inspect_relevant_details(workbook):
    print("\n=== Relevant Commodity Descriptions ===")

    for sheet in ["Description", "Index Weights"]:
        df = pd.read_excel(
            workbook,
            sheet_name=sheet,
            header=None,
            dtype=object
        )

        mask = df.apply(
            lambda row: row.astype(str).str.contains(
                r"\b(?:bananas?|oranges?)\b",
                case=False,
                regex=True
            ).any(),
            axis=1
        )

        print(f"\n{sheet}:")
        print(
            df.loc[mask]
            .dropna(axis=1, how="all")
            .to_string(index=True, header=False)
        )

    print("\n=== Complete Mismatch Summary ===")

    mismatch = pd.read_excel(
        workbook,
        sheet_name="Mismatch Details",
        header=3
    )

    print(f"Total mismatch rows: {len(mismatch)}")

    print("\nMismatches by commodity:")
    print(mismatch["Commodity"].value_counts().to_string())

    print("\nMismatches by difference type:")
    print(
        mismatch["Difference Type"]
        .value_counts()
        .to_string()
    )

    print("\nDuplicate period-commodity keys:")
    print(
        mismatch.duplicated(
            subset=["Period", "Commodity"]
        ).sum()
    )

    fruit_mask = mismatch["Commodity"].astype(str).str.contains(
        r"\b(?:bananas?|oranges?)\b",
        case=False,
        regex=True
    )

    print("\nBanana and Orange mismatches:")
    print(mismatch.loc[fruit_mask].to_string(index=False))

    print(f"Relevant fruit mismatches: {fruit_mask.sum()}")




def main():
    print("=== AtmoSync Commodity Workbook Inspection ===")
    print(f"Workbook: {XLSX.name}")

    if not XLSX.exists():
        raise FileNotFoundError(XLSX)

    with pd.ExcelFile(XLSX) as workbook:
        print("\nAvailable sheets:")

        for sheet in workbook.sheet_names:
            print(f"  - {sheet}")

        missing = [
            sheet for sheet in EXPECTED_SHEETS
            if sheet not in workbook.sheet_names
        ]

        print(f"\nMissing expected sheets: {missing}")

        for sheet in EXPECTED_SHEETS:
            if sheet in workbook.sheet_names:
                inspect_sheet(workbook, sheet)

        # NEW LINE ADDED HERE
        inspect_relevant_details(workbook)

    print("\n" + "=" * 80)
    print("Workbook inspection completed.")
    print("Original workbook unchanged.")
    print("=" * 80)


if __name__ == "__main__":
    main()
