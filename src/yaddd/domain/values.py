"""Common domain Value-Objects."""

UUID = NewType("UUID", uuid.UUID)

PrimaryKey = TypeVar("PrimaryKey", UUID, int, str)
