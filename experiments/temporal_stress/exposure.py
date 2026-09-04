"""A4/A6 — two histories, one current state, different accumulated exposure.

The claim under test
--------------------
``State(t)`` may be insufficient to reconstruct ``History[0:t]``, and the
insufficiency is *scientific*, not a storage inconvenience.

The probe, and why it is this small
-----------------------------------
One lumped body (consumer C1), two two-segment heat schedules over the same
physical interval::

    H_A:  Q = Q_hot   on [0, t_switch),   Q = Q_cool  on [t_switch, t_end]
    H_B:  Q = Q_cool  on [0, t_switch),   Q = Q_hot'  on [t_switch, t_end]

``Q_hot'`` is solved for **exactly** — the lumped balance is linear in ``Q``,
so the closing power that lands H_B on H_A's final temperature is a closed-form
root, not a search — so that both schedules end at the *same temperature at the
same physical time*.

The accumulated exposure is a single scalar::

    E(t_end) = ∫₀^{t_end} max(T(τ) − T_ref, 0) dτ        [K·s]

``max(T − T_ref, 0)`` is chosen because it is the smallest function that is
(a) monotone in temperature, (b) not linear, so ``∫f(T)`` is not recoverable
from ``∫T``, and (c) obviously not a physical damage law. **This probe models
no degradation.** It makes no claim about wear, fatigue, aging, creep or
lifetime, and nothing here should be read as one. It is an instrument for a
*representation* question: does a scalar functional of the path differ between
two paths with identical endpoints?

Each segment is advanced with C1's own closed form, which is exact for a
constant heat input over an interval — the realization's declared assumption —
so the segment chain introduces no time-discretisation error of its own.

The distinction this module exists to keep straight
---------------------------------------------------
**A stored solver trajectory is not scientific history.** They are separated
here by measurement, not by assertion:

* the *solver trajectory* is whatever samples a particular integrator happened
  to emit; refine or coarsen the sampling and you get a different array;
* the *scientific history* is the schedule ``Q(τ)`` and the path ``T(τ)`` it
  implies; refine the sampling and the exposure integral converges to the same
  number.

:func:`sampling_independence` measures exactly that: the same history evaluated
at two sampling densities two orders of magnitude apart. If exposure were an
artefact of the trajectory it would move; it does not.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from engcore.domains import thermal_lumped as lump
from engcore.scientific.units.quantity import Quantity

__all__ = [
    "Segment",
    "Schedule",
    "ExposureComparison",
    "SamplingIndependence",
    "closing_power_w",
    "matched_histories",
    "compare_histories",
    "sampling_independence",
]

KELVIN = "kelvin"
SECOND = "second"
WATT = "watt"
EXPOSURE_UNIT = "kelvin * second"

#: The exposure threshold. A declared constant of the instrument, not physics.
REFERENCE_TEMPERATURE_K = 305.0


@dataclass(frozen=True)
class Segment:
    """One interval of constant imposed heat — C1's realization assumption."""

    duration_s: float
    heat_w: float

    def __post_init__(self) -> None:
        if self.duration_s <= 0.0 or not math.isfinite(self.duration_s):
            raise ValueError("segment duration must be finite and positive")
        if not math.isfinite(self.heat_w):
            raise ValueError("segment heat input must be finite")


@dataclass(frozen=True)
class Schedule:
    """A named piecewise-constant heat schedule on one body."""

    label: str
    segments: tuple[Segment, ...]

    @property
    def total_duration_s(self) -> float:
        return sum(s.duration_s for s in self.segments)


def _body(*, duration_s: float, initial_k: float = 300.0) -> lump.ThermalBody:
    return lump.ThermalBody(
        body_id="exposure-body",
        heat_capacity=Quantity(400.0, "joule/kelvin"),
        ambient_conductance=Quantity(2.0, "watt/kelvin"),
        ambient_temperature=Quantity(300.0, KELVIN),
        initial_temperature=Quantity(initial_k, KELVIN),
        duration=Quantity(duration_s, SECOND),
    )


