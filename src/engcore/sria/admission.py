"""Admission declarations and the authority that may issue them.

A gateway that accepts any well-formed declaration is not an authority
boundary — it only checks that the caller filled in the right fields. M1.1
adds the missing half: a declaration carries a verifiable issuer, and the
gateway refuses declarations it cannot attribute to a registered authority.

Two semantics are fixed here, and they are the point of this module.

**A declaration is bound to one evidence record.** It carries the
``subject_record_hash`` it was issued for, so an admission granted to one
record cannot be replayed onto another — including onto a different record
that happens to make the identical scientific claim.

**Failing admission is not a scientific verdict.** Refusal, forgery and
malformation are *procedural* outcomes. They are recorded as
:class:`AdmissionAttempt` entries and they leave the evidence's scientific
standing exactly where it was. Only a scientific authority may move evidence
to ``INVALID``, and it does so through an explicit epistemic decision, never
as a side effect of a failed admission.

Scope of the mechanism, stated plainly: the signature is an integrity and
attribution check between components inside one trusted process. It prevents
a component from manufacturing admission through the supported API, and makes
forgery attempts visible in an audit log. It is not a cryptographic security
control and it does not defend against code that can read process memory,
monkey-patch this module, or import private names deliberately. Authority
secrets are per-process and are not persisted, so declarations verify within
the run that issued them; durable, signed admission records are deferred.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping

from ..scientific.serialization import require_schema, schema_string
from .errors import AdmissionAuthorityError, AdmissionError

ADMISSION_SCHEMA = schema_string("sria_admission", 2)
ADMISSION_ATTEMPT_SCHEMA = schema_string("sria_admission_attempt")


class AdmissionOutcome(str, Enum):
    """What happened when admission was attempted.

    All four are procedural facts about the admission process. None of them is
    a statement about whether the science is right.
    """

    ADMITTED = "admitted"
    REFUSED = "refused"            # a real authority declined
    UNAUTHORIZED = "unauthorized"  # issuer could not be verified
    MALFORMED = "malformed"        # declaration did not match its subject


@dataclass(frozen=True)
class AdmissionDeclaration:
    """An Arbiter's decision to admit or decline one evidence record."""

    admitted: bool
    arbiter_id: str
    subject_record_hash: str = ""
    issuer_id: str = ""
    issued_signature: str = ""
    arbiter_version: str = ""
    rationale: str = ""
    criteria_ref: tuple[str, ...] = ()
    decided_at: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.admitted, bool):
            raise AdmissionError("admission must be an explicit bool")
        arbiter = str(self.arbiter_id).strip()
        if not arbiter:
            raise AdmissionError(
                "admission requires an arbiter_id: evidence is never admitted "
                "by nobody"
            )
        object.__setattr__(self, "arbiter_id", arbiter)
        object.__setattr__(self, "criteria_ref", tuple(self.criteria_ref))

    def signing_payload(self) -> dict[str, Any]:
        """The fields an authority signs. Excludes the signature itself."""
        return {
            "admitted": self.admitted,
            "arbiter_id": self.arbiter_id,
            "subject_record_hash": self.subject_record_hash,
            "issuer_id": self.issuer_id,
            "arbiter_version": self.arbiter_version,
            "rationale": self.rationale,
            "criteria_ref": list(self.criteria_ref),
            "decided_at": self.decided_at,
        }

    @property
    def is_signed(self) -> bool:
        return bool(self.issuer_id and self.issued_signature)

    def to_dict(self) -> dict[str, Any]:
        payload = self.signing_payload()
        payload.update(
            {"schema": ADMISSION_SCHEMA, "issued_signature": self.issued_signature}
        )
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AdmissionDeclaration":
        require_schema(payload, ADMISSION_SCHEMA)
        return cls(
            admitted=bool(payload["admitted"]),
            arbiter_id=payload["arbiter_id"],
            subject_record_hash=payload.get("subject_record_hash", ""),
            issuer_id=payload.get("issuer_id", ""),
            issued_signature=payload.get("issued_signature", ""),
            arbiter_version=payload.get("arbiter_version", ""),
            rationale=payload.get("rationale", ""),
            criteria_ref=tuple(payload.get("criteria_ref", ())),
            decided_at=payload.get("decided_at"),
        )


@dataclass(frozen=True)
class AdmissionAttempt:
    """One append-only audit entry for an admission attempt."""

    outcome: AdmissionOutcome
    reason: str = ""
    arbiter_id: str = ""
    issuer_id: str = ""
    subject_record_hash: str = ""
    at: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "outcome", AdmissionOutcome(self.outcome))

    @property
    def succeeded(self) -> bool:
        return self.outcome is AdmissionOutcome.ADMITTED

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": ADMISSION_ATTEMPT_SCHEMA,
            "outcome": self.outcome.value,
            "reason": self.reason,
            "arbiter_id": self.arbiter_id,
            "issuer_id": self.issuer_id,
            "subject_record_hash": self.subject_record_hash,
            "at": self.at,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AdmissionAttempt":
        require_schema(payload, ADMISSION_ATTEMPT_SCHEMA)
        return cls(
            outcome=AdmissionOutcome(payload["outcome"]),
            reason=payload.get("reason", ""),
            arbiter_id=payload.get("arbiter_id", ""),
            issuer_id=payload.get("issuer_id", ""),
            subject_record_hash=payload.get("subject_record_hash", ""),
            at=payload.get("at"),
        )


