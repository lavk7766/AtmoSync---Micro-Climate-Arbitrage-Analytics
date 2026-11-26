from scripts.fetch_osrm_planned_baselines import (
    load_planned_baseline_inputs,
)


def test_two_planned_road_baselines_are_selected():
    rows = load_planned_baseline_inputs()
    assert len(rows) == 2


def test_only_road_containers_are_selected():
    rows = load_planned_baseline_inputs()
    assert {row["container_id"] for row in rows} == {
        "CONT001", "CONT003"
    }


def test_planned_origin_and_destination_are_present():
    rows = load_planned_baseline_inputs()

    for row in rows:
        assert row["origin"]
        assert row["planned_destination"]
        assert row["origin_latitude"]
        assert row["destination_latitude"]


def test_existing_route_quality_is_preserved():
    rows = load_planned_baseline_inputs()
    lookup = {row["container_id"]: row for row in rows}

    assert lookup["CONT001"]["original_route_quality"] == (
        "network_route_geometry"
    )
    assert lookup["CONT003"]["original_route_quality"] == (
        "illustrative_waypoints"
    )


def test_planned_routes_are_unique():
    rows = load_planned_baseline_inputs()
    ids = [row["container_id"] for row in rows]
    assert len(ids) == len(set(ids))
