# Sensor Data Quality Audit

## Scope

This audit compares the nine raw sensor CSVs in `Raw.zip` with the aligned sensor CSVs in `Preprocessed.zip`. Raw repeated-header rows were excluded before counting records and checking timestamps.

## Raw-file checks

All nine sensors have:
- Zero unparsed timestamps after excluding repeated headers
- Zero duplicate data rows
- Zero duplicate timestamps
- Zero missing temperature or humidity values

Repeated CSV headers found:
- `SENSOR01.CSV`: 1 repeated header row (CSV line 119255)
- `SENSOR03.CSV`: 3 repeated header rows (CSV lines 4, 7, and 10)

After removing these rows, the clean raw record counts are:

| Sensor | Clean raw rows |
|---|---:|
| SENSOR01 | 156,019 |
| SENSOR02 | 156,980 |
| SENSOR03 | 84,450 |
| SENSOR04 | 151,248 |
| SENSOR05 | 31,146 |
| SENSOR06 | 156,887 |
| SENSOR07 | 156,885 |
| SENSOR08 | 156,863 |
| SENSOR09 | 32,717 |

## Missing intervals in the preprocessed timeline

The aligned files contain 156,835 rows each, covering 2024-09-02 09:35:25 through 2024-09-11 11:24:55.

| Sensor | Missing rows | Interval | Finding |
|---|---:|---|---|
| SENSOR01 | 966 | 2024-09-09 07:04:15–08:24:40 | Interior gap; no raw readings in the interval |
| SENSOR03 | 72,391 | 2024-09-02 09:35:25–2024-09-06 14:07:55 | Leading gap in the aligned file; raw file has six readings on Sep 2 before a long source-data gap |
| SENSOR04 | 5,667 | 2024-09-11 03:32:45–11:24:55 | Trailing gap; raw file ends at 03:32:40 |
| SENSOR05 | 125,734 | 2024-09-02 09:35:25–2024-09-09 16:13:10 | Leading gap; raw file begins at 16:13:15 on Sep 9 |
| SENSOR09 | 124,135 | 2024-09-02 09:35:25–2024-09-09 13:59:55 | Leading gap; raw file begins at 14:00:00 on Sep 9 |

Sensors 02, 06, 07, and 08 have no missing readings in the aligned timeline.

## Raw-to-preprocessed reconciliation

For every sensor, within its preprocessed timeline:
- Raw timestamps absent from the preprocessed file: 0
- Preprocessed blank rows with a matching raw timestamp: 0
- Valid preprocessed rows without a matching raw timestamp: 0

This exact-timestamp check indicates that the preprocessing retained the raw readings within the aligned timeline and did not blank out timestamps that had raw measurements.

## Conclusions and handling

The observed missing values correspond to periods without source readings or to periods outside a sensor's recorded span. Sensor 01 has an interior source-data gap. Sensor 03 has six early raw readings before the shared aligned timeline, followed by a long source-data gap.

Do not impute these readings unless an approved project rule requires it. Preserve the missing values and distinguish source-data gaps from timeline padding in downstream analysis and dashboards.