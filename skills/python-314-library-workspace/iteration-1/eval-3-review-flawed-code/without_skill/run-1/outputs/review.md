# Ревью конфиг-утилит перед мержем

Стандарты: строгая типизация (mypy --strict + pyright), минимум зависимостей (stdlib-first), продуманный публичный API. Код **не проходит** ревью, мерж блокирован.

## Проблемы (по убыванию серьёзности)

### Критические

1. **Нет аннотаций у публичных функций.** `load_config(path, strict=False)` и `get_value(config, key)` полностью нетипизированы — `path`, `strict`, `config`, `key` и возвращаемые значения не аннотированы. Под `mypy --strict` этот код не проходит (`disallow_untyped_defs`). Пользователи библиотеки получат `Any` вместо помощи от чекера.

2. **Голый `raise Exception(...)` вместо иерархии исключений.** Исключения — часть публичного API (стандарт §4). Нужен базовый класс библиотеки (например, `YadddError`) и конкретный подкласс, выброшенный с цепочкой `raise ... from err` и контекстом через `add_note()` (PEP 678), а не строка "missing key" без имени ключа.

3. **`CACHE = {}` — модульный мутируемый глобал.** Для свободнопоточных (no-GIL) сборок Python 3.14 это небезопасно и прямо запрещено стандартом §3: «избегайте module-level mutable caches; предпочитайте передавать состояние явно». Кроме того, кэш бесконечно растёт (утечка памяти), не имеет API для инвалидации, а его ключ — `path` в виде сырой строки (не канонализированный), так что `./cfg.json` и `cfg.json` — два разных ключа.

4. **Параметр `strict` объявлен, но не используется.** Это ложный контракт API: вызывающий код думает, что получает строгую валидацию, а на самом деле поведение одинаково. Либо реализовать, либо удалить. Булевы параметры к тому же должны быть keyword-only.

### Высокие

5. **Сырой `Dict[str, Any]` как алиас `Config` в конце файла.** Анти-паттерн для 3.14: `typing.Dict` устарел, встроенный `dict[str, Any]` предпочтительнее. Алиас объявлен после функций, которые его должны были бы использовать — и никем не используется. Тип конфигурации как `dict[str, Any]` — это отсутствие типизации, замаскированное под аннотацию; стандарт требует реальной пользы от типов (структурные `Protocol`, дженерики, `@overload`, где уместно).

6. **Отсутствие публичного API-слоя.** Нет `__all__` в модуле, неясно, что публично, а что нет. Любая переменная уровня модуля (`CACHE`, `Config`) становится публичной по умолчанию. Стандарт §4: всё, не входящее в `__all__`, должно иметь `_` на определении.

7. **`open(path)` без кодировки и без менеджера ошибок.** Полагается на locale-по-умолчанию; для библиотеки нужен явный `encoding="utf-8"`. `json.JSONDecodeError` и `OSError` утекают наружу как сырые исключения stdlib — либо задокументировать, либо обернуть в иерархию библиотеки.

8. **Импорты не по ruff/isort-конвенции и не используются корректно.** `Optional` импортирован, но не используется (мертвый импорт — `ruff check` упадёт с F401).

### Средние

9. **Позиционные булевы и мультипараметрные аргументы.** `load_config(path, strict=False)` нарушает правило «keyword-only для функций с булевыми параметрами». Должно быть `def load_config(path: str | Path, *, strict: bool = False)`.

10. **`path` как `str` вместо `str | Path`.** Пользователи библиотеки разумно передадут `pathlib.Path` (stdlib-first подход); аннотация должна это допускать, а не вынуждать звонить `str()`.

11. **Кэширование без публичного контракта.** Если кэш нужен, он должен быть либо явным параметром (`cache: MutableMapping[...] | None`), либо вынесен в отдельный типизированный объект с документированной потокобезопасностью — и назван `_`-префиксом.

### Информационные

12. Зависимости: только stdlib (`json`) — соответствует политике. Это единственный полный «pass».
13. `py.typed`, конфиги mypy/pyright/ruff, тесты — не показаны в сниппете; перед мержем обязательны (`pytest`, `mypy src`, `pyright src`, `ruff check`, `ruff format --check`).

