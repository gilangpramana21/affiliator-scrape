"""Distributed work queue using Redis for multi-instance scraping coordination."""

import json
import logging
from typing import Optional

import redis

logger = logging.getLogger(__name__)

PENDING_KEY = "scraper:queue:pending"
PROCESSING_KEY = "scraper:queue:processing"
COMPLETED_KEY = "scraper:queue:completed"


class DistributedWorkQueue:
    """Redis-based work queue for distributed scraping.

    Uses Redis lists for pending/processing queues and a Redis set for
    completed items. Supports crash recovery via requeue_failed().

    Queue keys:
        - scraper:queue:pending    - LPUSH / BRPOPLPUSH source
        - scraper:queue:processing - BRPOPLPUSH destination / LREM source
        - scraper:queue:completed  - SADD destination
    """

    def __init__(self, redis_client: redis.Redis):
        """Initialize with a Redis client instance.

        Args:
            redis_client: A connected redis.Redis (or fakeredis) client.
        """
        self.redis = redis_client

    # ------------------------------------------------------------------
    # 22.3 push_work
    # ------------------------------------------------------------------

    def push_work(self, work_item: dict) -> None:
        """Push a work item onto the pending queue.

        Serialises *work_item* as JSON and performs an LPUSH so that
        pop_work() (BRPOPLPUSH from the right) processes items in FIFO
        order.

        Args:
            work_item: Arbitrary dict describing the unit of work.
        """
        payload = json.dumps(work_item, ensure_ascii=False)
        self.redis.lpush(PENDING_KEY, payload)
        logger.debug("Pushed work item: %s", work_item)

    # ------------------------------------------------------------------
    # 22.4 pop_work (blocking)
    # ------------------------------------------------------------------

    def pop_work(self, timeout: int = 30) -> Optional[dict]:
        """Atomically move one item from pending → processing and return it.

        Uses BRPOPLPUSH so the item is visible in the processing queue
        while it is being worked on, enabling crash recovery via
        requeue_failed().

        Args:
            timeout: Seconds to block waiting for an item (0 = forever).

        Returns:
            Deserialised work item dict, or None if the timeout expired.
        """
        result = self.redis.brpoplpush(PENDING_KEY, PROCESSING_KEY, timeout=timeout)
        if result is None:
            return None
        payload = result if isinstance(result, str) else result.decode("utf-8")
        work_item = json.loads(payload)
        logger.debug("Popped work item: %s", work_item)
        return work_item

    # ------------------------------------------------------------------
    # 22.5 complete_work
    # ------------------------------------------------------------------

    def complete_work(self, work_item: dict) -> None:
        """Remove a work item from processing and record it as completed.

        Args:
            work_item: The same dict that was returned by pop_work().
        """
        payload = json.dumps(work_item, ensure_ascii=False)
        removed = self.redis.lrem(PROCESSING_KEY, 1, payload)
        self.redis.sadd(COMPLETED_KEY, payload)
        logger.debug("Completed work item (removed=%d): %s", removed, work_item)

    # ------------------------------------------------------------------
    # 22.6 requeue_failed
    # ------------------------------------------------------------------

    def requeue_failed(self) -> int:
        """Move all items from processing back to pending for retry.

        Intended to be called on startup after a crash so that any items
        that were being processed (but never completed) are retried.

        Returns:
            Number of items requeued.
        """
        count = 0
        while True:
            item = self.redis.rpoplpush(PROCESSING_KEY, PENDING_KEY)
            if item is None:
                break
            count += 1
            logger.debug("Requeued failed item: %s", item)
        logger.info("Requeued %d failed work items", count)
        return count

    # ------------------------------------------------------------------
    # 22.7 is_completed
    # ------------------------------------------------------------------

    def is_completed(self) -> bool:
        """Return True when both pending and processing queues are empty.

        Returns:
            True if there is no more work in flight or waiting.
        """
        pending_len = self.redis.llen(PENDING_KEY)
        processing_len = self.redis.llen(PROCESSING_KEY)
        return pending_len == 0 and processing_len == 0

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_queue_size(self) -> int:
        """Return the number of items waiting in the pending queue."""
        return self.redis.llen(PENDING_KEY)
