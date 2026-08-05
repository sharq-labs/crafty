"""Scientific Core V0 foundation tests.

Runs under pytest, and standalone via ``python -m tests.test_scientific_core``
so the suite does not depend on pytest being installed.

Deterministic and synthetic throughout: no BBOB, no COCO, no network, no
physical-domain implementation.
"""

from __future__ import annotations

import json
import sys

from src.engcore.scientific import (
    AmbiguousSolverError,
    BoundaryCondition,
    BoundaryKind,
    CandidateCodec,
    CategoryCondition,
    ConstraintDefinition,
    ConstraintOperator,
    ConvergenceState,
    CoreCapabilities,
    DuplicateRegistrationError,
    EvaluationStatus,
    ExperimentBudget,
    FlagCondition,
    InitialCondition,
    InvalidScientificProblem,
    ModelNotFoundError,
    ModelReference,
    ModelRegistry,
    ModelType,
    ObjectiveDefinition,
    ObjectiveDirection,
    OptimizerAdapter,
    PreparedSolve,
    ProvenanceRecord,
    Quantity,
    RangeCondition,
    RawSolverOutput,
    ScientificEvaluation,
    ScientificExperiment,
    ScientificModelDefinition,
    ScientificParameter,
    ScientificProblem,
    ScientificResult,
    ScientificValidationError,
    ScientificVariable,
    SolverIdentity,
    SolverNotFoundError,
    SolverRegistry,
    Uncertainty,
    UncertaintyKind,
    UnitCompatibilityError,
    ValidationCheck,
    ValidationLevel,
    ValidationOutcome,
    ValidationReport,
    ValidityDomain,
    ValidityStatus,
    VariableKind,
    VariableRole,
)
from src.engcore.scientific.solvers.capability import SolverCapability


