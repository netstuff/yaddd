"""Unit tests: health vocabulary, concrete checks and their aggregation."""

import asyncio
from pathlib import Path

import pytest
from faststream.redis import RedisBroker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.application.health import CheckResult, HealthPayloadKey, HealthReport, ProbeStatus
from app.infrastructure.health import (
    BROKER_CHECK_NAME,
    DATABASE_CHECK_NAME,
    BrokerCheck,
    CompositeHealthProbe,
    DatabaseCheck,
    LivenessProbe,
)
from tests.shared.constants import (
    API_PROCESS_NAME,
    TEST_CHECK_EXPLODING,
    TEST_CHECK_SLOW,
    TEST_CHECK_WORKING,
    UNREACHABLE_BROKER_URL,
)


class WorkingCheck:
    name: str = TEST_CHECK_WORKING

    def __init__(self, status: ProbeStatus = ProbeStatus.OK) -> None:
        self._status: ProbeStatus = status

    async def __call__(self) -> CheckResult:
        return CheckResult(name=self.name, status=self._status)


class ExplodingCheck:
    name: str = TEST_CHECK_EXPLODING

    async def __call__(self) -> CheckResult:
        raise ConnectionError("connection refused")


class SlowCheck:
    name: str = TEST_CHECK_SLOW

    def __init__(self, delay: float) -> None:
        self._delay = delay

    async def __call__(self) -> CheckResult:
        await asyncio.sleep(self._delay)
        return CheckResult(name=self.name, status=ProbeStatus.OK)


def test_report_without_checks_is_ok() -> None:
    assert HealthReport().status == ProbeStatus.OK
    assert HealthReport().ready


def test_report_takes_the_worst_status() -> None:
    degraded = HealthReport(
        checks=(
            CheckResult("a", ProbeStatus.OK),
            CheckResult("b", ProbeStatus.DEGRADED),
            CheckResult("c", ProbeStatus.DOWN),
        ),
    )

    assert degraded.status == ProbeStatus.DOWN
    assert not degraded.ready


def test_degraded_is_still_ready() -> None:
    report = HealthReport(checks=(CheckResult("a", ProbeStatus.OK), CheckResult("b", ProbeStatus.DEGRADED)))

    assert report.status == ProbeStatus.DEGRADED
    assert report.ready


def test_report_renders_a_json_payload() -> None:
    report = HealthReport(checks=(CheckResult(DATABASE_CHECK_NAME, ProbeStatus.OK),))

    assert report.to_payload() == {
        HealthPayloadKey.STATUS: ProbeStatus.OK,
        HealthPayloadKey.READY: True,
        HealthPayloadKey.CHECKS: [
            {
                HealthPayloadKey.NAME: DATABASE_CHECK_NAME,
                HealthPayloadKey.STATUS: ProbeStatus.OK,
                HealthPayloadKey.DETAIL: None,
            }
        ],
    }


async def test_composite_aggregates_every_check() -> None:
    probe = CompositeHealthProbe(checks=(WorkingCheck(), WorkingCheck(ProbeStatus.DEGRADED)), timeout=1.0)

    report = await probe.report()

    assert [check.name for check in report.checks] == [TEST_CHECK_WORKING, TEST_CHECK_WORKING]
    assert report.status == ProbeStatus.DEGRADED


async def test_composite_turns_exceptions_into_down() -> None:
    probe = CompositeHealthProbe(checks=(WorkingCheck(), ExplodingCheck()), timeout=1.0)

    report = await probe.report()

    failing = next(check for check in report.checks if check.name == TEST_CHECK_EXPLODING)
    assert failing.status == ProbeStatus.DOWN
    assert failing.detail is not None
    assert report.status == "down"
    assert not report.ready


async def test_composite_turns_timeouts_into_down() -> None:
    probe = CompositeHealthProbe(checks=(SlowCheck(delay=1.0),), timeout=0.05)

    report = await probe.report()

    assert report.checks[0].status == ProbeStatus.DOWN


async def test_database_check_reports_ok(session_maker: async_sessionmaker[AsyncSession]) -> None:
    check = DatabaseCheck(session_maker, timeout=1.0)

    assert await check() == CheckResult(name=DATABASE_CHECK_NAME, status=ProbeStatus.OK)


async def test_database_check_reports_down_when_unreachable(tmp_path: Path) -> None:
    unreachable = async_sessionmaker(
        create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'missing' / 'db.sqlite3'}"),
        expire_on_commit=False,
    )
    check = DatabaseCheck(unreachable, timeout=1.0)

    result = await check()

    assert result.status == ProbeStatus.DOWN
    assert result.detail is not None


async def test_broker_check_reports_down_without_redis() -> None:
    broker = RedisBroker(url=UNREACHABLE_BROKER_URL)

    result = await BrokerCheck(broker, timeout=0.2)()

    assert result.name == BROKER_CHECK_NAME
    assert result.status == ProbeStatus.DOWN
    assert result.detail is not None


async def test_liveness_never_touches_a_dependency() -> None:
    report = await LivenessProbe(API_PROCESS_NAME).report()

    assert report.status == ProbeStatus.OK
    assert report.ready
    assert [check.name for check in report.checks] == [API_PROCESS_NAME]


@pytest.mark.parametrize("checks", [(), (WorkingCheck(),)])
async def test_probe_handles_an_empty_check_list(checks: tuple[WorkingCheck, ...]) -> None:
    assert (await CompositeHealthProbe(checks=checks, timeout=1.0).report()).ready
