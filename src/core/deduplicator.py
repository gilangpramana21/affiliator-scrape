"""Deduplicator for AffiliatorData records.

Tracks seen usernames and prevents duplicate records from being stored.
"""

from __future__ import annotations

import logging
from typing import List, Set

from src.models.models import AffiliatorData

logger = logging.getLogger(__name__)


class Deduplicator:
    """Deduplicates AffiliatorData records using username as the unique key."""

    def __init__(self) -> None:
        self._seen_usernames: Set[str] = set()
        self._unique_records: List[AffiliatorData] = []
        self._duplicate_count: int = 0

    def is_duplicate(self, affiliator: AffiliatorData) -> bool:
        """Return True if the affiliator's username has already been seen."""
        return affiliator.username in self._seen_usernames

    def add(self, affiliator: AffiliatorData) -> bool:
        """Add an affiliator record if it is not a duplicate.

        Returns True if the record was added, False if it was a duplicate.
        """
        if self.is_duplicate(affiliator):
            self._duplicate_count += 1
            logger.warning(
                "Duplicate affiliator detected: username='%s'", affiliator.username
            )
            return False

        self._seen_usernames.add(affiliator.username)
        self._unique_records.append(affiliator)
        return True

    def get_unique_count(self) -> int:
        """Return the number of unique affiliator records."""
        return len(self._unique_records)

    def get_duplicate_count(self) -> int:
        """Return the number of duplicate records detected."""
        return self._duplicate_count

    def get_all(self) -> List[AffiliatorData]:
        """Return a copy of the unique records list."""
        return list(self._unique_records)

    def clear(self) -> None:
        """Reset all internal state."""
        self._seen_usernames.clear()
        self._unique_records.clear()
        self._duplicate_count = 0
