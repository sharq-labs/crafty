from __future__ import annotations

import json
from pathlib import Path

import pytest

from engcore.design import (
    CandidateGenerationPlan,
    CandidateProposal,
    DesignSpace,
    GenerationStrategy,
    MixedVariableSampler,
    ProposalDecision,
    generate_initial_population,
    generation_binding_payload,
)
from engcore.scientific.errors import InvalidScientificProblem
from engcore.scientific.experiments.optimizer_adapter import CandidateCodec
from engcore.scientific.ir.problem import ModelReference
from engcore.scientific.ir.values import BooleanValue, CategoricalValue, IntegerValue
from engcore.scientific.ir.variables import ScientificVariable, VariableKind, VariableRole
from engcore.scientific.twins.definition import ScientificTwin, TwinDatum, TwinKind
from engcore.scientific.units.quantity import Quantity


def _mixed_space(*, constraint_refs: tuple[str, ...] = ()) -> DesignSpace:
    return DesignSpace(
        space_id="mixed-general",
        version="1",
        variables=(
            ScientificVariable(
                name="length",
                unit="m",
                kind=VariableKind.CONTINUOUS,
                role=VariableRole.DESIGN,
                lower=Quantity(1.0, "m"),
                upper=Quantity(9.0, "m"),
            ),
            ScientificVariable(
                name="count",
                unit="dimensionless",
                kind=VariableKind.INTEGER,
                role=VariableRole.DESIGN,
                lower=Quantity(2, "dimensionless"),
                upper=Quantity(7, "dimensionless"),
            ),
            ScientificVariable(
                name="variant",
                unit="dimensionless",
                kind=VariableKind.CATEGORICAL,
                role=VariableRole.DESIGN,
                categories=("alpha", "beta", "gamma"),
            ),
            ScientificVariable(
                name="enabled",
                unit="dimensionless",
                kind=VariableKind.BOOLEAN,
                role=VariableRole.DESIGN,
            ),
        ),
        constraint_refs=constraint_refs,
    )


class _Materializer:
    def materialize(self, proposal: CandidateProposal) -> ScientificTwin:
        return ScientificTwin(
            twin_id=f"twin:{proposal.candidate_id}",
            version="1",
            kind=TwinKind.CANDIDATE,
            models=(ModelReference("synthetic-model", "1"),),
            declarations=tuple(
                TwinDatum(name=name, value=value)
                for name, value in proposal.assignments.items()
            ),
        )


class _WrongKindMaterializer:
    def materialize(self, proposal: CandidateProposal) -> ScientificTwin:
        return ScientificTwin(
            twin_id=f"concept:{proposal.candidate_id}",
            version="1",
            kind=TwinKind.CONCEPT,
            declarations=(),
        )


class _ReusedTwinMaterializer:
    def materialize(self, proposal: CandidateProposal) -> ScientificTwin:
        return ScientificTwin(
            twin_id="same-twin",
            version="1",
            kind=TwinKind.CANDIDATE,
            models=(ModelReference("synthetic-model", "1"),),
        )


class _ParityGate:
    constraint_refs = ("synthetic:parity",)

    def decide(self, proposal: CandidateProposal) -> ProposalDecision:
        if proposal.sequence_index % 2 == 0:
            return ProposalDecision(True, ("synthetic gate accepted",))
        return ProposalDecision(False, ("synthetic gate rejected odd index",))


class _RejectAllGate:
    constraint_refs = ("synthetic:reject-all",)

    def decide(self, proposal: CandidateProposal) -> ProposalDecision:
        return ProposalDecision(False, ("synthetic rejection",))


class _WrongGate:
    constraint_refs = ("synthetic:wrong",)

    def decide(self, proposal: CandidateProposal) -> ProposalDecision:
        return ProposalDecision(True)


def _plan(space: DesignSpace, *, count: int = 8, **overrides) -> CandidateGenerationPlan:
    return CandidateGenerationPlan(
        population_id=overrides.pop("population_id", "population-d2"),
        design_space=space.reference,
        count=count,
        **overrides,
    )


