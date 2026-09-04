"""COUPLING-PACK-RELOCATION — the relocation itself, measured.

Preregistration: ``docs/coupling-pack-relocation-prereg.md``, committed alone
before any source file on this branch was added or edited. Every criterion
below is that document's, and this module is not free to move one.

The milestone is a **move**, not a design. So almost everything here is a
negative: nothing gained a domain branch, nothing gained a relaxation knob,
nothing was copied, nothing was aliased, no number changed, and universal
scientific Core gained nothing at all.
"""

from __future__ import annotations

import ast
import json
import pathlib
import subprocess
import sys
import textwrap

import pytest

from engcore import coupling as cpl
from engcore.coupling import execution, graph, plan, scales
from engcore.domains import thermal_lumped as lump
from engcore.domains.electrical import material as mat
from engcore.scientific.units.quantity import Quantity
from engcore.systems import electrothermal as et_pack
from engcore.systems import fluidthermal as ft_pack
from engcore.systems.electrothermal import coupled as etc
from engcore.systems.fluidthermal import coupled as ftc
from engcore.systems.fluidthermal import properties as prop

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
PACKAGE = REPO_ROOT / "src/engcore/coupling"
BASELINE = "ad6e6cd0833be7161b1575d9b5b5e97d339e4b27"

KELVIN = "kelvin"

#: Every token that would mean the generic package knows a science. Prereg §5.
DOMAIN_VOCABULARY = (
    # NB `current` is deliberately absent: it is also the ordinary English
    # word for "the value now", and the loop's own iterate variable is called
    # `current`. `ampere` is the electrical token that carries no such
    # ambiguity, and it is the one asserted.
    "electrical", "electro", "thermal", "joule", "resistor", "resistance",
    "circuit", "voltage", "ampere", "conductor", "fluid", "transport2d",
    "diffusivity", "efflux", "advection", "conductance", "temperature",
    "heat", "kelvin", "watt", "ohm", "volt", "pascal", "kinetics", "cstr",
    "structural", "stress", "reaction",
)

#: Prereg §12(b). Nothing speculative about acceleration entered the package.
RELAXATION_VOCABULARY = (
    "omega", "relax", "damp", "aitken", "anderson", "rollback", "checkpoint",
    "accelerat", "underrelax", "over_relax",
)


def _package_sources() -> list[tuple[pathlib.Path, str]]:
    return [
        (path, path.read_text(encoding="utf-8"))
        for path in sorted(PACKAGE.glob("*.py"))
    ]


def _code_only(source: str) -> str:
    """The source with every string constant blanked.

    Docstrings explain a rule; they are not the rule. A scan that cannot tell
    the two apart proves nothing about what the code does. The same helper the
    two consumers' own suites already use, restated here so this module stands
    alone.
    """
    tree = ast.parse(textwrap.dedent(source))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            node.value = ""
    return ast.unparse(tree)


def _string_literals(source: str) -> set[str]:
    """Every string constant that is NOT a docstring.

    The dual of :func:`_code_only`, and the reason both exist. A schema name
    can only ever appear as a string literal, so a sweep that blanks every
    string constant cannot find one — `architecture-falsifier` caught that as
    a guard incapable of failing. Docstrings stay excluded, because prose that
    *explains* the rename legitimately names the old strings.
    """
    tree = ast.parse(source)
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(
                body[0].value, ast.Constant
            ) and isinstance(body[0].value.value, str):
                docstrings.add(id(body[0].value))
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
    }


# =====================================================================
# §R — universal scientific Core gained nothing
# =====================================================================

