"""Tests for yaddd_linter checker rules."""

from pathlib import Path

from yaddd_linter.checker import (
    AggregateMutationChecker,
    LayerIsolationChecker,
    collect_aggregate_names,
)


def _tmp_file(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


class TestLayerIsolationChecker:
    def test_domain_imports_application(self, tmp_path: Path) -> None:
        path = _tmp_file(
            tmp_path,
            "packages/yaddd/src/yaddd/domain/order.py",
            "from yaddd.application.commands import CreateOrder\n",
        )
        violations = LayerIsolationChecker().check(path, path.read_text())
        assert len(violations) == 1
        assert violations[0].code == "YDDD003"
        assert "domain layer imports from application layer" in violations[0].message

    def test_application_imports_domain(self, tmp_path: Path) -> None:
        path = _tmp_file(
            tmp_path,
            "packages/yaddd/src/yaddd/application/service.py",
            "from yaddd.domain.order import Order\n",
        )
        violations = LayerIsolationChecker().check(path, path.read_text())
        assert len(violations) == 0

    def test_stdlib_import_allowed(self, tmp_path: Path) -> None:
        path = _tmp_file(
            tmp_path,
            "packages/yaddd/src/yaddd/domain/order.py",
            "from dataclasses import dataclass\nfrom uuid import UUID\n",
        )
        violations = LayerIsolationChecker().check(path, path.read_text())
        assert len(violations) == 0

    def test_infrastructure_imports_application(self, tmp_path: Path) -> None:
        path = _tmp_file(
            tmp_path,
            "packages/yaddd/src/yaddd/infrastructure/repo.py",
            "from yaddd.application.uow import UnitOfWork\n",
        )
        violations = LayerIsolationChecker().check(path, path.read_text())
        assert len(violations) == 0

    def test_domain_imports_third_party(self, tmp_path: Path) -> None:
        path = _tmp_file(
            tmp_path,
            "packages/yaddd/src/yaddd/domain/order.py",
            "import sqlalchemy\n",
        )
        violations = LayerIsolationChecker().check(path, path.read_text())
        assert len(violations) == 1
        assert violations[0].code == "YDDD004"
        assert "Domain layer imports third-party module" in violations[0].message

    def test_application_imports_third_party_allowed(self, tmp_path: Path) -> None:
        path = _tmp_file(
            tmp_path,
            "packages/yaddd/src/yaddd/application/service.py",
            "import sqlalchemy\n",
        )
        violations = LayerIsolationChecker().check(path, path.read_text())
        assert len(violations) == 0

    def test_plugin_imports_another_plugin(self, tmp_path: Path) -> None:
        path = _tmp_file(
            tmp_path,
            "packages/yaddd-sqlalchemy/src/yaddd_sqlalchemy/repo.py",
            "from yaddd_pydantic.value_objects import PydanticVO\n",
        )
        violations = LayerIsolationChecker().check(path, path.read_text())
        assert len(violations) == 1
        assert violations[0].code == "YDDD005"
        assert "yaddd_sqlalchemy" in violations[0].message
        assert "yaddd_pydantic" in violations[0].message

    def test_plugin_imports_core_allowed(self, tmp_path: Path) -> None:
        path = _tmp_file(
            tmp_path,
            "packages/yaddd-sqlalchemy/src/yaddd_sqlalchemy/repo.py",
            "from yaddd.domain.entities import AggregateRoot\n",
        )
        violations = LayerIsolationChecker().check(path, path.read_text())
        assert len(violations) == 0

    def test_src_layout_with_any_package_name_is_recognised(self, tmp_path: Path) -> None:
        path = _tmp_file(
            tmp_path,
            "apps/orders/src/orders/domain/order.py",
            "from orders.application.commands import CreateOrder\n",
        )

        violations = LayerIsolationChecker().check(path, path.read_text())

        assert len(violations) == 1
        assert violations[0].code == "YDDD003"

    def test_domain_imports_serialization_plugin_allowed(self, tmp_path: Path) -> None:
        path = _tmp_file(
            tmp_path,
            "packages/yaddd/src/yaddd/domain/order.py",
            "from yaddd_pydantic import PydanticVO\n",
        )

        violations = LayerIsolationChecker().check(path, path.read_text())

        assert len(violations) == 0

    def test_domain_imports_pydantic_for_constraints_allowed(self, tmp_path: Path) -> None:
        path = _tmp_file(
            tmp_path,
            "packages/yaddd/src/yaddd/domain/order.py",
            "from pydantic import Field\n",
        )

        violations = LayerIsolationChecker().check(path, path.read_text())

        assert len(violations) == 0

    def test_domain_imports_persistence_plugin_flagged(self, tmp_path: Path) -> None:
        path = _tmp_file(
            tmp_path,
            "packages/yaddd/src/yaddd/domain/order.py",
            "from yaddd_sqlalchemy import SqlCrudRepository\n",
        )

        violations = LayerIsolationChecker().check(path, path.read_text())

        assert len(violations) == 1
        assert violations[0].code == "YDDD004"

    def test_src_layout_infrastructure_imports_domain(self, tmp_path: Path) -> None:
        path = _tmp_file(
            tmp_path,
            "apps/orders/src/orders/infrastructure/db.py",
            "from orders.domain.order import Order\n",
        )

        violations = LayerIsolationChecker().check(path, path.read_text())

        assert len(violations) == 0

    def test_flat_layout_domain_imports_application(self, tmp_path: Path) -> None:
        path = _tmp_file(
            tmp_path,
            "app/domain/order.py",
            "from app.application.commands import CreateOrder\n",
        )

        violations = LayerIsolationChecker().check(path, path.read_text())

        assert len(violations) == 1
        assert violations[0].code == "YDDD003"

    def test_flat_layout_domain_imports_own_package(self, tmp_path: Path) -> None:
        path = _tmp_file(
            tmp_path,
            "app/domain/order.py",
            "from app.domain.value_objects import Money\n",
        )

        violations = LayerIsolationChecker().check(path, path.read_text())

        assert len(violations) == 0

    def test_flat_layout_domain_imports_third_party(self, tmp_path: Path) -> None:
        path = _tmp_file(
            tmp_path,
            "app/domain/order.py",
            "import sqlalchemy\n",
        )

        violations = LayerIsolationChecker().check(path, path.read_text())

        assert len(violations) == 1
        assert violations[0].code == "YDDD004"

    def test_flat_layout_domain_imports_foreign_top_level_package(self, tmp_path: Path) -> None:
        path = _tmp_file(
            tmp_path,
            "app/domain/order.py",
            "from lib.util import helper\n",
        )

        violations = LayerIsolationChecker().check(path, path.read_text())

        assert len(violations) == 1
        assert violations[0].code == "YDDD004"


class TestAggregateMutationChecker:
    def test_mutation_outside_aggregate(self, tmp_path: Path) -> None:
        source = """
from yaddd.domain.entities import AggregateRoot
from uuid import UUID

class Order(AggregateRoot):
    id: UUID
    status: str

    def pay(self) -> None:
        self.status = "paid"

async def bad_handler(order: Order) -> None:
    order.status = "shipped"
"""
        path = _tmp_file(tmp_path, "app.py", source)
        aggregates = collect_aggregate_names([path])
        violations = AggregateMutationChecker(aggregates).check(path, source)
        assert len(violations) == 1
        assert violations[0].code == "YDDD001"
        assert "status" in violations[0].message
        assert "order" in violations[0].message

    def test_self_mutation_inside_aggregate_allowed(self, tmp_path: Path) -> None:
        source = """
from yaddd.domain.entities import AggregateRoot
from uuid import UUID

class Order(AggregateRoot):
    id: UUID
    status: str

    def pay(self) -> None:
        self.status = "paid"
"""
        path = _tmp_file(tmp_path, "app.py", source)
        aggregates = collect_aggregate_names([path])
        violations = AggregateMutationChecker(aggregates).check(path, source)
        assert len(violations) == 0

    def test_mutation_of_constructed_aggregate(self, tmp_path: Path) -> None:
        source = """
from yaddd.domain.entities import AggregateRoot
from uuid import UUID

class Order(AggregateRoot):
    id: UUID
    status: str

def create() -> None:
    order = Order(id=UUID(int=0), status="new")
    order.status = "paid"
"""
        path = _tmp_file(tmp_path, "app.py", source)
        aggregates = collect_aggregate_names([path])
        violations = AggregateMutationChecker(aggregates).check(path, source)
        assert len(violations) == 1
        assert violations[0].code == "YDDD001"

    def test_mutating_call_on_aggregate_attribute(self, tmp_path: Path) -> None:
        source = """
from yaddd.domain.entities import AggregateRoot
from uuid import UUID

class Order(AggregateRoot):
    id: UUID
    items: list[str]

def bad_handler(order: Order) -> None:
    order.items.append("new")
"""
        path = _tmp_file(tmp_path, "app.py", source)
        aggregates = collect_aggregate_names([path])
        violations = AggregateMutationChecker(aggregates).check(path, source)
        assert len(violations) == 1
        assert violations[0].code == "YDDD002"
