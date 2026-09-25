# Design and reasoning

## Part A: extraction is an LLM task

Only transcript rows, including speaker labels, are sent to the model. The workbook's example answer column and load board are excluded from the prompt to prevent answer contamination. A Pydantic schema defines nullable fields, equipment labels, exact quotes, and row references. The application validates quote grounding after the response is parsed. Schema compliance and quote matching do not prove semantic correctness; the evidence remains available for human review.

No few-shot answers encode this conversation's cities or numbers. Tests change input values and verify that the extraction adapter accepts the changed model output. The LLM does not perform mileage calculations. Coordinates are resolved deterministically from the load board; missing or conflicting city coordinates require clarification.

Current location is Dallas, while home base is San Antonio. The floor is strictly greater than $2/mile. The driver operates a hotshot gooseneck, mapped to the two corresponding board labels. Asking whether dispatch serves flatbeds does not prove a generic Flatbed load fits this truck. Geographic preferences include destinations outside geographically southern Texas, so a simplistic latitude filter would be unjustified. Factoring approval cannot be checked because broker identities are absent.

The 44,000 lb figure describes a dispatcher-proposed load, not driver capacity. The driver never confirms carrying that load. Capacity therefore remains null. No default numeric capacity is silently inferred from trailer type.

## Part B: deterministic math and eligibility

Distance uses haversine on a sphere of radius 3,958.7613 miles. Every trip includes current location → origin → destination → home. Straight-line distance follows the assignment, not real road routing. Zero-length individual legs are valid; zero total distance is not.

Rows missing required fields, with invalid coordinates/nonpositive weights or prices, or duplicate load IDs are excluded with reasons. Complete rows receive all applicable rejection reasons. Equipment and weight are checked before rate eligibility, and all eligibility checks precede sorting. Sorting uses full precision with load ID as a deterministic tie-break; three-decimal formatting happens only at presentation.

Without capacity, otherwise-suitable loads are marked `needs_capacity`, and no definitive top three is reported. `--assumed-capacity-lb` enables a separate `conditional` scenario; it never changes the extracted profile. It cannot override a stated driver capacity. Fewer than three passing loads yields fewer than three results.

| Capacity scenario | Ranked loads |
|---|---|
| Unknown | No confirmed weight-eligible offers |
| 12,000 lb | L02 |
| 13,000 lb | L08, L02 |
| 15,000 lb | L03, L08, L02 |

L05 has an attractive rate but requires generic Flatbed compatibility, which is not established. L04 is a high-paying rejected example: Van equipment and a rate below the floor. The instruction claiming that the highest-paying/highest-rate load is a trap conflicts with the supplied data unless an unstated capacity assumption is introduced. We document the gap rather than reverse-engineer a hidden answer.

## Reproducibility

`uv.lock` pins dependencies. Each saved extraction records model, prompt hash, timestamp, and transcript hash. Raw API envelopes, environment variables, credentials, and request headers are never written to artifacts. There is no automatic fallback from a failed LLM call to a hand-authored answer.
