"""Safety application seam."""

from app.safety.crisis_links import (
    CrisisResource,
    CrisisResourceValidationError,
    get_curated_crisis_resources,
)
from app.safety.escalation import (
    CrisisMessagingValidationError,
    CrisisRoutingResponse,
    CrisisStepDownResponse,
    compose_crisis_routing_response,
    compose_crisis_step_down_response,
)
from app.safety.service import (
    SafetyAssessment,
    assess_message_safety,
    evaluate_incoming_message_safety,
    should_step_down_from_crisis,
)

__all__ = [
    "CrisisResource",
    "CrisisResourceValidationError",
    "CrisisMessagingValidationError",
    "CrisisRoutingResponse",
    "CrisisStepDownResponse",
    "SafetyAssessment",
    "assess_message_safety",
    "compose_crisis_step_down_response",
    "compose_crisis_routing_response",
    "evaluate_incoming_message_safety",
    "get_curated_crisis_resources",
    "should_step_down_from_crisis",
]
