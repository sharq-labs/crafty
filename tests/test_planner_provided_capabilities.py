"""PLANNER-PROVIDED-CAPABILITIES — executed evidence.

Preregistered in ``docs/planner-provided-capabilities-prereg.md``. This tests
the minimum universal model-discovery surface: a `provided_capabilities`
field on `ScientificModelDefinition` and a `ModelRegistry.providers_of`
query method, so a deterministic caller can answer "which registered models
provide capability X" — discovery, not ranking or selection.
"""

from __future__ import annotations

import json

import pytest

from src.engcore.scientific import (
    InvalidScientificCapability,
    ModelType,
    ModelValidationStatus,
    ScientificCapability,
    ScientificModelDefinition,
    to_json,
)
from src.engcore.scientific.models.registry import ModelRegistry

CONDUCTION = ScientificCapability("thermal", "heat_conduction")
ELASTICITY = ScientificCapability("mechanics", "linear_elasticity")
UNCLAIMED = ScientificCapability("electromagnetics", "wave_propagation")


def _model(model_id: str, *, provides=(), requires=()) -> ScientificModelDefinition:
    # required_capabilities is (pre-existing, unchanged by this milestone)
    # a bare-string frozenset, unlike the newly typed
    # provided_capabilities — normalize here so tests can pass
    # ScientificCapability fixtures to either without tripping over that
    # difference in convention.
    required = frozenset(
        c.identifier if isinstance(c, ScientificCapability) else c for c in requires
    )
    return ScientificModelDefinition(
        model_id=model_id,
        version="1.0.0",
        provided_capabilities=frozenset(provides),
        required_capabilities=required,
    )


# =====================================================================
# P3 — discovery proof: exactly one match, multiple matches, zero matches.
# =====================================================================


def test_discovery_exactly_one_match():
    conduction_model = _model("thermal.diffusion", provides={CONDUCTION})
    elasticity_model = _model("mechanics.beam", provides={ELASTICITY})
    registry = ModelRegistry([conduction_model, elasticity_model])

    matches = registry.providers_of(CONDUCTION)

    assert matches == (conduction_model,)


def test_discovery_multiple_matches_are_all_returned_unranked():
    fd_model = _model("thermal.diffusion.fd", provides={CONDUCTION})
    fem_model = _model("thermal.diffusion.fem", provides={CONDUCTION})
    unrelated = _model("mechanics.beam", provides={ELASTICITY})
    registry = ModelRegistry([fd_model, fem_model, unrelated])

    matches = registry.providers_of(CONDUCTION)

    # Both providers come back — the registry does not silently choose a
    # winner between them. That is ranking, and it is explicitly out of
    # scope for discovery. (ScientificModelDefinition carries a `metadata`
    # dict, so it is unhashable — compare by identity/model_id instead of
    # putting instances in a set.)
    assert len(matches) == 2
    assert fd_model in matches and fem_model in matches
    assert unrelated not in matches
    # Deterministic (model_id, version) order, not registration order.
    assert matches == (fd_model, fem_model)


def test_discovery_zero_matches_is_an_empty_result_not_an_error():
    conduction_model = _model("thermal.diffusion", provides={CONDUCTION})
    registry = ModelRegistry([conduction_model])

    matches = registry.providers_of(UNCLAIMED)

    assert matches == ()


def test_discovery_accepts_a_capability_identifier_string_too():
    conduction_model = _model("thermal.diffusion", provides={CONDUCTION})
    registry = ModelRegistry([conduction_model])

    assert registry.providers_of("thermal:heat_conduction") == (conduction_model,)


def test_discovery_answers_provides_not_requires():
    # A model that only *requires* the capability must not show up as a
    # provider of it — providers_of answers the opposite question from
    # ModelRegistry.list(capability=...).
    consumer = _model("thermal.needs_conduction", requires={CONDUCTION})
    registry = ModelRegistry([consumer])

    assert registry.providers_of(CONDUCTION) == ()
    assert registry.list(capability="thermal:heat_conduction") == (consumer,)


