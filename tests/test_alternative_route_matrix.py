import math

from scripts.build_alternative_route_matrix import (
    build_alternative_route_matrix,
    DISTANCE_METHOD,
)


def test_matrix_contains_all_35_comparisons():
    records = build_alternative_route_matrix()
    assert len(records) == 35


def test_matrix_has_17_positive_price_candidates():
    records = build_alternative_route_matrix()

    positive = [
        row for row in records
        if row["price_candidate_status"] == "POSITIVE_PRICE_CANDIDATE"
    ]

    assert len(positive) == 17


def test_container_candidate_pairs_are_unique():
    records = build_alternative_route_matrix()

    pairs = [
        (row["container_id"], row["candidate_market"].casefold())
        for row in records
    ]

    assert len(pairs) == len(set(pairs))


def test_straight_line_distances_are_positive_and_finite():
    records = build_alternative_route_matrix()

    for row in records:
        distance = float(row["straight_line_distance_km"])
        assert math.isfinite(distance)
        assert distance > 0


def test_distance_method_explicitly_disclaims_network_routing():
    records = build_alternative_route_matrix()

    for row in records:
        assert row["distance_method"] == DISTANCE_METHOD
        assert "not network routing" in row["distance_method"]


def test_operational_route_and_cost_fields_remain_blank():
    records = build_alternative_route_matrix()

    fields = [
        "transport_mode",
        "network_route_distance_km",
        "estimated_travel_hours",
        "transport_cost_inr",
        "transport_cost_currency",
        "route_source_type",
    ]

    for row in records:
        for field in fields:
            assert row[field] == ""


def test_origin_and_planned_destination_are_not_candidates():
    records = build_alternative_route_matrix()

    for row in records:
        assert row["candidate_market"].casefold() != row["origin"].casefold()
        assert (
            row["candidate_market"].casefold()
            != row["planned_destination"].casefold()
        )


def test_coordinate_provenance_is_retained():
    records = build_alternative_route_matrix()

    for row in records:
        assert row["origin_coordinate_source_type"]
        assert row["candidate_coordinate_source_type"]


def test_positive_candidates_require_route_verification():
    records = build_alternative_route_matrix()

    positive = [
        row for row in records
        if row["price_candidate_status"] == "POSITIVE_PRICE_CANDIDATE"
    ]

    assert all(
        row["route_status"] == "ROUTE_AND_COST_VERIFICATION_PENDING"
        for row in positive
    )
