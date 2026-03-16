import pytest

from app.safety.crisis_links import (
    CrisisResourceValidationError,
    get_curated_crisis_resources,
)


def test_get_curated_crisis_resources_returns_small_static_list() -> None:
    resources = get_curated_crisis_resources()

    assert 1 <= len(resources) <= 3
    assert all(resource.label for resource in resources)
    assert all(resource.url.startswith("https://") for resource in resources)
    assert all(resource.description for resource in resources)


def test_curated_crisis_resources_are_distinct_and_scannable() -> None:
    resources = get_curated_crisis_resources()

    labels = {resource.label for resource in resources}
    urls = {resource.url for resource in resources}

    assert len(labels) == len(resources)
    assert len(urls) == len(resources)
    assert all(len(resource.label) <= 40 for resource in resources)
    assert all(len(resource.description) <= 120 for resource in resources)


def test_curated_crisis_resources_raise_when_label_is_empty() -> None:
    with pytest.raises(CrisisResourceValidationError):
        get_curated_crisis_resources(
            source=[
                {
                    "label": "",
                    "url": "https://example.com",
                    "description": "invalid because empty label",
                }
            ]
        )


def test_curated_crisis_resources_raise_when_list_is_empty() -> None:
    with pytest.raises(CrisisResourceValidationError):
        get_curated_crisis_resources(source=[])


def test_curated_crisis_resources_raise_when_list_exceeds_max() -> None:
    valid_item = {
        "label": "Resource",
        "url": "https://example.com",
        "description": "A valid description",
    }
    with pytest.raises(CrisisResourceValidationError):
        get_curated_crisis_resources(
            source=[
                {**valid_item, "label": f"Resource {i}", "url": f"https://example{i}.com"}
                for i in range(4)
            ]
        )


def test_curated_crisis_resources_raise_when_url_is_not_https() -> None:
    with pytest.raises(CrisisResourceValidationError):
        get_curated_crisis_resources(
            source=[
                {
                    "label": "Insecure resource",
                    "url": "http://example.com",
                    "description": "Uses plain HTTP",
                }
            ]
        )


def test_curated_crisis_resources_raise_when_label_is_too_long() -> None:
    with pytest.raises(CrisisResourceValidationError):
        get_curated_crisis_resources(
            source=[
                {
                    "label": "A" * 41,
                    "url": "https://example.com",
                    "description": "Label too long",
                }
            ]
        )


def test_curated_crisis_resources_raise_when_description_is_too_long() -> None:
    with pytest.raises(CrisisResourceValidationError):
        get_curated_crisis_resources(
            source=[
                {
                    "label": "Valid label",
                    "url": "https://example.com",
                    "description": "D" * 121,
                }
            ]
        )


def test_curated_crisis_resources_raise_when_labels_are_duplicate() -> None:
    with pytest.raises(CrisisResourceValidationError):
        get_curated_crisis_resources(
            source=[
                {
                    "label": "Same label",
                    "url": "https://example1.com",
                    "description": "First resource",
                },
                {
                    "label": "Same label",
                    "url": "https://example2.com",
                    "description": "Second resource with duplicate label",
                },
            ]
        )


def test_curated_crisis_resources_raise_when_urls_are_duplicate() -> None:
    with pytest.raises(CrisisResourceValidationError):
        get_curated_crisis_resources(
            source=[
                {
                    "label": "First label",
                    "url": "https://example.com",
                    "description": "First resource",
                },
                {
                    "label": "Second label",
                    "url": "https://example.com",
                    "description": "Second resource with duplicate URL",
                },
            ]
        )


def test_curated_crisis_resources_raise_when_description_is_empty() -> None:
    with pytest.raises(CrisisResourceValidationError):
        get_curated_crisis_resources(
            source=[
                {
                    "label": "Valid label",
                    "url": "https://example.com",
                    "description": "",
                }
            ]
        )
