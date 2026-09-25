# Load matching results

Mode: **needs_capacity**

Driver capacity is unknown. Confirm capacity before offering a load; no definitive top three is available.

| Rank | Load | Route | Effective $/mile |
|---|---|---|---:|

## Audit

- L01: rejected; incompatible equipment; effective rate does not meet driver's minimum
- L02: needs_capacity; driver weight capacity not stated
- L03: needs_capacity; driver weight capacity not stated
- L04: rejected; incompatible equipment; effective rate does not meet driver's minimum
- L05: rejected; incompatible equipment
- L06: rejected; missing or invalid price
- L07: rejected; missing Destination; missing or invalid destination latitude
- L08: needs_capacity; driver weight capacity not stated

## Submission note

Code: Local repository; public GitHub URL pending.
OpenAI structured-output extraction with transcript-quote validation identifies current location, home, equipment, and a >$2/mile floor. Coordinates come from the load board. Capacity is not stated, so no load can be confirmed weight-eligible and no definitive top three is supplied. Hotshot and Gooseneck labels are compatible; generic Flatbed is not assumed compatible. Geographic preferences remain soft; broker factoring approval cannot be checked from this board. Incomplete L06 (price) and L07 (destination) are excluded. L04 pays $1,500 but requires Van equipment and also fails the effective-rate floor. Haversine miles include Dallas-to-pickup, delivery, and the empty return to San Antonio; unrounded rates determine order. The highest-paying L08 is not inherently incompatible: its 12,600 lb weight requires capacity clarification. The workbook's trap assertion cannot be resolved from the supplied transcript.