def _advance(body: lump.ThermalBody, *, start_k: float, segment: Segment) -> float:
    """One segment, advanced by C1's own solver through the full lifecycle.

    Not re-implemented here. The body is rebuilt with this segment's initial
    temperature and duration and handed to ``LumpedThermalSolver``, so the
    number this returns is the consumer's number, produced by the consumer's
    contract path.
    """
    segment_body = lump.ThermalBody(
        body_id=body.body_id,
        heat_capacity=body.heat_capacity,
        ambient_conductance=body.ambient_conductance,
        ambient_temperature=body.ambient_temperature,
        initial_temperature=Quantity(start_k, KELVIN),
        duration=Quantity(segment.duration_s, SECOND),
    )
    problem = lump.build_lumped_thermal_problem(
        segment_body, problem_id=f"exposure-{id(segment)}"
    )
    solver = lump.LumpedThermalSolver()
    solver.bind_body(
        segment_body, problem.problem_id, heat_input=Quantity(segment.heat_w, WATT)
    )
    prepared = solver.prepare(problem)
    raw = solver.solve(prepared)
    metrics = solver.extract_metrics(prepared, raw)
    return metrics[lump.TEMPERATURE_METRIC].magnitude_in(KELVIN)


def _temperature_at(
    body: lump.ThermalBody,
    *,
    start_k: float,
    heat_w: float,
    elapsed_s: float,
    constants: tuple[float, float, float] | None = None,
) -> float:
    """The closed form, evaluated inside one segment.

    Used only to *sample* a segment for the exposure integral. The segment
    endpoints themselves always come from :func:`_advance`, i.e. from the
    consumer's solver, and a test asserts the two agree.

    ``constants`` is ``(tau_s, ambient_k, conductance_w_per_k)`` hoisted by the
    caller. The body's own accessors each perform a unit conversion, which is
    correct and which must not be paid once per sample of a dense path — the
    unit-carrying values are read once per *schedule*, not once per point.
    """
    if constants is None:
        constants = (body.time_constant_s, body.ambient_k, body.conductance_w_per_k)
    tau, ambient_k, conductance = constants
    steady = ambient_k + heat_w / conductance
    return steady + (start_k - steady) * math.exp(-elapsed_s / tau)


