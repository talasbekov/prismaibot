from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class ProfileFactInput(BaseModel):
    fact_key: str
    fact_value: str
    confidence: str = "medium"
    # Pre-promotion placeholder; always overwritten by _promote_profile_facts before persistence.
    retention_scope: str = "candidate"


class SessionSummaryPayload(BaseModel):
    session_id: uuid.UUID
    telegram_user_id: int
    reflective_mode: str
    source_turn_count: int
    prior_context: str | None = None
    latest_user_message: str
    takeaway: str
    next_steps: list[str] = Field(default_factory=list)
    allowed_profile_facts: list[ProfileFactInput] = Field(default_factory=list)


class SessionSummaryDraft(BaseModel):
    takeaway: str
    key_facts: list[str] = Field(default_factory=list)
    emotional_tensions: list[str] = Field(default_factory=list)
    uncertainty_notes: list[str] = Field(default_factory=list)
    next_step_context: list[str] = Field(default_factory=list)
    profile_facts: list[ProfileFactInput] = Field(default_factory=list)


class SessionSummaryRecord(BaseModel):
    session_id: uuid.UUID
    takeaway: str
    reflective_mode: str
    source_turn_count: int
    retention_scope: str
    deletion_eligible: bool


class ProfileFactRecord(BaseModel):
    fact_key: str
    fact_value: str
    confidence: str
    retention_scope: str
    deletion_eligible: bool
    source_session_id: uuid.UUID


class ContinuityOverview(BaseModel):
    telegram_user_id: int
    summaries: list[SessionSummaryRecord] = Field(default_factory=list)
    profile_facts: list[ProfileFactRecord] = Field(default_factory=list)


class SessionRecallContext(BaseModel):
    telegram_user_id: int
    last_session_takeaway: str
    continuity_context: str
    profile_facts: list[ProfileFactRecord] = Field(default_factory=list)