def test_plan_and_proposal_round_trip_deterministically() -> None:
    space = _mixed_space()
    plan = _plan(space, count=5, sequence_start=3, attempt_budget=50)
    payload = plan.to_dict()
    assert CandidateGenerationPlan.from_dict(payload).to_dict() == payload

    sampler = MixedVariableSampler(space)
    proposal = CandidateProposal(
        candidate_id=plan.candidate_id_for(3),
        design_space=space.reference,
        sequence_index=3,
        assignments=sampler.assignments_at(3),
    )
    proposal_payload = proposal.to_dict()
    assert CandidateProposal.from_dict(proposal_payload).to_dict() == proposal_payload
    assert len(proposal.digest) == 64

    tampered = json.loads(json.dumps(proposal_payload))
    tampered["digest"] = "0" * 64
    with pytest.raises(InvalidScientificProblem):
        CandidateProposal.from_dict(tampered)


def test_mixed_sampler_generates_all_four_existing_scientific_value_kinds() -> None:
    space = _mixed_space()
    sampler = MixedVariableSampler(space)
    assignments = sampler.assignments_at(7)

    assert isinstance(assignments["length"], Quantity)
    assert isinstance(assignments["count"], IntegerValue)
    assert isinstance(assignments["variant"], CategoricalValue)
    assert isinstance(assignments["enabled"], BooleanValue)
    assert 1.0 <= assignments["length"].magnitude <= 9.0
    assert 2 <= assignments["count"].value <= 7
    assert assignments["variant"].value in {"alpha", "beta", "gamma"}
    assert space.validate_assignments(assignments) == assignments


def test_generation_is_deterministic_and_materializes_candidate_twins() -> None:
    space = _mixed_space()
    plan = _plan(space, count=16, sequence_start=5)

    first = generate_initial_population(
        design_space=space, plan=plan, materializer=_Materializer()
    )
    second = generate_initial_population(
        design_space=space, plan=plan, materializer=_Materializer()
    )

    assert [item.to_dict() for item in first.proposals] == [
        item.to_dict() for item in second.proposals
    ]
    assert [item.to_dict() for item in first.candidates] == [
        item.to_dict() for item in second.candidates
    ]
    assert first.accepted_sequence_indices == second.accepted_sequence_indices
    assert len(first.candidates) == 16
    assert first.population.validate_candidates(first.candidates) is first.population

    for proposal, candidate, twin in zip(
        first.proposals, first.candidates, first.twins
    ):
        assert candidate.twin.key == twin.reference.key
        assert candidate.assignments == dict(proposal.assignments)
        binding = generation_binding_payload(twin)
        assert binding["candidate_id"] == proposal.candidate_id
        assert binding["design_space_id"] == space.space_id
        assert binding["design_space_version"] == space.version
        assert binding["sequence_index"] == proposal.sequence_index
        assert binding["strategy"] == GenerationStrategy.HALTON_V1.value
        assert binding["assignment_digest"] == proposal.digest


def test_sequence_start_changes_generation_identity_and_values() -> None:
    space = _mixed_space()
    first = generate_initial_population(
        design_space=space,
        plan=_plan(space, count=4, sequence_start=1),
        materializer=_Materializer(),
    )
    second = generate_initial_population(
        design_space=space,
        plan=_plan(space, count=4, sequence_start=101, population_id="population-d2-b"),
        materializer=_Materializer(),
    )
    assert first.accepted_sequence_indices != second.accepted_sequence_indices
    assert {item.digest for item in first.proposals}.isdisjoint(
        {item.digest for item in second.proposals}
    )


def test_declared_constraints_require_exact_caller_owned_gate_and_resample() -> None:
    space = _mixed_space(constraint_refs=("synthetic:parity",))
    plan = _plan(space, count=5, attempt_budget=20)

    with pytest.raises(InvalidScientificProblem):
        generate_initial_population(
            design_space=space, plan=plan, materializer=_Materializer()
        )

    with pytest.raises(InvalidScientificProblem):
        generate_initial_population(
            design_space=space,
            plan=plan,
            materializer=_Materializer(),
            gate=_WrongGate(),
        )

    batch = generate_initial_population(
        design_space=space,
        plan=plan,
        materializer=_Materializer(),
        gate=_ParityGate(),
    )
    assert len(batch.candidates) == 5
    assert all(index % 2 == 0 for index in batch.accepted_sequence_indices)
    assert batch.rejected
    assert all(rejection.reasons for rejection in batch.rejected)


def test_attempt_budget_exhaustion_fails_closed() -> None:
    space = _mixed_space(constraint_refs=("synthetic:reject-all",))
    plan = _plan(space, count=3, attempt_budget=3)
    with pytest.raises(InvalidScientificProblem, match="attempt budget exhausted"):
        generate_initial_population(
            design_space=space,
            plan=plan,
            materializer=_Materializer(),
            gate=_RejectAllGate(),
        )


