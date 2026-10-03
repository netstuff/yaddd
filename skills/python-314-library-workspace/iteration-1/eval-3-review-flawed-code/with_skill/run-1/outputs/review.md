# Ревью кода перед мержем

Проверено по `references/review-checklist.md` (skill `python-314-library`). Пункты чек-листа указаны в скобках. Найдено 12 проблем, отсортировано по серьёзности.

## Blocker — не мержить

### 1. Полное отсутствие аннотаций типов (Typing)
Ни одна публичная функция не аннотирована: `load_config(path, strict=False)`, `get_value(config, key)`.
`mypy --strict` отклонит файл сразу (`disallow_untyped_defs`), pyright strict аналогично. При этом
библиотека заявляет строгую типизацию: неаннотированный публичный API ломает проверку типов у
пользователей. `json.load()` возвращает `Any`, и без аннотаций это `Any` протекает наружу молча.

### 2. `raise Exception("missing key")` (Public API)
Нарушены сразу четыре правила из раздела про исключения:
- поднимается голый `Exception` вместо специфичного подкласса от библиотечной базы;
- оригинальный `KeyError` теряется — нет chaining `raise ... from ...`;
- контекст (какой именно ключ, какие есть) не добавлен через `exc.add_note()` (PEP 678);
- конструкция `try/except KeyError: raise Exception(...)` — анти-паттерн: перехватываем исключение,
  чтобы выбросить менее информативное.

### 3. Модульный мутабельный кэш `CACHE = {}` (Deprecation & compatibility, Python 3.14)
Раздел 3 стандарта прямо запрещает module-level mutable caches и глобальные реестры — free-threaded
(no-GIL) сборки уже в дикой природе, и `CACHE[path] = data` без синхронизации даёт гонку. Кроме того:
кэш неограничен по размеру, ключуется сырым `path` (две разные строки одного файла — два слота),
инвалидации нет, а объявленный UPPERCASE-именем он становится случайной публичной частью API.

### 4. Мёртвый параметр `strict`
`strict=False` принимается, но нигде не используется — молчаливая ложь в публичном API. Либо
параметр должен что-то делать, либо его нет. «Молчаливое изменение поведения запрещено» работает и
в обе стороны: обещанное поведение не реализовано.

### 5. Легаси-алиасы `typing.Dict` / `typing.Optional` (Typing, 3.14)
`from typing import Any, Dict, Optional` — запрещённая привычка «any modern Python». Ruff с
`target-version = "py314"` и правилами `UP` это перепишет (`UP006`/`UP007`): `dict[str, Any]`,
`X | None`. В 3.14 псевдонимы типов оформляются через PEP 695 (`type Config = ...`).

## Major — исправить до мержа

### 6. `Optional` импортирован, но не используется (Toolchain)
`F401` — `ruff check` не пройдёт.

### 7. Булев параметр позиционный (Public API)
`def load_config(path, strict=False)` — булев аргумент позиционно это ловушка читаемости. Правило:
все булевы и функции с >1 параметром — keyword-only: `def load_config(path, *, strict: bool = ...)`.

### 8. Нет `__all__` и дисциплины публичных имён (Public API)
Модуль экспортирует всё подряд: `json`, `Any`, `CACHE`, `Config`... По стандарту модуль объявляет
`__all__`, всё прочее приватно (с `_`). `CACHE` как публичное имя — следствие этого пропуска.

### 9. Нет тестов (Tests)
Новое публичное поведение не покрыто pytest-тестами: нет `pytest.raises(ConfigError, match=...)`
проверки контракта сообщения об ошибке, нет теста кэширования и загрузки. Правило: изменение не
готово, пока не зелёные `pytest`, `mypy src`, `pyright src`, `ruff check`, `ruff format --check`.

## Minor — замечания

### 10. `open(path)` без `encoding`
Поведение зависит от locale пользователя. Для детерминированной библиотеки — явный `encoding="utf-8"`
(через `pathlib.Path.open` или `io`).

