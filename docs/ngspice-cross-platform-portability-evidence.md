# NGSPICE-CROSS-PLATFORM-PORTABILITY — Evidence

**Milestone:** `ngspice-cross-platform-portability`
**Branch:** `ngspice-cross-platform-portability`, based on `min-cross-domain-foundation` @ `62e5915`
**Environment:** native Linux Cloud, Python 3.11.15, `ngspice-42` at `/usr/bin/ngspice`
**Date:** 2026-09-03

This is a portability/reproducibility correction, not an architecture change. It
touches exactly one production file — `NgspiceInvocation`'s executable
discovery in `src/engcore/domains/electrical/ngspice.py` — plus the four test
files whose static "nothing under `src/` moved" guards were written to protect
*earlier* milestones and needed a one-line, documented exception for this one.

## 1. Measured root cause (not "Windows/WSL assumptions" taken on faith)

The prior Foundation cycle's report of "2002 passed, 12 failed, 14 errors" was
re-measured from scratch. Before any edit, `pytest tests/test_heterogeneous_ngspice.py -q`
on this native-Linux environment produced **exactly** 12 failed + 14 errors —
confirming the count, not yet the cause.

Every one of the 26 failing/erroring tests traced to the same single line, via
the same traceback shape:

```
self = NgspiceInvocation(command=('wsl.exe', '-e', 'ngspice'), timeout_seconds=60.0)
    def probe_version(self) -> str:
        ...
        except FileNotFoundError as exc:
>           raise NgspiceUnavailable(
                f"could not launch the ngspice provider as {self.command!r}"
            ) from exc
E           src.engcore.domains.electrical.ngspice.NgspiceUnavailable: could not launch the ngspice provider as ('wsl.exe', '-e', 'ngspice')
```

