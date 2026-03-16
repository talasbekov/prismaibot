from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class CrisisResource:
    label: str
    url: str
    description: str


class CrisisResourceValidationError(ValueError):
    """Raised when the static crisis resource list is incomplete or unsafe."""


MAX_CRISIS_RESOURCE_COUNT = 3

_CURATED_CRISIS_RESOURCES: tuple[Mapping[str, str], ...] = (
    {
        "label": "988 Lifeline",
        "url": "https://988lifeline.org/",
        "description": "Если нужен срочный разговор с кризисным консультантом, можно позвонить, написать или открыть чат 24/7.",
    },
    {
        "label": "988 Chat",
        "url": "https://988lifeline.org/chat/",
        "description": "Если легче не звонить, а писать, можно открыть чат с 988 и получить живую поддержку.",
    },
    {
        "label": "Find local support",
        "url": "https://befrienders.org/find-support-now/",
        "description": "Если ты не в США или нужен местный вариант помощи, можно быстро найти ближайшую линию поддержки.",
    },
)


def get_curated_crisis_resources(
    *,
    source: Sequence[Mapping[str, str]] | None = None,
) -> tuple[CrisisResource, ...]:
    raw_resources = source if source is not None else _CURATED_CRISIS_RESOURCES
    resources = tuple(
        CrisisResource(
            label=item.get("label", "").strip(),
            url=item.get("url", "").strip(),
            description=item.get("description", "").strip(),
        )
        for item in raw_resources
    )
    _validate_resources(resources)
    return resources


def _validate_resources(resources: Sequence[CrisisResource]) -> None:
    if not resources:
        raise CrisisResourceValidationError("At least one crisis resource is required.")
    if len(resources) > MAX_CRISIS_RESOURCE_COUNT:
        raise CrisisResourceValidationError("Crisis resource list must stay small and scannable.")

    labels: set[str] = set()
    urls: set[str] = set()
    for resource in resources:
        if not resource.label:
            raise CrisisResourceValidationError("Crisis resource label cannot be blank.")
        if not resource.description:
            raise CrisisResourceValidationError("Crisis resource description cannot be blank.")
        if len(resource.label) > 40:
            raise CrisisResourceValidationError("Crisis resource label is too long.")
        if len(resource.description) > 120:
            raise CrisisResourceValidationError("Crisis resource description is too long.")
        if not resource.url.startswith("https://"):
            raise CrisisResourceValidationError("Crisis resource URL must use https.")
        if resource.label in labels:
            raise CrisisResourceValidationError("Crisis resource labels must be distinct.")
        if resource.url in urls:
            raise CrisisResourceValidationError("Crisis resource URLs must be distinct.")
        labels.add(resource.label)
        urls.add(resource.url)