def test_model_provides_method_mirrors_realization_provides():
    model = _model("thermal.diffusion", provides={CONDUCTION})
    other = _model("mechanics.beam", provides={ELASTICITY})

    assert model.provides(CONDUCTION) is True
    assert model.provides("thermal:heat_conduction") is True
    assert other.provides(CONDUCTION) is False


def test_invalid_capability_identifier_is_rejected_not_coerced():
    model = _model("thermal.diffusion", provides={CONDUCTION})
    registry = ModelRegistry([model])
    with pytest.raises(InvalidScientificCapability):
        registry.providers_of("not-a-namespaced-identifier")


# =====================================================================
# P4 — backward compatibility: models lacking the field stay loadable,
# report no provided capabilities, and never infer one.
# =====================================================================

LEGACY_PAYLOAD_WITHOUT_PROVIDED_CAPABILITIES = {
    "schema": "scientific_model_definition/1",
    "model_id": "legacy.thermal.diffusion",
    "version": "0.1.0",
    "name": "Legacy diffusion model",
    "domain": "thermal",
    "model_type": "empirical_correlation",
    "description": "A record written before provided_capabilities existed.",
    "inputs": [],
    "outputs": [],
    "assumptions": [],
    "validity": {"schema": "validity_domain/1", "conditions": [], "description": ""},
    "references": [],
    "required_capabilities": [],
    "validation_status": "self_consistent",
    "metadata": {},
}


def test_legacy_payload_without_the_field_still_loads():
    model = ScientificModelDefinition.from_dict(
        LEGACY_PAYLOAD_WITHOUT_PROVIDED_CAPABILITIES
    )
    assert model.key == ("legacy.thermal.diffusion", "0.1.0")


def test_legacy_payload_reports_no_provided_capabilities_not_an_inferred_one():
    """No default is inferred from model_id/domain, even though both name
    'thermal' — absence of a declaration must stay absence, not a guess."""
    model = ScientificModelDefinition.from_dict(
        LEGACY_PAYLOAD_WITHOUT_PROVIDED_CAPABILITIES
    )
    assert model.provided_capabilities == frozenset()
    assert model.provides(CONDUCTION) is False


def test_legacy_model_is_simply_undiscoverable_by_capability_not_an_error():
    model = ScientificModelDefinition.from_dict(
        LEGACY_PAYLOAD_WITHOUT_PROVIDED_CAPABILITIES
    )
    registry = ModelRegistry([model])
    assert registry.providers_of(CONDUCTION) == ()


def test_model_without_the_field_constructs_directly_too():
    model = ScientificModelDefinition(model_id="bare", version="1.0.0")
    assert model.provided_capabilities == frozenset()


def test_serialization_round_trips_with_the_new_field():
    model = _model("thermal.diffusion", provides={CONDUCTION, ELASTICITY})
    payload = model.to_dict()
    assert payload["provided_capabilities"] == [
        "mechanics:linear_elasticity",
        "thermal:heat_conduction",
    ]
    restored = ScientificModelDefinition.from_dict(payload)
    assert restored == model
    assert to_json(restored) == to_json(model)


def test_serialization_round_trips_with_an_empty_declared_set():
    model = _model("thermal.diffusion")
    payload = model.to_dict()
    assert payload["provided_capabilities"] == []
    restored = ScientificModelDefinition.from_dict(payload)
    assert restored.provided_capabilities == frozenset()


def test_json_round_trip_is_stable():
    model = _model("thermal.diffusion", provides={CONDUCTION})
    text = to_json(model)
    payload = json.loads(text)
    restored = ScientificModelDefinition.from_dict(payload)
    assert restored == model


# =====================================================================
# Provided and required capabilities are independent, unvalidated axes.
# =====================================================================


def test_provided_and_required_capabilities_are_not_cross_checked():
    """Unlike ModelRealizationDefinition (which forbids a self-dependency
    overlap between provides/requires), ScientificModelDefinition's two
    capability sets are deliberately independent: nothing here asserts they
    are disjoint or related, because a model's needs and its offerings are
    not each other's inverse."""
    model = _model(
        "thermal.diffusion",
        provides={CONDUCTION},
        requires={CONDUCTION},
    )
    assert model.provides(CONDUCTION) is True
    assert "thermal:heat_conduction" in model.required_capabilities
