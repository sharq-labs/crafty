# Release 1 scientific semantics

These non-equivalences are load-bearing. Release 1 code, examples, and claims
must preserve them.

| Non-equivalence | Release 1 meaning |
|---|---|
| Candidate != Twin | A Candidate is a declared choice set referencing one exact Twin. It is not the represented system itself. |
| Twin != Model | A Twin represents a specific object/system/candidate and may reference models; it is not an equation or model definition. |
| Model != Solver | A Model declares scientific relationships and validity; a Solver is an execution mechanism for a compatible problem/model. |
| Study != Result | A Study declares an inquiry and execution context; a Result is evidence returned by an execution. |
| Result != Evaluation | A ScientificResult records scientific output and provenance; a DesignEvaluation attributes that result to an exact Candidate, Twin, and design space. |
| Evaluation != Target PASS/FAIL | An evaluation may be attributable and eligible while failing a declared target. Target failure is not scientific invalidity. |
| SelectionEligibility != Target PASS | Eligibility permits declared comparison/selection. It does not assert target satisfaction, safety, feasibility, optimality, or truth. |
| Memory retention != scientific truth | Retention is a declared policy decision over attributable eligible observations. Memory does not certify the evidence as universally true. |
| Prediction != evidence | A prediction may motivate an inquiry; only an executed, attributable observation becomes new scientific evidence. |
| Decision provenance != scientific evidence | A decision identity explains why a Study was selected. It cannot substitute for a measured or computed ScientificResult. |
| Numerical verification != physical validation | Numerical checks establish properties of an implementation/reference solution within scope. They do not establish agreement with the physical world. |
| Physical validation != safety certification | Agreement with physical evidence does not by itself establish safe operation, regulatory approval, or certification. |
| Synthetic closed-loop execution != real-world discovery | The D4/D7 cycle is a real typed software execution over a synthetic analytic reference. It is not physical-world discovery or experimental validation. |

Additional Release 1 distinctions follow from the same rule: compatibility is
not scientific validity; reported uncertainty is not computed uncertainty;
deterministic replay is not independent scientific replication; selected is
not automatically valid, feasible, adequate, converged, optimal, safe, or
true.

The honest default for unavailable uncertainty is `UNKNOWN`. A validation
report claims only the levels its checks attained, including explicit
`NOT_RUN`. Fail-closed errors are part of the scientific behavior; release
orchestration does not infer missing evidence or silently continue after an
identity mismatch.
