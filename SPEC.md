# SPEC — yaddd (Yet Another DDD for Python)

Статус: draft v0.1
Целевая платформа: Python >= 3.12

## 1. Обзор

`yaddd` — framework-agnostic библиотека базовых абстракций для построения
приложений по DDD (Domain-Driven Design). Библиотека предоставляет тонкий,
строго типизированный каркас слоёв:

- **Domain** — ValueObject, Entity, AggregateRoot, DomainEvent, DomainService,
  Factory, Specification, BusinessRule;
- **Application** — ApplicationService, Command, Query, Handler, DTO, Mapper;
- **Infrastructure** — Repository, ReadModel, Connector;
- **Presentation (entrypoints)** — порты для CLI, HTTP, GraphQL.

Библиотека не привязана к веб-фреймворку, ORM или DI-контейнеру: она задаёт
контракты (Protocols/ABC) и базовые реализации, а интеграции с внешними
библиотеками вынесены в опциональные extras.

## 2. Цели

1. Дать единый словарь абстракций DDD, разложенный по слоям (см. §11).
2. Обеспечить строгую типизацию публичного API: `mypy --strict` + `pyright`,
   маркер `py.typed` в пакете.
3. Нулевые обязательные зависимости: ядро использует только stdlib.
4. Предсказуемые правила зависимостей между слоями (см. §4).
5. Простота: минимум метапрограммирования, композиция вместо наследования,
   никакой «магии» в публичном API.

## 3. Нецели (non-goals)

- Не является веб-фреймворком, ORM, message bus или DI-контейнером.
- Не навязывает конкретную структуру приложения (модули/контексты пользователь
  организует сам).
- Не реализует Event Sourcing, CQRS-шину, saga/process manager — только
  базовые строительные блоки; расширение — дело пользователя.
- Не поддерживает Python < 3.12 и compatibility-шимы (`typing_extensions` и т.п.).

## 4. Архитектура: правила зависимостей

Зависимости направлены только внутрь:

```
presentation  →  application  →  domain
infrastructure → domain (реализует порты домена)
```

- **domain** не импортирует ничего из application/infrastructure/presentation.
  Здесь объявлены порты (Protocols) репозиториев.
- **application** зависит только от domain.
- **infrastructure** зависит от domain (реализации портов, коннекторы,
  read models). Опциональные сторонние пакеты импортируются лениво, внутри
  модуля интеграции.
- **presentation** зависит от application и domain; адаптеры к конкретным
  фреймворкам (FastAPI, aiohttp, strawberry, click/argparse) — опциональные
  extras, ядро определяет только порты.

Ядро синхронное; инфраструктурные порты (Repository, Connector, UnitOfWork,
EventPublisher) — async-only (`async def`), т.к. их реализации по природе
I/O-bound. Доменная модель (Entity, ValueObject, события, правила) — строго
синхронная и не содержит I/O. Sync-вариантов портов нет: sync-сценарий
(CLI-скрипт, cron-джоба) закрывается на entrypoint'е, который владеет
event loop (`asyncio.run(main())`). Если позже возникнет массовый спрос на
sync (например, Django-ORM), sync-порты добавятся отдельным модулем без
ломки существующих.

## 5. Структура пакета

