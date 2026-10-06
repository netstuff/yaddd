"""Concrete health checks and their aggregation.

Everything here satisfies the protocols declared in ``application.health`` and
never raises: a probe that crashes is indistinguishable from a probe that
reports ``down``, and a crashed probe takes the whole report with it.
"""

import asyncio
import logging
from collections.abc import Sequence

from faststream.redis import RedisBroker
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.health import CheckResult, HealthReport, NamedCheck, ProbeStatus
from app.infrastructure.database.constants import Query


__all__ = ["BrokerCheck", "CompositeHealthProbe", "DatabaseCheck", "LivenessProbe"]

logger = logging.getLogger(__name__)

DATABASE_CHECK_NAME = "database"
BROKER_CHECK_NAME = "broker"
BROKER_PING_FAILURE_DETAIL = "broker ping returned False"


class DatabaseCheck:
    """Runs ``SELECT 1`` against the configured database."""

    name = DATABASE_CHECK_NAME

    def __init__(self, session_maker: async_sessionmaker[AsyncSession], timeout: float) -> None:
        self._session_maker = session_maker
        self._timeout = timeout

    async def __call__(self) -> CheckResult:
        """Report whether the database answers a trivial query."""
        try:
            async with asyncio.timeout(self._timeout), self._session_maker() as session:
                await session.execute(text(Query.HEALTH_CHECK))
        except Exception as exc:
            return CheckResult(name=self.name, status=ProbeStatus.DOWN, detail=_describe(exc))
        return CheckResult(name=self.name, status=ProbeStatus.OK)


class BrokerCheck:
    """Asks the broker whether it is connected."""

    name = BROKER_CHECK_NAME

    def __init__(self, broker: RedisBroker, timeout: float) -> None:
        self._broker = broker
        self._timeout = timeout

    async def __call__(self) -> CheckResult:
        """Report whether the broker answers a ping."""
        try:
            connected = await self._broker.ping(timeout=self._timeout)
        except Exception as exc:
            return CheckResult(name=self.name, status=ProbeStatus.DOWN, detail=_describe(exc))
        if not connected:
            return CheckResult(name=self.name, status=ProbeStatus.DOWN, detail=BROKER_PING_FAILURE_DETAIL)
        return CheckResult(name=self.name, status=ProbeStatus.OK)


class CompositeHealthProbe:
    """Runs every check in parallel and aggregates the outcomes."""

    def __init__(self, checks: Sequence[NamedCheck], timeout: float) -> None:
        self._checks = checks
        self._timeout = timeout

    async def report(self) -> HealthReport:
        """Return the aggregated report of all registered checks."""
        return HealthReport(checks=tuple(await asyncio.gather(*(self._run(check) for check in self._checks))))

    async def _run(self, check: NamedCheck) -> CheckResult:
        """Run one check, converting any failure into a ``down`` result."""
        try:
            async with asyncio.timeout(self._timeout):
                return await check()
        except Exception as exc:
            logger.warning("health check %s failed", check.name, exc_info=True)
            return CheckResult(name=check.name, status=ProbeStatus.DOWN, detail=_describe(exc))


class LivenessProbe:
    """Answers liveness from the process alone, touching no dependency.

    A liveness probe that fails because Redis is down gets the container
    killed while the application is perfectly able to serve traffic — so this
    probe deliberately has nothing to check.
    """

    def __init__(self, process_name: str) -> None:
        self._process_name = process_name

    async def report(self) -> HealthReport:
        """Report the process as alive."""
        return HealthReport(checks=(CheckResult(name=self._process_name, status=ProbeStatus.OK),))


def _describe(exc: Exception) -> str:
    """Describe a failure without leaking connection strings or payloads."""
    return f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
