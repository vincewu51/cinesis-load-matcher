import math
from collections import Counter

from .models import DriverProfile
from .workbook import city_coordinates

EARTH_RADIUS_MILES = 3958.7613


def haversine(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(min(1.0, max(0.0, h))))


def number(value, label: str, *, positive: bool = False) -> float:
    try:
        if isinstance(value, bool):
            raise TypeError
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"missing or invalid {label}") from None
    if not math.isfinite(result) or (positive and result <= 0):
        raise ValueError(f"invalid {label}")
    return result


def rank_loads(
    profile: DriverProfile, loads: list[dict], assumed_capacity_lb: float | None = None
) -> dict:
    for field in ["current_location", "home_base", "equipment", "minimum_rate"]:
        if not getattr(profile, field).value:
            raise ValueError(f"Clarification required: {field}")
    actual_capacity = profile.weight_capacity_lb.value
    if assumed_capacity_lb is not None:
        assumed_capacity_lb = number(
            assumed_capacity_lb, "assumed capacity", positive=True
        )
        if actual_capacity is not None:
            raise ValueError(
                "Cannot override a stated driver capacity with an assumption"
            )
    capacity = actual_capacity if actual_capacity is not None else assumed_capacity_lb
    mode = (
        "verified_capacity"
        if actual_capacity is not None
        else "conditional"
        if capacity is not None
        else "needs_capacity"
    )
    current = city_coordinates(profile.current_location.value, loads)
    home = city_coordinates(profile.home_base.value, loads)
    equipment = {e.casefold() for e in profile.equipment.value}
    duplicates = {
        key
        for key, count in Counter(str(row.get("Load ID")) for row in loads).items()
        if count > 1
    }
    audit = []
    for row in loads:
        result = {
            "load_id": str(row.get("Load ID", "")),
            "origin": row.get("Origin"),
            "destination": row.get("Destination"),
            "equipment": row.get("Trailer"),
            "weight_lb": row.get("Weight"),
            "price_usd": row.get("Price ($)"),
            "status": "rejected",
            "reasons": [],
        }
        reasons = result["reasons"]
        for name in ["Load ID", "Origin", "Destination", "Trailer"]:
            if row.get(name) is None or str(row[name]).strip().casefold() in {
                "",
                "missing",
                "n/a",
                "null",
            }:
                reasons.append(f"missing {name}")
        if result["load_id"] in duplicates:
            reasons.append("duplicate Load ID")
        try:
            price = number(row.get("Price ($)"), "price", positive=True)
            weight = number(row.get("Weight"), "weight", positive=True)
            origin = (
                number(row.get("Origin Lat"), "origin latitude"),
                number(row.get("Origin Lon"), "origin longitude"),
            )
            dest = (
                number(row.get("Dest Lat"), "destination latitude"),
                number(row.get("Dest Lon"), "destination longitude"),
            )
            for lat, lon in [origin, dest]:
                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    raise ValueError("coordinates out of range")
        except ValueError as exc:
            reasons.append(str(exc))
            audit.append(result)
            continue
        if reasons:
            audit.append(result)
            continue
        result.update(price_usd=price, weight_lb=weight)
        if str(row["Trailer"]).strip().casefold() not in equipment:
            reasons.append("incompatible equipment")
        if capacity is not None and weight > capacity:
            reasons.append(f"weight exceeds {capacity:g} lb capacity")
        legs = (
            haversine(current, origin),
            haversine(origin, dest),
            haversine(dest, home),
        )
        total = sum(legs)
        result.update(
            deadhead_to_origin_miles=legs[0],
            loaded_miles=legs[1],
            deadhead_home_miles=legs[2],
            total_miles=total,
        )
        if total <= 0:
            reasons.append("zero total trip distance")
        else:
            rpm = price / total
            result["effective_rate_per_mile"] = rpm
            minimum = profile.minimum_rate.value
            meets_rate = (
                rpm > minimum.dollars_per_mile
                if minimum.comparison == ">"
                else rpm >= minimum.dollars_per_mile
            )
            if not meets_rate:
                reasons.append("effective rate does not meet driver's minimum")
        if not reasons:
            if capacity is None:
                result["status"] = "needs_capacity"
                reasons.append("driver weight capacity not stated")
            else:
                result["status"] = (
                    "conditional" if mode == "conditional" else "eligible"
                )
        audit.append(result)
    candidates = [r for r in audit if r["status"] in {"eligible", "conditional"}]
    candidates.sort(key=lambda r: (-r["effective_rate_per_mile"], r["load_id"]))
    return {
        "mode": mode,
        "capacity_lb": capacity,
        "capacity_source": "transcript"
        if actual_capacity is not None
        else "explicit_assumption"
        if capacity is not None
        else "unknown",
        "current_coordinates": current,
        "home_coordinates": home,
        "earth_radius_miles": EARTH_RADIUS_MILES,
        "top_three": candidates[:3],
        "audit": audit,
        "unverified_requirements": [
            "Factoring approval requires broker information absent from the board."
        ],
        "notes": [
            "Geographic preferences are soft, not hard filters.",
            "Generic Flatbed is not assumed compatible with Hotshot/Gooseneck.",
            "No road routing or driving-time estimates are used.",
        ],
    }
