USE ROLE ACCOUNTADMIN;
USE WAREHOUSE ATMOSYNC_WH;

-- Dev-only sample data: remove old sample rows, then reload
DELETE FROM ATMOSYNC.RAW.RAW_CONTAINER_TELEMETRY WHERE KAFKA_TOPIC = 'sample';

INSERT INTO ATMOSYNC.RAW.RAW_CONTAINER_TELEMETRY (EVENT_PAYLOAD, KAFKA_TOPIC, KAFKA_PARTITION, KAFKA_OFFSET)
SELECT PARSE_JSON('{"event_id":"EVT001","container_id":"CONT001","timestamp":"2026-11-05T10:30:00Z","temperature_c":8.5,"humidity_pct":72.5,"vibration_g":0.35,"latitude":19.70,"longitude":-101.19,"source_type":"synthetic_simulated"}'), 'sample', 0, 1
UNION ALL
SELECT PARSE_JSON('{"event_id":"EVT002","container_id":"CONT001","timestamp":"2026-11-05T10:31:00Z","temperature_c":8.7,"humidity_pct":73.0,"vibration_g":0.33,"latitude":19.71,"longitude":-101.18,"source_type":"synthetic_simulated"}'), 'sample', 0, 2
UNION ALL
SELECT PARSE_JSON('{"event_id":"EVT003","container_id":"CONT002","timestamp":"2026-11-05T10:30:00Z","temperature_c":11.2,"humidity_pct":85.0,"vibration_g":0.41,"latitude":20.66,"longitude":-103.35,"source_type":"synthetic_simulated"}'), 'sample', 0, 3
UNION ALL
SELECT PARSE_JSON('{"event_id":"EVT004","container_id":"CONT002","timestamp":"2026-11-05T10:31:00Z","temperature_c":11.6,"humidity_pct":85.4,"vibration_g":0.44,"latitude":20.67,"longitude":-103.34,"source_type":"synthetic_simulated"}'), 'sample', 0, 4
UNION ALL
SELECT PARSE_JSON('{"event_id":"EVT005","container_id":"CONT003","timestamp":"2026-11-05T10:30:00Z","temperature_c":13.4,"humidity_pct":88.9,"vibration_g":0.25,"latitude":-2.17,"longitude":-79.92,"source_type":"synthetic_simulated"}'), 'sample', 0, 5;

-- Dev-only sample prices
DELETE FROM ATMOSYNC.RAW.RAW_COMMODITY_PRICES;

INSERT INTO ATMOSYNC.RAW.RAW_COMMODITY_PRICES VALUES
  ('avocado', 'Mexico City', 19.43, -99.13, 2.10, '2026-11-05'),
  ('avocado', 'Houston',     29.76, -95.37, 3.40, '2026-11-05'),
  ('avocado', 'Rotterdam',   51.92,   4.48, 4.80, '2026-11-05'),
  ('banana',  'Lima',       -12.05, -77.04, 0.90, '2026-11-05');