class AdmissionAuthority:
    """Issues attributable admission declarations.

    M1.1 deliberately implements only issuance and verification — no admission
    *policy*. Deciding whether the critics justify admission is the Arbiter's
    job and belongs to a later milestone.
    """

    def __init__(self, authority_id: str, secret: str | None = None) -> None:
        authority_id = str(authority_id).strip()
        if not authority_id:
            raise AdmissionAuthorityError("admission authority requires an id")
        self._authority_id = authority_id
        self._secret = secret if secret is not None else secrets.token_hex(32)

    @property
    def authority_id(self) -> str:
        return self._authority_id

    def _sign(self, payload: Mapping[str, Any]) -> str:
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hmac.new(
            str(self._secret).encode("utf-8"),
            blob.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def issue(
        self,
        *,
        admitted: bool,
        subject_record_hash: str,
        arbiter_id: str | None = None,
        arbiter_version: str = "",
        rationale: str = "",
        criteria_ref: Iterable[str] = (),
        decided_at: str | None = None,
    ) -> AdmissionDeclaration:
        """Produce a signed declaration bound to one evidence record."""
        subject = str(subject_record_hash).strip()
        if not subject:
            raise AdmissionAuthorityError(
                "an admission declaration must name the evidence record it "
                "applies to, otherwise it can be replayed onto another record"
            )
        unsigned = AdmissionDeclaration(
            admitted=admitted,
            arbiter_id=arbiter_id or self._authority_id,
            subject_record_hash=subject,
            issuer_id=self._authority_id,
            arbiter_version=arbiter_version,
            rationale=rationale,
            criteria_ref=tuple(criteria_ref),
            decided_at=decided_at,
        )
        signature = self._sign(unsigned.signing_payload())
        return AdmissionDeclaration(
            admitted=unsigned.admitted,
            arbiter_id=unsigned.arbiter_id,
            subject_record_hash=unsigned.subject_record_hash,
            issuer_id=unsigned.issuer_id,
            issued_signature=signature,
            arbiter_version=unsigned.arbiter_version,
            rationale=unsigned.rationale,
            criteria_ref=unsigned.criteria_ref,
            decided_at=unsigned.decided_at,
        )

    def verifies(self, declaration: AdmissionDeclaration) -> bool:
        if declaration.issuer_id != self._authority_id:
            return False
        expected = self._sign(declaration.signing_payload())
        return hmac.compare_digest(expected, declaration.issued_signature or "")


class AdmissionAuthorityRegistry:
    """The set of authorities a gateway is willing to trust."""

    def __init__(self, authorities: Iterable[AdmissionAuthority] = ()) -> None:
        self._authorities: dict[str, AdmissionAuthority] = {}
        for authority in authorities:
            self.register(authority)

    def register(self, authority: AdmissionAuthority) -> None:
        if not isinstance(authority, AdmissionAuthority):
            raise AdmissionAuthorityError(
                "only an AdmissionAuthority may be registered"
            )
        self._authorities[authority.authority_id] = authority

    @property
    def authority_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._authorities))

    def verify(
        self, declaration: AdmissionDeclaration, *, subject_record_hash: str
    ) -> AdmissionAttempt:
        """Check issuer and binding. Returns the attempt; never raises."""
        base = {
            "arbiter_id": declaration.arbiter_id,
            "issuer_id": declaration.issuer_id,
            "subject_record_hash": declaration.subject_record_hash,
            "at": declaration.decided_at,
        }

        if not declaration.is_signed:
            return AdmissionAttempt(
                outcome=AdmissionOutcome.UNAUTHORIZED,
                reason="declaration carries no issuer signature",
                **base,
            )
        authority = self._authorities.get(declaration.issuer_id)
        if authority is None:
            return AdmissionAttempt(
                outcome=AdmissionOutcome.UNAUTHORIZED,
                reason=f"issuer {declaration.issuer_id!r} is not registered",
                **base,
            )
        if not authority.verifies(declaration):
            return AdmissionAttempt(
                outcome=AdmissionOutcome.UNAUTHORIZED,
                reason=f"signature does not verify for issuer "
                f"{declaration.issuer_id!r}",
                **base,
            )
        if declaration.subject_record_hash != subject_record_hash:
            return AdmissionAttempt(
                outcome=AdmissionOutcome.MALFORMED,
                reason=(
                    "declaration was issued for a different evidence record "
                    f"({declaration.subject_record_hash[:12]}… != "
                    f"{subject_record_hash[:12]}…)"
                ),
                **base,
            )
        if not declaration.admitted:
            return AdmissionAttempt(
                outcome=AdmissionOutcome.REFUSED,
                reason=declaration.rationale or "authority declined admission",
                **base,
            )
        return AdmissionAttempt(
            outcome=AdmissionOutcome.ADMITTED,
            reason=declaration.rationale or "admitted",
            **base,
        )