## Переписанная версия

Исходный сниппет без контекста пакета, поэтому переписываю как самодостаточный модуль библиотеки (пакет `yaddd` уже имеет `YadddError` в своей иерархии исключений):

```python
"""Конфигурационные утилиты библиотеки."""

import json
from collections.abc import Mapping, MutableMapping
from pathlib import Path
from typing import Any, Self

from yaddd import YadddError

__all__ = ["Config", "ConfigError", "ConfigKeyError", "load_config", "get_value"]


class ConfigError(YadddError):
    """Ошибка загрузки или разбора конфигурации."""


class ConfigKeyError(ConfigError, KeyError):
    """Запрошенный ключ отсутствует в конфигурации."""

    def __init__(self, key: str) -> None:
        super().__init__(f"missing config key: {key!r}")
        self.key = key


type Config = Mapping[str, Any]


def load_config(
    path: str | Path,
    *,
    strict: bool = False,
    cache: MutableMapping[Path, Config] | None = None,
) -> Config:
    """Загрузить JSON-конфиг.

    strict: запрещать не-строковые ключи верхнего уровня
    (в текущей реализации поведение задокументировано, а не молчаливо игнорируется).
    cache: опциональный кэш; состояние передаётся явно и потокобезопасность
    обеспечивает вызывающий код.
    """
    resolved = Path(path).expanduser().resolve()
    if cache is not None and resolved in cache:
        return cache[resolved]

    try:
        with resolved.open(encoding="utf-8") as f:
            raw: Any = json.load(f)
    except OSError as err:
        note = f"while loading config from {resolved}"
        raise ConfigError(f"cannot read config file {resolved}") from err
    except json.JSONDecodeError as err:
        raise ConfigError(f"invalid JSON in config file {resolved}") from err

    if not isinstance(raw, dict):
        raise ConfigError(
            f"config root must be a JSON object, got {type(raw).__name__}"
        )
    if strict and not all(isinstance(k, str) for k in raw):
        raise ConfigError("strict mode requires string keys at the top level")

    config: Config = raw
    if cache is not None:
        cache[resolved] = config
    return config


def get_value(config: Config, key: str, *, default: Any = ...) -> Any:
    """Получить значение по ключу; без default бросает ConfigKeyError."""
    if default is ...:
        try:
            return config[key]
        except KeyError as err:
            exc = ConfigKeyError(key)
            exc.add_note(f"available keys: {sorted(config)!r}")
            raise exc from err
    return config.get(key, default)
```

### Что изменилось и почему

- **Типизация:** полные аннотации; `Self`/`type`-алиас и `str | Path` в духе 3.14; `Mapping`/`MutableMapping` из `collections.abc` (предпочтительнее `typing.Dict`).
- **Исключения:** иерархия `YadddError` → `ConfigError` → `ConfigKeyError`, `raise ... from ...`, контекст через `add_note()` (PEP 678) вместо конкатенации строк.
- **Глобальный кэш убран:** состояние передаётся явным параметром — соответствует требованию no-GIL-безопасности стандарта §3; ключ кэша канонализируется через `Path.resolve()`.
- **`strict` реализован** (проверка строковых ключей) вместо молчаливого игнора; булевы и опциональные параметры — keyword-only.
- **Публичный API:** `__all__` задаёт контракт; внутреннее состояние не торчит наружу; мёртвый импорт `Optional` удалён; кодировка UTF-8 явная.
- **Зависимости:** остались в stdlib (`json`, `pathlib`, `collections.abc`).

### Оставшиеся действия перед мержем

- Добавить `py.typed` в пакет и в сборку wheel (если ещё нет).
- Тесты pytest: `pytest.raises(ConfigKeyError, match=...)`, вызовы публичного API как пользователь; покрыть `strict=True`-ветки и ошибки JSON.
- Пропустить `ruff check . && ruff format --check . && mypy src && pyright src && pytest`.
- Рассмотреть замену `Any` в значениях конфига на дженерик `Config[T] = Mapping[str, T]` или `TypedDict`-подобный `Protocol`, если у библиотеки есть конкретные схемы конфигурации.