def _raises(exc_type, fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except exc_type:
        return True
    except Exception as other:  # noqa: BLE001
        raise AssertionError(
            f"expected {exc_type.__name__}, got {type(other).__name__}: {other}"
        ) from other
    raise AssertionError(f"expected {exc_type.__name__}, nothing raised")


# =====================================================================
# 23. GENERALITY — two synthetic problems through the SAME IR
# =====================================================================

def build_algebraic_problem() -> ScientificProblem:
    """Problem A: steady algebraic-style study (no time, no conditions).

    Synthetic on purpose: a 'device' with a driving level and a scale factor,
    reporting a response and a load. No physical law is implemented.
    """
    return ScientificProblem(
        problem_id="synthetic_algebraic_v0",
        name="Synthetic algebraic study",
        description="Domain-neutral steady-state study used to exercise the IR.",
        variables=(
            ScientificVariable(
                name="drive_level",
                unit="volt",
                lower=Quantity(1.0, "volt"),
                upper=Quantity(12.0, "volt"),
                role=VariableRole.DESIGN,
            ),
            ScientificVariable(
                name="scale_factor",
                unit="ohm",
                lower=Quantity(10.0, "ohm"),
                upper=Quantity(1000.0, "ohm"),
                role=VariableRole.DESIGN,
            ),
            ScientificVariable(
                name="response", unit="ampere", role=VariableRole.OBSERVABLE
            ),
        ),
        parameters=(
            ScientificParameter("ambient", Quantity(300.0, "kelvin")),
        ),
        objectives=(
            ObjectiveDefinition(
                name="minimize_load",
                metric="load",
                direction=ObjectiveDirection.MINIMIZE,
                unit="watt",
            ),
        ),
        constraints=(
            ConstraintDefinition(
                name="response_ceiling",
                metric="response",
                operator=ConstraintOperator.LESS_EQUAL,
                bound=Quantity(0.5, "ampere"),
            ),
        ),
        models=(ModelReference("synthetic.linear_response", "1.0.0"),),
        required_capabilities=frozenset({CoreCapabilities.ALGEBRAIC.name}),
    )


def build_time_state_problem() -> ScientificProblem:
    """Problem B: time-dependent state study — same top-level contract."""
    return ScientificProblem(
        problem_id="synthetic_time_state_v0",
        name="Synthetic time-state study",
        description="Domain-neutral transient study used to exercise the IR.",
        variables=(
            ScientificVariable(
                name="decay_rate",
                unit="1/second",
                lower=Quantity(0.01, "1/second"),
                upper=Quantity(5.0, "1/second"),
                role=VariableRole.DESIGN,
            ),
            ScientificVariable(
                name="state", unit="meter", role=VariableRole.STATE
            ),
        ),
        parameters=(
            ScientificParameter("horizon", Quantity(10.0, "second")),
        ),
        objectives=(
            ObjectiveDefinition(
                name="minimize_settling",
                metric="settling_time",
                direction=ObjectiveDirection.MINIMIZE,
                unit="second",
            ),
        ),
        initial_conditions=(
            InitialCondition(
                variable="state",
                value=Quantity(1.0, "meter"),
                time=Quantity(0.0, "second"),
            ),
        ),
        boundary_conditions=(
            BoundaryCondition(
                name="far_field",
                variable="state",
                kind=BoundaryKind.DIRICHLET,
                region="outer",
                value=Quantity(0.0, "meter"),
            ),
        ),
        models=(ModelReference("synthetic.first_order_decay", "1.0.0"),),
        required_capabilities=frozenset({CoreCapabilities.ODE.name}),
    )


def test_generality_same_ir_two_problem_shapes():
    algebraic = build_algebraic_problem()
    transient = build_time_state_problem()

    assert type(algebraic) is type(transient) is ScientificProblem
    assert not algebraic.is_time_dependent
    assert transient.is_time_dependent
    assert algebraic.required_capabilities != transient.required_capabilities

    # Both round-trip through the identical serialization contract.
    for problem in (algebraic, transient):
        restored = ScientificProblem.from_dict(problem.to_dict())
        assert restored.to_dict() == problem.to_dict()


# =====================================================================
# A/B/C. Problem, variable and bound validation
# =====================================================================

def test_problem_requires_id():
    _raises(InvalidScientificProblem, ScientificProblem, problem_id="  ")


def test_duplicate_variable_and_parameter_names_rejected():
    variable = ScientificVariable("x", "meter")
    _raises(
        InvalidScientificProblem,
        ScientificProblem,
        problem_id="dup",
        variables=(variable, ScientificVariable("x", "second")),
    )
    _raises(
        InvalidScientificProblem,
        ScientificProblem,
        problem_id="dup2",
        variables=(variable,),
        parameters=(ScientificParameter("x", Quantity(1.0, "meter")),),
    )


def test_invalid_bounds_rejected():
    _raises(
        InvalidScientificProblem,
        ScientificVariable,
        name="x",
        unit="meter",
        lower=Quantity(5.0, "meter"),
        upper=Quantity(1.0, "meter"),
    )
    _raises(
        InvalidScientificProblem,
        ScientificVariable,
        name="x",
        unit="meter",
        lower=Quantity(float("inf"), "meter"),
    )
    _raises(InvalidScientificProblem, ScientificVariable, name="", unit="meter")


def test_variable_bounds_must_match_declared_dimension():
    _raises(
        UnitCompatibilityError,
        ScientificVariable,
        name="x",
        unit="meter",
        lower=Quantity(1.0, "second"),
    )


def test_bounds_expressed_in_other_units_are_converted_not_rejected():
    variable = ScientificVariable(
        "length", "meter", lower=Quantity(10.0, "cm"), upper=Quantity(2.0, "m")
    )
    assert variable.lower.units == "meter"
    assert abs(variable.lower.magnitude - 0.1) < 1e-12


def test_categorical_variable_rules():
    ok = ScientificVariable(
        "material", "dimensionless", kind=VariableKind.CATEGORICAL,
        categories=("steel", "aluminium"),
    )
    assert ok.kind is VariableKind.CATEGORICAL
    _raises(
        InvalidScientificProblem,
        ScientificVariable,
        name="material",
        unit="dimensionless",
        kind=VariableKind.CATEGORICAL,
        categories=("steel",),
    )
    _raises(
        InvalidScientificProblem,
        ScientificVariable,
        name="x",
        unit="meter",
        categories=("a", "b"),
    )


def test_condition_must_reference_known_variable():
    _raises(
        InvalidScientificProblem,
        ScientificProblem,
        problem_id="bad_ic",
        variables=(ScientificVariable("state", "meter"),),
        initial_conditions=(
            InitialCondition(variable="ghost", value=Quantity(1.0, "meter")),
        ),
    )


def test_parameter_requires_quantity():
    _raises(InvalidScientificProblem, ScientificParameter, name="p", value=3.0)


# =====================================================================
# D/E/F. Units
# =====================================================================

def test_unit_conversion():
    assert abs(Quantity(10.0, "cm").to("m").magnitude - 0.1) < 1e-15
    assert abs(Quantity(1.0, "kilometer").magnitude_in("meter") - 1000.0) < 1e-9
    voltage = Quantity(12.0, "V")
    assert voltage.magnitude == 12.0 and voltage.dimensionality != ""
    resistance = Quantity(100.0, "ohm")
    assert resistance.is_compatible_with("ohm")


def test_dimensional_compatibility_of_compound_units():
    force = Quantity(1.0, "kg * m / s**2")
    assert force.is_compatible_with(Quantity(1.0, "newton"))
    assert abs(force.to("newton").magnitude - 1.0) < 1e-15


def test_incompatible_dimensions_rejected():
    _raises(UnitCompatibilityError, Quantity(1.0, "meter").to, "second")
    _raises(
        UnitCompatibilityError,
        lambda: Quantity(1.0, "meter") + Quantity(1.0, "kelvin"),
    )
    assert not Quantity(1.0, "volt").is_compatible_with("ampere")


def test_unparsable_and_empty_units_rejected():
    _raises(UnitCompatibilityError, Quantity, 1.0, "not_a_unit_xyz")
    _raises(UnitCompatibilityError, Quantity, 1.0, "   ")


def test_quantity_never_parses_a_bare_number():
    _raises(UnitCompatibilityError, Quantity.parse, "42")


def test_quantity_serialization_round_trip():
    quantity = Quantity(2.5, "kilogram")
    assert Quantity.from_dict(quantity.to_dict()) == quantity


# =====================================================================
# G/H. Objectives and constraints
# =====================================================================

def test_objective_serialization():
    objective = ObjectiveDefinition(
        name="minimize_mass", metric="mass",
        direction=ObjectiveDirection.MINIMIZE, unit="kilogram", weight=2.0,
    )
    payload = objective.to_dict()
    assert payload["direction"] == "minimize"
    assert ObjectiveDefinition.from_dict(payload) == objective
    assert objective.sense == -1
    assert json.loads(json.dumps(payload, sort_keys=True)) == payload


def test_objective_rejects_nonpositive_weight():
    _raises(
        InvalidScientificProblem,
        ObjectiveDefinition,
        name="o", metric="m", direction=ObjectiveDirection.MAXIMIZE, weight=0.0,
    )


def test_constraint_unit_consistency_and_checking():
    constraint = ConstraintDefinition(
        name="temperature_limit",
        metric="temperature",
        operator=ConstraintOperator.LESS_EQUAL,
        bound=Quantity(350.0, "kelvin"),
    )
    satisfied = constraint.check(Quantity(300.0, "kelvin"))
    assert satisfied.satisfied and satisfied.margin.magnitude > 0

    violated = constraint.check(Quantity(400.0, "kelvin"))
    assert not violated.satisfied and violated.margin.magnitude < 0

    # A value in a different but compatible unit is converted, not refused.
    converted = constraint.check(Quantity(20.0, "degC"))
    assert converted.satisfied

    # An incompatible metric value is refused rather than silently compared.
    _raises(UnitCompatibilityError, constraint.check, Quantity(1.0, "volt"))
    assert ConstraintDefinition.from_dict(constraint.to_dict()) == constraint


def test_constraint_tolerance_must_share_dimension():
    _raises(
        UnitCompatibilityError,
        ConstraintDefinition,
        name="c", metric="m", operator=ConstraintOperator.LESS_EQUAL,
        bound=Quantity(1.0, "kelvin"), tolerance=Quantity(1.0, "volt"),
    )


def test_constraint_bound_must_be_quantity():
    _raises(
        InvalidScientificProblem,
        ConstraintDefinition,
        name="c", metric="m", operator=ConstraintOperator.LESS_EQUAL, bound=3.0,
    )


# =====================================================================
# I/J. Model registry and validity
# =====================================================================

def _demo_model() -> ScientificModelDefinition:
    return ScientificModelDefinition(
        model_id="synthetic.linear_response",
        version="1.0.0",
        name="Synthetic linear response",
        domain="synthetic",
        model_type=ModelType.APPROXIMATION,
        required_variables=("drive_level", "scale_factor"),
        provided_metrics=("response", "load"),
        assumptions=("synthetic demo model", "no physical law implemented"),
        validity=ValidityDomain(
            conditions=(
                RangeCondition(
                    name="ambient",
                    minimum=Quantity(250.0, "kelvin"),
                    maximum=Quantity(350.0, "kelvin"),
                ),
                CategoryCondition(name="regime", allowed=frozenset({"linear"})),
                FlagCondition(name="steady_state", expected=True),
            )
        ),
        required_capabilities=frozenset({CoreCapabilities.ALGEBRAIC.name}),
    )


def test_model_registry_register_get_duplicate():
    registry = ModelRegistry()
    model = _demo_model()
    registry.register(model)
    assert registry.get("synthetic.linear_response", "1.0.0") is model
    assert len(registry) == 1
    _raises(DuplicateRegistrationError, registry.register, model)
    _raises(ModelNotFoundError, registry.get, "synthetic.linear_response", "9.9.9")
    _raises(ModelNotFoundError, registry.get, "missing", "1.0.0")


def test_model_registry_is_not_global():
    first, second = ModelRegistry(), ModelRegistry()
    first.register(_demo_model())
    assert len(first) == 1 and len(second) == 0


def test_model_registry_listing_and_resolution():
    registry = ModelRegistry([_demo_model()])
    assert len(registry.list(domain="synthetic")) == 1
    assert len(registry.list(domain="thermal")) == 0
    assert len(registry.list(provides_metric="load")) == 1
    assert registry.versions("synthetic.linear_response") == ("1.0.0",)
    resolved = registry.resolve(ModelReference("synthetic.linear_response", "1.0.0"))
    assert resolved.model_id == "synthetic.linear_response"


def test_model_validity_states():
    model = _demo_model()

    in_domain = model.assess_validity(
        {"ambient": Quantity(300.0, "kelvin"), "regime": "linear",
         "steady_state": True}
    )
    assert in_domain.status is ValidityStatus.IN_DOMAIN

    outside = model.assess_validity(
        {"ambient": Quantity(500.0, "kelvin"), "regime": "linear",
         "steady_state": True}
    )
    assert outside.status is ValidityStatus.OUTSIDE_VALIDATED_DOMAIN
    assert "ambient" in outside.violated

    unknown = model.assess_validity({"regime": "linear", "steady_state": True})
    assert unknown.status is ValidityStatus.UNKNOWN
    assert "ambient" in unknown.unknown

    wrong_regime = model.assess_validity(
        {"ambient": Quantity(300.0, "kelvin"), "regime": "turbulent",
         "steady_state": True}
    )
    assert wrong_regime.status is ValidityStatus.OUTSIDE_VALIDATED_DOMAIN


def test_empty_validity_domain_is_unknown_not_valid():
    model = ScientificModelDefinition(model_id="m", version="1")
    assert model.assess_validity({"anything": True}).status is ValidityStatus.UNKNOWN


def test_model_serialization_round_trip():
    model = _demo_model()
    assert ScientificModelDefinition.from_dict(model.to_dict()) == model


def test_model_missing_requirements():
    model = _demo_model()
    assert model.missing_requirements(build_algebraic_problem()) == ()
    assert "drive_level" in model.missing_requirements(build_time_state_problem())


# =====================================================================
# K. Solver registry
# =====================================================================

class _DemoSolver:
    """Minimal solver satisfying the protocol. No science implemented."""

    def __init__(self, solver_id: str, capabilities, version: str = "1.0.0"):
        self._identity = SolverIdentity(solver_id, version, backend="synthetic")
        self._capabilities = frozenset(capabilities)

    @property
    def identity(self) -> SolverIdentity:
        return self._identity

    @property
    def capabilities(self):
        return self._capabilities

    def supports(self, problem) -> bool:
        declared = {c.name for c in self._capabilities}
        return set(problem.required_capabilities).issubset(declared)

    def prepare(self, problem) -> PreparedSolve:
        return PreparedSolve(problem=problem, solver=self._identity)

    def solve(self, prepared: PreparedSolve) -> RawSolverOutput:
        return RawSolverOutput(
            convergence=ConvergenceState.NOT_APPLICABLE, values={"load": 1.0}
        )

    def validate(self, prepared, raw) -> ValidationReport:
        return ValidationReport(
            checks=(
                ValidationCheck(
                    name="dimensional_consistency",
                    outcome=ValidationOutcome.PASS,
                    establishes=ValidationLevel.DIMENSIONALLY_VALID,
                ),
            )
        )

    def extract_metrics(self, prepared, raw):
        return {"load": Quantity(raw.values["load"], "watt")}


def test_solver_registry_no_match():
    registry = SolverRegistry()
    _raises(SolverNotFoundError, registry.resolve, build_algebraic_problem())

    registry.register(_DemoSolver("ode_only", {CoreCapabilities.ODE}))
    _raises(SolverNotFoundError, registry.resolve, build_algebraic_problem())


def test_solver_registry_single_match():
    registry = SolverRegistry([_DemoSolver("algebraic", {CoreCapabilities.ALGEBRAIC})])
    solver = registry.resolve(build_algebraic_problem())
    assert solver.identity.solver_id == "algebraic"


def test_solver_registry_ambiguous_match():
    registry = SolverRegistry(
        [
            _DemoSolver("first", {CoreCapabilities.ALGEBRAIC}),
            _DemoSolver("second", {CoreCapabilities.ALGEBRAIC}),
        ]
    )
    problem = build_algebraic_problem()
    _raises(AmbiguousSolverError, registry.resolve, problem)

    # An explicit rule resolves it — the choice is recorded, never implicit.
    chosen = registry.resolve(
        problem,
        selection_rule=lambda solvers: min(
            solvers, key=lambda s: s.identity.solver_id
        ),
    )
    assert chosen.identity.solver_id == "first"


def test_solver_registry_duplicate_and_capabilities():
    solver = _DemoSolver("algebraic", {CoreCapabilities.ALGEBRAIC})
    registry = SolverRegistry([solver])
    _raises(DuplicateRegistrationError, registry.register, solver)
    assert registry.capability_names() == (CoreCapabilities.ALGEBRAIC.name,)
    registry.unregister("algebraic", "1.0.0")
    assert len(registry) == 0
    _raises(SolverNotFoundError, registry.unregister, "algebraic", "1.0.0")


def test_capability_identifier_is_extensible():
    domain_capability = SolverCapability("electrical:dc", "future domain capability")
    registry = SolverRegistry([_DemoSolver("dc", {domain_capability})])
    problem = ScientificProblem(
        problem_id="future_domain",
        variables=(ScientificVariable("v", "volt"),),
        required_capabilities=frozenset({"electrical:dc"}),
    )
    assert registry.resolve(problem).identity.solver_id == "dc"
    _raises(Exception, SolverCapability, "has whitespace")


# =====================================================================
# L/M/N. Result, validation report, provenance
# =====================================================================

def _provenance() -> ProvenanceRecord:
    return ProvenanceRecord(
        run_id="run-0001",
        software_version="scientific-core-v0",
        git_commit="0" * 40,
        models=(("synthetic.linear_response", "1.0.0"),),
        solvers=(("algebraic", "1.0.0"),),
        inputs={"drive_level": Quantity(5.0, "volt")},
        assumptions=("synthetic demo",),
        tolerances={"rtol": 1e-9},
        environment={"python": "3.x"},
        timestamp="2026-01-01T00:00:00+00:00",
    )


def _result(**overrides) -> ScientificResult:
    payload = dict(
        result_id="res-0001",
        problem_id="synthetic_algebraic_v0",
        values={"load": Quantity(2.5, "watt"), "response": Quantity(0.1, "ampere")},
        models=(("synthetic.linear_response", "1.0.0"),),
        solver=SolverIdentity("algebraic", "1.0.0"),
        convergence=ConvergenceState.NOT_APPLICABLE,
        validation=ValidationReport(
            checks=(
                ValidationCheck(
                    name="dimensional_consistency",
                    outcome=ValidationOutcome.PASS,
                    establishes=ValidationLevel.DIMENSIONALLY_VALID,
                ),
            )
        ),
        uncertainty={"load": Uncertainty.unknown("not evaluated in V0")},
        assumptions=("synthetic demo",),
        provenance=_provenance(),
    )
    payload.update(overrides)
    return ScientificResult(**payload)


def test_result_serialization_round_trip():
    result = _result()
    payload = result.to_dict()
    restored = ScientificResult.from_dict(payload)
    assert restored.to_dict() == payload
    assert json.loads(json.dumps(payload, sort_keys=True)) == payload
    assert restored.value("load").units == "watt"


def test_result_rejects_bare_numbers_and_missing_provenance():
    _raises(Exception, _result, values={"load": 2.5})
    _raises(Exception, ScientificResult, result_id="r", values={}, provenance=None)


def test_result_uncertainty_defaults_to_unknown():
    result = _result()
    assert result.uncertainty_of("load").kind is UncertaintyKind.UNKNOWN
    assert result.uncertainty_of("response").kind is UncertaintyKind.UNKNOWN
    assert not result.uncertainty_of("response").is_quantified


def test_result_unit_check_against_problem():
    problem = build_algebraic_problem()
    _result().check_units_against(problem.metric_units())
    bad = _result(values={"load": Quantity(2.5, "ampere")})
    _raises(UnitCompatibilityError, bad.check_units_against, problem.metric_units())


def test_validation_report_states():
    empty = ValidationReport()
    assert empty.status is ValidationOutcome.NOT_RUN
    assert empty.attained_levels == frozenset()

    mixed = ValidationReport(
        checks=(
            ValidationCheck("a", ValidationOutcome.PASS,
                            establishes=ValidationLevel.DIMENSIONALLY_VALID),
            ValidationCheck("b", ValidationOutcome.WARNING),
            ValidationCheck("c", ValidationOutcome.NOT_RUN),
        )
    )
    assert mixed.status is ValidationOutcome.WARNING
    assert len(mixed.warnings) == 1 and len(mixed.not_run) == 1

    failed = mixed.with_check(ValidationCheck("d", ValidationOutcome.FAIL))
    assert failed.status is ValidationOutcome.FAIL
    assert len(failed.failures) == 1


def test_validation_level_requires_a_passing_check():
    """Guardrail: a result may not claim validation that was not performed."""
    not_run = ValidationReport(
        checks=(
            ValidationCheck(
                "benchmark", ValidationOutcome.NOT_RUN,
                establishes=ValidationLevel.BENCHMARK_VALIDATED,
            ),
        )
    )
    assert not not_run.claims(ValidationLevel.BENCHMARK_VALIDATED)
    _raises(
        ScientificValidationError,
        not_run.require_level,
        ValidationLevel.BENCHMARK_VALIDATED,
    )

    failed = ValidationReport(
        checks=(
            ValidationCheck(
                "benchmark", ValidationOutcome.FAIL,
                establishes=ValidationLevel.BENCHMARK_VALIDATED,
            ),
        )
    )
    assert not failed.claims(ValidationLevel.BENCHMARK_VALIDATED)

    passed = ValidationReport(
        checks=(
            ValidationCheck(
                "benchmark", ValidationOutcome.PASS,
                establishes=ValidationLevel.BENCHMARK_VALIDATED,
            ),
        )
    )
    assert passed.claims(ValidationLevel.BENCHMARK_VALIDATED)
    passed.require_level(ValidationLevel.BENCHMARK_VALIDATED)


def test_forged_validation_claim_is_rejected_on_load():
    payload = ValidationReport(
        checks=(ValidationCheck("x", ValidationOutcome.NOT_RUN),)
    ).to_dict()
    payload["attained_levels"] = ["experimentally_validated"]
    _raises(ScientificValidationError, ValidationReport.from_dict, payload)


def test_validation_report_round_trip_and_duplicate_names():
    report = ValidationReport(
        checks=(
            ValidationCheck("a", ValidationOutcome.PASS,
                            establishes=ValidationLevel.NUMERICALLY_CONVERGED,
                            residual=1e-12, tolerance=1e-9),
        )
    )
    assert ValidationReport.from_dict(report.to_dict()) == report
    _raises(
        ScientificValidationError,
        ValidationReport,
        checks=(
            ValidationCheck("a", ValidationOutcome.PASS),
            ValidationCheck("a", ValidationOutcome.FAIL),
        ),
    )


def test_uncertainty_rules():
    unknown = Uncertainty.unknown()
    assert unknown.kind is UncertaintyKind.UNKNOWN and not unknown.is_quantified

    standard = Uncertainty(
        kind=UncertaintyKind.STANDARD,
        standard_uncertainty=Quantity(0.1, "watt"),
        method="linearized_least_squares",
    )
    assert standard.is_quantified
    assert Uncertainty.from_dict(standard.to_dict()) == standard

    # UNKNOWN must not smuggle values, and quantified kinds must state a method.
    _raises(
        Exception, Uncertainty, kind=UncertaintyKind.UNKNOWN,
        standard_uncertainty=Quantity(0.1, "watt"),
    )
    _raises(
        Exception, Uncertainty, kind=UncertaintyKind.STANDARD,
        standard_uncertainty=Quantity(0.1, "watt"),
    )
    _raises(Exception, Uncertainty, kind=UncertaintyKind.INTERVAL,
            lower=Quantity(1.0, "watt"), method="m")


def test_provenance_deterministic_round_trip():
    record = _provenance()
    payload = record.to_dict()
    restored = ProvenanceRecord.from_dict(payload)
    assert restored == record
    assert restored.to_dict() == payload
    # Deterministic: identical inputs serialize byte-identically.
    assert json.dumps(payload, sort_keys=True) == json.dumps(
        ProvenanceRecord.from_dict(payload).to_dict(), sort_keys=True
    )


def test_provenance_requires_units_and_run_id():
    _raises(Exception, ProvenanceRecord, run_id="")
    _raises(Exception, ProvenanceRecord, run_id="r", inputs={"x": 1.0})


def test_provenance_lineage():
    parent = _provenance()
    child = parent.derived("run-0002")
    assert child.parent_run_id == parent.run_id and child.run_id == "run-0002"


# =====================================================================
# O. Experiment and evaluation
# =====================================================================

def _evaluation(index: int, load: float, status=EvaluationStatus.OK):
    problem = build_algebraic_problem()
    constraint = problem.constraints[0]
    result = _result(result_id=f"res-{index}") if status is EvaluationStatus.OK else None
    return ScientificEvaluation(
        evaluation_id=f"eval-{index}",
        candidate={
            "drive_level": Quantity(5.0, "volt"),
            "scale_factor": Quantity(100.0, "ohm"),
        },
        status=status,
        result=result,
        objective_values={"minimize_load": Quantity(load, "watt")},
        constraint_checks=(constraint.check(Quantity(0.1, "ampere")),),
    )


def test_experiment_records_and_budget():
    problem = build_algebraic_problem()
    experiment = ScientificExperiment(
        "exp-0001", problem, ExperimentBudget(max_observations=2)
    )
    assert experiment.remaining_observations == 2

    experiment.record(_evaluation(1, 5.0))
    experiment.record(_evaluation(2, 3.0))
    assert experiment.observations == 2 and experiment.remaining_observations == 0
    assert experiment.is_exhausted
    _raises(Exception, experiment.record, _evaluation(3, 1.0))


def test_experiment_failed_evaluation_does_not_consume_observation_budget():
    problem = build_algebraic_problem()
    experiment = ScientificExperiment(
        "exp-0002", problem, ExperimentBudget(max_observations=1, max_attempts=3)
    )
    experiment.record(_evaluation(1, 5.0, status=EvaluationStatus.FAILED))
    assert experiment.attempts == 1
    assert experiment.observations == 0
    assert experiment.failures == 1
    assert experiment.remaining_observations == 1


def test_experiment_best_respects_direction():
    problem = build_algebraic_problem()
    experiment = ScientificExperiment(
        "exp-0003", problem, ExperimentBudget(max_observations=5)
    )
    experiment.record(_evaluation(1, 5.0))
    experiment.record(_evaluation(2, 2.0))
    experiment.record(_evaluation(3, 9.0))
    best = experiment.best("minimize_load")
    assert best is not None and best.evaluation_id == "eval-2"
    _raises(Exception, experiment.best, "no_such_objective")


def test_experiment_round_trip_and_objective_subset_rule():
    problem = build_algebraic_problem()
    experiment = ScientificExperiment(
        "exp-0004", problem, ExperimentBudget(max_observations=3)
    )
    experiment.record(_evaluation(1, 4.0))
    payload = experiment.to_dict()
    restored = ScientificExperiment.from_dict(payload)
    assert restored.to_dict() == payload
    assert restored.observations == 1

    foreign = ObjectiveDefinition(
        name="not_declared", metric="x", direction=ObjectiveDirection.MAXIMIZE
    )
    _raises(
        Exception, ScientificExperiment, "exp-bad", problem,
        ExperimentBudget(max_observations=1), objectives=(foreign,),
    )


def test_failed_evaluation_may_not_carry_a_result():
    _raises(
        Exception, ScientificEvaluation, evaluation_id="e",
        candidate={}, status=EvaluationStatus.FAILED, result=_result(),
    )


def test_ok_evaluation_requires_a_result():
    _raises(
        Exception, ScientificEvaluation, evaluation_id="e",
        candidate={}, status=EvaluationStatus.OK,
    )


# =====================================================================
# P. Optimizer adapter
# =====================================================================

def test_codec_round_trip_scientific_to_vector_to_scientific():
    problem = build_algebraic_problem()
    codec = CandidateCodec.from_problem(problem)
    assert codec.dimension == 2
    assert codec.names == ("drive_level", "scale_factor")

    candidate = {
        "drive_level": Quantity(6.5, "volt"),
        "scale_factor": Quantity(505.0, "ohm"),
    }
    vector = codec.encode(candidate)
    assert all(0.0 <= v <= 1.0 for v in vector)

    restored = codec.decode(vector)
    for name, value in candidate.items():
        assert restored[name].units == value.units
        assert abs(restored[name].magnitude - value.magnitude) < 1e-9


def test_codec_accepts_compatible_units_and_rejects_bare_numbers():
    problem = build_algebraic_problem()
    codec = CandidateCodec.from_problem(problem)
    vector = codec.encode(
        {
            "drive_level": Quantity(6500.0, "millivolt"),  # == 6.5 V
            "scale_factor": Quantity(0.505, "kiloohm"),    # == 505 ohm
        }
    )
    restored = codec.decode(vector)
    assert abs(restored["drive_level"].magnitude - 6.5) < 1e-9
    assert abs(restored["scale_factor"].magnitude - 505.0) < 1e-6

    _raises(Exception, codec.encode, {"drive_level": 6.5, "scale_factor": Quantity(1.0, "ohm")})
    _raises(Exception, codec.decode, (0.5,))


def test_codec_requires_bounded_continuous_variables():
    unbounded = ScientificProblem(
        problem_id="unbounded",
        variables=(ScientificVariable("x", "meter"),),
    )
    _raises(InvalidScientificProblem, CandidateCodec.from_problem, unbounded)

    categorical = ScientificProblem(
        problem_id="categorical",
        variables=(
            ScientificVariable(
                "material", "dimensionless", kind=VariableKind.CATEGORICAL,
                categories=("a", "b"), lower=Quantity(0.0, "dimensionless"),
                upper=Quantity(1.0, "dimensionless"),
            ),
        ),
    )
    _raises(InvalidScientificProblem, CandidateCodec.from_problem, categorical)


def test_optimizer_adapter_encodes_objective_direction():
    problem = build_algebraic_problem()
    adapter = OptimizerAdapter.for_problem(problem)
    # The declared objective minimizes; a search backend that maximizes must
    # therefore receive a negated score.
    assert adapter.objective.sense == -1
    assert adapter.objective.encode(Quantity(3.0, "watt")) == -3.0
    assert adapter.objective.decode(-3.0) == Quantity(3.0, "watt")
    assert adapter.objective.encode(Quantity(3000.0, "milliwatt")) == -3.0
    _raises(Exception, adapter.objective.encode, 3.0)
    assert adapter.to_dict()["objective_sense"] == -1


def test_optimizer_adapter_refuses_silent_objective_choice():
    problem = build_algebraic_problem()
    two_objectives = ScientificProblem(
        problem_id=problem.problem_id,
        variables=problem.variables,
        objectives=(
            problem.objectives[0],
            ObjectiveDefinition(
                name="maximize_response", metric="response",
                direction=ObjectiveDirection.MAXIMIZE, unit="ampere",
            ),
        ),
    )
    _raises(InvalidScientificProblem, OptimizerAdapter.for_problem, two_objectives)
    chosen = OptimizerAdapter.for_problem(two_objectives, "maximize_response")
    assert chosen.objective.sense == 1


def test_adapter_drives_a_synthetic_search_backend_end_to_end():
    """Scientific candidate -> vector -> backend -> vector -> candidate.

    Uses a deterministic stub backend: the core must never import a concrete
    optimizer, so the contract is what is tested.
    """
    problem = build_algebraic_problem()
    adapter = OptimizerAdapter.for_problem(problem)

    class _StubBackend:
        def __init__(self):
            self.told: list[tuple[tuple[float, ...], float]] = []
            self._grid = [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0)]

        def ask(self, count: int = 1):
            return [self._grid[len(self.told) % len(self._grid)]] * count

        def tell(self, points, scores):
            for point, score in zip(points, scores):
                self.told.append((tuple(point), float(score)))

    backend = _StubBackend()
    for _ in range(3):
        (point,) = backend.ask(1)
        candidate = adapter.codec.decode(point)
        # A "simulator" stands in here; the core does not implement science.
        load = Quantity(
            candidate["drive_level"].magnitude
            * candidate["scale_factor"].magnitude
            / 1000.0,
            "watt",
        )
        backend.tell([point], [adapter.objective.encode(load)])

    assert len(backend.told) == 3
    # Minimization: the best score corresponds to the smallest physical load.
    best_point, best_score = max(backend.told, key=lambda item: item[1])
    best_candidate = adapter.codec.decode(best_point)
    assert best_candidate["drive_level"].units == "volt"
    assert best_score <= 0.0


