USE ROLE ACCOUNTADMIN;
USE WAREHOUSE ATMOSYNC_WH;
USE SCHEMA ATMOSYNC.RAW;

-- Real sensor readings (9 sensors, one reading every 5 seconds), loaded as received
-- from data/raw/sensor_data/Raw.zip. Repeated header lines inside the files are skipped.
-- The source files give no time zone, so READING_TS has none either.
CREATE TABLE IF NOT EXISTS RAW_SENSOR_READINGS (
  SENSOR_ID     STRING,
  READING_TS    TIMESTAMP_NTZ,
  TEMPERATURE_C FLOAT,
  HUMIDITY_PCT  FLOAT,
  SOURCE_FILE   STRING,
  LOADED_AT     TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- The loader reloads this table in full, so it needs DELETE as well
GRANT SELECT, INSERT, DELETE ON TABLE ATMOSYNC.RAW.RAW_SENSOR_READINGS TO ROLE ATMOSYNC_LOADER;

SHOW TABLES LIKE 'RAW_SENSOR_READINGS' IN SCHEMA ATMOSYNC.RAW;