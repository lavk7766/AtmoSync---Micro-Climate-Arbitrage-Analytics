
import json
import time

from simulator.config import SIMULATION_INTERVAL_SECONDS, MAX_EVENTS
from simulator.event_builder import build_sensor_event, event_to_dict
from kafka_client.producer import TelemetryProducer
from simulator.container_generator import create_containers
from simulator.data_validator import validate_event


def main():
    containers = create_containers()
    producer = TelemetryProducer()

    events_generated = 0
    events_published = 0

    print("AtmoSync IoT Simulator Started")
    print(f"Simulated containers: {len(containers)}")

    if MAX_EVENTS is None:
        print("Event limit: Unlimited")
    else:
        print(f"Event limit: {MAX_EVENTS}")

    print("Sending telemetry to Kafka...")
    print("Press CTRL+C to stop.\n")

    try:
        while MAX_EVENTS is None or events_generated < MAX_EVENTS:

            for container_id in containers:

                # Stop when the total event limit is reached.
                if MAX_EVENTS is not None and events_generated >= MAX_EVENTS:
                    break

                event = build_sensor_event(container_id)
                event_data = event_to_dict(event)
                events_generated += 1

                is_valid, message = validate_event(event_data)

                if is_valid:
                    metadata = producer.send_event(event_data)
                    events_published += 1

                    print(json.dumps(event_data, indent=4))
                    print(f"Validation: {message}")
                    print(f"Kafka Topic: {metadata.topic}")
                    print(f"Partition: {metadata.partition}")
                    print(f"Offset: {metadata.offset}\n")

                else:
                    print(f"Invalid event: {message}")

            # Stop without an unnecessary final sleep.
            if MAX_EVENTS is not None and events_generated >= MAX_EVENTS:
                print("\nConfigured event limit reached.")
                break

            time.sleep(SIMULATION_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nAtmoSync Simulator Stopped.")

    finally:
        producer.close()
        print("Kafka producer connection closed.")
        print(f"Total events generated: {events_generated}")
        print(f"Total events published: {events_published}")


if __name__ == "__main__":
    main()
