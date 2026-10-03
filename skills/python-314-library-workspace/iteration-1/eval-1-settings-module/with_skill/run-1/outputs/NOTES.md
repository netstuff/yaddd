# NOTES: модуль `yaddd.settings_config`

## Что сделано

Модуль `src/yaddd/settings_config.py` — загрузка настроек из переменных
окружения с дефолтами и типизированным доступом, только stdlib
(`os`, `typing`, `collections.abc`). `pydantic-settings` не используется —
заменяет собой старый `src_old/yaddd/settings/http.py`, который тянул
pydantic в обязательные зависимости.

Публичный API модуля (всё в `__all__`):

- `Settings` — базовый класс. Пользователь объявляет subclass с
  аннотированными атрибутами класса: значение атрибута — дефолт, атрибут
  без дефолта — обязательная настройка. Загрузка — `Settings.from_env()`.
- `SettingsError` — базовый класс ошибок модуля.
- `MissingSettingError` — обязательная настройка не задана ни дефолтом, ни env.
- `InvalidSettingError` — значение env не конвертируется в объявленный тип.
- `UnsupportedSettingTypeError` — объявлен неподдерживаемый тип поля.

Поддерживаемые типы полей: `str`, `int`, `float`, `bool`
(bool парсится из `1/true/yes/on`, `0/false/no/off`, регистронезависимо).
Имя переменной окружения: `prefix + name.upper()`, префикс задаётся
keyword-аргументом `from_env(prefix="MYAPP_")`. `environ` можно передать
явно (например, `dict` в тестах) — иначе читается `os.environ`.

Пример использования:

```python
from yaddd import Settings


class ServerSettings(Settings):
    host: str = "localhost"
    port: int = 8000
    debug: bool = False
    api_key: str  # required: без дефолта


settings = ServerSettings.from_env(prefix="MYAPP_")
settings.port  # int, типизированный доступ
```

## Экспорт публичного API из пакета

Файл `src/yaddd/__init__.py` (скелет — пакет сейчас в репозитории пустой,
после реструктуризации):

```python
"""yaddd public API."""

from yaddd.settings_config import (
    InvalidSettingError,
    MissingSettingError,
    Settings,
    SettingsError,
    UnsupportedSettingTypeError,
)

__all__ = [
    "InvalidSettingError",
    "MissingSettingError",
    "Settings",
    "SettingsError",
    "UnsupportedSettingTypeError",
]
```

Правило навыка: один импорт покрывает 95% случаев, всё не в `__all__` —
приватно. В модуле служебные имена (`_PARSERS`, `_parse_bool`, `_convert`,
`_MISSING`) вынесены вниз файла и начинаются с `_`.

## Какие правила навыка применены

- **§1 stdlib-first**: только stdlib; десятков строк кода хватает, чтобы не
  тянуть `pydantic-settings` в core. Core-зависимости остаются пустыми.
- **§2 strict typing**: полная аннотация всех публичных символов,
  `Self` для `from_env` (корректный тип возвращаемого инстанса),
  `Final` для констант модуля. Проверено `mypy --strict` и `pyright` —
  оба чисто. Аннотации читаются через `typing.get_type_hints()`, а не через
  `cls.__annotations__` — это правило §3 (PEP 649: deferred annotations по
  умолчанию в 3.14).
- **§3 Python 3.14**: никаких `typing_extensions`/шимов; контекст ошибок
  добавляется через `exc.add_note()` (PEP 678), а не склейкой строк в
  сообщение. Module-level состояние — только неизменяемое
  (`frozenset`, dict констант, `Final`), что безопасно для free-threaded
  сборок (§3): мутабельного кеша/реестра нет, состояние живёт в инстансе.
- **§4 public API**: иерархия исключений с корневым `SettingsError`,
  raise самого специфичного подкласса, цепочка `raise ... from exc` при
  конвертации значений; keyword-only параметры у `from_env`
  (`*, environ, prefix`); иммутабельность инстансов (`__setattr__`
  запрещает присваивание, конструктор направляет к `from_env`).
  Про `slots=True`: здесь он неприменим — поля объявляются аннотациями
  на subclass пользователя, а не в одном dataclass; защиту от опечаток и
  мутаций даёт запрет `__setattr__`. `ClassVar`-аннотации отфильтровываются,
  чтобы не попасть в поля настроек.
- **§5 DRY/KISS**: парсеры — dict типов (`_PARSERS`), а не if-цепочка и не
  класс на каждый тип; проверка поддерживаемости типа выполняется до
  чтения env (fail-fast), без отдельной фазы валидации.
- **§6 тесты**: `tests/unit/test_settings_config.py`, 21 тест, публичный API
  вызывается как у пользователя; `pytest.raises(..., match=...)` фиксирует
  контракт сообщений; контракт `add_note` проверяется через `__notes__`,
  цепочка исключений — через `__cause__`; env изолируется явным `environ={}`
  или `monkeypatch` с уникальным префиксом; параметризация для вариантов
  bool. Импорт — в конвенции репозитория (`from src.yaddd...`, `pythonpath =
  ["src"]` из pyproject).
- **§7 toolchain**: импорты отсортированы под конфиг isort репозитория
  (`lines-after-imports = 2`), line-length 120.

## Верификация (скратч-копия репозитория, Python 3.13)

- `pytest` — 21 passed
- `mypy --strict src/yaddd/settings_config.py` — clean
- `pyright src/yaddd/settings_config.py` — 0 errors, 0 warnings
- `ruff check .` / `ruff format --check .` с конфигом репозитория — clean

## Файлы

- `settings_config.py` — исходник модуля (класть в `src/yaddd/`)
- `test_settings_config.py` — тесты (класть в `tests/unit/`)
- `NOTES.md` — этот файл
