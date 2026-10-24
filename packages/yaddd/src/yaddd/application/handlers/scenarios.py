"""Declarative scenario runner for multi-step application workflows.

Scenarios are declared as classes inheriting from :class:`Scenario`. Steps are
methods decorated with ``@step``. Each step receives a mutable :class:`Context`
carrying the workflow state and may:

* mutate the state in-place;
* return a new state to replace ``context.state``;
* return ``None`` to leave the state unchanged (useful for side-effects);
* return a :class:`Branch` to transfer control to another scenario.

Steps can be skipped declaratively via ``when``. The runner detects scenario
cycles at runtime by tracking visited scenario names in the context.

Examples:
    >>> from yaddd import (
    ...     Argument,
    ...     Context,
    ...     Scenario,
    ...     ScenarioRunner,
    ...     State,
    ...     Variable,
    ...     step,
    ... )

    >>> class OrderState(State):
    ...     user_id: int = Argument()
    ...     order_id: str = Argument(validate=str)
    ...     total: float = Variable(default=0.0)

    >>> class PlaceOrder(Scenario[OrderState]):
    ...     @step
    ...     async def add_tax(self, ctx: Context[OrderState]) -> None:
    ...         ctx.state.total *= 1.2

    >>> async def main() -> OrderState:
    ...     return await ScenarioRunner().run(
    ...         [PlaceOrder()],
    ...         initial_state=OrderState(user_id=1, order_id="abc"),
    ...     )
"""

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from inspect import isawaitable
from time import monotonic
from typing import Any, Literal, Protocol, cast

from yaddd.exceptions import ApplicationError


__all__ = [
    "BatchLogger",
    "Branch",
    "Context",
    "Logger",
    "Scenario",
    "ScenarioCycleError",
    "ScenarioError",
    "ScenarioMetrics",
    "ScenarioRunner",
    "Skip",
    "Step",
    "TraceEntry",
    "step",
]

type LogLevel = Literal["debug", "info", "warning", "error"]

type StepAction[State] = Callable[[Context[State]], Awaitable[StepResult[State]]]
type StepCondition[State] = Callable[[Context[State]], bool | Awaitable[bool]]
type StepResult[State] = State | Branch[State] | Skip | None
type ScenarioFactory[State] = Callable[[Context[State]], Scenario[State]]
type ScenarioTarget[State] = Scenario[State] | ScenarioFactory[State]
type RawStepMethod[State] = Callable[..., Awaitable[StepResult[State]]]


@dataclass(frozen=True, kw_only=True, slots=True)
class TraceEntry:
    """Record of a single step invocation."""

    scenario_name: str
    step_name: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    level: LogLevel = "info"
    skipped: bool = False
    duration_ms: float = 0.0
    correlation_id: str | None = None
    error: str | None = None
    state: Any | None = None


class Logger(Protocol):
    """Pluggable destination for scenario step traces."""

    async def log(self, entry: TraceEntry) -> None: ...


class BatchLogger:
    """Buffer trace entries and flush them to another logger in batches.

    Flushes automatically when the buffer reaches ``batch_size`` entries.
    Call ``flush()`` explicitly, or rely on :meth:`ScenarioRunner.run` to
    flush any remaining entries at the end of a run.
    """

    def __init__(self, logger: Logger, *, batch_size: int = 10) -> None:
        self._logger = logger
        self._batch_size = batch_size
        self._buffer: list[TraceEntry] = []

    async def log(self, entry: TraceEntry) -> None:
        """Buffer a trace entry; flush if the batch is full."""
        self._buffer.append(entry)
        if len(self._buffer) >= self._batch_size:
            await self.flush()

    async def flush(self) -> None:
        """Flush all buffered entries to the underlying logger."""
        for entry in self._buffer:
            await self._logger.log(entry)
        self._buffer.clear()


def _new_trace() -> list[TraceEntry]:
    return []


@dataclass(kw_only=True, slots=True)
class ScenarioMetrics:
    """Counters collected during a scenario run."""

    steps_total: int = 0
    steps_skipped: int = 0
    steps_failed: int = 0
    branches_total: int = 0
    total_duration_ms: float = 0.0