```
src/yaddd/
├── __init__.py            # публичный реэкспорт + __all__
├── py.typed
├── exceptions.py          # иерархия исключений (§9)
├── shared/
│   ├── specification.py   # Specification + комбинаторы
│   └── dataclasses.py     # DataclassMixin/FrozenDataclassMixin (PEP 681)
├── domain/
│   ├── __init__.py
│   ├── value_object/
│   │   ├── __init__.py      # публичный реэкспорт VO + __all__
│   │   ├── base.py          # ValueObject, SensitiveValueObject
│   │   ├── base_types.py    # Numeric/AnyStr/AnyDate/Dict и конкретные VO-базы
│   │   ├── registry.py      # VOBaseTypesRegistry
│   │   └── (sqlalchemy/, pydantic/ — отложенные extras, см. §11)
│   ├── entities.py        # Entity, AggregateRoot
│   ├── events.py          # DomainEvent
│   ├── services.py        # DomainService
│   ├── factories.py       # Factory (Protocol)
│   ├── rules.py           # BusinessRule
│   └── repositories.py    # порты репозиториев (Protocols)
├── application/
│   ├── __init__.py
│   ├── commands.py        # Command, Query
│   ├── handlers.py        # CommandHandler, QueryHandler (Protocols)
│   ├── services.py        # ApplicationService
│   ├── uow.py             # UnitOfWork (Protocol)
│   ├── events.py          # EventPublisher (Protocol), InMemoryEventPublisher
│   ├── dto.py             # DTO
│   └── mappers.py         # Mapper (Protocol)
├── infrastructure/
│   ├── __init__.py
│   ├── repositories.py    # InMemoryCrudRepository, ReadModelRepository
│   ├── read_models.py     # ReadModel
│   └── connectors.py      # Connector (Protocol)
└── presentation/
    ├── __init__.py
    ├── cli.py             # порт CLI
    ├── http.py            # порты Request/Response/Router
    └── graphql.py         # порт Resolver
```

Каждый модуль объявляет `__all__`; корневой `__init__.py` реэкспортирует
публичную поверхность так, чтобы одного `from yaddd import ...` хватало
для типового использования.

## 6. Domain layer

### 6.1 ValueObject

