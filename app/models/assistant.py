from pydantic import BaseModel, Field


class AssistantResponse(BaseModel):
    ruling: str = Field(description="Short final ruling for the described game situation.")
    evidence: str | None = Field(
        default=None,
        description="Single short supporting quote from rules when available.",
    )
    source: str | None = Field(
        default=None,
        description="Source section for the evidence in format '<game> - <section>'.",
    )
    follow_up: str | None = Field(
        default=None,
        description="Clarifying question only when needed.",
    )
