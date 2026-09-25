# Load matching results

Mode: **conditional**

Assumed capacity: **15000 lb**. These are conditional offers, not confirmed eligibility.

| Rank | Load | Route | Effective $/mile |
|---|---|---|---:|
| 1 | L03 | Austin → Corpus Christi | 3.098 |
| 2 | L08 | Dallas → McAllen | 2.480 |
| 3 | L02 | Houston → Laredo | 2.418 |

## Audit

- L01: rejected; incompatible equipment; weight exceeds 15000 lb capacity; effective rate does not meet driver's minimum
- L02: conditional; passes checks under the stated scenario
- L03: conditional; passes checks under the stated scenario
- L04: rejected; incompatible equipment; weight exceeds 15000 lb capacity; effective rate does not meet driver's minimum
- L05: rejected; incompatible equipment
- L06: rejected; missing or invalid price
- L07: rejected; missing Destination; missing or invalid destination latitude
- L08: conditional; passes checks under the stated scenario

## Submission note

Code: Local repository; public GitHub URL pending.
OpenAI structured-output extraction with transcript-quote validation identifies current location, home, equipment, and a >$2/mile floor. Coordinates come from the load board. Capacity is not stated; 15000 lb is an explicit scenario assumption, not an extracted fact. All listed loads are conditional on that capacity. Hotshot and Gooseneck labels are compatible; generic Flatbed is not assumed compatible. Geographic preferences remain soft; broker factoring approval cannot be checked from this board. Incomplete L06 (price) and L07 (destination) are excluded. L04 pays $1,500 but requires Van equipment and also fails the effective-rate floor. Haversine miles include Dallas-to-pickup, delivery, and the empty return to San Antonio; unrounded rates determine order. The highest-paying L08 is not inherently incompatible: its 12,600 lb weight requires capacity clarification. The workbook's trap assertion cannot be resolved from the supplied transcript.
