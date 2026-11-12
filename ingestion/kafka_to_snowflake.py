"""
Kafka -> Snowflake loader for AtmoSync.

Reads sensor events from a Kafka topic, validates them against the rules in
docs/architecture/event_schema.md, and inserts them into
ATMOSYNC.RAW.RAW_CONTAINER_TELEMETRY (raw JSON stored as VARIANT).

Usage:
    python ingestion/kafka_to_snowflake.py --check      # test Snowflake login only
    python ingestion/kafka_to_snowflake.py --dry-run    # read Kafka, validate, do not insert
    python ingestion/kafka_to_snowflake.py              # full run
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import snowflake.connector
from dotenv import load_dotenv
from kafka import KafkaConsumer

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")

REJECTED_FILE = REPO_ROOT / "logs" / "rejected_events.jsonl"
BATCH_SIZE = 500
POLL_TIMEOUT_MS = 5000
MAX_RETRIES = 3

REQUIRED_TEXT_FIELDS = ["event_id", "container_id", "timestamp", "source_type"]
REQUIRED_NUMERIC_FIELDS = ["temperature_c", "humidity_pct", "vibration_g"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("loader")


def validate(event):
    """Return None if the event is valid, otherwise a short error string."""
    if not isinstance(event, dict):
        return "event is not a JSON object"

    for field in REQUIRED_TEXT_FIELDS:
        value = event.get(field)
        if not isinstance(value, str) or not value.strip():
            return f"missing or empty field: {field}"

    try:
        datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
    except ValueError:
        return "timestamp is not a valid ISO 8601 value"

    for field in REQUIRED_NUMERIC_FIELDS:
        value = event.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return f"field is not numeric: {field}"

    if not 0 <= event["humidity_pct"] <= 100:
        return "humidity_pct outside 0-100"

    return None


def reject(raw_value, reason):
    """Keep invalid events in logs/rejected_events.jsonl (git-ignored)."""
    REJECTED_FILE.parent.mkdir(exist_ok=True)
    record = {"reason": reason, "raw": raw_value}
    with open(REJECTED_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def connect_snowflake():
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role=os.environ["SNOWFLAKE_ROLE"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        schema=os.environ["SNOWFLAKE_SCHEMA"],
    )


def check_connection():
    conn = connect_snowflake()
    try:
        cur = conn.cursor()
        cur.execute("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE()")
        log.info("Connected as (user, role, warehouse): %s", cur.fetchone())
        cur.execute("SELECT COUNT(*) FROM RAW_CONTAINER_TELEMETRY")
        log.info("Rows currently in RAW_CONTAINER_TELEMETRY: %s", cur.fetchone()[0])
    finally:
        conn.close()


def insert_batch(conn, rows):
    """rows: list of (json_string, topic, partition, offset)."""
    placeholders = ",".join(["(%s,%s,%s,%s)"] * len(rows))
    sql = (
        "INSERT INTO RAW_CONTAINER_TELEMETRY "
        "(EVENT_PAYLOAD, KAFKA_TOPIC, KAFKA_PARTITION, KAFKA_OFFSET) "
        "SELECT PARSE_JSON(column1), column2, column3, column4 "
        f"FROM VALUES {placeholders}"
    )
    params = [item for row in rows for item in row]
    conn.cursor().execute(sql, params)


def insert_with_retry(conn, rows):
    """Insert a batch; reconnect and retry on failure. Returns the live connection."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            insert_batch(conn, rows)
            return conn
        except Exception as exc:  # noqa: BLE001
            log.error("Insert failed (attempt %d/%d): %s", attempt, MAX_RETRIES, exc)
            if attempt == MAX_RETRIES:
                raise
            time.sleep(2 * attempt)
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass
            conn = connect_snowflake()
    return conn


def run(dry_run):
    topic = os.environ["KAFKA_TOPIC"]
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=os.environ["KAFKA_BOOTSTRAP_SERVERS"],
        group_id="atmosync-snowflake-loader",
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )
    conn = None if dry_run else connect_snowflake()
    loaded = rejected = 0
    log.info("Listening on topic '%s' (dry_run=%s). Ctrl+C to stop.", topic, dry_run)

    try:
        while True:
            polled = consumer.poll(timeout_ms=POLL_TIMEOUT_MS, max_records=BATCH_SIZE)
            rows = []

            for tp, messages in polled.items():
                for msg in messages:
                    raw = msg.value.decode("utf-8", errors="replace")
                    try:
                        event = json.loads(raw)
                    except json.JSONDecodeError:
                        reject(raw, "invalid JSON")
                        rejected += 1
                        continue

                    error = validate(event)
                    if error:
                        reject(raw, error)
                        rejected += 1
                        continue

                    rows.append((json.dumps(event), msg.topic, msg.partition, msg.offset))

            if rows:
                if dry_run:
                    log.info("DRY RUN: %d valid events, first: %s", len(rows), rows[0][0])
                else:
                    conn = insert_with_retry(conn, rows)
                loaded += len(rows)
                log.info("Batch done: %d valid | total loaded %d | total rejected %d",
                         len(rows), loaded, rejected)

            if polled and not dry_run:
                consumer.commit()  # only after a successful insert
    except KeyboardInterrupt:
        log.info("Stopping. Loaded %d, rejected %d.", loaded, rejected)
    finally:
        consumer.close()
        if conn is not None:
            conn.close()


def main():
    parser = argparse.ArgumentParser(description="AtmoSync Kafka -> Snowflake loader")
    parser.add_argument("--check", action="store_true", help="test the Snowflake login and exit")
    parser.add_argument("--dry-run", action="store_true", help="read and validate, do not insert")
    args = parser.parse_args()

    if args.check:
        check_connection()
        return 0

    run(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())