from pathlib import Path

import pytest

from cinesis.models import DriverProfile
from cinesis.workbook import read_inputs, transcript_hash

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def workbook():
    return ROOT / "data/input.xlsx"


@pytest.fixture
def inputs(workbook):
    return read_inputs(workbook)


@pytest.fixture
def profile():
    return DriverProfile.model_validate_json(
        (ROOT / "tests/fixtures/profile.json").read_text()
    )


@pytest.fixture
def document(profile, inputs):
    return {
        "schema_version": 1,
        "transcript_sha256": transcript_hash(inputs[0]),
        "extraction": {"kind": "test_fixture", "model": "none"},
        "profile": profile.model_dump(),
    }
