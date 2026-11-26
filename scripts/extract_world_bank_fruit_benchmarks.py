import csv
import posixpath
import re
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET


SOURCE = Path(
    "data/raw/commodity_prices/CMO-Historical-Data-Monthly.xlsx"
)

OUTPUT = Path(
    "data/processed/commodity_benchmarks/"
    "world_bank_fruit_benchmarks.csv"
)

NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "p": "http://schemas.openxmlformats.org/package/2006/relationships",
}

REL_NS = (
    "{http://schemas.openxmlformats.org/"
    "officeDocument/2006/relationships}id"
)

SELECTED_SERIES = {
    "Banana, Europe",
    "Banana, US",
    "Orange",
}


def column_number(reference):
    letters = re.match(r"[A-Z]+", reference).group()
    result = 0

    for char in letters:
        result = result * 26 + ord(char) - 64

    return result


def read_cell(cell, shared_strings):
    cell_type = cell.get("t")

    if cell_type == "inlineStr":
        return "".join(
            node.text or ""
            for node in cell.findall(".//m:t", NS)
        )

    value_node = cell.find("m:v", NS)

    if value_node is None:
        return None

    if cell_type == "s":
        return shared_strings[int(value_node.text)]

    return value_node.text


def load_monthly_sheet(archive):
    workbook = ET.fromstring(
        archive.read("xl/workbook.xml")
    )

    relationships = ET.fromstring(
        archive.read("xl/_rels/workbook.xml.rels")
    )

    relationship_map = {
        relationship.get("Id"): relationship.get("Target")
        for relationship in relationships.findall(
            "p:Relationship", NS
        )
    }

    monthly_sheet = next(
        (
            sheet
            for sheet in workbook.find("m:sheets", NS)
            if sheet.get("name") == "Monthly Prices"
        ),
        None,
    )

    if monthly_sheet is None:
        raise ValueError("Monthly Prices worksheet was not found.")

    relationship_id = monthly_sheet.get(REL_NS)
    target = relationship_map[relationship_id]

    sheet_path = (
        target.lstrip("/")
        if target.startswith("/")
        else posixpath.normpath("xl/" + target)
    )

    root = ET.fromstring(archive.read(sheet_path))
    sheet_data = root.find("m:sheetData", NS)

    shared_strings = []

    if "xl/sharedStrings.xml" in archive.namelist():
        shared_root = ET.fromstring(
            archive.read("xl/sharedStrings.xml")
        )

        shared_strings = [
            "".join(
                node.text or ""
                for node in item.findall(".//m:t", NS)
            )
            for item in shared_root.findall("m:si", NS)
        ]

    rows = {}

    for row in sheet_data.findall("m:row", NS):
        row_number = int(row.get("r"))
        cells = {}

        for cell in row.findall("m:c", NS):
            cells[column_number(cell.get("r"))] = read_cell(
                cell, shared_strings
            )

        rows[row_number] = cells

    return rows


def main():
    if not SOURCE.exists():
        raise FileNotFoundError(
            f"Source workbook not found: {SOURCE}"
        )

    with ZipFile(SOURCE) as archive:
        rows = load_monthly_sheet(archive)

    date_pattern = re.compile(r"^(\d{4})M(\d{2})$")

    dated_rows = []

    for row_number, cells in rows.items():
        period = cells.get(1)

        if isinstance(period, str) and date_pattern.fullmatch(period):
            dated_rows.append((row_number, cells, period))

    if not dated_rows:
        raise ValueError("No monthly observation rows were found.")

    dated_rows.sort(key=lambda item: item[0])

    first_date_row = dated_rows[0][0]

    header_row = rows[first_date_row - 2]
    unit_row = rows[first_date_row - 1]

    column_lookup = {
        str(value).strip(): column
        for column, value in header_row.items()
        if value is not None
    }

    missing_series = SELECTED_SERIES - set(column_lookup)

    if missing_series:
        raise ValueError(
            f"Expected benchmark series not found: {missing_series}"
        )

    update_text = rows.get(4, {}).get(1, "")
    update_date = ""

    match = re.search(
        r"Updated on (.+)",
        str(update_text),
        flags=re.IGNORECASE,
    )

    if match:
        try:
            update_date = datetime.strptime(
                match.group(1).strip(),
                "%B %d, %Y",
            ).date().isoformat()
        except ValueError:
            pass

    records = []

    for row_number, cells, period in dated_rows:
        year, month = map(int, date_pattern.fullmatch(period).groups())
        observation_month = f"{year:04d}-{month:02d}"

        for series_name in sorted(SELECTED_SERIES):
            column = column_lookup[series_name]
            raw_value = cells.get(column)

            price_value = ""

            if raw_value is not None:
                try:
                    numeric_value = float(raw_value)

                    if numeric_value == numeric_value and abs(numeric_value) != float("inf"):
                        if numeric_value < 0:
                            raise ValueError(
                                f"Negative benchmark value: {series_name}, {period}"
                            )

                        price_value = format(numeric_value, ".12g")

                except (ValueError, TypeError):
                    # Source placeholders such as ellipses remain missing.
                    price_value = ""

            region = (
                series_name.split(",", 1)[1].strip()
                if "," in series_name
                else "Not specified in series label"
            )

            records.append({
                "observation_month": observation_month,
                "commodity_series": series_name,
                "commodity_name": series_name.split(",", 1)[0].strip(),
                "market_coverage": region,
                "price_value": price_value,
                "price_unit": str(unit_row.get(column, "")).strip(),
                "currency": "USD",
                "normalized_unit": "USD/kg",
                "source_type": "global_reference_benchmark",
                "source_name": "World Bank Commodity Price Data (Pink Sheet)",
                "source_sheet": "Monthly Prices",
                "source_update_date": update_date,
                "source_file": SOURCE.name,
            })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(records[0].keys())

    with OUTPUT.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    numeric_records = [
        row for row in records if row["price_value"] != ""
    ]

    print("\n========== BENCHMARK EXTRACTION ==========")
    print("Source:", SOURCE)
    print("Output:", OUTPUT)
    print("Selected series:", len(SELECTED_SERIES))
    print("Monthly periods:", len(dated_rows))
    print("Total output records:", len(records))
    print("Numeric observations:", len(numeric_records))
    print("Missing observations:", len(records) - len(numeric_records))
    print("Workbook update date:", update_date)
    print("First period:", dated_rows[0][2])
    print("Last period:", dated_rows[-1][2])

    print("\n========== LATEST AVAILABLE VALUES ==========")

    for series_name in sorted(SELECTED_SERIES):
        latest = next(
            (
                row for row in reversed(records)
                if row["commodity_series"] == series_name
                and row["price_value"] != ""
            ),
            None,
        )

        if latest:
            print(
                f'{series_name}: '
                f'{latest["price_value"]} '
                f'{latest["currency"]}/kg '
                f'({latest["observation_month"]})'
            )
        else:
            print(f"{series_name}: no numeric observations")

    print("\nExtraction completed successfully.")


if __name__ == "__main__":
    main()
