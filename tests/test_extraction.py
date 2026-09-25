import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from openai import OpenAIError
from pydantic import ValidationError

from cinesis import extraction
from cinesis.models import DriverProfile, Evidence, validate_evidence


def mock_client(monkeypatch, response):
    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-not-a-real-key")
    monkeypatch.setattr(extraction, "load_dotenv", lambda *a, **kw: None)
    client = MagicMock()
    client.__enter__.return_value = client
    client.responses.parse.return_value = response
    factory = MagicMock(return_value=client)
    monkeypatch.setattr(extraction, "OpenAI", factory)
    return client, factory


def test_real_transcript_evidence(profile, inputs):
    validate_evidence(profile, inputs[0])
    assert profile.weight_capacity_lb.value is None


def test_fabricated_quote_rejected(profile, inputs):
    profile.current_location.evidence = [Evidence(row=4, quote="I am in Boston")]
    with pytest.raises(ValueError, match="Unsupported evidence"):
        validate_evidence(profile, inputs[0])


def test_claim_requires_evidence(profile):
    data = profile.model_dump()
    data["weight_capacity_lb"]["value"] = 44000
    with pytest.raises(ValidationError):
        DriverProfile.model_validate(data)


def test_llm_request_and_saved_provenance(monkeypatch, profile, inputs):
    client, factory = mock_client(
        monkeypatch,
        SimpleNamespace(output_parsed=profile, status="completed", model="test-model"),
    )
    document = extraction.extract(inputs[0], "test-model")
    args = client.responses.parse.call_args.kwargs
    assert args["store"] is False
    assert args["text_format"] is DriverProfile
    assert json.loads(args["input"][1]["content"]) == inputs[0]
    assert "unit-test-not-a-real-key" not in json.dumps(document)
    assert document["extraction"]["kind"] == "openai"
    assert document["profile"]["weight_capacity_lb"]["value"] is None
    assert factory.call_args.kwargs["base_url"] == "https://api.openai.com/v1"


def test_changed_transcript_not_hardcoded(monkeypatch, profile, inputs):
    conversation = inputs[0]
    conversation[2]["dialogue"] = conversation[2]["dialogue"].replace(
        "Dallas", "Houston"
    )
    profile.current_location.value = "Houston"
    profile.current_location.evidence = [Evidence(row=4, quote="I'm in Houston.")]
    mock_client(
        monkeypatch,
        SimpleNamespace(output_parsed=profile, status="completed", model="test-model"),
    )
    result = extraction.extract(conversation, "test-model")
    assert result["profile"]["current_location"]["value"] == "Houston"


@pytest.mark.parametrize("status,parsed", [("incomplete", True), ("completed", False)])
def test_incomplete_or_refused_response(monkeypatch, profile, inputs, status, parsed):
    mock_client(
        monkeypatch,
        SimpleNamespace(
            output_parsed=profile if parsed else None, status=status, model="test-model"
        ),
    )
    with pytest.raises(extraction.ExtractionError, match="incomplete"):
        extraction.extract(inputs[0], "test-model")


def test_provider_errors_do_not_expose_payloads(monkeypatch, profile, inputs):
    client, _ = mock_client(monkeypatch, None)
    client.responses.parse.side_effect = OpenAIError("sensitive-marker")
    with pytest.raises(extraction.ExtractionError) as exc:
        extraction.extract(inputs[0], "test-model")
    assert "sensitive-marker" not in str(exc.value)


def test_missing_key_no_network(monkeypatch, inputs):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(extraction, "load_dotenv", lambda *a, **kw: None)
    client = MagicMock()
    monkeypatch.setattr(extraction, "OpenAI", client)
    with pytest.raises(extraction.ExtractionError, match="Configure"):
        extraction.extract(inputs[0])
    client.assert_not_called()


def test_stale_saved_profile_rejected(tmp_path, document, inputs):
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(document))
    inputs[0][0]["dialogue"] = "changed"
    with pytest.raises(ValueError, match="fingerprint"):
        extraction.read_profile(path, inputs[0])
