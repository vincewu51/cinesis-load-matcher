"""Read task inputs; populate answer cells without rewriting unrelated Excel content."""

import hashlib
import json
import math
import posixpath
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from openpyxl import load_workbook

HEADERS = [
    "Load ID",
    "Origin",
    "Origin Lat",
    "Origin Lon",
    "Destination",
    "Dest Lat",
    "Dest Lon",
    "Trailer",
    "Weight",
    "Price ($)",
]


def read_inputs(path: Path) -> tuple[list[dict], list[dict]]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        conversation = [
            {"row": i, "speaker": str(row[0]), "dialogue": str(row[1])}
            for i, row in enumerate(
                workbook["Sample Conversation"].iter_rows(max_col=2, values_only=True),
                1,
            )
            if i > 1 and row[0] and row[1]
        ]
        rows = list(workbook["Loads"].iter_rows(max_col=10, values_only=True))
        if list(rows[0]) != HEADERS:
            raise ValueError("Unexpected Loads column headers")
        loads = [dict(zip(HEADERS, row)) for row in rows[1:] if any(v is not None for v in row)]
        if not conversation or not loads:
            raise ValueError("Workbook has no conversation or loads")
        return conversation, loads
    finally:
        workbook.close()


def transcript_hash(conversation: list[dict]) -> str:
    return hashlib.sha256(
        json.dumps(conversation, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


def normalize_city(name: str) -> str:
    return (
        " ".join(name.lower().replace(",", " ").split()).removesuffix(" texas").removesuffix(" tx")
    )


def city_coordinates(city: str, loads: list[dict]) -> tuple[float, float]:
    matches = set()
    for load in loads:
        for field, lat, lon in [
            ("Origin", "Origin Lat", "Origin Lon"),
            ("Destination", "Dest Lat", "Dest Lon"),
        ]:
            if normalize_city(str(load[field])) == normalize_city(city):
                try:
                    point = (float(load[lat]), float(load[lon]))
                except (ValueError, TypeError):
                    continue
                if (
                    all(math.isfinite(v) for v in point)
                    and -90 <= point[0] <= 90
                    and -180 <= point[1] <= 180
                ):
                    matches.add(point)
    if len(matches) != 1:
        raise ValueError(f"Expected one unambiguous coordinate pair for {city}")
    return next(iter(matches))


def fill_workbook(source: Path, target: Path, answers: dict[str, dict]) -> None:
    """Patch only values in the two answer sheets; preserve drawings, styles, and all other ZIP parts."""
    if source.resolve() == target.resolve():
        raise ValueError("Output must not overwrite the original workbook")
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    namespace = ns["m"]
    with zipfile.ZipFile(source) as archive:
        relationships = {
            r.get("Id"): r.get("Target")
            for r in ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        }
        replacements = {}
        for sheet in ET.fromstring(archive.read("xl/workbook.xml")).find("m:sheets", ns):
            if sheet.get("name") not in answers:
                continue
            rel = sheet.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
            )
            name = relationships[rel]
            name = name.lstrip("/") if name.startswith("/") else posixpath.normpath("xl/" + name)
            root = ET.fromstring(archive.read(name))
            data = root.find("m:sheetData", ns)
            for address, value in answers[sheet.get("name")].items():
                row_number = int("".join(c for c in address if c.isdigit()))
                row = next((r for r in data if int(r.get("r")) == row_number), None)
                if row is None:
                    row = ET.Element(f"{{{namespace}}}row", {"r": str(row_number)})
                    index = next(
                        (i for i, r in enumerate(data) if int(r.get("r")) > row_number),
                        len(data),
                    )
                    data.insert(index, row)
                cell = next((c for c in row if c.get("r") == address), None)
                if cell is None:
                    cell = ET.SubElement(row, f"{{{namespace}}}c", {"r": address})
                if sheet.get("name") == "Part B (Fill In)" and address == "A11":
                    # Reuse the template's wrapped paragraph style and give the merged answer room.
                    paragraph = root.find(".//m:c[@r='A10']", ns)
                    cell.set("s", paragraph.get("s", "0"))
                    for answer_row in data:
                        if 11 <= int(answer_row.get("r")) <= 14:
                            answer_row.set("ht", "60")
                            answer_row.set("customHeight", "1")
                for child in list(cell):
                    cell.remove(child)
                cell.attrib.pop("t", None)
                if value is None:
                    continue
                if isinstance(value, (int, float)):
                    ET.SubElement(cell, f"{{{namespace}}}v").text = str(value)
                else:
                    cell.set("t", "inlineStr")
                    text = ET.SubElement(
                        ET.SubElement(cell, f"{{{namespace}}}is"), f"{{{namespace}}}t"
                    )
                    text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                    text.text = str(value)
            replacements[name] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        if len(replacements) != len(answers):
            raise ValueError("Missing expected answer sheet")
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as output:
            for entry in archive.infolist():
                output.writestr(
                    entry,
                    replacements.get(entry.filename, archive.read(entry.filename)),
                )


def submission_note(result, repo_url, extraction_kind, profile):
    extraction = (
        "One OpenAI call reads the full transcript and returns structured fields with quotes and row references. Python validates types and checks each quote against its source."
        if extraction_kind == "openai"
        else "Manual test fixture; no live LLM extraction."
    )
    if result["capacity_source"] == "catalog_minimum":
        capacity = (
            f"Capacity unstated; {result['capacity_lb']:,.0f} lb is a catalog estimate, not a guaranteed truck limit. "
            f"Source: {result['capacity_estimate']['source_url']}"
        )
    elif result["capacity_source"] == "explicit_assumption":
        capacity = (
            f"Capacity unstated; this scenario assumes {result['capacity_lb']:,.0f} lb. "
            "Recommendations require capacity confirmation."
        )
    elif result["capacity_lb"] is not None:
        capacity = f"Use the stated {result['capacity_lb']:,.0f} lb capacity."
    else:
        capacity = (
            "Capacity unstated; weight eligibility and the final top three remain unresolved."
        )
    minimum = profile.minimum_rate.value
    sections = [
        f"Code: {repo_url or 'Public GitHub URL pending.'}",
        f"1. Extraction: {extraction}",
        "2. Ranking: Use board coordinates and haversine miles for current location → pickup → delivery → home. "
        "Effective rate = price / total miles. "
        f"Filter equipment, weight, and rate {minimum.comparison} ${minimum.dollars_per_mile:g}/mile before sorting; display three decimals.",
        f"3. Assumptions: {capacity} Geography is a preference. Generic Flatbed compatibility and broker factoring approval are unconfirmed.",
        "4. Incomplete data: Exclude L06 (missing price) and L07 (missing destination); do not substitute zeros.",
        "5. Rejected example: L04 pays $1,500 but requires Van equipment, which does not match this driver's Hotshot/Gooseneck. Its $1.419 effective rate also falls below the $2 minimum.",
    ]
    return "\n\n".join(sections)


def write_outputs(source, output, profile, document, result, repo_url=None):
    """Write one profile, one auditable ranking, and the completed workbook."""
    output.mkdir(parents=True, exist_ok=True)
    note = submission_note(result, repo_url, document["extraction"]["kind"], profile)
    if len(note.split()) > 200:
        raise ValueError("Workbook note exceeds 200 words")
    a = dict(
        zip(
            ["B5", "B6", "B7", "B8", "B9", "B10", "B11", "B12", "B13"],
            [
                profile.current_location.value,
                *result["current_coordinates"],
                profile.home_base.value,
                *result["home_coordinates"],
                f"{profile.minimum_rate.value.comparison} ${profile.minimum_rate.value.dollars_per_mile:.2f}",
                " / ".join(profile.equipment.value),
                profile.weight_capacity_lb.value or "Unknown — not stated",
            ],
        )
    )
    a.update(
        A16="Catalog estimate (not confirmed)"
        if result["capacity_source"] == "catalog_minimum"
        else "Capacity assumption (not extracted)",
        B16=result["capacity_lb"] if result["mode"] == "conditional" else "None",
    )
    label = (
        f"CONDITIONAL: assumes {result['capacity_lb']:g} lb capacity."
        if result["mode"] == "conditional"
        else result["mode"]
    )
    b = {
        "A2": label
        + " Effective rate includes all three legs. Factoring approval remains unverified.",
        "A11": note,
    }
    if document["extraction"]["kind"] != "openai":
        a["A1"] = b["A1"] = "PREVIEW — test fixture, not live LLM output"
    for i in range(3):
        row = result["top_three"][i] if i < len(result["top_three"]) else None
        b[f"B{i + 5}"] = row["load_id"] if row else "Not established"
        b[f"C{i + 5}"] = f"{row['effective_rate_per_mile']:.3f}" if row else None
    fill_workbook(source, output / "completed.xlsx", {"Part A (Fill In)": a, "Part B (Fill In)": b})
    for name, data in [("profile", document), ("ranking", result)]:
        (output / f"{name}.json").write_text(
            json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        )
