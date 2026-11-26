from scripts.fetch_osrm_road_candidate_routes import (
    build_osrm_request_url,
    extract_route_metrics,
    load_road_candidate_inputs,
)


def test_only_eleven_positive_road_candidates_are_selected():
    candidates = load_road_candidate_inputs()
    assert len(candidates) == 11


def test_selected_candidates_belong_only_to_road_shipments():
    candidates = load_road_candidate_inputs()
    assert {row["container_id"] for row in candidates} == {
        "CONT001", "CONT003"
    }


def test_candidate_pairs_are_unique():
    candidates = load_road_candidate_inputs()
    pairs = [
        (row["container_id"], row["candidate_market"].casefold())
        for row in candidates
    ]
    assert len(pairs) == len(set(pairs))


def test_candidate_coordinates_are_present():
    candidates = load_road_candidate_inputs()

    for row in candidates:
        for field in (
            "origin_latitude",
            "origin_longitude",
            "destination_latitude",
            "destination_longitude",
        ):
            assert isinstance(row[field], float)


def test_osrm_url_uses_longitude_latitude_order():
    candidate = {
        "origin_longitude": 77.20877,
        "origin_latitude": 28.61393,
        "destination_longitude": 77.59456,
        "destination_latitude": 12.97160,
    }

    url = build_osrm_request_url(candidate)

    assert "/77.20877,28.61393;77.59456,12.9716?" in url
    assert "alternatives=false" in url


def test_successful_osrm_response_is_converted_to_km_and_hours():
    response = {
        "code": "Ok",
        "routes": [
            {
                "distance": 2027080.0,
                "duration": 87192.0,
            }
        ],
        "waypoints": [
            {
                "distance": 0.33,
                "location": [77.20877, 28.613927],
            },
            {
                "distance": 31.04,
                "location": [77.59467, 12.971859],
            },
        ],
    }

    result = extract_route_metrics(response)

    assert result["network_distance_km"] == 2027.08
    assert result["estimated_duration_hours"] == 24.22
    assert result["origin_snap_distance_m"] == 0.33
    assert result["destination_snap_distance_m"] == 31.04


def test_no_route_response_does_not_produce_fake_metrics():
    assert extract_route_metrics({"code": "NoRoute"}) is None


def test_failed_response_does_not_produce_metrics():
    assert extract_route_metrics({"code": "InvalidQuery"}) is None


def test_osrm_request_is_not_configured_to_download_route_geometry():
    candidate = {
        "origin_longitude": 77.20877,
        "origin_latitude": 28.61393,
        "destination_longitude": 77.59456,
        "destination_latitude": 12.97160,
    }

    url = build_osrm_request_url(candidate)

    assert "overview=false" in url