Назначение: типизированное, иммутабельное значение с валидацией на входе.
После конструирования значение считается доверенным (parse, don't validate).

```python
class ValueObject[V](ABC):
    def __init__(self, raw_value: V) -> None: ...
    @classmethod
    @abstractmethod
    def validate(cls, value: V) -> V: ...
    @property
    def value(self) -> V: ...

class SensitiveValueObject[V](ValueObject[V]):
    """VO, чьё значение не должно попадать в логи/репрезентации."""
```

Требования:
- равенство и хеш — по классу и значению; VO разных классов никогда не равны;
- сравнения (`<`, `<=`, `>`, `>=`) допустимы только между VO одного класса,
  иначе `TypeError`;
- `SensitiveValueObject` — отдельный подкласс (не флаг): `repr` маскирует
  значение (`ClassName([MASKED])`), `str` бросает
  `SensitiveValueAccessError` — защита от утечки в логи; маскирование
  наследуется подклассами;
- копирование (`copy`/`deepcopy`) возвращает VO того же класса.

### 6.2 Entity

Назначение: объект с идентичностью. Подклассы автоматически становятся
dataclass'ами (`eq=False, kw_only=True`) через `__init_subclass__` +
`@dataclass_transform` (PEP 681) — без метаклассов, с пониманием
синтезированного `__init__` type checker'ами.

```python
class Entity:
    PRIMARY_KEY_NAME: ClassVar[str] = "id"
    INVARIANTS: ClassVar[tuple[BusinessRule[Any], ...]] = ()
    @property
    def pk(self) -> PrimaryKey: ...  # type PrimaryKey = UUID | int | str
```

- равенство и хеш — по `pk` внутри одного класса;
- `to_dict() -> dict[str, Any]` — сериализация полей;
- `INVARIANTS` на уровне сущности — правила **самосогласованности**
  («количество > 0», «конец периода ≥ начала»); проверяются в
  `__post_init__`, нарушение — `InvariantViolationError`;
- инварианты, охватывающие несколько сущностей, размещаются на корне
  агрегата — размещение правила документирует его область действия;
- пользователь объявляет поля аннотациями, декоратор не нужен; если класс
  уже задекорирован `@dataclass` вручную, автоматика уступает (для identity-
  семантики вручную декорировать только с `eq=False`);
- при переопределении `__post_init__` в подклассе обязателен вызов
  `super().__post_init__()` (проверка инвариантов).

### 6.3 AggregateRoot

```python
class AggregateRoot(Entity):
    def add_event(self, event: DomainEvent) -> None: ...
    def pull_events(self) -> list[DomainEvent]: ...  # забирает и очищает
```

- наследует механизм инвариантов от `Entity`; на корне размещаются
  инварианты **уровня агрегата** — правила, охватывающие несколько сущностей;
- `INVARIANTS: ClassVar[tuple[BusinessRule[Any], ...]]` — единственный
  механизм инвариантов; экспериментальные декораторы `invariants` из
  прототипа отброшены;
- агрегат накапливает доменные события; репозиторий/шина забирает их через
  `pull_events()` после успешного сохранения;
- все изменения состояния внутри агрегата идут только через корень —
  это требование к пользовательскому коду, библиотека предоставляет
  только базовые механики.

### 6.4 DomainEvent

```python
class DomainEvent(FrozenDataclassMixin):
    occurred_at: datetime  # UTC, default=now
```

- иммутабельное событие о свершившемся факте; имя события — имя класса;
- `occurred_at` заполняется автоматически (`datetime.now(UTC)`);
- подклассы автоматически становятся frozen-dataclass'ами через
  `__init_subclass__` + `@dataclass_transform` — пользователь только
  объявляет полезную нагрузку аннотациями;
- версионирование: v0.1 события живут только внутри процесса (in-memory
  публикация), поле версии не вводится. Принцип на будущее: событие,
  покидающее процесс (outbox, брокер), обязано версионироваться
  (`event_version: int = 1` + upcasters) — механика реализуется на стороне
  соответствующего адаптера; добавление поля будет обратно-совместимым
  изменением dataclass'ы.

### 6.5 DomainService

Протокол для безсостояной доменной логики, не принадлежащей одному агрегату
(операции над несколькими агрегатами или требующие внешних данных через порты).

```python
class DomainService(Protocol):
    """Маркерный протокол; конкретные сервисы определяет пользователь."""
```

### 6.6 Factory

```python
class Factory[T: AggregateRoot](Protocol):
    def create(self, **data: Any) -> T: ...
```

- инкапсулирует сложное конструирование агрегата (восстановление из сырых
  данных, генерация идентификаторов, проверка правил перед созданием).

### 6.7 Specification

```python
class Specification[C](ABC):
    @abstractmethod
    def is_satisfied_by(self, candidate: C) -> bool: ...
    def __and__(self, other: Self) -> Self: ...
    def __or__(self, other: Self) -> Self: ...
    def __invert__(self) -> Self: ...
    def __xor__(self, other: Self) -> Self: ...
```

- композиция через операторы `&`, `|`, `~`, `^` (уже реализовано,
  переносится из `src_old/yaddd/shared/specification.py`);
- `_AndSpecification`/`_OrSpecification` выравнивают цепочки (and + and
  сливаются в плоский кортеж).

### 6.8 BusinessRule

```python
class BusinessRule[C](Specification[C], ABC):
    message: ClassVar[str]
    def check(self, candidate: C) -> None: ...  # raise BusinessRuleViolationError
```

- правило = спецификация + человекочитаемое сообщение;
- `check()` бросает `BusinessRuleViolationError`, если правило не выполнено;
- используется в `AggregateRoot.INVARIANTS`.

### 6.9 Порты репозиториев (domain/repositories.py)

```python
class Repository[T: AggregateRoot](Protocol): ...
class CrudRepository[T: AggregateRoot](Repository[T], Protocol):
    async def get(self, pk: PrimaryKey) -> T | None: ...
    async def read(self, filter: dict | None = None, *, slice: tuple[int, int] = (0, 0)) -> list[T]: ...
    async def create(self, instance: T) -> T: ...
    async def update(self, instance: T) -> T: ...
    async def delete(self, pk: PrimaryKey) -> None: ...
```

## 7. Application layer

Слой оркестрации: принимает вход от entrypoints, исполняет сценарий
использования над доменом, возвращает DTO. Не содержит доменной логики.

### 7.1 Command / Query

```python
class Command(FrozenDataclassMixin): ...
class Query(FrozenDataclassMixin): ...
```

- иммутабельные намерения (изменить состояние / прочитать состояние);
- никакой логики, только данные;
- подклассы автоматически становятся frozen-dataclass'ами (механизм
  `FrozenDataclassMixin` из `shared/dataclasses.py`, как у `DomainEvent`).

