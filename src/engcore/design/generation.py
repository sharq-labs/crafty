"""D2 — domain-neutral mixed-variable initial candidate generation.

Generation creates typed proposals and exact candidate/Twin identities. It does
not evaluate science, infer feasibility, rank designs, or interpret product
constraints. System-specific admission and Twin materialization are explicit
caller-owned protocols.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Protocol, runtime_checkable

from ..scientific.errors import InvalidScientificProblem
from ..scientific.ir.values import ScientificValue, decode_value, encode_value, require_scientific_value
from ..scientific.serialization import require_schema, schema_string
from ..scientific.twins.definition import ScientificTwin, TwinKind
from .candidate import DesignCandidate
from .population import DesignPopulation
from .sampling import HALTON_V1, MixedVariableSampler
from .space import DesignSpace, DesignSpaceReference

GENERATION_PLAN_SCHEMA = schema_string("candidate_generation_plan")
CANDIDATE_PROPOSAL_SCHEMA = schema_string("candidate_proposal")
GENERATION_BINDING_METADATA_KEY = "engcore.design.generation_binding"


class GenerationStrategy(str, Enum):
    HALTON_V1 = HALTON_V1


@dataclass(frozen=True)
class CandidateGenerationPlan:
    """Persistent declaration of one deterministic initial-population request."""

    population_id: str
    design_space: DesignSpaceReference
    count: int
    generation: int = 0
    sequence_start: int = 1
    attempt_budget: int | None = None
    strategy: GenerationStrategy = GenerationStrategy.HALTON_V1
    candidate_prefix: str = ""

    def __post_init__(self) -> None:
        population_id = str(self.population_id).strip()
        if not population_id:
            raise InvalidScientificProblem("generation plan requires population_id")
        if not isinstance(self.design_space, DesignSpaceReference):
            raise InvalidScientificProblem(
                "generation plan requires exact DesignSpaceReference"
            )
        if isinstance(self.count, bool) or not isinstance(self.count, int) or self.count < 1:
            raise InvalidScientificProblem("generation plan count must be a positive integer")
        if isinstance(self.generation, bool) or not isinstance(self.generation, int):
            raise InvalidScientificProblem("generation number must be an integer")
        if self.generation != 0:
            raise InvalidScientificProblem(
                "D2 V0.1 generates initial generation zero only; derived generations "
                "require successor lineage/recombination semantics"
            )
        if (
            isinstance(self.sequence_start, bool)
            or not isinstance(self.sequence_start, int)
            or self.sequence_start < 1
        ):
            raise InvalidScientificProblem("sequence_start must be an integer >= 1")

        attempt_budget = self.attempt_budget
        if attempt_budget is None:
            attempt_budget = self.count * 20
        if (
            isinstance(attempt_budget, bool)
            or not isinstance(attempt_budget, int)
            or attempt_budget < self.count
        ):
            raise InvalidScientificProblem(
                "attempt_budget must be an integer >= requested candidate count"
            )

        strategy = GenerationStrategy(self.strategy)
        prefix = str(self.candidate_prefix).strip() or population_id

        object.__setattr__(self, "population_id", population_id)
        object.__setattr__(self, "attempt_budget", attempt_budget)
        object.__setattr__(self, "strategy", strategy)
        object.__setattr__(self, "candidate_prefix", prefix)

    def candidate_id_for(self, sequence_index: int) -> str:
        if isinstance(sequence_index, bool) or not isinstance(sequence_index, int):
            raise InvalidScientificProblem("candidate sequence index must be an integer")
        if sequence_index < 1:
            raise InvalidScientificProblem("candidate sequence index must be >= 1")
        return f"{self.candidate_prefix}:g{self.generation}:s{sequence_index}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": GENERATION_PLAN_SCHEMA,
            "population_id": self.population_id,
            "design_space": self.design_space.to_dict(),
            "count": self.count,
            "generation": self.generation,
            "sequence_start": self.sequence_start,
            "attempt_budget": self.attempt_budget,
            "strategy": self.strategy.value,
            "candidate_prefix": self.candidate_prefix,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CandidateGenerationPlan":
        require_schema(payload, GENERATION_PLAN_SCHEMA)
        return cls(
            population_id=payload["population_id"],
            design_space=DesignSpaceReference.from_dict(payload["design_space"]),
            count=payload["count"],
            generation=payload.get("generation", 0),
            sequence_start=payload.get("sequence_start", 1),
            attempt_budget=payload.get("attempt_budget"),
            strategy=GenerationStrategy(payload.get("strategy", HALTON_V1)),
            candidate_prefix=payload.get("candidate_prefix", ""),
        )


def _canonical_assignments(assignments: Mapping[str, ScientificValue]) -> str:
    payload = {
        name: encode_value(value)
        for name, value in sorted(assignments.items(), key=lambda item: item[0])
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def assignment_digest(assignments: Mapping[str, ScientificValue]) -> str:
    """Content identity for an exact typed assignment set."""
    return hashlib.sha256(_canonical_assignments(assignments).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CandidateProposal:
    """Typed generated choices before system-specific Twin materialization."""

    candidate_id: str
    design_space: DesignSpaceReference
    sequence_index: int
    assignments: Mapping[str, ScientificValue]
    strategy: GenerationStrategy = GenerationStrategy.HALTON_V1
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        candidate_id = str(self.candidate_id).strip()
        if not candidate_id:
            raise InvalidScientificProblem("candidate proposal requires candidate_id")
        if not isinstance(self.design_space, DesignSpaceReference):
            raise InvalidScientificProblem(
                "candidate proposal requires exact DesignSpaceReference"
            )
        if (
            isinstance(self.sequence_index, bool)
            or not isinstance(self.sequence_index, int)
            or self.sequence_index < 1
        ):
            raise InvalidScientificProblem("proposal sequence_index must be >= 1")
        assignments = dict(self.assignments)
        if not assignments:
            raise InvalidScientificProblem("candidate proposal requires assignments")
        for name, value in assignments.items():
            if not isinstance(name, str) or not name.strip():
                raise InvalidScientificProblem(
                    "candidate proposal assignment names must be non-empty strings"
                )
            require_scientific_value(value, context=f"candidate proposal {name!r}")
        strategy = GenerationStrategy(self.strategy)
        digest = assignment_digest(assignments)

        object.__setattr__(self, "candidate_id", candidate_id)
        object.__setattr__(self, "assignments", MappingProxyType(assignments))
        object.__setattr__(self, "strategy", strategy)
        object.__setattr__(self, "digest", digest)

    def validate_against(self, space: DesignSpace) -> "CandidateProposal":
        if not isinstance(space, DesignSpace):
            raise InvalidScientificProblem("proposal validation requires DesignSpace")
        if self.design_space.key != space.reference.key:
            raise InvalidScientificProblem("proposal design-space identity mismatch")
        space.validate_assignments(self.assignments)
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": CANDIDATE_PROPOSAL_SCHEMA,
            "candidate_id": self.candidate_id,
            "design_space": self.design_space.to_dict(),
            "sequence_index": self.sequence_index,
            "assignments": {
                name: encode_value(value)
                for name, value in sorted(self.assignments.items(), key=lambda item: item[0])
            },
            "strategy": self.strategy.value,
            "digest": self.digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CandidateProposal":
        require_schema(payload, CANDIDATE_PROPOSAL_SCHEMA)
        proposal = cls(
            candidate_id=payload["candidate_id"],
            design_space=DesignSpaceReference.from_dict(payload["design_space"]),
            sequence_index=payload["sequence_index"],
            assignments={
                name: decode_value(value)
                for name, value in payload.get("assignments", {}).items()
            },
            strategy=GenerationStrategy(payload.get("strategy", HALTON_V1)),
        )
        recorded = str(payload.get("digest", "")).strip()
        if not recorded or recorded != proposal.digest:
            raise InvalidScientificProblem(
                "candidate proposal assignment digest is missing or does not match payload"
            )
        return proposal


@dataclass(frozen=True)
class ProposalDecision:
    accepted: bool
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.accepted, bool):
            raise InvalidScientificProblem("proposal decision accepted must be bool")
        reasons = tuple(str(reason).strip() for reason in self.reasons)
        if any(not reason for reason in reasons):
            raise InvalidScientificProblem("proposal decision reasons must be non-empty")
        if not self.accepted and not reasons:
            raise InvalidScientificProblem("rejected proposal requires at least one reason")
        object.__setattr__(self, "reasons", reasons)


@runtime_checkable
class ProposalGate(Protocol):
    """Caller-owned domain/system generation admission boundary."""

    constraint_refs: tuple[str, ...]

    def decide(self, proposal: CandidateProposal) -> ProposalDecision:
        ...


@runtime_checkable
class TwinMaterializer(Protocol):
    """Caller-owned system logic that creates one concrete candidate Twin."""

    def materialize(self, proposal: CandidateProposal) -> ScientificTwin:
        ...


@dataclass(frozen=True)
class ProposalRejection:
    candidate_id: str
    sequence_index: int
    assignment_digest: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class CandidateGenerationBatch:
    plan: CandidateGenerationPlan
    population: DesignPopulation
    proposals: tuple[CandidateProposal, ...]
    candidates: tuple[DesignCandidate, ...]
    twins: tuple[ScientificTwin, ...]
    rejected: tuple[ProposalRejection, ...] = ()

    def __post_init__(self) -> None:
        count = self.plan.count
        if not (
            len(self.proposals)
            == len(self.candidates)
            == len(self.twins)
            == len(self.population.members)
            == count
        ):
            raise InvalidScientificProblem(
                "successful D2 batch must contain exactly the requested candidate count"
            )
        candidate_ids = tuple(candidate.candidate_id for candidate in self.candidates)
        proposal_ids = tuple(proposal.candidate_id for proposal in self.proposals)
        population_ids = tuple(member.candidate_id for member in self.population.members)
        if set(candidate_ids) != set(proposal_ids) or set(candidate_ids) != set(population_ids):
            raise InvalidScientificProblem(
                "D2 batch proposal/candidate/population identities do not match"
            )
        twin_keys = [twin.reference.key for twin in self.twins]
        if len(twin_keys) != len(set(twin_keys)):
            raise InvalidScientificProblem("D2 batch requires unique Twin references")
        digests = [proposal.digest for proposal in self.proposals]
        if len(digests) != len(set(digests)):
            raise InvalidScientificProblem("D2 batch requires unique typed assignments")

    @property
    def accepted_sequence_indices(self) -> tuple[int, ...]:
        return tuple(proposal.sequence_index for proposal in self.proposals)


def _binding_payload(proposal: CandidateProposal) -> dict[str, Any]:
    return {
        "candidate_id": proposal.candidate_id,
        "design_space_id": proposal.design_space.space_id,
        "design_space_version": proposal.design_space.version,
        "sequence_index": proposal.sequence_index,
        "strategy": proposal.strategy.value,
        "assignment_digest": proposal.digest,
    }


def _binding_string(proposal: CandidateProposal) -> str:
    return json.dumps(
        _binding_payload(proposal), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def bind_generation_to_twin(
    twin: ScientificTwin, proposal: CandidateProposal
) -> ScientificTwin:
    """Attach immutable internal generation identity to a candidate Twin."""
    if not isinstance(twin, ScientificTwin):
        raise InvalidScientificProblem("Twin materializer must return ScientificTwin")
    if twin.kind is not TwinKind.CANDIDATE:
        raise InvalidScientificProblem(
            "D2 Twin materializer must return ScientificTwin(kind=CANDIDATE)"
        )
    binding = _binding_string(proposal)
    metadata = dict(twin.metadata)
    existing = metadata.get(GENERATION_BINDING_METADATA_KEY)
    if existing is not None and existing != binding:
        raise InvalidScientificProblem(
            "materialized Twin carries a conflicting D2 generation binding"
        )
    metadata[GENERATION_BINDING_METADATA_KEY] = binding
    return replace(twin, metadata=metadata)


def generation_binding_payload(twin: ScientificTwin) -> dict[str, Any]:
    """Read and validate the immutable JSON-string D2 binding from a Twin."""
    if not isinstance(twin, ScientificTwin):
        raise InvalidScientificProblem("generation binding requires ScientificTwin")
    raw = twin.metadata.get(GENERATION_BINDING_METADATA_KEY)
    if not isinstance(raw, str) or not raw:
        raise InvalidScientificProblem("ScientificTwin is missing D2 generation binding")
    try:
        payload = json.loads(raw)
    except Exception as exc:
        raise InvalidScientificProblem("malformed D2 generation binding JSON") from exc
    required = {
        "candidate_id",
        "design_space_id",
        "design_space_version",
        "sequence_index",
        "strategy",
        "assignment_digest",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise InvalidScientificProblem("malformed D2 generation binding payload")
    return payload


def _require_gate_alignment(space: DesignSpace, gate: ProposalGate | None) -> None:
    declared = tuple(space.constraint_refs)
    if gate is None:
        if declared:
            raise InvalidScientificProblem(
                "design space declares constraint_refs but no ProposalGate was supplied"
            )
        return

    refs = tuple(str(ref).strip() for ref in getattr(gate, "constraint_refs", ()))
    if any(not ref for ref in refs) or len(refs) != len(set(refs)):
        raise InvalidScientificProblem("ProposalGate constraint_refs are malformed")
    if frozenset(refs) != frozenset(declared):
        raise InvalidScientificProblem(
            "ProposalGate constraint_refs must exactly match DesignSpace.constraint_refs"
        )


def generate_initial_population(
    *,
    design_space: DesignSpace,
    plan: CandidateGenerationPlan,
    materializer: TwinMaterializer,
    gate: ProposalGate | None = None,
) -> CandidateGenerationBatch:
    """Generate exactly ``plan.count`` unique generation-zero candidates.

    Rejected proposals and duplicate assignment sets consume the explicit
    attempt budget. Returning fewer candidates while claiming success is never
    allowed.
    """
    if not isinstance(design_space, DesignSpace):
        raise InvalidScientificProblem("D2 generation requires DesignSpace")
    if not isinstance(plan, CandidateGenerationPlan):
        raise InvalidScientificProblem("D2 generation requires CandidateGenerationPlan")
    if plan.design_space.key != design_space.reference.key:
        raise InvalidScientificProblem("generation plan design-space identity mismatch")
    if not hasattr(materializer, "materialize"):
        raise InvalidScientificProblem("D2 generation requires TwinMaterializer")

    sampler = MixedVariableSampler(design_space)
    cardinality = sampler.fully_discrete_cardinality
    if cardinality is not None and plan.count > cardinality:
        raise InvalidScientificProblem(
            f"requested {plan.count} unique candidates from fully discrete design "
            f"space with cardinality {cardinality}"
        )
    _require_gate_alignment(design_space, gate)

    proposals: list[CandidateProposal] = []
    candidates: list[DesignCandidate] = []
    twins: list[ScientificTwin] = []
    rejected: list[ProposalRejection] = []
    seen_digests: set[str] = set()
    seen_twin_keys: set[tuple[str, str]] = set()

    for attempt_offset in range(plan.attempt_budget):
        if len(candidates) >= plan.count:
            break
        sequence_index = plan.sequence_start + attempt_offset
        assignments = sampler.assignments_at(sequence_index)
        proposal = CandidateProposal(
            candidate_id=plan.candidate_id_for(sequence_index),
            design_space=plan.design_space,
            sequence_index=sequence_index,
            assignments=assignments,
            strategy=plan.strategy,
        ).validate_against(design_space)

        if proposal.digest in seen_digests:
            rejected.append(
                ProposalRejection(
                    candidate_id=proposal.candidate_id,
                    sequence_index=proposal.sequence_index,
                    assignment_digest=proposal.digest,
                    reasons=("duplicate typed assignment",),
                )
            )
            continue
        seen_digests.add(proposal.digest)

        if gate is not None:
            decision = gate.decide(proposal)
            if not isinstance(decision, ProposalDecision):
                raise InvalidScientificProblem(
                    "ProposalGate.decide() must return ProposalDecision"
                )
            if not decision.accepted:
                rejected.append(
                    ProposalRejection(
                        candidate_id=proposal.candidate_id,
                        sequence_index=proposal.sequence_index,
                        assignment_digest=proposal.digest,
                        reasons=decision.reasons,
                    )
                )
                continue

        raw_twin = materializer.materialize(proposal)
        twin = bind_generation_to_twin(raw_twin, proposal)
        if twin.reference.key in seen_twin_keys:
            raise InvalidScientificProblem(
                f"Twin materializer reused Twin reference {twin.reference.key!r} "
                "for multiple generated candidates"
            )
        seen_twin_keys.add(twin.reference.key)

        candidate = DesignCandidate(
            candidate_id=proposal.candidate_id,
            design_space=plan.design_space,
            twin=twin.reference,
            assignments=proposal.assignments,
            generation=0,
            parents=(),
            operator=plan.strategy.value,
        ).validate_against(design_space)

        proposals.append(proposal)
        candidates.append(candidate)
        twins.append(twin)

    if len(candidates) != plan.count:
        raise InvalidScientificProblem(
            f"D2 attempt budget exhausted: accepted {len(candidates)} of "
            f"requested {plan.count} after {plan.attempt_budget} attempts"
        )

    population = DesignPopulation(
        population_id=plan.population_id,
        design_space=plan.design_space,
        generation=0,
        members=tuple(candidate.reference for candidate in candidates),
    )
    population.validate_candidates(tuple(candidates))

    return CandidateGenerationBatch(
        plan=plan,
        population=population,
        proposals=tuple(proposals),
        candidates=tuple(candidates),
        twins=tuple(twins),
        rejected=tuple(rejected),
    )