# =====================================================================
# 24. Architectural guardrails
# =====================================================================

def test_scientific_core_has_no_ai_or_platform_dependencies():
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1] / "src" / "engcore" / "scientific"
    banned = (
        "openai", "anthropic", "google.generativeai", "gemini", "cohere",
        "langchain", "fastapi", "flask", "django", "sqlalchemy", "torch",
        "bbob", "cocoex",
    )
    offenders = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                for name in banned:
                    if name in stripped:
                        offenders.append(f"{path.name}: {stripped}")
    assert not offenders, f"forbidden imports in Scientific Core: {offenders}"


def test_scientific_core_contains_no_eval_or_exec():
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1] / "src" / "engcore" / "scientific"
    offenders = []
    for path in root.rglob("*.py"):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "eval(" in stripped or "exec(" in stripped:
                offenders.append(f"{path.name}:{number}")
    assert not offenders, f"dynamic execution found: {offenders}"


def test_scientific_core_does_not_import_the_optimizer_stack():
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1] / "src" / "engcore" / "scientific"
    banned = ("stacked_engine", "adaptive_stacked", "logei_engine", "validation.")
    offenders = []
    for path in root.rglob("*.py"):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                for name in banned:
                    if name in stripped:
                        offenders.append(f"{path.name}: {stripped}")
    assert not offenders, f"Scientific Core must not bind to an optimizer: {offenders}"


# =====================================================================
# standalone runner (pytest optional)
# =====================================================================

def _all_tests():
    module = sys.modules[__name__]
    return [
        (name, getattr(module, name))
        for name in sorted(dir(module))
        if name.startswith("test_") and callable(getattr(module, name))
    ]


def main() -> int:
    print("Scientific Core V0 — foundation tests")
    print("=" * 72)
    failures = 0
    for name, test in _all_tests():
        try:
            test()
            print(f"[PASS] {name}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"[FAIL] {name}: {type(exc).__name__}: {exc}")
    print("=" * 72)
    total = len(_all_tests())
    if failures:
        print(f"Scientific Core V0 tests: FAIL ({failures}/{total})")
        return 1
    print(f"Scientific Core V0 tests: PASS ({total}/{total})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
