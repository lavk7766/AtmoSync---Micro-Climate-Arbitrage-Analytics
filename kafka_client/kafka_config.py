# AtmoSync - Kafka Configuration

# Kafka connection settings
BOOTSTRAP_SERVERS = "localhost:9092"

# Kafka topic
TELEMETRY_TOPIC = "container_sensor_telemetry"

# Producer settings
PRODUCER_ACKS = "all"
PRODUCER_RETRIES = 5

# Consumer settings
CONSUMER_GROUP_ID = "atmosync_test_consumer"
AUTO_OFFSET_RESET = "earliest"
ENABLE_AUTO_COMMIT = False
# Consumer broker recovery settings
CONSUMER_RECONNECT_BACKOFF_MS = 500
CONSUMER_RECONNECT_BACKOFF_MAX_MS = 10000