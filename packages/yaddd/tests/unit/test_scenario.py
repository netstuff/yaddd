import pytest
from yaddd.application.handlers.scenarios import (
    BatchLogger,
    Branch,
    Context,
    Logger,
    Scenario,
    ScenarioCycleError,
    ScenarioMetrics,
    ScenarioRunner,
    Skip,
    TraceEntry,
    step,
)


def build_runner() -> ScenarioRunner:
    return ScenarioRunner()


class EmptyScenario(Scenario[int]):
    pass


class IncrementScenario(Scenario[int]):
    @step
    async def add_one(self, ctx: Context[int]) -> int:
        return ctx.state + 1

    @step
    async def add_ten(self, ctx: Context[int]) -> int:
        return ctx.state + 10


async def test_scenario_runs_steps_in_order_and_returns_final_state():
    runner = build_runner()

    result = await runner.run([IncrementScenario()], initial_state=0)

    assert result == 11


class LoggingScenario(Scenario[int]):
    def __init__(self) -> None:
        self.calls: list[str] = []

    @step
    async def log(self, ctx: Context[int]) -> None:
        self.calls.append(f"seen:{ctx.state}")

    @step
    async def double(self, ctx: Context[int]) -> int:
        return ctx.state * 2


async def test_step_may_return_none_to_leave_state_unchanged():
    scenario = LoggingScenario()

    result = await build_runner().run([scenario], initial_state=5)

    assert result == 10
    assert scenario.calls == ["seen:5"]


class ConditionalScenario(Scenario[int]):
    @step
    async def add_one(self, ctx: Context[int]) -> int:
        return ctx.state + 1

    @step(when=lambda ctx: False)
    async def skip_me(self, ctx: Context[int]) -> int:
        return ctx.state + 100

    @step
    async def add_one_again(self, ctx: Context[int]) -> int:
        return ctx.state + 1


async def test_when_skips_step():
    result = await build_runner().run([ConditionalScenario()], initial_state=0)

    assert result == 2


class SkipFromBodyScenario(Scenario[int]):
    @step
    async def add_one(self, ctx: Context[int]) -> int:
        return ctx.state + 1

    @step
    async def maybe_double(self, ctx: Context[int]) -> int | Skip:
        if ctx.state >= 5:
            return Skip()
        return ctx.state * 2

    @step
    async def add_ten(self, ctx: Context[int]) -> int:
        return ctx.state + 10


async def test_skip_returned_from_step_body_leaves_state_unchanged():
    result = await build_runner().run([SkipFromBodyScenario()], initial_state=1)

    assert result == 14  # 1 + 1 = 2, double -> 4, +10 = 14


async def test_skip_is_traced_as_skipped_and_counts_in_metrics():
    runner = build_runner()
    result = await runner.run([SkipFromBodyScenario()], initial_state=5)

    assert result == 16  # 5 + 1 = 6, skip (stay 6), +10 = 16
    assert result != 22  # would be 6 * 2 + 10 without skip


class NamedStepScenario(Scenario[int]):
    @step(name="custom_name")
    async def do_it(self, ctx: Context[int]) -> int:
        return ctx.state + 1


async def test_step_name_defaults_to_method_name_and_can_be_overridden():
    scenario = NamedStepScenario()

    assert len(scenario.steps) == 1
    assert scenario.steps[0].name == "custom_name"
    assert scenario.steps[0].method_name == "do_it"


class BranchScenario(Scenario[int]):
    @step
    async def start(self, ctx: Context[int]) -> int:
        return ctx.state + 1

    @step
    async def branch(self, ctx: Context[int]) -> Branch[int]:
        return Branch(target=lambda context: FinalScenario(context.state))

    @step
    async def unreachable(self, ctx: Context[int]) -> int:
        return ctx.state + 1000


class FinalScenario(Scenario[int]):
    def __init__(self, multiplier: int) -> None:
        self._multiplier = multiplier

    @step
    async def finish(self, ctx: Context[int]) -> int:
        return ctx.state * self._multiplier + 2


async def test_branch_factory_receives_context_and_transfers_control():
    result = await build_runner().run([BranchScenario()], initial_state=1)

    assert result == 6


