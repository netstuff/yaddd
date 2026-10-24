"""In-process notification adapters.

Real notification delivery (e-mail, push, SMS) would live here as concrete
implementations of :class:`app.application.notifications.NotificationSender`.
The default adapter is a no-op that only logs, keeping the template runnable
without third-party delivery credentials.
"""

import logging
from collections.abc import Mapping
from typing import Any


__all__ = ["NoOpNotificationSender"]

logger = logging.getLogger(__name__)


class NoOpNotificationSender:
    """Logs notifications instead of delivering them."""

    async def send(self, *, event_type: str, payload: Mapping[str, Any]) -> None:
        logger.info("notification %s for order %s", event_type, payload.get("order_id", "-"))