@dataclass(kw_only=True, slots=True)
class Context[State]:
    """Execution context passed to every step of a scenario.

    The context is mutable so that steps can enrich it in-place. The same
    context instance is propagated across branches and across the sequential
    scenarios passed to :meth:`ScenarioRunner.run`.
    """

    state: State
    visited: tuple[str, ...] = ()
    correlation_id: str | None = None
    trace: list[TraceEntry] = field(default_factory=_new_trace)
    metrics: ScenarioMetrics = field(default_factory=ScenarioMetrics)

    def visit(self, scenario_name: str) -> None:
        """Record ``scenario_name`` as visited."""
        self.visited = self.visited + (scenario_name,)

    def record(self, entry: TraceEntry) -> None:
        """Append a trace entry to the shared execution trace."""
        self.trace.append(entry)


@dataclass(kw_only=True, slots=True)
class Branch[State]:
    """Transfer control to another scenario.

    ``target`` is either a scenario instance or a factory that receives the
    current context and returns a scenario instance. The factory form is the
    natural choice when the target scenario has dependencies (DI ports).
    """

    target: ScenarioTarget[State]


class Skip:
    """Tell the runner to skip the current step from inside the step itself.

    Use ``Skip()`` when the decision to skip depends on state that is only
    available after previous steps have run. For purely declarative skipping
    prefer ``@step(when=...)``.
    """


@dataclass(kw_only=True, slots=True)
class Step[State]:
    """A single unit of work inside a scenario."""

    name: str
    method_name: str
    when: StepCondition[State] | None = None
    branch_to: ScenarioTarget[State] | None = None
    level: LogLevel = "info"


