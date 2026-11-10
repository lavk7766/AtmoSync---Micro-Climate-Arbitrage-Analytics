
# AtmoSync - IoT Simulator Configuration

# Simulator settings
NUM_CONTAINERS = 5
SIMULATION_INTERVAL_SECONDS = 5
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