### 7.2 Handlers

```python
class CommandHandler[C: Command, R](Protocol):
    async def handle(self, command: C) -> R: ...

class QueryHandler[Q: Query, R](Protocol):
    async def handle(self, query: Q) -> R: ...
```

- один handler = одна команда/запрос (1:1);
- handler получает зависимости (репозитории, порты) через конструктор —
  явный DI без контейнера.

### 7.3 ApplicationService

```python
class ApplicationService[C: Command, R](ABC):
    async def __call__(self, command: C) -> R: ...  # делегирует execute
    @abstractmethod
    async def execute(self, command: C) -> R: ...
```

Координатор сценария: загружает агрегат через порт репозитория, вызывает
доменные методы, сохраняет, публикует события. Может делегировать шаги
handler'ам. Базовый класс предоставляет только каркас (точку входа
`execute`/`__call__`); зависимости — через конструктор.

### 7.4 UnitOfWork

```python
class UnitOfWork(Protocol):
    async def __aenter__(self) -> Self: ...
    async def __aexit__(self, exc_type, exc_value, traceback) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
```

- транзакционная граница use case'а «загрузил → изменил → сохранил»;
- handler/ApplicationService получает UoW через конструктор (явный DI);
  репозитории создаются поверх сессии UoW и **не коммитят сами**;
- выход из контекста без `commit()` = rollback; исключение внутри
  контекста = rollback;
- в ядре только Protocol; реализации — в infrastructure
  (`SqlUnitOfWork` в extra `sqlalchemy`).

### 7.5 EventPublisher

```python
EventHandler: TypeAlias = Callable[[DomainEvent], Awaitable[None]]

class EventPublisher(Protocol):
    async def publish(self, events: Sequence[DomainEvent]) -> None: ...

class InMemoryEventPublisher:
    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None: ...
    async def publish(self, events: Sequence[DomainEvent]) -> None: ...
```

- единственная санкционированная точка публикации доменных событий;
- публикация **после** `uow.commit()`: handler/ApplicationService забирает
  события через `aggregate.pull_events()` и передаёт в `publish()` — событие
  не уходит наружу, пока состояние не зафиксировано;
- репозитории события не публикуют никогда;
- ядро содержит Protocol + `InMemoryEventPublisher` (подписка на типы событий,
  для монолитов и тестов); брокерные адаптеры (Kafka, RabbitMQ) — вне ядра;
- семантика `InMemoryEventPublisher`: диспетчеризация по `isinstance`
  (подписка на базовый тип ловит подтипы), вызов последовательно в порядке
  подписки, исключение handler'а прерывает диспетчеризацию и пробрасывается;
- известный компромисс v0.1: зазор между commit и publish (publish упал —
  события потеряны). Кому нужны гарантии — реализует transactional outbox
  поверх тех же портов; дизайн ему не мешает.

### 7.6 DTO

```python
class DTO(FrozenDataclassMixin): ...
```

- объект передачи данных через границу application↔presentation;
- плоский, сериализуемый, без ссылок на доменные объекты;
- подклассы автоматически становятся frozen-dataclass'ами (без `slots=True` —
  авто-применение dataclass работает только in-place, см. `DomainEvent`).

### 7.7 Mapper

```python
class Mapper[D, T: AggregateRoot](Protocol):
    def to_dto(self, domain: T) -> D: ...
    def to_domain(self, dto: D) -> T: ...
```

- преобразование домен↔DTO; пользователь реализует протокол напрямую.

## 8. Infrastructure layer

### 8.1 Реализации репозиториев

- `InMemoryCrudRepository[T]` — dict-backed реализация порта `CrudRepository`
  (§6.9) в ядре: для тестов, прототипов и простых приложений; `create`
  вставляет или заменяет, `update` требует существования записи
  (`EntityNotFoundError`), `delete` идемпотентен.
- Отложено до extras: `SqlRepository[T]` над SQLAlchemy `AsyncSession`,
  `HttpRepository[T]` поверх внешних HTTP-сервисов, connector-based ABC
  (база, хранящая `Connector`) — появятся вместе с первым реальным
  потребителем, чтобы не плодить мёртвый код.