`NgspiceInvocation.command` defaulted to the literal tuple
`("wsl.exe", "-e", "ngspice")` — a hard-coded reference to the Windows-Subsystem-
for-Linux launcher, which does not exist as a binary on native Linux. Every test
that constructed a default `NgspiceInvocation()` (directly, via
`from_environment()`, or via `NgspiceDCSolver()`'s own default) hit
`subprocess.run(["wsl.exe", ...])`, got a real `FileNotFoundError` from the OS,
and the adapter correctly turned that into `NgspiceUnavailable` — the adapter's
own execution-failure handling was working exactly as designed; the input to
it was wrong for this platform.

This was **not**: a wrong binary name, a missing CLI flag, an output-parsing
mismatch for ngspice-42's format, a working-directory assumption, or a timeout.
`ngspice --version` and `ngspice -b` both work fine and unmodified against the
production parsing code (`parse_print_output`, the version regex) once they are
actually invoked — confirmed by every test passing once only the invocation's
default command changed. The failure lived entirely in the execution-mechanics
layer (`NgspiceInvocation.command`'s default), not in the provider adapter's
translation or parsing logic, and not in test harness/fixture code beyond one
test (`test_j`, below) that hard-coded the same assumption.

## 2. The fix

`src/engcore/domains/electrical/ngspice.py`:

- Added `_discover_command()`: `shutil.which("ngspice")` first — capability
  discovery, identical on Linux, macOS and Windows — returning `(native_path,)`
  when found. Only when nothing is discoverable does it fall back to
  `("wsl.exe", "-e", "ngspice")`, preserving the existing Windows-via-WSL route
  structurally (untestable here, not removed).
- `NgspiceInvocation.command`'s dataclass default changed from the literal WSL
  tuple to `field(default_factory=_discover_command)`, so both `NgspiceInvocation()`
  and `NgspiceInvocation.from_environment()` (which calls `cls()` when
  `CRAFTY_NGSPICE_ARGV` is unset) discover the same way and stay equal, per
  `test_j2_the_invocation_is_configuration_and_reads_the_environment`.
- No change to: netlist emission, output parsing, the admission relations,
  `build_validation_report`, `SolverIdentity`'s fields, or any tolerance.
  `SolverIdentity` still carries only `solver_id`/`version`/`backend` — the
  discovered route (native vs. WSL) is `NgspiceInvocation` configuration, never
  serialized, exactly as before.
- Two docstring updates (module-level and on `NgspiceInvocation`) replacing
  prose that stated "this machine reaches ngspice through WSL" as if that were
  a fixed fact, with prose describing discovery between the two supported
  routes.

`tests/test_heterogeneous_ngspice.py`:

- `test_j_relocating_the_provider_leaves_the_result_byte_identical` hard-coded
  `("wsl.exe", "-e", "ngspice")` for *both* of its two argv routes to the "same"
  provider — making the one test of relocation-invariance itself unrunnable
  anywhere but a WSL-equipped Windows machine. Rewritten to use whatever
  `NgspiceInvocation()` discovers as the "direct" route, and a
  `sys.executable -c "os.execvp(...)"` re-exec wrapper as the "wrapped" route —
  a platform-neutral way to reach the identical binary through a structurally
  different argv, with no dependency on a shell, WSL, or one OS. The assertion
  (`direct.invocation != wrapped.invocation` and byte-identical serialized
  results) is unchanged.

`tests/test_executable_scientific_spec.py`, `tests/test_cross_domain_coverage.py`,
`tests/test_exec_spec_structured_input.py`:

- Each carries a static architecture-fitness guard, written for an *earlier*
  milestone, asserting `git diff --name-only HEAD -- src/...` is empty — i.e.
  "this earlier milestone touched nothing under `src/`" (true when each was
  written, and still true of what each milestone itself changed). None of them
  anticipated a later, separate portability milestone legitimately needing to
  touch `ngspice.py`. Each guard now excludes exactly
  `src/engcore/domains/electrical/ngspice.py` from its comparison, with a
  comment naming this milestone and this document, and continues to fail if
  any *other* file under its guarded path changes.

## 3. Before / after counts

| Suite | Before | After |
|---|---|---|
| `tests/test_heterogeneous_ngspice.py` | 12 failed, 14 passed, 14 errors | **40 passed** |
| `test_executable_scientific_spec.py` + `test_min_cross_domain_foundation.py` + `test_hostile_core_domain_stress.py` + `test_cross_domain_coverage.py` | 3 failed (post-fix-of-ngspice.py, pre-fix-of-guards), 187 passed | **190 passed** |
| FAST (`-m "not expensive"`) | not separately re-measured pre-fix (subsumes the above) | **1464 passed, 565 deselected, 0 failed** |
| FULL (no marker selection) | not separately re-measured pre-fix; prior cycle reported 2002 passed / 12 failed / 14 errors | **2029 passed, 0 failed, 0 errors** (1082s / 18m02s) |

The FULL count (2029) is close to but not identical to the prior cycle's
reported total (2002+12+14 = 2028); the one-test difference was not tracked
down further since it is not attributable to this milestone — this milestone
added zero new test functions (`test_j` was rewritten, not added, and the
guard-test edits added no new `test_` functions either).

Zero unexpected failures. Zero unexpected errors. Zero skips introduced by this
change (`test_j` was fixed, not skipped; no test anywhere was marked `xfail`
or given a Linux-specific skip).

## 4. Differential provider proof (unchanged tolerances)

Re-ran the full differential/heterogeneous set from `docs/heterogeneous-ngspice-evidence.md`:

```
tests/test_heterogeneous_ngspice.py::test_c_native_and_ngspice_agree_within_the_preregistered_tolerance PASSED
tests/test_heterogeneous_ngspice.py::test_c2_the_provider_answer_satisfies_craftys_own_assembled_equations PASSED
tests/test_heterogeneous_ngspice.py::test_e_case_a_coupled_results_agree PASSED
tests/test_heterogeneous_ngspice.py::test_e2_case_e_two_stage_coupled_results_agree PASSED
tests/test_heterogeneous_ngspice.py::test_e3_the_electrical_quantities_at_the_fixed_point_agree PASSED
tests/test_heterogeneous_ngspice.py::test_e4_iteration_counts_are_recorded_not_required PASSED
```

against the module's original preregistered tolerances, byte-unchanged by this
milestone:

```python
REL_TOL = 1e-9
ABS_FLOOR = 1e-12
COUPLED_T_ATOL = 1e-4
COUPLED_REL_TOL = 1e-6
```

Native MNA and the real ngspice-42 process (now reached directly, not through
WSL) still agree within these tolerances on both the standalone electrical
result and the coupled electro-thermal fixed point. The provider-element
admission relations (`I ≈ V_drop/R`, `P ≈ V_drop·I`) and the singular-circuit
precondition check are exercised unchanged by
`test_p*` / `test_g5_the_singular_precondition_is_detected_on_both_paths`, all
passing.

**Zero scientific/numerical baseline drift.** The fix is entirely in
`NgspiceInvocation.command`'s default value; no metric, tolerance, validation
rule, or `SolverIdentity` field changed.

## 5. What was deliberately not touched

- `SolverSettings`, `SolverIdentity`, `ScientificProblem`/`ModelReference` — no
  platform or execution-route information was ever, or is now, encoded in any
  of these.
- The Windows-via-WSL route (`("wsl.exe", "-e", "ngspice")`) — kept as the
  fallback in `_discover_command()` for a machine with no native `ngspice` on
  `PATH`. Not exercised on this Linux environment; preserved structurally per
  the milestone's explicit instruction not to remove or break a path that
  cannot be tested here.
- `CRAFTY_NGSPICE_ARGV` override semantics — unchanged; still takes priority
  over discovery.
