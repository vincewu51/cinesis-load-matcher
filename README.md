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
