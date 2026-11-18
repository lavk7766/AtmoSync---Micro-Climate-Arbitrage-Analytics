
# AtmoSync - IoT Simulator Configuration

# Simulator settings
NUM_CONTAINERS = 5
SIMULATION_INTERVAL_SECONDS = 5
# Simulation time acceleration.
# 1.0 = normal time
# 60.0 = 1 real second represents 1 simulated minute
# 3600.0 = 1 real second represents 1 simulated hour
SIMULATION_TIME_MULTIPLIER = 1.0
# Maximum total events generated per run.
# None means continuous simulation until CTRL+C.
MAX_EVENTS = None
# Illustrative transport speeds (km/h)
TRANSPORT_SPEED_KMH = {
    "road": 60.0,
    "rail": 80.0,
    "sea": 30.0,
}

# Sensor reading ranges (development assumptions)
TEMPERATURE_RANGE = (2.0, 10.0)
HUMIDITY_RANGE = (40.0, 90.0)
VIBRATION_RANGE = (0.0, 1.0)

# Event settings
SOURCE_TYPE = "synthetic_simulated"
# Scheduled temperature fault injection.
TEMPERATURE_FAULT_ENABLED = True
TEMPERATURE_FAULT_CONTAINER_ID = "CONT001"

# Values are measured in simulated seconds.
TEMPERATURE_FAULT_START_DELAY_SECONDS = 5.0
TEMPERATURE_FAULT_DURATION_SECONDS = 30.0

# Inject a high-temperature excursion above the product's
# recommended maximum, rather than hard-coding a product limit.
TEMPERATURE_FAULT_OFFSET_C = 5.0