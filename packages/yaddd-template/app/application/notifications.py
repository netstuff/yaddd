"""Notification port used by post-order scenarios.

Scenarios are decoupled from concrete delivery mechanisms (e-mail, push,
broker-side events) by this small protocol. The composition root decides which
implementation is active in a given process.
"""

from collections.abc import Mapping
from typing import Any, Protocol


__all__ = ["NotificationSender"]


class NotificationSender(Protocol):
    """Fire-and-forget sender of application notifications."""

    async def send(self, *, event_type: str, payload: Mapping[str, Any]) -> None: ...
