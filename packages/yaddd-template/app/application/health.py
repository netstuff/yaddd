"""Health vocabulary shared by the adapters and the probes.

A probe answers two questions separately:

- **liveness** — is the process itself healthy? Never touches dependencies;
- **readiness** — can the process serve traffic right now? Depends on the
  database and the broker being reachable.

The vocabulary lives here so ``presentation`` can render a report it never
computes, and ``infrastructure`` can produce one without importing a
framework.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol


__all__ = ["Check", "CheckResult", "HealthPayloadKey", "HealthProbe", "HealthReport", "NamedCheck", "ProbeStatus"]


class ProbeStatus(StrEnum):
    """Possible outcomes of a health check."""

    OK = "ok"
    DEGRADED = "degraded"
    DOWN = "down"


class HealthPayloadKey:
    """Keys of the JSON health report payload."""

    STATUS = "status"
    READY = "ready"
    CHECKS = "checks"
    NAME = "name"
    DETAIL = "detail"


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Outcome of a single dependency check."""

    name: str
    status: ProbeStatus
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class HealthReport:
    """Aggregated outcome of every check the probe runs."""

    checks: tuple[CheckResult, ...] = ()

    @property
    def status(self) -> ProbeStatus:
        """Worst status across all checks."""
        if any(check.status == ProbeStatus.DOWN for check in self.checks):
            return ProbeStatus.DOWN
        if any(check.status == ProbeStatus.DEGRADED for check in self.checks):
            return ProbeStatus.DEGRADED
        return ProbeStatus.OK

    @property
    def ready(self) -> bool:
        """True when the process may accept traffic."""
        return self.status != ProbeStatus.DOWN

    def to_payload(self) -> dict[str, Any]:
        """Render the report as a JSON-ready mapping, for non-FastAPI entrypoints."""
        return {
            HealthPayloadKey.STATUS: self.status,
            HealthPayloadKey.READY: self.ready,
            HealthPayloadKey.CHECKS: [
                {
                    HealthPayloadKey.NAME: check.name,
                    HealthPayloadKey.STATUS: check.status,
                    HealthPayloadKey.DETAIL: check.detail,
                }
                for check in self.checks
            ],
        }


class Check(Protocol):
    """A single dependency probe."""

    async def __call__(self) -> CheckResult:
        """Probe the dependency and report its state."""
        ...


class NamedCheck(Check, Protocol):
    """A check that knows its own name, for aggregation into a report."""

    name: str


class HealthProbe(Protocol):
    """Runs every check and aggregates the results."""

    async def report(self) -> HealthReport:
        """Return the current report."""
        ...
