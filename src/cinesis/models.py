from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, model_validator

T = TypeVar("T")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Evidence(StrictModel):
    row: int
    quote: str


class Claim(StrictModel, Generic[T]):
    value: T | None
    evidence: list[Evidence]
    interpretation: str

    @model_validator(mode="after")
    def require_evidence(self):
        if self.value is not None and not self.evidence:
            raise ValueError("Every populated claim needs transcript evidence")
        return self


class Rate(StrictModel):
    dollars_per_mile: float
    comparison: Literal[">", ">="]

    @model_validator(mode="after")
    def positive(self):
        if self.dollars_per_mile <= 0:
            raise ValueError("Minimum rate must be positive")
        return self


class DriverProfile(StrictModel):
    current_location: Claim[str]
    home_base: Claim[str]
    minimum_rate: Claim[Rate]
    equipment: Claim[list[Literal["Hotshot", "Gooseneck", "Flatbed", "Van", "Reefer"]]]
    weight_capacity_lb: Claim[float]
    geographic_preferences: Claim[list[str]]
    factoring_requirement: Claim[str]
    ambiguities: list[str]

    @model_validator(mode="after")
    def validate_capacity(self):
        if (
            self.weight_capacity_lb.value is not None
            and self.weight_capacity_lb.value <= 0
        ):
            raise ValueError("Capacity must be positive")
        return self


def validate_evidence(profile: DriverProfile, conversation: list[dict]) -> None:
    """Quotes must occur verbatim (ignoring whitespace) in the cited transcript row."""
    rows = {line["row"]: " ".join(line["dialogue"].split()) for line in conversation}
    for name in DriverProfile.model_fields:
        claim = getattr(profile, name)
        if not isinstance(claim, Claim):
            continue
        for item in claim.evidence:
            quote = " ".join(item.quote.split())
            if not quote or quote not in rows.get(item.row, ""):
                raise ValueError(f"Unsupported evidence for {name}, row {item.row}")
