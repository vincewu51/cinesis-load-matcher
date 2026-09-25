# Cinesis load matcher

## Problem

Extract driver requirements and rank three eligible loads:

`effective $/mile = price / (Dallas → pickup + pickup → delivery + delivery → San Antonio)`

## Solution

OpenAI extracts fields with quotes. Python validates evidence, uses board coordinates and haversine miles, then filters equipment, weight, and rate before ranking.

Capacity is **unknown**; results assume **15,000 lb**. Geography is a preference; factoring approval remains unverified. Exclude generic Flatbed. L06/L07 lack data; high-paying L04 requires Van equipment and fails the rate floor.

## Check results

| Rank | Load | $/mile |
|---|---|---:|
| 1 | L03 | 3.098 |
| 2 | L08 | 2.480 |
| 3 | L02 | 2.418 |

Inspect the [completed workbook](results/completed.xlsx), [live extraction/evidence](results/profile.json), and [distances/rejection reasons](results/ranking.json).

## Reproduce

Requires Python 3.11+/uv:

```sh
uv sync --extra dev
uv run python solve.py --assumed-capacity-lb 15000
uv run pytest -q
```

Replays the saved profile without API calls into `outputs/`. Omit capacity for unresolved eligibility.

For fresh extraction:

```sh
uv run python security.py --set-key
uv run python solve.py --refresh --assumed-capacity-lb 15000
```

Keys stay in owner-only, Git-ignored `.env`. Before publishing:

```sh
uv run python security.py --check
```

Add `--repo-url YOUR_PUBLIC_GITHUB_URL` for submission.

## How each component works

### 1. Read the workbook — `workbook.py`

Read the conversation with speaker labels and spreadsheet row numbers, and read the load board separately. Only the conversation goes to the LLM; the example answers and load rows are excluded. City coordinates are looked up from the board after extraction, so the model does not invent coordinates.

### 2. Extract the profile — `solve.py`

Send the **whole transcript in one request**, together with the extraction prompt and a structured output schema. Full context lets the model connect “Yes, that’s correct” to the dispatcher's preceding question about San Antonio, while recognizing Dallas as the current location.

The schema asks for current location, home base, minimum rate, equipment, capacity, geographic preferences, and factoring requirements. Each field includes a value, supporting quotes with row numbers, and an interpretation. Unknown values remain `null`.

The prompt is manually written from the task requirements and observed ambiguities. It separates current location from home, load weight from truck capacity, and hypothetical negotiations from a minimum rate. It also specifies our equipment-label interpretation: “hotshot gooseneck” maps to Hotshot and Gooseneck, without assuming generic Flatbed compatibility. The model does not calculate mileage or rank loads.

### 3. Validate and save the extraction — `solve.py`

Validate field types, allowed equipment labels, positive numeric constraints, and evidence for populated claims. Check that every quote appears in its cited transcript row. This catches fabricated quotes, but does not prove a quote supports the interpretation; the saved evidence remains available for review.

Save the profile with its model, timestamp, prompt hash, and transcript hash. Normal runs replay this profile without API calls; a changed transcript fails the fingerprint check. `--refresh` requests a new extraction, whose wording may differ.

### 4. Handle unknown capacity — `solve.py`

The dispatcher mentions a **44,000 lb load**, but the driver never states a payload capacity. The extracted capacity therefore stays unknown. **15,000 lb is an explicit scenario assumption**, not a fact inferred from the trailer type.

`--assumed-capacity-lb 15000` enables a conditional ranking without modifying the extracted profile. Without it, otherwise suitable loads remain unresolved. A stated capacity cannot be overridden by this assumption. Geographic preferences remain soft; broker factoring approval cannot be checked from the available columns.

### 5. Filter and rank — `solve.py`

Reject incomplete or invalid rows, then check equipment, weight, and effective rate before sorting. L06 has no price; L07 has no destination. L04 requires Van equipment and also fails the rate floor. Apply the driver's “above $2” wording as a strict `> 2` threshold to effective rate, as required by the assignment.

Calculate haversine distance for Dallas → pickup, pickup → delivery, and delivery → San Antonio. For L03, these total approximately **484.256 miles**; `$1,500 / 484.256 = $3.098/mile`. Sort passing loads by the unrounded rate, using load ID to break ties, and display three decimals. If fewer than three pass, return fewer than three.

### 6. Write results and protect credentials

`workbook.py` writes `profile.json`, `ranking.json` (including distances and rejection reasons), and `completed.xlsx`. Only the two answer sheets are changed; the original workbook and other embedded content are preserved. The workbook identifies the capacity assumption and includes a submission note of at most 200 words.

`security.py` saves the API key through a hidden prompt into an owner-only, Git-ignored `.env`. Its pre-publication check scans staged files, including Excel contents, without printing matched secrets. `test_solver.py` checks extraction handling, filtering, calculations, and workbook preservation without making live API calls.