def _path(
    body: lump.ThermalBody, schedule: Schedule, *, samples_per_segment: int
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Dense (t, T) samples of one schedule. Domain-local, never a record."""
    constants = (body.time_constant_s, body.ambient_k, body.conductance_w_per_k)
    times: list[float] = []
    temperatures: list[float] = []
    clock = 0.0
    state = body.initial_k
    for segment in schedule.segments:
        for index in range(samples_per_segment + 1):
            elapsed = segment.duration_s * index / samples_per_segment
            times.append(clock + elapsed)
            temperatures.append(
                _temperature_at(
                    body,
                    start_k=state,
                    heat_w=segment.heat_w,
                    elapsed_s=elapsed,
                    constants=constants,
                )
            )
        state = _advance(body, start_k=state, segment=segment)
        clock += segment.duration_s
    return tuple(times), tuple(temperatures)


def _exposure(
    times: Sequence[float],
    temperatures: Sequence[float],
    *,
    reference_k: float = REFERENCE_TEMPERATURE_K,
) -> float:
    """``∫ max(T − T_ref, 0) dt`` by trapezoid. Units K·s."""
    total = 0.0
    for index in range(1, len(times)):
        dt = times[index] - times[index - 1]
        if dt <= 0.0:
            continue
        left = max(temperatures[index - 1] - reference_k, 0.0)
        right = max(temperatures[index] - reference_k, 0.0)
        total += 0.5 * (left + right) * dt
    return total


def closing_power_w(
    body: lump.ThermalBody,
    *,
    start_k: float,
    duration_s: float,
    target_k: float,
) -> float:
    """The constant heat that carries ``start_k`` to ``target_k`` in ``duration_s``.

    Exact, not searched. For the linear balance,

        T(t) = T_amb + Q/hA + (T0 − T_amb − Q/hA) e^{−t/τ}

    is affine in ``Q``, so inverting it is arithmetic::

        Q = hA · [ (T_target − T_amb) − (T0 − T_amb) e ] / (1 − e)

    Using a root finder here would have made the matched endpoint an
    approximation, and the whole probe rests on the two histories genuinely
    ending at the same state.
    """
    decay = math.exp(-duration_s / body.time_constant_s)
    numerator = (target_k - body.ambient_k) - (start_k - body.ambient_k) * decay
    return body.conductance_w_per_k * numerator / (1.0 - decay)


@dataclass(frozen=True)
class ExposureComparison:
    """Two histories, their endpoints, and their exposures."""

    label_a: str
    label_b: str
    total_duration_s: float
    final_temperature_a_k: float
    final_temperature_b_k: float
    peak_temperature_a_k: float
    peak_temperature_b_k: float
    exposure_a_k_s: float
    exposure_b_k_s: float
    schedule_a: Schedule
    schedule_b: Schedule

    @property
    def endpoint_difference_k(self) -> float:
        return abs(self.final_temperature_a_k - self.final_temperature_b_k)

    @property
    def exposure_difference_k_s(self) -> float:
        return abs(self.exposure_a_k_s - self.exposure_b_k_s)

    @property
    def exposure_relative_difference(self) -> float:
        scale = max(self.exposure_a_k_s, self.exposure_b_k_s)
        if scale == 0.0:
            return 0.0
        return self.exposure_difference_k_s / scale


def matched_histories(
    *,
    t_switch_s: float = 300.0,
    t_end_s: float = 600.0,
    hot_w: float = 40.0,
    cool_w: float = 4.0,
) -> tuple[lump.ThermalBody, Schedule, Schedule]:
    """Two schedules on one body, guaranteed to meet at ``t_end_s``.

    H_A is hot-then-cool. H_B starts cool at the same power and closes with
    whatever constant power lands it on H_A's final temperature. Because the
    balance is linear that closing power is computed, not tuned.
    """
    body = _body(duration_s=t_end_s)
    schedule_a = Schedule(
        "hot-then-cool",
        (Segment(t_switch_s, hot_w), Segment(t_end_s - t_switch_s, cool_w)),
    )
    # Where H_A ends.
    state = body.initial_k
    for segment in schedule_a.segments:
        state = _advance(body, start_k=state, segment=segment)
    target_k = state

    # Where H_B stands after its cool first segment.
    first = Segment(t_switch_s, cool_w)
    midpoint = _advance(body, start_k=body.initial_k, segment=first)
    closing = closing_power_w(
        body,
        start_k=midpoint,
        duration_s=t_end_s - t_switch_s,
        target_k=target_k,
    )
    schedule_b = Schedule(
        "cool-then-hot", (first, Segment(t_end_s - t_switch_s, closing))
    )
    return body, schedule_a, schedule_b


def compare_histories(
    *, samples_per_segment: int = 4000, **kwargs
) -> ExposureComparison:
    """Execute both histories and compare endpoint against exposure."""
    body, schedule_a, schedule_b = matched_histories(**kwargs)
    times_a, temps_a = _path(body, schedule_a, samples_per_segment=samples_per_segment)
    times_b, temps_b = _path(body, schedule_b, samples_per_segment=samples_per_segment)
    return ExposureComparison(
        label_a=schedule_a.label,
        label_b=schedule_b.label,
        total_duration_s=schedule_a.total_duration_s,
        final_temperature_a_k=temps_a[-1],
        final_temperature_b_k=temps_b[-1],
        peak_temperature_a_k=max(temps_a),
        peak_temperature_b_k=max(temps_b),
        exposure_a_k_s=_exposure(times_a, temps_a),
        exposure_b_k_s=_exposure(times_b, temps_b),
        schedule_a=schedule_a,
        schedule_b=schedule_b,
    )


@dataclass(frozen=True)
class SamplingIndependence:
    """Exposure of ONE history evaluated at two sampling densities."""

    coarse_samples: int
    fine_samples: int
    exposure_coarse_k_s: float
    exposure_fine_k_s: float

    @property
    def relative_difference(self) -> float:
        scale = max(abs(self.exposure_fine_k_s), 1e-30)
        return abs(self.exposure_coarse_k_s - self.exposure_fine_k_s) / scale


def sampling_independence(
    *, coarse: int = 100, fine: int = 20000
) -> SamplingIndependence:
    """Separate scientific history from stored solver trajectory.

    The same physical history is sampled 200× more densely. A quantity that is
    a property of the *history* converges; a quantity that is an artefact of
    the *stored trajectory* would not. Exposure converges, so it is the former
    — which is why "we already keep a trajectory" is not an answer to the
    history question, and why "history is just a big array" is not either.
    """
    body, schedule_a, _ = matched_histories()
    times_c, temps_c = _path(body, schedule_a, samples_per_segment=coarse)
    times_f, temps_f = _path(body, schedule_a, samples_per_segment=fine)
    return SamplingIndependence(
        coarse_samples=len(times_c),
        fine_samples=len(times_f),
        exposure_coarse_k_s=_exposure(times_c, temps_c),
        exposure_fine_k_s=_exposure(times_f, temps_f),
    )
