
from simulator.config import NUM_CONTAINERS


def create_containers():
    """
    Create unique IDs for simulated containers.
    """
    containers = []

    for number in range(1, NUM_CONTAINERS + 1):
        container_id = f"CONT{number:03d}"
        containers.append(container_id)

    return containers


def get_container_count(containers):
    return len(containers)
