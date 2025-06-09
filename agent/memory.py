"""Simple short-term memory storage using a deque."""

from __future__ import annotations

from collections import deque
from typing import Deque, List


class ShortTermMemory:
    """A fixed-size short-term memory buffer.

    Parameters
    ----------
    limit:
        Maximum number of messages to store. Older messages are
        discarded once the limit is exceeded.
    """

    def __init__(self, limit: int = 10) -> None:
        self.limit = limit
        self._messages: Deque[str] = deque(maxlen=limit)

    def add(self, message: str) -> None:
        """Insert a message into memory.

        Parameters
        ----------
        message:
            Text message to store.
        """
        self._messages.append(message)

    def get(self) -> List[str]:
        """Return all messages currently stored in order."""
        return list(self._messages)

