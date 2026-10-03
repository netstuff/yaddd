from uuid import UUID, uuid4

from yaddd.domain import AggregateRoot, DomainService


class Account(AggregateRoot):
    id: UUID
    balance: int

    def withdraw(self, amount: int) -> None:
        self.balance -= amount

    def deposit(self, amount: int) -> None:
        self.balance += amount


class TransferService:
    """Domain service: moves money between two accounts."""

    def transfer(self, source: Account, target: Account, amount: int) -> None:
        source.withdraw(amount)
        target.deposit(amount)


def test_domain_service_operates_across_aggregates():
    service = TransferService()
    source = Account(id=uuid4(), balance=100)
    target = Account(id=uuid4(), balance=0)

    service.transfer(source, target, 40)

    assert source.balance == 60
    assert target.balance == 40


def test_domain_service_marker_protocol_structural_conformance():
    service: DomainService = TransferService()  # type-checks structurally; no runtime members
    assert service is not None
