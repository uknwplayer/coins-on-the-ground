from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from coins_on_the_ground.opportunity import Opportunity


class Scout(Protocol):
    """Read-only opportunity source.

    Scouts discover and normalize public candidates. They do not claim rewards,
    move assets, authenticate as third parties, or execute financial actions.
    """

    name: str

    def discover(self) -> AsyncIterator[Opportunity]:
        """Yield normalized opportunities discovered from the source."""
        ...