class Scenario[State]:
    """Base class for declaring a workflow as a set of ``@step`` methods.

    Subclasses can accept dependencies through ``__init__`` (repositories,
    event publishers, etc.). The runner only needs a scenario instance; how
    you build that instance is up to the composition root.
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls._declared_steps = _collect_steps(cls)

    @classmethod
    def scenario_name(cls) -> str:
        """Unique scenario identifier used for cycle detection."""
        return cls.__qualname__

    @property
    def steps(self) -> Sequence[Step[State]]:
        """Steps declared on this scenario class, in declaration order."""
        return self._declared_steps


def _collect_steps(scenario_cls: type[Scenario[Any]]) -> list[Step[Any]]:
    """Collect ``@step`` methods from the class and its scenario bases."""
    collected: dict[str, Step[Any]] = {}
    for base in reversed(scenario_cls.__mro__):
        if base is Scenario or not issubclass(base, Scenario):
            continue
        for method_name, attr in base.__dict__.items():
            if not callable(attr) or not hasattr(attr, "_step_name"):
                continue
            collected[method_name] = Step(
                name=getattr(attr, "_step_name") or method_name,  # noqa: B009
                method_name=method_name,
                when=getattr(attr, "_step_when", None),  # noqa: B009
                branch_to=getattr(attr, "_step_branch_to", None),  # noqa: B009
                level=getattr(attr, "_step_level", "info"),  # noqa: B009
            )
    return list(collected.values())


def step[State](
    method: RawStepMethod[State] | None = None,
    *,
    name: str | None = None,
    when: StepCondition[State] | None = None,
    branch_to: ScenarioTarget[State] | None = None,
    level: LogLevel = "info",
) -> RawStepMethod[State] | Callable[[RawStepMethod[State]], RawStepMethod[State]]:
    """Mark a method as a scenario step.

    Can be used bare (``@step``) or with parameters
    (``@step(name=..., when=..., branch_to=..., level=...)``).

    The decorated method receives the current :class:`Context` and may return
    a new state, ``None`` for an in-place side effect, or a :class:`Branch`.
    """

    def decorator(meth: RawStepMethod[State]) -> RawStepMethod[State]:
        object.__setattr__(meth, "_step_name", name)
        object.__setattr__(meth, "_step_when", when)
        object.__setattr__(meth, "_step_branch_to", branch_to)
        object.__setattr__(meth, "_step_level", level)
        return meth

    if method is None:
        return decorator
    return decorator(method)


class ScenarioError(ApplicationError):
    """Base for scenario-related errors."""


class ScenarioCycleError(ScenarioError):
    """Raised when branching would re-enter an already-visited scenario."""

    def __init__(self, scenario_name: str, path: Sequence[str]) -> None:
        self.scenario_name = scenario_name
        self.path = list(path)
        super().__init__(f"Scenario cycle detected at '{scenario_name}' along path {self.path}")


class _NoOpLogger:
    """Default logger that discards every trace entry."""

    async def log(self, entry: TraceEntry) -> None:
        del entry  # no-op


class ScenarioRunner[State]:
    """Executes :class:`Scenario` objects sequentially with a shared context.

    A single run creates one mutable :class:`Context` and passes it through
    each scenario in order. Branches create/resolve the target scenario and
    continue with the same context instance. Step traces are sent to the
    optional :class:`Logger` dependency and also kept in ``context.trace``.
    """

    def __init__(self, logger: Logger | None = None) -> None:
        self._logger = logger or _NoOpLogger()

    async def run(
        self,
        scenarios: Sequence[Scenario[State]],
        *,
        initial_state: State,
        correlation_id: str | None = None,
    ) -> State:
        """Run ``scenarios`` sequentially starting from ``initial_state``.

        The same :class:`Context` is shared across all scenarios. Returns the
        final state after the last scenario finishes.
        """
        context = Context(state=initial_state, correlation_id=correlation_id)
        for scenario in scenarios:
            await self._execute(scenario, context)
        await self._flush_logger()
        return context.state

    async def _execute(self, scenario: Scenario[State], context: Context[State]) -> None:
        name = scenario.scenario_name()
        if name in context.visited:
            raise ScenarioCycleError(name, list(context.visited))

        context.visit(name)

        for step in scenario.steps:
            skipped = False
            if step.when is not None:
                when_result = step.when(context)
                if isawaitable(when_result):
                    when_result = await when_result
                if not when_result:
                    skipped = True

            if skipped:
                await self._trace(context, name, step, skipped=True, duration_ms=0.0)
                continue

            started_at = monotonic()
            try:
                result = await getattr(scenario, step.method_name)(context)
            except Exception as exc:
                duration_ms = (monotonic() - started_at) * 1000
                await self._trace(
                    context,
                    name,
                    step,
                    skipped=False,
                    duration_ms=duration_ms,
                    error=str(exc),
                )
                raise
            duration_ms = (monotonic() - started_at) * 1000

            if isinstance(result, Branch):
                await self._trace(
                    context, name, step, skipped=False, duration_ms=duration_ms, branch=True
                )
                branch = cast(Branch[State], result)
                target = self._resolve(branch.target, context)
                await self._execute(target, context)
                return

            if isinstance(result, Skip):
                await self._trace(context, name, step, skipped=True, duration_ms=duration_ms)
                continue

            if result is not None:
                context.state = result

            await self._trace(context, name, step, skipped=False, duration_ms=duration_ms)

            if step.branch_to is not None:
                await self._trace(
                    context, name, step, skipped=False, duration_ms=duration_ms, branch=True
                )
                target = self._resolve(step.branch_to, context)
                await self._execute(target, context)
                return

    async def _trace(
        self,
        context: Context[State],
        scenario_name: str,
        step: Step[State],
        *,
        skipped: bool,
        duration_ms: float,
        error: str | None = None,
        branch: bool = False,
    ) -> None:
        entry = TraceEntry(
            scenario_name=scenario_name,
            step_name=step.name,
            level=step.level,
            skipped=skipped,
            duration_ms=duration_ms,
            correlation_id=context.correlation_id,
            error=error,
            state=context.state,
        )
        context.record(entry)
        await self._logger.log(entry)

        metrics = context.metrics
        metrics.steps_total += 1
        metrics.total_duration_ms += duration_ms
        if skipped:
            metrics.steps_skipped += 1
        if error is not None:
            metrics.steps_failed += 1
        if branch:
            metrics.branches_total += 1

    async def _flush_logger(self) -> None:
        flush = getattr(self._logger, "flush", None)
        if flush is not None:
            await flush()

    def _resolve(self, target: ScenarioTarget[State], context: Context[State]) -> Scenario[State]:
        if callable(target):
            return target(context)
        return target
