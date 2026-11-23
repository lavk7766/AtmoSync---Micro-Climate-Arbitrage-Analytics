import json
import math
import time
from datetime import timedelta

from simulator.config import (
    SIMULATION_INTERVAL_SECONDS,
    MAX_EVENTS,
    TEMPERATURE_FAULT_ENABLED,
    TEMPERATURE_FAULT_CONTAINER_ID,
    TEMPERATURE_FAULT_START_DELAY_SECONDS,
    TEMPERATURE_FAULT_DURATION_SECONDS,
    TEMPERATURE_FAULT_OFFSET_C,
    HUMIDITY_FAULT_ENABLED,
    HUMIDITY_FAULT_CONTAINER_ID,
    HUMIDITY_FAULT_START_DELAY_SECONDS,
    HUMIDITY_FAULT_DURATION_SECONDS,
    HUMIDITY_FAULT_VALUE_PCT,
)

from simulator.event_builder import build_sensor_event, event_to_dict
from simulator.simulation_clock import simulation_clock
from simulator.temperature_fault_injector import (
    TemperatureFaultInjector,
    TemperatureFaultWindow,
)
from simulator.humidity_fault_injector import (
    HumidityFaultInjector,
    HumidityFaultWindow,
)
from simulator.product_reference import ProductReference
from kafka_client.producer import TelemetryProducer
from simulator.container_generator import create_containers
from simulator.data_validator import validate_event
from simulator.simulation_metadata import (
    load_product_references_for_containers,
)


def create_temperature_fault_injector(
    containers,
    product_references,
    run_started_at,
):
    """
    Create a startup-relative fault schedule for one configured container.

    Fault injection requires a real ProductReference. If that reference
    is unavailable, return None rather than inventing product limits.
    """
    if not TEMPERATURE_FAULT_ENABLED:
        return None, None, "disabled in configuration"

    configured_id = TEMPERATURE_FAULT_CONTAINER_ID.strip().upper()

    target_container = next(
        (
            container_id
            for container_id in containers
            if str(container_id).strip().upper() == configured_id
        ),
        None,
    )

    if target_container is None:
        return (
            None,
            None,
            f"target container {configured_id} is not in this run",
        )

    product_reference = product_references.get(target_container)

    if product_reference is None:
        return (
            None,
            None,
            f"no product reference loaded for {target_container}",
        )

    if not isinstance(product_reference, ProductReference):
        raise TypeError(
            f"Invalid product reference for {target_container}"
        )

    settings = {
        "start delay": TEMPERATURE_FAULT_START_DELAY_SECONDS,
        "duration": TEMPERATURE_FAULT_DURATION_SECONDS,
        "temperature offset": TEMPERATURE_FAULT_OFFSET_C,
    }

    for setting_name, value in settings.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError(
                f"Temperature fault {setting_name} must be finite"
            )

    if TEMPERATURE_FAULT_START_DELAY_SECONDS < 0:
        raise ValueError("Temperature fault start delay cannot be negative")

    if TEMPERATURE_FAULT_DURATION_SECONDS <= 0:
        raise ValueError("Temperature fault duration must be positive")

    if TEMPERATURE_FAULT_OFFSET_C <= 0:
        raise ValueError("Temperature fault offset must be positive")

    recommended_max = product_reference.recommended_temp_max_c

    # A deliberate high-temperature excursion relative to the
    # actual reference assigned to this container.
    fault_temperature = float(
        recommended_max + TEMPERATURE_FAULT_OFFSET_C
    )

    fault_start = run_started_at + timedelta(
        seconds=TEMPERATURE_FAULT_START_DELAY_SECONDS
    )

    fault_end = fault_start + timedelta(
        seconds=TEMPERATURE_FAULT_DURATION_SECONDS
    )

    window = TemperatureFaultWindow(
        start_at=fault_start,
        end_at=fault_end,
        temperature_c=fault_temperature,
        label="simulated_high_temperature_excursion",
    )

    injector = TemperatureFaultInjector({
        target_container: [window]
    })

    details = {
        "container_id": target_container,
        "start_at": window.start_at,
        "end_at": window.end_at,
        "temperature_c": window.temperature_c,
        "recommended_max_c": recommended_max,
    }

    return injector, details, "active"


