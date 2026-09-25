import csv
import json
from pathlib import Path

from .models import DriverProfile
from .workbook import fill_workbook


def submission_note(
    result: dict, repo_url: str | None, extraction_kind: str, profile: DriverProfile
) -> str:
    source = (
        "OpenAI structured-output extraction with transcript-quote validation"
        if extraction_kind == "openai"
        else "A manually authored test fixture (not a live LLM extraction)"
    )
    capacity = (
        f"Capacity is not stated; {result['capacity_lb']:g} lb is an explicit scenario assumption, not an extracted fact. All listed loads are conditional on that capacity."
        if result["mode"] == "conditional"
        else "Capacity is not stated, so no load can be confirmed weight-eligible and no definitive top three is supplied."
        if result["mode"] == "needs_capacity"
        else "Weight eligibility uses the stated capacity."
    )
    return (
        f"Code: {repo_url or 'Local repository; public GitHub URL pending.'}\n"
        f"{source} identifies current location, home, equipment, and a {profile.minimum_rate.value.comparison}${profile.minimum_rate.value.dollars_per_mile:g}/mile floor. "
        "Coordinates come from the load board. " + capacity + " "
        "Hotshot and Gooseneck labels are compatible; generic Flatbed is not assumed compatible. "
        "Geographic preferences remain soft; broker factoring approval cannot be checked from this board. "
        "Incomplete L06 (price) and L07 (destination) are excluded. "
        "L04 pays $1,500 but requires Van equipment and also fails the effective-rate floor. "
        f"Haversine miles include {profile.current_location.value}-to-pickup, delivery, and the empty return to {profile.home_base.value}; unrounded rates determine order. "
        "The highest-paying L08 is not inherently incompatible: its 12,600 lb weight requires capacity clarification. "
        "The workbook's trap assertion cannot be resolved from the supplied transcript."
    )


def write_outputs(
    source: Path,
    output: Path,
    profile: DriverProfile,
    document: dict,
    result: dict,
    repo_url: str | None,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    note = submission_note(result, repo_url, document["extraction"]["kind"], profile)
    if len(note.split()) > 200:
        raise ValueError("Submission note exceeds 200 words")
    result["extraction"] = document["extraction"]
    result["transcript_sha256"] = document["transcript_sha256"]
    (output / "results.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    )
    (output / "profile.json").write_text(
        json.dumps(document, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    )
    (output / "submission-note.md").write_text(note + "\n")
    columns = [
        "load_id",
        "origin",
        "destination",
        "equipment",
        "weight_lb",
        "price_usd",
        "status",
        "deadhead_to_origin_miles",
        "loaded_miles",
        "deadhead_home_miles",
        "total_miles",
        "effective_rate_per_mile",
        "reasons",
    ]
    with (output / "load-audit.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in result["audit"]:
            record = {**row, "reasons": "; ".join(row["reasons"])}
            # Prevent spreadsheet formula execution when exported text is opened as CSV.
            for key, value in record.items():
                if isinstance(value, str) and value.startswith(
                    ("=", "+", "-", "@", "\t", "\r")
                ):
                    record[key] = "'" + value
            writer.writerow(record)
    summary = ["# Load matching results", "", f"Mode: **{result['mode']}**", ""]
    if result["mode"] == "conditional":
        summary += [
            f"Assumed capacity: **{result['capacity_lb']:g} lb**. These are conditional offers, not confirmed eligibility.",
            "",
        ]
    elif result["mode"] == "needs_capacity":
        summary += [
            "Driver capacity is unknown. Confirm capacity before offering a load; no definitive top three is available.",
            "",
        ]
    if document["extraction"]["kind"] != "openai":
        summary += ["**TEST FIXTURE: not a live OpenAI extraction.**", ""]
    summary += ["| Rank | Load | Route | Effective $/mile |", "|---|---|---|---:|"]
    for i, row in enumerate(result["top_three"], 1):
        summary.append(
            f"| {i} | {row['load_id']} | {row['origin']} → {row['destination']} | {row['effective_rate_per_mile']:.3f} |"
        )
    summary += ["", "## Audit", ""]
    for row in result["audit"]:
        summary.append(
            f"- {row['load_id']}: {row['status']}; {'; '.join(row['reasons']) or 'passes checks under the stated scenario'}"
        )
    summary += ["", "## Submission note", "", note]
    (output / "results.md").write_text("\n".join(summary) + "\n")
    a = {
        "B5": profile.current_location.value,
        "B6": result["current_coordinates"][0],
        "B7": result["current_coordinates"][1],
        "B8": profile.home_base.value,
        "B9": result["home_coordinates"][0],
        "B10": result["home_coordinates"][1],
        "B11": f"{profile.minimum_rate.value.comparison} ${profile.minimum_rate.value.dollars_per_mile:.2f}",
        "B12": " / ".join(profile.equipment.value),
        "B13": profile.weight_capacity_lb.value or "Unknown — not stated",
        "A16": "Capacity assumption (not extracted)",
        "B16": result["capacity_lb"] if result["mode"] == "conditional" else "None",
    }
    status = (
        f"CONDITIONAL ranking — assumes {result['capacity_lb']:g} lb capacity; actual capacity is unknown."
        if result["mode"] == "conditional"
        else "Capacity clarification required; no definitive top three."
        if result["mode"] == "needs_capacity"
        else "Ranked using stated capacity."
    )
    b = {
        "A2": status
        + f" Effective rate = price / ({profile.current_location.value}-to-origin + loaded miles + destination-to-{profile.home_base.value}). Factoring approval remains unverified.",
        "A10": note,
    }
    for index in range(3):
        row = result["top_three"][index] if index < len(result["top_three"]) else None
        b[f"B{index + 5}"] = row["load_id"] if row else "Not established"
        b[f"C{index + 5}"] = f"{row['effective_rate_per_mile']:.3f}" if row else None
    if document["extraction"]["kind"] != "openai":
        a["A1"] = "PREVIEW — manually authored test fixture, not live LLM output"
        b["A1"] = "PREVIEW — manually authored test fixture, not live LLM output"
    fill_workbook(
        source,
        output / "completed.xlsx",
        {"Part A (Fill In)": a, "Part B (Fill In)": b},
    )