### 11. Алиас `Config` объявлен после использующих функций
Читаемость и порядок «публичная поверхность сверху»: сигнатуры используют `Config` до его
определения. Плюс — см. п. 5: синтаксис PEP 695.

### 12. `Any` в публичном API — не оговорён
`Config = Dict[str, Any]` протекает `Any` везде. Для JSON-конфига это честно (значения действительно
произвольны), но это должно быть осознанным решением, задокументированным в сигнатуре, а не
следствием безразличия.

## Что прошло

- Зависимости: только stdlib (`json`, `typing`) — stdlib-first соблюдён, третьих сторон нет.
- Классы-иерархии, метаклассы, декораторы-переписыватели сигнатур — отсутствуют (KISS ок).

## Переписанная версия

```python
"""Загрузка и доступ к JSON-конфигурации."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = ["Config", "ConfigCache", "ConfigError", "get_value", "load_config"]

# Псевдоним PEP 695. Any здесь осознанный выбор: значения JSON-подобны.
type Config = dict[str, Any]


class ConfigError(Exception):
    """Ошибка загрузки или доступа к конфигурации."""


def load_config(path: str | Path) -> Config:
    """Загрузить JSON-файл и вернуть верхнеуровневый объект.

    Верхнеуровневое значение обязано быть JSON-объектом — это же валидация,
    которую раньше должен был делать (но не делал) параметр `strict`.
    """
    with Path(path).open(encoding="utf-8") as f:
        data: Any = json.load(f)
    if not isinstance(data, dict):
        msg = f"expected a JSON object at the top level of {path}"
        raise ConfigError(msg)
    return data  # isinstance сузил тип: мимо mypy --strict не пройдёт непроверенный Any


def get_value(config: Config, key: str) -> Any:
    """Вернуть config[key]; при отсутствии ключа — ConfigError с контекстом."""
    try:
        return config[key]
    except KeyError as exc:
        err = ConfigError(f"missing key: {key!r}")
        err.add_note(f"available keys: {sorted(config)!r}")
        raise err from exc


@dataclass(slots=True)
class ConfigCache:
    """Явный кэш конфигураций: владение состоянием у вызывающего, не у модуля.

    Не потокобезопасен — делитесь экземпляром осознанно. Это замена глобальному
    CACHE для free-threaded (no-GIL) сборок: состояние передаётся явно.
    """

    _configs: dict[Path, Config] = field(default_factory=dict)

    def load(self, path: str | Path) -> Config:
        key = Path(path)
        if key not in self._configs:
            self._configs[key] = load_config(key)
        return self._configs[key]
```

Ключевые решения при переписывании:

- **`strict` удалён**, а не оживлён: для голого `json` у него нет честной семантики без схемы.
  Проверка «верхний уровень — объект» стала безусловной. Если понадобится настоящая валидация —
  это отдельное дизайн-решение (возможно, optional-extra на pydantic, лениво импортируемый).
- **Глобальный `CACHE` заменён на явный `ConfigCache`** со `slots=True` — состояние передаётся
  вызывающим, потокобезопасность честно задокументирована («не потокобезопасен» лучше молчаливой
  гонки).
- **`Any` в сигнатуре `get_value` — осознанный** (JSON-значения произвольны), остальное проверено:
  `load_config` сужает `Any` через `isinstance`, что проходит `warn_return_any` из `mypy --strict`.
- **Исключения**: библиотечная база `ConfigError`, chaining `from exc`, контекст через `add_note()`,
  а не склейка строк в сообщение.
- Перед мержем дополнительно нужны: `tests/` (в т.ч. `pytest.raises(ConfigError, match="missing key")`),
  `py.typed` в пакете и экспорт из корневого `__init__.py` с `__all__`, прогон
  `ruff check && ruff format --check && mypy src && pyright src && pytest`.
