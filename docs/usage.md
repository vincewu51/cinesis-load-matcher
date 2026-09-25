# Running and submitting

Use Python 3.11+ and [uv](https://docs.astral.sh/uv/). From the repository root:

```sh
uv sync --extra dev
python scripts/set_api_key.py
uv run cinesis extract --output outputs/profile.json
uv run cinesis rank --profile outputs/profile.json --output-dir outputs/strict
uv run cinesis rank --profile outputs/profile.json --assumed-capacity-lb 15000 --output-dir outputs/conditional
```

Or perform both parts with `uv run cinesis solve --assumed-capacity-lb 15000`.
The model defaults to `gpt-6-astra`; change `OPENAI_MODEL` in `.env` or pass `--model`.
A live run requires access to that model and incurs API usage. Only the supplied conversation is sent to OpenAI.
The Responses API uses `store=False`; this is not a blanket guarantee of zero provider retention.
Saved profiles allow deterministic re-ranking without another API call. A transcript fingerprint prevents using a profile from a different conversation.

Outputs: `profile.json` (evidence and provenance), `results.json`, `results.md`, `load-audit.csv`, `completed.xlsx`, and a submission note of at most 200 words. The original workbook is preserved. Only the answer sheet XML is changed in the completed copy, preserving styles, drawings, and other workbook content.

## API key

The setup script reads the key without echo; it never appears in shell history or process arguments. The `.env` file has mode 0600 and is ignored before creation. Environment variables override `.env`. Keep the key out of chat, notebooks, screenshots, logs, and Git. `.env.example` contains only an empty placeholder. The app pins requests to the official OpenAI endpoint and suppresses provider exception payloads. Do not enable HTTP debug tracing when using credentials. Rotate a key if it has been exposed; deleting the file does not remove Git history.

## Offline development

`uv run pytest` uses synthetic/mocked API responses and a hand-authored profile fixture. It does not call OpenAI or require a key. The fixture is explicitly labeled; it is not evidence of a live extraction. Test coverage includes different transcript values, fabricated quote rejection, incomplete responses, missing data, threshold boundaries, capacity changes, round-trip distance, and workbook preservation.

## Public submission

No repository is automatically published. Review the code and generated outputs, then create a public GitHub repo when ready. Add the actual URL with `--repo-url https://github.com/OWNER/cinesis-load-matcher` when rerunning `rank`; it goes into the workbook note.

Copy only reviewed artifacts into a `submission/` directory; `outputs/` remains ignored to avoid accidental publication of arbitrary future driver data. Stage the intended files and run:

```sh
uv run python scripts/check_secrets.py
git diff --cached --check
git diff --cached --stat
```

The scanner checks staged content, including embedded XLSX XML, without printing matched secrets. It is an extra check, not a replacement for review. Do not force-add `.env`. For future GitHub CI, tests need no key; live API credentials belong in GitHub Actions secrets, never workflow YAML.

Official references: [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [API-key practices](https://developers.openai.com/api/docs/guides/production-best-practices).
