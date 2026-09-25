# Live OpenAI run

Part A was extracted through the OpenAI API using `gpt-6-astra`. Saved profiles include model, timestamp, prompt/transcript hashes, and source quotes. Quotes were validated against the supplied transcript and reviewed before generating these artifacts. These files are live results, not the manually authored test fixture.

## Conditional top three

[Completed workbook](conditional/completed.xlsx) · [Readable results](conditional/results.md) · [Extracted profile](conditional/profile.json) · [Load audit](conditional/load-audit.csv)

| Rank | Load | Effective $/mile |
|---|---|---:|
| 1 | L03 | 3.098 |
| 2 | L08 | 2.480 |
| 3 | L02 | 2.418 |

This scenario explicitly assumes **15,000 lb capacity**. The transcript supplies no capacity. The extracted field stays unknown, and the workbook marks the ranking conditional. Broker factoring compatibility remains unverified.

## Strict interpretation

[Completed workbook](strict/completed.xlsx) · [Readable results](strict/results.md)

Without a capacity assumption, no load is confirmed weight-eligible and no definitive top three is supplied. The strict workbook makes this limitation explicit.

## Before submitting

The public GitHub URL is still pending. Once the repository exists, rerun ranking with `--repo-url` to insert its URL in the workbook submission note, then replace these reviewed artifacts. See [usage](../docs/usage.md) for commands. Neither credentials nor raw API response envelopes are included.