Каждый репозиторий работает ровно с одним агрегатом.
Репозитории не управляют транзакцией: коммит/откат — ответственность
`UnitOfWork` (§7.4), поверх сессии которого создаётся репозиторий.
Репозитории не публикуют доменные события — это делает
`EventPublisher` (§7.5) после успешного `commit()`.

### 8.2 UnitOfWork implementations

- Отложено до extra `sqlalchemy`: `SqlUnitOfWork` поверх `AsyncSession`;
  `commit()` → `session.commit()`, `rollback()`/`__aexit__` при исключении →
  `session.rollback()`;
- ядро реализаций не содержит — только Protocol из §7.4.

### 8.3 ReadModel

```python
class ReadModel(FrozenDataclassMixin): ...

class ReadModelRepository[M: ReadModel](Protocol):
    async def find(self, filter: dict[str, Any] | None = None, *, slice: tuple[int, int] = (0, 0)) -> list[M]: ...
    async def find_one(self, pk: PrimaryKey) -> M | None: ...
```

- денормализованная модель «на чтение», оптимизированная под запросы;
- read models не проходят через агрегаты и не навлекают доменных инвариантов;
- подклассы автоматически становятся frozen-dataclass'ами;
- порт `ReadModelRepository` живёт в `infrastructure/repositories.py` — рядом
  с другими репозиториями слоя (по аналогии с портами агрегатов в
  `domain/repositories.py`).

### 8.4 Connector

```python
class Connector(Protocol):
    session: Any
```

- абстракция над источником данных (БД-сессия, HTTP-клиент и т.п.);
- конкретные коннекторы (`HttpConnector` и др.) получают настройки через
  конструктор (typed settings).

## 9. Presentation layer (entrypoints)

Ядро определяет только порты и нейтральные типы запрос/ответ; адаптеры к
конкретным фреймворкам — вне ядра (опциональные extras или код приложения).

- **CLI**: `CliCommand` (Protocol) — `run(args) -> int` (exit code);
  нейтрален к argparse/click/typer.
- **HTTP**: нейтральные `HttpRequest`/`HttpResponse` (dataclass: method, path,
  headers, body / status, headers, body) + `HttpHandler` (Protocol:
  `async def handle(request) -> HttpResponse`). Адаптер к FastAPI/aiohttp
  отображает фреймворковые типы на эти порты.
- **GraphQL**: `Resolver` (Protocol) — `async def resolve(root, info, **args)`;
  привязка к strawberry/ariadne — на стороне приложения.

Общее правило entrypoints: parse вход → Command/Query → handler → DTO →
отображение в транспортный ответ. Никакой доменной логики.

## 10. Исключения

Единая иерархия, корень — `YadddError`:

```
YadddError
├── DomainError
│   ├── BusinessRuleViolationError   # правило/спецификация не выполнено
│   ├── InvariantViolationError      # нарушен инвариант агрегата
│   ├── ValidationError              # VO.validate отклонил значение
│   └── SensitiveValueAccessError    # доступ к sensitive-значению
├── ApplicationError
│   └── HandlerNotFoundError
└── InfrastructureError
    ├── EntityNotFoundError          # репозиторий не нашёл запись
    └── ConnectorError
```

- бросаем максимально специфичный подкласс; контекст — через `add_note()`,
  причинную цепочку — через `raise ... from ...`.

## 11. Опциональные интеграции (extras)

| Extra        | Что даёт                                             | Требование |
|--------------|------------------------------------------------------|------------|
| `sqlalchemy` | type decorators для ValueObject, `SqlRepository`, `SqlUnitOfWork` | ленивый импорт; ядро не импортирует sqlalchemy |

Отложено до будущих версий: extra `pydantic` (валидаторы Pydantic для
ValueObject, typed settings) — была удалена из v0.1 и вернётся с более
осознанным дизайном интеграции.

Правило: `pip install yaddd` никогда не тянет сторонних пакетов;
импорт ядра никогда не падает из-за отсутствия optional-зависимости —
модуль интеграции бросает `ImportError` с подсказкой `pip install yaddd[...]`.