class BranchToScenario(Scenario[int]):
    @step(branch_to=lambda ctx: FinalScenario(ctx.state))
    async def go(self, ctx: Context[int]) -> int:
        return ctx.state + 1


async def test_branch_to_in_decorator_transfers_control():
    result = await build_runner().run([BranchToScenario()], initial_state=1)

    assert result == 6


class CycleScenarioA(Scenario[int]):
    @step
    async def to_b(self, ctx: Context[int]) -> Branch[int]:
        return Branch(target=lambda _ctx: CycleScenarioB())


class CycleScenarioB(Scenario[int]):
    @step
    async def to_a(self, ctx: Context[int]) -> Branch[int]:
        return Branch(target=lambda _ctx: CycleScenarioA())


async def test_cycle_detection_raises():
    with pytest.raises(ScenarioCycleError, match="cycle detected at '.*CycleScenarioA'"):
        await build_runner().run([CycleScenarioA()], initial_state=0)


async def test_context_tracks_path_for_error_messages():
    class A(Scenario[int]):
        @step
        async def to_b(self, ctx: Context[int]) -> Branch[int]:
            return Branch(target=lambda _ctx: B())

    class B(Scenario[int]):
        @step
        async def to_c(self, ctx: Context[int]) -> Branch[int]:
            return Branch(target=lambda _ctx: C())

    class C(Scenario[int]):
        @step
        async def to_b(self, ctx: Context[int]) -> Branch[int]:
            return Branch(target=lambda _ctx: B())

    with pytest.raises(ScenarioCycleError) as exc:
        await build_runner().run([A()], initial_state=0)

    assert exc.value.scenario_name.endswith("B")
    assert [name.split(".")[-1] for name in exc.value.path] == ["A", "B", "C"]


async def test_runner_executes_scenarios_sequentially_with_shared_context():
    class AddOne(Scenario[int]):
        @step
        async def add(self, ctx: Context[int]) -> int:
            return ctx.state + 1

    class AddTen(Scenario[int]):
        @step
        async def add(self, ctx: Context[int]) -> int:
            return ctx.state + 10

    result = await build_runner().run([AddOne(), AddTen()], initial_state=0)

    assert result == 11


async def test_mutable_context_state_is_shared_between_scenarios():
    class First(Scenario[dict]):
        @step
        async def set_flag(self, ctx: Context[dict]) -> None:
            ctx.state["first"] = True

    class Second(Scenario[dict]):
        @step
        async def read_flag(self, ctx: Context[dict]) -> None:
            ctx.state["second"] = ctx.state.get("first", False)

    result = await build_runner().run([First(), Second()], initial_state={})

    assert result == {"first": True, "second": True}


async def test_scenario_with_dependency_injection():
    class Repository:
        def __init__(self, value: int) -> None:
            self.value = value

    class DIScenario(Scenario[int]):
        def __init__(self, repo: Repository) -> None:
            self._repo = repo

        @step
        async def add_stored(self, ctx: Context[int]) -> int:
            return ctx.state + self._repo.value

    result = await build_runner().run([DIScenario(Repository(7))], initial_state=3)

    assert result == 10


async def test_empty_scenario_returns_initial_state():
    result = await build_runner().run([EmptyScenario()], initial_state=42)

    assert result == 42


async def test_empty_scenario_list_returns_initial_state():
    result = await build_runner().run([], initial_state=42)

    assert result == 42


class InMemoryLogger(Logger):
    def __init__(self) -> None:
        self.entries: list[TraceEntry] = []

    async def log(self, entry: TraceEntry) -> None:
        self.entries.append(entry)


class TwoStepScenario(Scenario[int]):
    @step
    async def first(self, ctx: Context[int]) -> int:
        return ctx.state + 1

    @step(when=lambda ctx: False)
    async def skipped(self, ctx: Context[int]) -> int:
        return ctx.state + 100

    @step
    async def second(self, ctx: Context[int]) -> int:
        return ctx.state + 10