def test_r_universal_core_is_untouched():
    """Prereg §4 and §18 F6. Predicted 0 files; loudly reported otherwise."""
    changed = subprocess.run(
        ["git", "diff", "--name-only", BASELINE, "--", "src/engcore/scientific/"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert changed == "", changed


def test_r2_no_coupling_name_was_promoted_into_core():
    """The new package is infrastructure; it is not `engcore.scientific`."""
    import engcore.scientific as core

    assert not set(core.__all__) & set(cpl.__all__)
    for path in (REPO_ROOT / "src/engcore/scientific").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        code = _code_only(path.read_text(encoding="utf-8"))
        for name in ("CoupledRun", "FixedPointCouplingPlan", "TornEndpoint",
                     "CouplingOutcome", "run_fixed_point", "engcore.coupling"):
            assert name not in code, (name, path)


# =====================================================================
# §I — one identity, two consumers, no copy
# =====================================================================

def test_i_both_production_consumers_use_the_same_objects_by_identity():
    """Object identity, not name equality and not positional equivalence."""
    for pack in (etc, ftc):
        assert pack.run_fixed_point is cpl.run_fixed_point
        assert pack.FixedPointCouplingPlan is cpl.FixedPointCouplingPlan
        assert pack.TornEndpoint is cpl.TornEndpoint
        assert pack.CoupledRun is cpl.CoupledRun
    # …and the identity really is the module object in the new package, not a
    # re-created twin that happens to compare equal.
    assert cpl.run_fixed_point is execution.run_fixed_point
    assert cpl.FixedPointCouplingPlan is plan.FixedPointCouplingPlan
    assert cpl.execution_order is graph.execution_order
    assert cpl.is_ratio_scale is scales.is_ratio_scale


def test_i2_no_pack_retains_a_copied_equivalent():
    """A move, not a fork — measured over the AST of every pack module."""
    relocated = {
        "is_ratio_scale", "shares_origin", "_require_ratio_scale", "edge_key",
        "CouplingOutcome", "TornEndpoint", "FixedPointCouplingPlan", "_edges",
        "execution_order", "cycle_edges", "CoupledIteration", "CoupledRun",
        "run_fixed_point",
    }
    for path in (REPO_ROOT / "src/engcore").rglob("*.py"):
        if "__pycache__" in path.parts or PACKAGE in path.parents:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        defined = {
            node.name for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.ClassDef))
        }
        assert not defined & relocated, (path, sorted(defined & relocated))


def test_i3_no_pack_republishes_a_generic_coupling_name():
    """False ownership removed, not renamed. Prereg §7(B)."""
    generic = set(cpl.__all__)
    for module in (et_pack, ft_pack, etc, ftc):
        published = set(getattr(module, "__all__", ()))
        assert not published & generic, (module.__name__, sorted(published & generic))


def test_i4_the_generic_package_imports_no_domain_and_no_system_pack():
    """A dependency edge from `engcore.coupling` into a science would be the
    whole failure of the milestone, and it is checked structurally."""
    for path, source in _package_sources():
        tree = ast.parse(source)
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.ImportFrom):
                targets.append(node.module or "")
                # a relative import of level 2 from engcore/coupling/x.py
                # reaches engcore.<module>; level >= 3 leaves engcore entirely.
                assert node.level <= 2, (path, node.module, node.level)
            elif isinstance(node, ast.Import):
                targets += [a.name for a in node.names]
            for target in targets:
                assert "domains" not in target, (path, target)
                assert "systems" not in target, (path, target)


# =====================================================================
# §11 / genericity attack — zero domain vocabulary in executable source
# =====================================================================

def test_q_the_generic_package_carries_no_domain_vocabulary_in_its_code():
    """Prereg §5. Docstrings are scanned separately; code must be clean."""
    for path, source in _package_sources():
        code = _code_only(source).lower()
        for word in DOMAIN_VOCABULARY:
            assert word not in code, f"{word!r} in {path.name}"


def test_q2_the_generic_package_has_no_domain_specific_branch():
    """No `if` anywhere tests a domain token. Goal: zero such branches."""
    for path, source in _package_sources():
        tree = ast.parse(_code_only(source))
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.IfExp)):
                rendered = ast.dump(node.test).lower()
                for word in DOMAIN_VOCABULARY:
                    assert word not in rendered, (path, word)