def create_humidity_fault_injector(
    containers,
    product_references,
    run_started_at,
):
    """Create an optional startup-relative humidity fault schedule."""
    if not HUMIDITY_FAULT_ENABLED:
        return None, None, "disabled in configuration"

    configured_id = HUMIDITY_FAULT_CONTAINER_ID.strip().upper()

    target_container = next(
        (
            container_id
            for container_id in containers
            if str(container_id).strip().upper() == configured_id
        ),
        None,
    )

    if target_container is None:
        return (
            None,
            None,
            f"target container {configured_id} is not in this run",
        )

    product_reference = product_references.get(target_container)

    if product_reference is None:
        return (
            None,
            None,
            f"no product reference loaded for {target_container}",
        )

    if not isinstance(product_reference, ProductReference):
        raise TypeError(
            f"Invalid product reference for {target_container}"
        )

    settings = {
        "start delay": HUMIDITY_FAULT_START_DELAY_SECONDS,
        "duration": HUMIDITY_FAULT_DURATION_SECONDS,
        "humidity value": HUMIDITY_FAULT_VALUE_PCT,
    }

    for setting_name, value in settings.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError(
                f"Humidity fault {setting_name} must be finite"
            )

    if HUMIDITY_FAULT_START_DELAY_SECONDS < 0:
        raise ValueError("Humidity fault start delay cannot be negative")

    if HUMIDITY_FAULT_DURATION_SECONDS <= 0:
        raise ValueError("Humidity fault duration must be positive")

    humidity_value = float(HUMIDITY_FAULT_VALUE_PCT)

    if not 0 <= humidity_value <= 100:
        raise ValueError("Humidity fault value must be between 0 and 100")

    minimum = product_reference.humidity_min_pct
    maximum = product_reference.humidity_max_pct

    if minimum <= humidity_value <= maximum:
        raise ValueError(
            "Configured humidity fault value is inside the product "
            "recommended humidity range"
        )

    fault_start = run_started_at + timedelta(
        seconds=HUMIDITY_FAULT_START_DELAY_SECONDS
    )
    fault_end = fault_start + timedelta(
        seconds=HUMIDITY_FAULT_DURATION_SECONDS
    )

    window = HumidityFaultWindow(
        start_at=fault_start,
        end_at=fault_end,
        humidity_pct=humidity_value,
        label="simulated_humidity_excursion",
    )

    injector = HumidityFaultInjector({
        target_container: [window]
    })

    details = {
        "container_id": target_container,
        "start_at": window.start_at,
        "end_at": window.end_at,
        "humidity_pct": window.humidity_pct,
        "recommended_min_pct": minimum,
        "recommended_max_pct": maximum,
    }

    return injector, details, "active"


def main():

    containers = create_containers()

    # Load product references once before connecting to Kafka.
    product_references = load_product_references_for_containers(
        containers
    )

    producer = TelemetryProducer()

    events_generated = 0
    events_published = 0

    try:
        # Start the fault schedule after the Kafka producer is ready.
        run_started_at = simulation_clock.now()

        fault_injector, fault_details, fault_status = (
            create_temperature_fault_injector(
                containers,
                product_references,
                run_started_at,
            )
        )

        humidity_fault_injector, humidity_fault_details, humidity_fault_status = (
            create_humidity_fault_injector(
                containers,
                product_references,
                run_started_at,
            )
        )

        print("AtmoSync IoT Simulator Started")
        print(f"Simulated containers: {len(containers)}")

        if MAX_EVENTS is None:
            print("Event limit: Unlimited")
        else:
            print(f"Event limit: {MAX_EVENTS}")

        if fault_details is not None:
            print("\nTemperature fault injection: ACTIVE")
            print(
                f"Target container: "
                f"{fault_details['container_id']}"
            )
            print(
                f"Fault window (simulated UTC): "
                f"{fault_details['start_at'].isoformat()} "
                f"to {fault_details['end_at'].isoformat()}"
            )
            print(
                f"Injected temperature: "
                f"{fault_details['temperature_c']:.2f} C"
            )
            print(
                f"Product recommended maximum: "
                f"{fault_details['recommended_max_c']:.2f} C\n"
            )
        else:
            print(
                "\nTemperature fault injection: INACTIVE "
                f"({fault_status})\n"
            )

        if humidity_fault_details is not None:
            print("\nHumidity fault injection: ACTIVE")
            print(f"Target container: {humidity_fault_details['container_id']}")
            print(f"Fault window (simulated UTC): {humidity_fault_details['start_at'].isoformat()} to {humidity_fault_details['end_at'].isoformat()}")
            print(f"Injected humidity: {humidity_fault_details['humidity_pct']:.2f}%")
            print(f"Product recommended range: {humidity_fault_details['recommended_min_pct']:.2f}% to {humidity_fault_details['recommended_max_pct']:.2f}%\n")
        else:
            print(f"\nHumidity fault injection: INACTIVE ({humidity_fault_status})\n")

        print("Sending telemetry to Kafka...")
        print("Press CTRL+C to stop.\n")

        while MAX_EVENTS is None or events_generated < MAX_EVENTS:

            for container_id in containers:

                if (
                    MAX_EVENTS is not None
                    and events_generated >= MAX_EVENTS
                ):
                    break

                event_kwargs = {
                    'product_reference': product_references.get(container_id),
                    'fault_injector': fault_injector,
                }
                if humidity_fault_injector is not None:
                    event_kwargs['humidity_fault_injector'] = humidity_fault_injector

                event = build_sensor_event(
                    container_id,
                    **event_kwargs,
                )

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

            if (
                MAX_EVENTS is not None
                and events_generated >= MAX_EVENTS
            ):
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