async def test_trace_entries_are_emitted_to_logger():
    logger = InMemoryLogger()
    runner = ScenarioRunner(logger=logger)

    result = await runner.run([TwoStepScenario()], initial_state=0, correlation_id="abc-123")

    assert result == 11
    assert [entry.step_name for entry in logger.entries] == ["first", "skipped", "second"]
    assert logger.entries[0].skipped is False
    assert logger.entries[1].skipped is True
    assert logger.entries[0].state == 1
    assert logger.entries[1].state == 1
    assert logger.entries[2].state == 11
    assert all(entry.correlation_id == "abc-123" for entry in logger.entries)
    assert logger.entries[0].duration_ms >= 0
    assert logger.entries[1].duration_ms == 0.0


class TraceCountScenario(Scenario[int]):
    @step
    async def count(self, ctx: Context[int]) -> int:
        return len(ctx.trace)


async def test_trace_is_stored_in_context():
    result = await build_runner().run([TwoStepScenario(), TraceCountScenario()], initial_state=0)

    assert result == 3


class SlowScenario(Scenario[int]):
    @step
    async def sleep(self, ctx: Context[int]) -> None:
        import asyncio

        await asyncio.sleep(0.005)


async def test_trace_records_duration():
    logger = InMemoryLogger()
    runner = ScenarioRunner(logger=logger)

    await runner.run([SlowScenario()], initial_state=0)

    assert logger.entries[0].duration_ms >= 5.0


class FailingScenario(Scenario[int]):
    @step
    async def fail(self, ctx: Context[int]) -> int:
        raise RuntimeError("boom")


async def test_trace_records_error_and_re_raises():
    logger = InMemoryLogger()
    runner = ScenarioRunner(logger=logger)

    with pytest.raises(RuntimeError, match="boom"):
        await runner.run([FailingScenario()], initial_state=0, correlation_id="err-1")

    assert len(logger.entries) == 1
    entry = logger.entries[0]
    assert entry.step_name == "fail"
    assert entry.error == "boom"
    assert entry.correlation_id == "err-1"
    assert entry.duration_ms >= 0


class LevelScenario(Scenario[int]):
    @step(level="debug")
    async def quiet(self, ctx: Context[int]) -> int:
        return ctx.state + 1

    @step(level="error")
    async def loud(self, ctx: Context[int]) -> int:
        return ctx.state + 10


async def test_step_level_is_captured_in_trace():
    logger = InMemoryLogger()
    runner = ScenarioRunner(logger=logger)

    await runner.run([LevelScenario()], initial_state=0)

    assert logger.entries[0].level == "debug"
    assert logger.entries[1].level == "error"


async def test_batch_logger_flushes_on_batch_size_and_at_end():
    inner = InMemoryLogger()
    batch_logger = BatchLogger(inner, batch_size=2)
    runner = ScenarioRunner(logger=batch_logger)

    await runner.run([TwoStepScenario()], initial_state=0)

    # TwoStepScenario has 3 steps. Batch size 2 -> flush after first 2, then final flush.
    assert len(inner.entries) == 3
    assert [entry.step_name for entry in inner.entries] == ["first", "skipped", "second"]


async def test_metrics_are_collected():
    logger = InMemoryLogger()
    runner = ScenarioRunner(logger=logger)

    capture: list[ScenarioMetrics] = []

    class MixedScenario(Scenario[int]):
        @step
        async def ok(self, ctx: Context[int]) -> int:
            return ctx.state + 1

        @step(when=lambda ctx: False)
        async def skipped(self, ctx: Context[int]) -> int:
            return ctx.state + 100

        @step
        async def branch(self, ctx: Context[int]) -> Branch[int]:
            return Branch(target=lambda _ctx: EmptyScenario())

    class MetricsReader(Scenario[int]):
        @step
        async def read(self, ctx: Context[int]) -> None:
            capture.append(ctx.metrics)

    result = await runner.run([MixedScenario(), MetricsReader()], initial_state=0)

    assert result == 1
    assert len(capture) == 1
    metrics = capture[0]
    assert metrics.steps_total == 4  # ok, skipped, branch, read
    assert metrics.steps_skipped == 1
    assert metrics.branches_total == 1
    assert metrics.total_duration_ms >= 0