def test_fully_discrete_cardinality_prevents_impossible_unique_population() -> None:
    space = DesignSpace(
        space_id="finite",
        version="1",
        variables=(
            ScientificVariable(
                name="flag",
                unit="dimensionless",
                kind=VariableKind.BOOLEAN,
                role=VariableRole.DESIGN,
            ),
        ),
    )
    sampler = MixedVariableSampler(space)
    assert sampler.fully_discrete_cardinality == 2

    with pytest.raises(InvalidScientificProblem, match="cardinality 2"):
        generate_initial_population(
            design_space=space,
            plan=_plan(space, count=3, population_id="finite-pop"),
            materializer=_Materializer(),
        )


@pytest.mark.parametrize(
    "variable",
    [
        ScientificVariable(
            name="unbounded",
            unit="m",
            kind=VariableKind.CONTINUOUS,
            role=VariableRole.DESIGN,
        ),
        ScientificVariable(
            name="dimensional-integer",
            unit="m",
            kind=VariableKind.INTEGER,
            role=VariableRole.DESIGN,
            lower=Quantity(1, "m"),
            upper=Quantity(4, "m"),
        ),
        ScientificVariable(
            name="fractional-integer",
            unit="dimensionless",
            kind=VariableKind.INTEGER,
            role=VariableRole.DESIGN,
            lower=Quantity(1.5, "dimensionless"),
            upper=Quantity(4.5, "dimensionless"),
        ),
        ScientificVariable(
            name="bounded-category",
            unit="dimensionless",
            kind=VariableKind.CATEGORICAL,
            role=VariableRole.DESIGN,
            lower=Quantity(0, "dimensionless"),
            upper=Quantity(1, "dimensionless"),
            categories=("x", "y"),
        ),
        ScientificVariable(
            name="bounded-bool",
            unit="dimensionless",
            kind=VariableKind.BOOLEAN,
            role=VariableRole.DESIGN,
            lower=Quantity(0, "dimensionless"),
            upper=Quantity(1, "dimensionless"),
        ),
    ],
)
def test_searchability_rules_fail_closed(variable: ScientificVariable) -> None:
    space = DesignSpace(space_id="unsafe", version="1", variables=(variable,))
    with pytest.raises(InvalidScientificProblem):
        MixedVariableSampler(space)


def test_generation_zero_only_and_frozen_continuous_codec_remains_mixed_unsafe() -> None:
    space = _mixed_space()
    with pytest.raises(InvalidScientificProblem, match="generation zero only"):
        _plan(space, count=2, generation=1)

    with pytest.raises(InvalidScientificProblem, match="only continuous variables"):
        CandidateCodec(space.variables)


def test_materializer_must_return_unique_candidate_twins() -> None:
    space = _mixed_space()
    plan = _plan(space, count=2)

    with pytest.raises(InvalidScientificProblem, match="kind=CANDIDATE"):
        generate_initial_population(
            design_space=space,
            plan=plan,
            materializer=_WrongKindMaterializer(),
        )

    with pytest.raises(InvalidScientificProblem, match="reused Twin reference"):
        generate_initial_population(
            design_space=space,
            plan=plan,
            materializer=_ReusedTwinMaterializer(),
        )


def test_1000_mixed_candidates_are_unique_typed_and_population_valid() -> None:
    space = _mixed_space()
    plan = _plan(space, count=1000, attempt_budget=1000, population_id="population-1000")
    batch = generate_initial_population(
        design_space=space,
        plan=plan,
        materializer=_Materializer(),
    )

    assert len(batch.candidates) == 1000
    assert len({candidate.candidate_id for candidate in batch.candidates}) == 1000
    assert len({proposal.digest for proposal in batch.proposals}) == 1000
    assert len({twin.reference.key for twin in batch.twins}) == 1000
    assert not batch.rejected
    assert batch.population.validate_candidates(batch.candidates) is batch.population
    for candidate in batch.candidates:
        space.validate_assignments(candidate.assignments)


def test_d2_source_remains_domain_neutral() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "engcore" / "design"
    source = "\n".join(
        (root / name).read_text(encoding="utf-8").lower()
        for name in ("sampling.py", "generation.py")
    )
    forbidden = (
        "engcore.domains",
        "engcore.systems",
        "drone",
        "aircraft",
        "hvac",
        "battery",
        "motor",
        "propeller",
        "wing",
        "compressor",
        "reactor",
    )
    for token in forbidden:
        assert token not in source
