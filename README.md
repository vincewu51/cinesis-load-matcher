# Cinesis load matcher

Part A uses OpenAI structured outputs to extract a driver profile with exact transcript evidence. Part B validates loads, filters by equipment/weight/rate, and ranks using haversine miles across all three legs, including the empty trip home.

**Capacity is absent from the transcript.** The default reports unresolved eligibility. An explicit 15,000 lb scenario produces **L03 (3.098), L08 (2.480), L02 (2.418)** dollars/mile; these are conditional, not confirmed offers. Geographic preferences remain soft. Factoring approval needs unavailable broker data. Generic Flatbed is not assumed compatible with Hotshot/Gooseneck. The floor is strictly above $2/mile.

L06 lacks price; L07 lacks destination. Both are excluded. L04 pays $1,500 but requires Van equipment and fails the rate floor. L08, the highest-paying load, is not automatically ineligible; the workbook's trap claim cannot be established without capacity.

```sh
uv sync --extra dev
python scripts/set_api_key.py
uv run cinesis solve --assumed-capacity-lb 15000
uv run pytest
```

The hidden prompt saves an owner-only, Git-ignored `.env`; never paste keys into code or commands. Generated files live in ignored `outputs/`.

See [usage and publication](docs/usage.md), [design](docs/design.md), and the generated `outputs/submission-note.md` for the workbook note.

[Live results and completed workbooks](submission/README.md) are available for review.