## 12. Требования к качеству

- **Типизация**: каждый публичный символ аннотирован; проходят `mypy --strict`
  и `pyright`; `py.typed` включён в wheel; PEP 695 generics
  (`class CrudRepository[T: AggregateRoot]`), `Self`, `Protocol` для
  интерфейсов, `ABC` только там, где нужно общее состояние/`super()`.
- **Линт/формат**: `ruff check` + `ruff format` (конфигурация уже в pyproject).
- **Тесты**: pytest; тесты покрывают публичный API «как пользователь»;
  `pytest.raises(..., match=...)` для контрактов исключений; фейковые
  реализации Protocols вместо моков внутренностей.
- **Гейты перед завершением изменения**: `ruff check . && ruff format --check .`
  `&& mypy src && pyright src && pytest`.
- **Стиль**: keyword-only аргументы для функций с >1 параметром и всех bool;
  `slots=True` в dataclass'ах; без метаклассов — поведение выражается
  наследованием (напр., `SensitiveValueObject` вместо мета-флага).

## 13. Протокол архитектурных решений

Все открытые вопросы закрыты (2026-10-03):

1. ~~**Unit of Work**~~ — **вариант A**: порт `UnitOfWork` в application-слое
   (§7.4), реализации в infrastructure (§8.2). Репозитории транзакцией не
   управляют.
2. ~~**Шина доменных событий**~~ — **вариант A**: порт `EventPublisher` в
   application-слое (§7.5), публикация после `uow.commit()`, репозитории
   событий не публикуют. In-memory реализация в ядре, брокеры — вне ядра;
   outbox — документированное расширение.
3. ~~**Версионирование событий**~~ — **вариант A**: в v0.1 поле версии не
   вводится (события живут внутри процесса). Принцип «событие, покидающее
   процесс, обязано версионироваться» зафиксирован в §6.4; добавление
   `event_version` будет обратно-совместимым изменением.
4. ~~**Синхронные реализации портов**~~ — **вариант A**: async-only. Sync-
   сценарии закрываются entrypoint'ом, владеющим event loop
   (`asyncio.run(main())`); см. §4. Sync-порты, если появится спрос,
   добавятся отдельным модулем без ломки существующих.

## 14. Глоссарий DDD-терминов

### 14.1 Domain layer

| Термин | Определение | В yaddd |
|--------|-------------|---------|
| Value Object (объект-значение) | Объект без идентичности, равенство по значению; валидируется при создании и далее считается доверенным | `ValueObject[V]`, `SensitiveValueObject[V]`, `domain/value_object/` |
| Entity (сущность) | Объект с идентичностью; равенство по идентификатору, а не по полям | `Entity`, `domain/entities.py` |
| Aggregate Root (корень агрегата) | Единственная точка входа в граф сущностей агрегата; гарантирует инварианты | `AggregateRoot`, `INVARIANTS`, `check_invariants()` |
| Invariant (инвариант) | Условие, которое агрегат обязан соблюдать всегда | `BusinessRule` в `AggregateRoot.INVARIANTS` |
| Domain Event (доменное событие) | Иммутабельная запись о свершившемся доменном факте | `DomainEvent`, `add_event/pull_events` |
| Domain Service (доменный сервис) | Безсостояная доменная операция, не принадлежащая одному агрегату | `DomainService` (Protocol) |
| Factory (фабрика) | Инкапсуляция сложного конструирования агрегата | `Factory[T]` (Protocol) |
| Specification (спецификация) | Переиспользуемое, композитное (`&`, `\|`, `~`, `^`) условие над кандидатом | `Specification[C]`, `shared/specification.py` |
| Business Rule (бизнес-правило) | Спецификация с сообщением об ошибке; нарушение — исключение | `BusinessRule[C]`, `domain/rules.py` |
| Repository interface (порт репозитория) | Контракт хранилища агрегатов на языке домена, без деталей хранения | `Repository`, `CrudRepository` (Protocols), `domain/repositories.py` |
| Primary Key (идентификатор) | Значение идентичности сущности: `UUID \| int \| str` | `PrimaryKey` TypeVar, `Entity.pk` |
| Ubiquitous Language (единый язык) | Словарь, общий для кода и предметной области; имена классов повторяют термины домена | этот глоссарий + именование публичного API |