def test_q3_the_generic_package_names_no_model_metric_solver_or_provider():
    """It transports identities; it never enumerates one."""
    for path, source in _package_sources():
        code = _code_only(source)
        for name in (
            "LINEAR_TCR_MODEL", "LUMPED_CAPACITY_MODEL", "TRANSPORT2D_MODEL",
            "POWER_LAW_DIFFUSIVITY_MODEL", "WALL_CONDUCTANCE_MODEL",
            "PHI_D_METRIC", "RESISTANCE_METRIC", "HEAT_INPUT", "ngspice",
            "electrical_dc:", "thermal-lumped", "fluids-transport2d",
        ):
            assert name not in code, (path, name)


def test_p_relaxation_was_not_added_anywhere_in_the_package():
    """Prereg §12(b). 40 sweeps → limit and 56 → convergence, undamped."""
    for path, source in _package_sources():
        tree = ast.parse(source)
        identifiers = (
            {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
            | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
            | {n.arg for n in ast.walk(tree) if isinstance(n, ast.arg)}
            | {
                n.name for n in ast.walk(tree)
                if isinstance(n, (ast.FunctionDef, ast.ClassDef))
            }
        )
        for forbidden in RELAXATION_VOCABULARY:
            assert not any(forbidden in name.lower() for name in identifiers), (
                path, forbidden
            )


def test_p2_the_outcome_enum_still_has_exactly_two_members():
    """Prereg §9 Z3. No `DIVERGED` was minted from intuition by the move."""
    assert {m.value for m in cpl.CouplingOutcome} == {
        "criterion_met", "iteration_limit_reached"
    }


def test_p3_no_field_mesh_or_transfer_concept_entered_the_package():
    """Prereg §12(a) and the non-goals list, checked rather than promised."""
    for path, source in _package_sources():
        code = _code_only(source)
        for forbidden in (
            "ScientificField", "Mesh", "Topology", "interpolat", "transfer_op",
            "TransferOperator", "Scheduler", "Planner", "Provider",
        ):
            assert forbidden not in code, (path, forbidden)


# =====================================================================
# §E — the schema family
# =====================================================================

def test_e_the_four_coupling_schemas_are_the_renamed_generic_family():
    assert cpl.TORN_ENDPOINT_SCHEMA == "coupling_torn_endpoint/1"
    assert cpl.FIXED_POINT_PLAN_SCHEMA == "coupling_fixed_point_plan/1"
    assert cpl.COUPLED_ITERATION_SCHEMA == "coupling_fixed_point_iteration/1"
    assert cpl.COUPLED_RUN_SCHEMA == "coupling_fixed_point_run/1"


def test_e2_the_packs_declare_no_coupling_schema_of_their_own():
    """One family, one owner. Neither pack mints a coupling schema string.

    Measured over string LITERALS, docstrings excluded — the same repair
    `architecture-falsifier` required for `test_o3`: a schema name exists only
    as a literal, so the `_code_only` form of this sweep could not fail.
    """
    forbidden = ("torn_endpoint", "fixed_point_plan", "coupled_iteration",
                 "coupled_run", "coupling_fixed_point_run",
                 "coupling_fixed_point_iteration")
    for pack in ("electrothermal", "fluidthermal"):
        for path in sorted((REPO_ROOT / "src/engcore/systems" / pack).glob("*.py")):
            source = path.read_text(encoding="utf-8")
            literals = _string_literals(source)
            for token in forbidden:
                assert not any(token in text for text in literals), (path, token)
            # and no pack mints a schema string at all
            tree = ast.parse(source)
            called = {
                node.func.id for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            }
            assert "schema_string" not in called, path

    # The guard must be able to fail.
    assert any("coupled_run" in t
               for t in _string_literals('X = schema_string("coupled_run")'))


# =====================================================================
# §F — the stored-payload search, re-run as a test
# =====================================================================

def test_f_no_stored_payload_carries_a_coupling_schema_string():
    """Prereg §6. The rename was safe because nothing persisted reads it.

    Re-executed here so the claim cannot silently rot: if a fixture, results
    archive or example payload ever starts carrying a coupling record, this
    fails and the compatibility question becomes live again.
    """
    tokens = ("torn_endpoint", "fixed_point_plan", "coupled_iteration",
              "coupled_run", "coupling_fixed_point_run",
              "coupling_fixed_point_iteration", "coupling_torn_endpoint")
    offenders: list[tuple[str, str]] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in {".json", ".jsonl", ".yaml", ".yml"}:
            continue
        if any(part in {".git", ".venv", "__pycache__"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in tokens:
            if token in text:
                offenders.append((str(path.relative_to(REPO_ROOT)), token))
    assert offenders == [], offenders


# =====================================================================
# §J — serialization, for BOTH consumers, under the SAME identities
# =====================================================================

def _et_run():
    system = etc.CoupledElectroThermalSystem(
        stages=(
            etc.CoupledStage(
                mat.TemperatureDependentConductor(
                    component_id="R1",
                    reference_resistance=Quantity(10.0, "ohm"),
                    temperature_coefficient=Quantity(0.00393, "1/kelvin"),
                    reference_temperature=Quantity(293.15, KELVIN),
                ),
                lump.ThermalBody(
                    body_id="R1",
                    heat_capacity=Quantity(2.5, "joule/kelvin"),
                    ambient_conductance=Quantity(0.05, "watt/kelvin"),
                    ambient_temperature=Quantity(300.0, KELVIN),
                    initial_temperature=Quantity(300.0, KELVIN),
                    duration=Quantity(120.0, "second"),
                ),
            ),
        ),
        source_voltage=Quantity(5.0, "volt"),
    )
    problems = etc.coupled_problems(
        system, {"R1": Quantity(10.0, "ohm")}
    )
    dependencies = etc.coupled_dependencies(system, problems)
    plan_ = etc.nominal_plan(
        system, dependencies, seed=Quantity(300.0, KELVIN),
        tolerance=Quantity(1e-6, KELVIN), max_iterations=50,
    )
    return system, plan_, etc.run_fixed_point_coupling(
        system, plan_, run_id="reloc-et"
    )


def _ft_system(n_cells: int = 16, heat_w: float = 6.0):
    return ft_pack.FluidThermalSystem(
        slice=ft_pack.FluidSlice(
            slice_id="slab-a",
            side=Quantity(1.0, "meter"),
            angular_rate=Quantity(1.0, "1/s"),
            grid=__import__(
                "engcore.domains.fluids.transport2d", fromlist=["Transport2DGrid"]
            ).Transport2DGrid(n_cells=n_cells),
        ),
        medium=ft_pack.GasDiffusivity(
            medium_id="air-like",
            reference_diffusivity=Quantity(0.01, "m**2/s"),
            reference_temperature=Quantity(300.0, KELVIN),
            temperature_exponent=Quantity(1.75, "dimensionless"),
        ),
        wall=ft_pack.WallCoupling(
            medium_id="air-like",
            volumetric_heat_capacity=Quantity(1.2e3, "joule/(meter**3*kelvin)"),
            depth=Quantity(1.0e-3, "meter"),
        ),
        body=ft_pack.HeatedBody(
            body_id="body-a",
            heat_capacity=Quantity(600.0, "joule/kelvin"),
            ambient_temperature=Quantity(300.0, KELVIN),
            initial_temperature=Quantity(300.0, KELVIN),
            duration=Quantity(600.0, "second"),
            heat_input=Quantity(heat_w, "watt"),
            posing_conductance=Quantity(0.1, "watt/kelvin"),
        ),
    )


def _ft_run():
    system = _ft_system()
    dependencies = ft_pack.coupled_dependencies(system)
    plan_ = ft_pack.nominal_plan(system, dependencies, max_iterations=40)
    return system, plan_, ft_pack.run_fluid_thermal_coupling(
        system, plan_, run_id="reloc-ft"
    )


@pytest.fixture(scope="module")
def et_case():
    return _et_run()


@pytest.fixture(scope="module")
def ft_case():
    return _ft_run()


@pytest.mark.expensive
@pytest.mark.parametrize("which", ["et", "ft"])
def test_j_every_relocated_record_round_trips_for_both_consumers(
    which, et_case, ft_case
):
    _, plan_, run = et_case if which == "et" else ft_case

    for endpoint in plan_.torn:
        assert cpl.TornEndpoint.from_dict(endpoint.to_dict()) == endpoint
    assert json.dumps(
        cpl.FixedPointCouplingPlan.from_dict(plan_.to_dict()).to_dict(),
        sort_keys=True,
    ) == json.dumps(plan_.to_dict(), sort_keys=True)

    iteration = run.iterations[0]
    assert json.dumps(
        cpl.CoupledIteration.from_dict(iteration.to_dict()).to_dict(),
        sort_keys=True,
    ) == json.dumps(iteration.to_dict(), sort_keys=True)

    revived = cpl.CoupledRun.from_dict(run.to_dict())
    assert revived.outcome is run.outcome
    assert revived.iterations_run == run.iterations_run
    assert revived.final_values.keys() == run.final_values.keys()
    assert json.dumps(revived.to_dict(), sort_keys=True) == json.dumps(
        run.to_dict(), sort_keys=True
    )


@pytest.mark.expensive
def test_j2_both_consumers_serialize_under_the_same_generic_identities(
    et_case, ft_case
):
    """The record type is the same, so the schema identity must be the same."""
    et_payload = et_case[2].to_dict()
    ft_payload = ft_case[2].to_dict()
    for payload in (et_payload, ft_payload):
        assert payload["schema"] == cpl.COUPLED_RUN_SCHEMA
        assert payload["plan"]["schema"] == cpl.FIXED_POINT_PLAN_SCHEMA
        assert payload["plan"]["torn"][0]["schema"] == cpl.TORN_ENDPOINT_SCHEMA
        assert payload["iterations"][0]["schema"] == cpl.COUPLED_ITERATION_SCHEMA


@pytest.mark.expensive
def test_j3_the_pack_specific_payload_content_stayed_pack_specific(
    et_case, ft_case
):
    """A shared schema is not a shared payload. The physics still differs."""
    et_ids = {e["problem_id"] for e in et_case[2].to_dict()["final_values"]}
    ft_ids = {e["problem_id"] for e in ft_case[2].to_dict()["final_values"]}
    assert et_ids and ft_ids and not (et_ids & ft_ids)
    assert any("resistance-tcr" in p for p in et_ids)
    assert any("fluid-diffusivity" in p for p in ft_ids)
    # and the participants named across the whole run are disjoint too
    et_all = {r["problem_id"] for i in et_case[2].to_dict()["iterations"]
              for r in i["results"]}
    ft_all = {r["problem_id"] for i in ft_case[2].to_dict()["iterations"]
              for r in i["results"]}
    assert any("electrical_dc:" in p for p in et_all)
    assert any("fluids-transport2d" in p for p in ft_all)
    assert not (et_all & ft_all)


# =====================================================================
# §L — provenance naming: a records-only reader is not misinformed
# =====================================================================

@pytest.mark.expensive
def test_l_a_fluid_thermal_record_no_longer_calls_itself_electrothermal(ft_case):
    """The defect `FT-SCALAR-COUPLING` recorded as falsifier C-4, closed.

    A records-only reader of the serialized fluid-thermal run must be able to
    identify the coupled run, its participants, its exchange dependencies and
    its iteration outcome **without a single token telling it the coupling is
    electro-thermal.**
    """
    system, _, run = ft_case
    text = json.dumps(run.to_dict(), sort_keys=True)
    assert "electrothermal" not in text
    assert "electro-thermal" not in text
    assert "electrical" not in text

    payload = json.loads(text)
    assert payload["schema"] == "coupling_fixed_point_run/1"
    assert payload["outcome"] in {"criterion_met", "iteration_limit_reached"}
    participants = {
        r["problem_id"]
        for iteration in payload["iterations"]
        for r in iteration["results"]
    }
    assert participants == {
        system.diffusivity_problem_id, system.fluid_problem_id,
        system.wall_problem_id, system.thermal_problem_id,
    }
    edges = {
        (d["source_problem_id"], d["source_quantity"],
         d["target_problem_id"], d["target_quantity"])
        for d in payload["plan"]["dependencies"]
    }
    assert len(edges) == 4


@pytest.mark.expensive
def test_l2_an_electro_thermal_record_is_equally_unbranded(et_case):
    """The generic identity is generic in BOTH directions, not just one."""
    payload = et_case[2].to_dict()
    for key in ("schema",):
        assert "electrothermal" not in payload[key]
    assert "electrothermal" not in payload["plan"]["schema"]
    assert "electrothermal" not in payload["iterations"][0]["schema"]
    # The pack's own identifiers legitimately still say what they are — that is
    # payload content, and it is the pack's to name.
    assert any(
        "electrothermal-series" in r["problem_id"]
        for r in payload["iterations"][0]["results"]
    )


# =====================================================================
# §K — fresh-process reconstruction, for BOTH systems
# =====================================================================

_ET_FRESH = """
import json, sys
payload = json.loads(sys.stdin.read())
from engcore.coupling import FixedPointCouplingPlan, execution_order

plan = FixedPointCouplingPlan.from_dict(payload["plan"])
# The participant set is RECOVERED from the run record, not handed in. Every
# participant is solved in every sweep, so the first iteration's results
# enumerate them. `architecture-falsifier` C-6: an injected node list would
# have left prereg §14's "from the records alone" unproven.
recovered_ids = sorted({
    r["problem_id"] for r in payload["run"]["iterations"][0]["results"]
})
print(json.dumps({
    "plan_id": plan.plan_id,
    "schema": plan.to_dict()["schema"],
    "torn": [list(e) for e in plan.torn_endpoints],
    "order": list(execution_order(recovered_ids, plan.uncut)),
    "recovered_ids": recovered_ids,
    "tolerance": [plan.absolute_tolerance.magnitude, plan.absolute_tolerance.units],
    "budget": plan.max_iterations,
    "edges": sorted(
        (d.source_problem_id, d.source_quantity,
         d.target_problem_id, d.target_quantity)
        for d in plan.dependencies
    ),
    "run_outcome": __import__("engcore.coupling", fromlist=["CoupledRun"])
        .CoupledRun.from_dict(payload["run"]).outcome.value,
    "run_sweeps": __import__("engcore.coupling", fromlist=["CoupledRun"])
        .CoupledRun.from_dict(payload["run"]).iterations_run,
    "run_final": sorted(
        (p, q, v.magnitude_in("kelvin"))
        for (p, q), v in __import__("engcore.coupling", fromlist=["CoupledRun"])
        .CoupledRun.from_dict(payload["run"]).final_values.items()
    ),
}))
"""


def _fresh(payload: dict) -> dict:
    completed = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(_ET_FRESH)],
        input=json.dumps(payload), capture_output=True, text=True,
        timeout=300, cwd=str(REPO_ROOT),
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


@pytest.mark.expensive
@pytest.mark.parametrize("which", ["et", "ft"])
def test_k_the_generic_records_reconstruct_in_a_genuinely_fresh_interpreter(
    which, et_case, ft_case
):
    """JSON in; plan, order and outcome out. No hidden Python object survives.

    The pack executors are pack code and are **not** claimed to be serialized —
    what crosses is the plan and the run, which is exactly what the generic
    records promise to carry.
    """
    system, plan_, run = et_case if which == "et" else ft_case
    problems = (
        etc.coupled_problems(system, {"R1": Quantity(10.0, "ohm")})
        if which == "et" else ft_pack.coupled_problems(system)
    )
    fresh = _fresh({"plan": plan_.to_dict(), "run": run.to_dict()})

    # The node set was recovered inside the fresh interpreter, and it is the
    # composition's own — proved against the pack-built problems here, in the
    # parent, where they exist.
    assert fresh["recovered_ids"] == sorted(p.problem_id for p in problems)
    assert fresh["plan_id"] == plan_.plan_id
    assert fresh["schema"] == "coupling_fixed_point_plan/1"
    assert [tuple(e) for e in fresh["torn"]] == list(plan_.torn_endpoints)
    assert tuple(fresh["order"]) == cpl.execution_order(
        [p.problem_id for p in problems], plan_.uncut
    )
    assert fresh["budget"] == plan_.max_iterations
    assert fresh["run_outcome"] == run.outcome.value
    assert fresh["run_sweeps"] == run.iterations_run
    assert len(fresh["edges"]) == len(plan_.dependencies)
    in_process = sorted(
        (p, q, v.magnitude_in(KELVIN)) for (p, q), v in run.final_values.items()
    )
    assert [tuple(row) for row in fresh["run_final"]] == in_process


@pytest.mark.expensive
def test_k2_the_fresh_process_holds_no_reference_to_either_system_pack(et_case):
    """Attack 8: does reconstruction only work because a pack object survived?

    The reconstruction script imports ``engcore.coupling`` and nothing else,
    and the fresh interpreter is asserted never to have imported either system
    pack, either domain, or numpy.
    """
    _, plan_, run = et_case
    script = textwrap.dedent("""
    import json, sys
    payload = json.loads(sys.stdin.read())
    from engcore.coupling import CoupledRun, FixedPointCouplingPlan
    plan = FixedPointCouplingPlan.from_dict(payload["plan"])
    run = CoupledRun.from_dict(payload["run"])
    loaded = sorted(m for m in sys.modules
                    if m.startswith("engcore.systems")
                    or m.startswith("engcore.domains"))
    print(json.dumps({
        "outcome": run.outcome.value,
        "sweeps": run.iterations_run,
        "edges": len(plan.dependencies),
        "domain_modules_imported": loaded,
    }))
    """)
    completed = subprocess.run(
        [sys.executable, "-c", script],
        input=json.dumps({"plan": plan_.to_dict(), "run": run.to_dict()}),
        capture_output=True, text=True, timeout=300, cwd=str(REPO_ROOT),
    )
    assert completed.returncode == 0, completed.stderr
    out = json.loads(completed.stdout)
    assert out["domain_modules_imported"] == []
    assert out["outcome"] == run.outcome.value
    assert out["sweeps"] == run.iterations_run


# =====================================================================
# §H — the numbers did not move
# =====================================================================

@pytest.mark.expensive
def test_h_the_frozen_numerical_baselines_are_unchanged(et_case, ft_case):
    """Prereg §10, the values frozen BEFORE implementation, restated here.

    Not `approx`: these are the exact doubles the baseline commit produced, and
    the milestone's own falsification criterion F1 is that any one of them
    moves. No tolerance is widened, because none is used.
    """
    _, _, et_run = et_case
    assert et_run.outcome is cpl.CouplingOutcome.CRITERION_MET
    assert et_run.iterations_run == 10
    (et_value,) = et_run.final_values.values()
    assert et_value.magnitude_in(KELVIN) == 338.5770175652607
    assert et_run.final_iterate_change.magnitude_in(KELVIN) == 4.7410196657438064e-07

    system, _, ft_run = ft_case
    assert ft_run.outcome is cpl.CouplingOutcome.CRITERION_MET
    assert ft_run.iterations_run == 16
    assert ft_run.final_values[
        (system.diffusivity_problem_id, prop.TEMPERATURE)
    ].magnitude_in(KELVIN) == 362.0282839384463
    assert ft_run.final_iterate_change.magnitude_in(KELVIN) == 5.0614276972282823e-05


@pytest.mark.expensive
def test_h2_the_dependency_order_is_unchanged_for_both_consumers(et_case, ft_case):
    system, plan_, _ = et_case
    problems = etc.coupled_problems(system, {"R1": Quantity(10.0, "ohm")})
    assert cpl.execution_order(
        [p.problem_id for p in problems], plan_.uncut
    ) == (
        "resistance-tcr-R1",
        "electrical_dc:electrothermal-series-R1",
        "thermal-lumped-R1",
    )

    system, plan_, _ = ft_case
    problems = ft_pack.coupled_problems(system)
    assert cpl.execution_order(
        [p.problem_id for p in problems], plan_.uncut
    ) == (
        "fluid-diffusivity-air-like",
        "fluids-transport2d-slab-a",
        "wall-conductance-air-like",
        "thermal-lumped-body-a",
    )
