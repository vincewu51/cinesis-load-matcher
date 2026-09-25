import math

import pytest

from cinesis.models import Evidence
from cinesis.ranking import haversine, rank_loads
from cinesis.workbook import city_coordinates


def test_haversine_known_geometry():
    assert haversine((0, 0), (0, 0)) == 0
    assert haversine((0, 0), (0, 90)) == pytest.approx(6218.4071, abs=0.001)
    assert haversine((29, -98), (32, -96)) == haversine((32, -96), (29, -98))


def test_conditional_top_three_and_empty_return(profile, inputs):
    result = rank_loads(profile, inputs[1], 15000)
    assert result["mode"] == "conditional"
    assert [r["load_id"] for r in result["top_three"]] == ["L03", "L08", "L02"]
    assert [f"{r['effective_rate_per_mile']:.3f}" for r in result["top_three"]] == [
        "3.098",
        "2.480",
        "2.418",
    ]
    l08 = next(r for r in result["audit"] if r["load_id"] == "L08")
    assert l08["deadhead_to_origin_miles"] == 0
    assert l08["deadhead_home_miles"] == pytest.approx(223.111, abs=0.001)
    assert profile.weight_capacity_lb.value is None


def test_unknown_capacity_is_not_eligibility(profile, inputs):
    result = rank_loads(profile, inputs[1])
    assert result["mode"] == "needs_capacity"
    assert result["top_three"] == []
    assert [
        r["load_id"] for r in result["audit"] if r["status"] == "needs_capacity"
    ] == ["L02", "L03", "L08"]


@pytest.mark.parametrize(
    "capacity,expected",
    [
        (12000, ["L02"]),
        (12600, ["L08", "L02"]),
        (13000, ["L08", "L02"]),
        (14200, ["L03", "L08", "L02"]),
    ],
)
def test_capacity_sensitivity(profile, inputs, capacity, expected):
    assert [
        r["load_id"] for r in rank_loads(profile, inputs[1], capacity)["top_three"]
    ] == expected


def test_equipment_missing_data_and_rejections(profile, inputs):
    rows = {r["load_id"]: r for r in rank_loads(profile, inputs[1], 15000)["audit"]}
    assert "incompatible equipment" in rows["L05"]["reasons"]
    assert "incompatible equipment" in rows["L04"]["reasons"]
    assert "effective rate does not meet" in " ".join(rows["L04"]["reasons"])
    assert "price" in " ".join(rows["L06"]["reasons"])
    assert "Destination" in " ".join(rows["L07"]["reasons"])


def test_strict_rate_boundary_uses_full_precision(profile, inputs):
    rows = inputs[1]
    rate = next(
        r for r in rank_loads(profile, rows, 15000)["audit"] if r["load_id"] == "L03"
    )["effective_rate_per_mile"]
    profile.minimum_rate.value.dollars_per_mile = rate
    assert not rank_loads(profile, rows, 15000)["top_three"]
    profile.minimum_rate.value.comparison = ">="
    assert rank_loads(profile, rows, 15000)["top_three"][0]["load_id"] == "L03"


def test_confirmed_capacity_cannot_be_overridden(profile, inputs):
    profile.weight_capacity_lb.value = 13000
    profile.weight_capacity_lb.evidence = [
        Evidence(row=20, quote="example for unit test")
    ]
    result = rank_loads(profile, inputs[1])
    assert result["mode"] == "verified_capacity"
    assert [r["load_id"] for r in result["top_three"]] == ["L08", "L02"]
    with pytest.raises(ValueError):
        rank_loads(profile, inputs[1], 15000)


@pytest.mark.parametrize("bad", [0, -1, math.nan, math.inf])
def test_invalid_capacity(profile, inputs, bad):
    with pytest.raises(ValueError):
        rank_loads(profile, inputs[1], bad)


@pytest.mark.parametrize(
    "field,value",
    [
        ("Price ($)", math.nan),
        ("Weight", -1),
        ("Dest Lat", 91),
        ("Dest Lon", -181),
        ("Destination", ""),
    ],
)
def test_malformed_load_excluded(profile, inputs, field, value):
    rows = inputs[1]
    rows[2][field] = value
    assert "L03" not in [
        r["load_id"] for r in rank_loads(profile, rows, 15000)["top_three"]
    ]


def test_duplicate_ids_and_ties(profile, inputs):
    rows = inputs[1]
    copy = {**rows[2], "Load ID": "L00"}
    assert [
        r["load_id"] for r in rank_loads(profile, rows + [copy], 15000)["top_three"]
    ][:2] == ["L00", "L03"]
    duplicated = rank_loads(profile, rows + [rows[2]], 15000)
    assert "L03" not in [r["load_id"] for r in duplicated["top_three"]]


def test_zero_total_distance_excluded(profile, inputs):
    profile.current_location.value = "San Antonio"
    rows = inputs[1] + [
        {
            "Load ID": "ZERO",
            "Origin": "San Antonio",
            "Origin Lat": 29.4241,
            "Origin Lon": -98.4936,
            "Destination": "San Antonio",
            "Dest Lat": 29.4241,
            "Dest Lon": -98.4936,
            "Trailer": "Hotshot",
            "Weight": 1000,
            "Price ($)": 5000,
        }
    ]
    result = rank_loads(profile, rows, 15000)
    assert result["audit"][-1]["reasons"] == ["zero total trip distance"]


def test_coordinate_lookup_rejects_conflicts(inputs):
    rows = inputs[1]
    assert city_coordinates("Dallas, TX", rows) == (32.7767, -96.797)
    rows.append({**rows[-1], "Origin Lat": 33})
    with pytest.raises(ValueError):
        city_coordinates("Dallas", rows)
