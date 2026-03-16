"""Runtime boundary documentation for the MVP foundation.

Legacy auth and CRUD modules are retained temporarily for compatibility and tests,
but product growth should extend the modular seams below instead of expanding
the template-centric login/users/items surface.
"""

PRODUCT_MODULE_SEAMS = (
    "bot",
    "conversation",
    "memory",
    "safety",
    "billing",
    "ops",
    "shared",
)

LEGACY_RUNTIME_POLICY = "isolated-from-runtime-center"

