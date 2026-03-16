"""Memory application seam."""

from app.memory.schemas import (
    ContinuityOverview,
    ProfileFactInput,
    ProfileFactRecord,
    SessionRecallContext,
    SessionSummaryDraft,
    SessionSummaryPayload,
    SessionSummaryRecord,
)
from app.memory.service import (
    build_session_summary,
    derive_allowed_profile_facts,
    generate_and_persist_session_summary,
    get_continuity_overview,
    get_session_recall_context,
    persist_session_summary,
    record_memory_failure,
    schedule_session_summary_generation,
)

__all__ = [
    "ContinuityOverview",
    "ProfileFactInput",
    "ProfileFactRecord",
    "SessionRecallContext",
    "SessionSummaryDraft",
    "SessionSummaryPayload",
    "SessionSummaryRecord",
    "build_session_summary",
    "derive_allowed_profile_facts",
    "generate_and_persist_session_summary",
    "get_continuity_overview",
    "get_session_recall_context",
    "persist_session_summary",
    "record_memory_failure",
    "schedule_session_summary_generation",
]