### 14.2 Application layer

| Термин | Определение | В yaddd |
|--------|-------------|---------|
| Command (команда) | Иммутабельное намерение изменить состояние системы | `Command`, `application/commands.py` |
| Query (запрос) | Иммутабельное намерение прочитать состояние без побочных эффектов | `Query` |
| Command/Query Handler (обработчик) | Исполнитель одной команды/запроса (1:1), получает порты через конструктор | `CommandHandler[C, R]`, `QueryHandler[Q, R]` |
| Application Service (сервис приложения) | Оркестратор сценария использования: загрузка агрегата → доменный вызов → сохранение → события | `ApplicationService`, `application/services.py` |
| DTO (Data Transfer Object) | Плоский сериализуемый объект передачи данных через границы слоёв | `DTO`, `application/dto.py` |
| Mapper (маппер) | Преобразование между доменной моделью и DTO | `Mapper[D, T]` (Protocol) |
| Use Case (сценарий использования) | Конкретная операция системы, реализуемая handler'ом/сервисом приложения | пары Command+Handler |
| Unit of Work (единица работы) | Транзакционная граница use case'а: все сохранения коммитятся атомарно или откатываются | `UnitOfWork` (Protocol), `application/uow.py` |
| Event Publisher (издатель событий) | Порт публикации доменных событий после успешного commit'а | `EventPublisher`, `InMemoryEventPublisher`, `application/events.py` |
| Event Handler (обработчик события) | Реакция на доменное событие; подписывается на тип события | подписки `InMemoryEventPublisher.subscribe` |
| Port (порт) | Интерфейс, объявленный внутренним слоем, реализуемый внешним | Protocols репозиториев/коннекторов |

### 14.3 Infrastructure layer

| Термин | Определение | В yaddd |
|--------|-------------|---------|
| Repository implementation | Реализация порта репозитория под конкретное хранилище | `InMemoryCrudRepository` (ядро); `SqlRepository`, `HttpRepository` — отложенные extras |
| Unit of Work implementation | Реализация порта UoW поверх конкретной сессии/клиента | `SqlUnitOfWork` (отложенный extra `sqlalchemy`) |
| Read Model (модель чтения) | Денормализованная проекция, оптимизированная под запросы; минует агрегаты | `ReadModel`, `infrastructure/read_models.py` |
| Read Model Repository | Доступ «только чтение» к read models | `ReadModelRepository[M]` (Protocol) |
| Connector (коннектор) | Абстракция над источником данных: БД-сессия, HTTP-клиент | `Connector` (Protocol), `HttpConnector` |
| Anti-Corruption Layer (ACL) | Прослойка, защищающая домен от чужой модели (внешний API, legacy) | мапперы + `HttpRepository` как точка адаптации |
| Persistence Ignorance | Домен не знает о деталях хранения | порты в domain, реализации в infrastructure |

### 14.4 Entrypoints (presentation layer)

| Термин | Определение | В yaddd |
|--------|-------------|---------|
| Entrypoint (точка входа) | Граница системы, преобразующая внешний вызов в Command/Query | `presentation/` |
| Adapter (адаптер) | Реализация порта под конкретный транспорт/фреймворк | адаптеры CLI/HTTP/GraphQL вне ядра |
| CLI | Командная точка входа: аргументы → команда → exit code | `CliCommand` (Protocol), `presentation/cli.py` |
| HTTP handler | Нейтральный обработчик запрос/ответ без привязки к фреймворку | `HttpRequest`, `HttpResponse`, `HttpHandler` |
| GraphQL resolver | Функция разрешения поля схемы в вызов application-слоя | `Resolver` (Protocol), `presentation/graphql.py` |
| Primary/Driving adapter | Адаптер, инициирующий работу системы (в отличие от driven-адаптеров инфраструктуры) | все адаптеры этого слоя |
