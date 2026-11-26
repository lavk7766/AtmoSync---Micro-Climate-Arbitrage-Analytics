from simulator.routes import CONTAINER_ROUTES
from scripts.build_market_location_reference import (
    MARKET_ENDPOINTS,
    build_market_location_records,
)


def test_all_nine_markets_have_location_records():
    records = build_market_location_records()
    assert len(records) == 9
    assert {row["market_name"] for row in records} == set(MARKET_ENDPOINTS)


def test_market_names_are_unique():
    records = build_market_location_records()
    names = [row["market_name"] for row in records]
    assert len(names) == len(set(names))


def test_all_coordinates_are_valid_wgs84():
    records = build_market_location_records()

    for row in records:
        latitude = float(row["latitude"])
        longitude = float(row["longitude"])

        assert -90 <= latitude <= 90
        assert -180 <= longitude <= 180


def test_only_cont001_endpoints_use_osm_source_label():
    records = build_market_location_records()

    osm_markets = {
        row["market_name"]
        for row in records
        if row["coordinate_source_type"] == "osm_osrm_route_endpoint"
    }

    assert osm_markets == {"Delhi", "Lucknow"}


def test_mumbai_uses_generic_city_waypoint_not_sea_port_waypoint():
    records = build_market_location_records()
    mumbai = next(row for row in records if row["market_name"] == "Mumbai")

    expected = CONTAINER_ROUTES["CONT002"][0]
    sea_port = CONTAINER_ROUTES["CONT005"][0]

    assert float(mumbai["latitude"]) == expected[0]
    assert float(mumbai["longitude"]) == expected[1]
    assert expected != sea_port
    assert "port-area" in mumbai["source_note"]


def test_mangaluru_is_labelled_as_port_area_endpoint():
    records = build_market_location_records()
    mangaluru = next(
        row for row in records
        if row["market_name"] == "Mangaluru"
    )

    assert mangaluru["source_route_container"] == "CONT005"
    assert "port-area endpoint" in mangaluru["source_note"]


def test_all_coordinate_records_disclose_their_limitations():
    records = build_market_location_records()

    for row in records:
        assert row["coordinate_system"] == "WGS84"
        assert row["coordinate_order"] == "latitude,longitude"
        assert "Not a verified" in row["source_note"]
