
import pytest

import simulator.container_generator as container_generator


def test_create_containers_generates_sequential_ids(monkeypatch):
    monkeypatch.setattr(container_generator, "NUM_CONTAINERS", 3)

    containers = container_generator.create_containers()

    assert containers == [
        "CONT001",
        "CONT002",
        "CONT003",
    ]


def test_create_containers_handles_zero_containers(monkeypatch):
    monkeypatch.setattr(container_generator, "NUM_CONTAINERS", 0)

    assert container_generator.create_containers() == []


@pytest.mark.parametrize(
    "containers, expected_count",
    [
        ([], 0),
        (["CONT001"], 1),
        (["CONT001", "CONT002", "CONT003"], 3),
    ],
)
def test_get_container_count(containers, expected_count):
    assert container_generator.get_container_count(
        containers
    ) == expected_count
