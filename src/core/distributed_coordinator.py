"""Distributed coordinator for multi-instance scraping coordination.

Provides distributed locking, instance registration, health checking,
and failure recovery using Redis.
"""

import logging
import time
from typing import List, Optional, TYPE_CHECKING

import redis

if TYPE_CHECKING:
    from src.core.distributed_queue import DistributedWorkQueue

logger = logging.getLogger(__name__)

LOCK_PREFIX = "scraper:lock:"
INSTANCE_PREFIX = "scraper:instances:"


class DistributedCoordinator:
    """Coordinates multiple scraper instances via Redis.

    Provides:
    - Distributed locking (SET NX EX) to prevent duplicate work
    - Instance registration and heartbeat for liveness tracking
    - Health checking via Redis ping
    - Failure recovery by detecting dead instances and requeuing their work
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        instance_id: str,
        ttl: int = 30,
    ) -> None:
        """Initialise the coordinator.

        Args:
            redis_client: A connected redis.Redis (or fakeredis) client.
            instance_id: Unique identifier for this scraper instance.
            ttl: Time-to-live in seconds for locks and instance heartbeats.
        """
        self.redis = redis_client
        self.instance_id = instance_id
        self.ttl = ttl

    # ------------------------------------------------------------------
    # 23.1 Distributed locking
    # ------------------------------------------------------------------

    def acquire_lock(self, resource_key: str, timeout: int = 10) -> bool:
        """Attempt to acquire a distributed lock for *resource_key*.

        Uses the Redis SET NX EX pattern so the lock is automatically
        released after *ttl* seconds even if the holder crashes.

        Args:
            resource_key: Logical name of the resource to lock (e.g. an
                affiliator username).
            timeout: Maximum seconds to spend trying to acquire the lock.

        Returns:
            True if the lock was acquired, False if it could not be
            obtained within *timeout* seconds.
        """
        lock_key = f"{LOCK_PREFIX}{resource_key}"
        deadline = time.monotonic() + timeout
        while True:
            acquired = self.redis.set(
                lock_key,
                self.instance_id,
                nx=True,
                ex=self.ttl,
            )
            if acquired:
                logger.debug("Lock acquired: %s by %s", lock_key, self.instance_id)
                return True
            if time.monotonic() >= deadline:
                break
            # Brief sleep before retry to avoid busy-waiting
            time.sleep(0.05)
        logger.debug("Lock NOT acquired: %s (timeout)", lock_key)
        return False

    def release_lock(self, resource_key: str) -> bool:
        """Release a lock only if this instance owns it.

        Args:
            resource_key: The same key passed to acquire_lock().

        Returns:
            True if the lock was released, False if it was not owned by
            this instance (or did not exist).
        """
        lock_key = f"{LOCK_PREFIX}{resource_key}"
        current_owner = self.redis.get(lock_key)
        if current_owner is None:
            logger.debug("Release skipped: lock %s does not exist", lock_key)
            return False
        # Normalise bytes → str
        if isinstance(current_owner, bytes):
            current_owner = current_owner.decode("utf-8")
        if current_owner != self.instance_id:
            logger.debug(
                "Release skipped: lock %s owned by %s, not %s",
                lock_key,
                current_owner,
                self.instance_id,
            )
            return False
        self.redis.delete(lock_key)
        logger.debug("Lock released: %s by %s", lock_key, self.instance_id)
        return True

    # ------------------------------------------------------------------
    # 23.2 Instance registration
    # ------------------------------------------------------------------

    def register_instance(self) -> None:
        """Register this instance in Redis with a TTL-based heartbeat key.

        The key ``scraper:instances:{instance_id}`` is set with the
        current timestamp as value and expires after *ttl* seconds.
        Call heartbeat() periodically to keep the registration alive.
        """
        key = f"{INSTANCE_PREFIX}{self.instance_id}"
        self.redis.setex(key, self.ttl, str(time.time()))
        logger.info("Instance registered: %s (ttl=%ds)", self.instance_id, self.ttl)

    def heartbeat(self) -> None:
        """Refresh the TTL of this instance's registration key.

        Should be called at an interval shorter than *ttl* to prevent
        the key from expiring while the instance is still alive.
        """
        key = f"{INSTANCE_PREFIX}{self.instance_id}"
        self.redis.expire(key, self.ttl)
        logger.debug("Heartbeat sent: %s", self.instance_id)

    def get_active_instances(self) -> List[str]:
        """Return the list of currently registered instance IDs.

        Uses KEYS to scan for ``scraper:instances:*`` entries.  Only
        instances that have not yet expired are returned.

        Returns:
            List of instance ID strings.
        """
        pattern = f"{INSTANCE_PREFIX}*"
        keys = self.redis.keys(pattern)
        prefix_len = len(INSTANCE_PREFIX)
        instances = []
        for key in keys:
            if isinstance(key, bytes):
                key = key.decode("utf-8")
            instances.append(key[prefix_len:])
        return instances

    def deregister_instance(self) -> None:
        """Remove this instance's registration key from Redis."""
        key = f"{INSTANCE_PREFIX}{self.instance_id}"
        self.redis.delete(key)
        logger.info("Instance deregistered: %s", self.instance_id)

    # ------------------------------------------------------------------
    # 23.3 Health checking
    # ------------------------------------------------------------------

    def check_health(self) -> bool:
        """Verify that the Redis connection is alive.

        Returns:
            True if Redis responds to PING, False otherwise.
        """
        try:
            return self.redis.ping()
        except Exception as exc:
            logger.error("Redis health check failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # 23.4 Failure recovery
    # ------------------------------------------------------------------

    def recover_failed_instances(self, work_queue: "DistributedWorkQueue") -> int:
        """Detect dead instances and requeue their in-flight work.

        An instance is considered dead when its heartbeat key has expired
        (i.e. it no longer appears in get_active_instances()).  This
        method calls work_queue.requeue_failed() to move any items stuck
        in the processing queue back to pending so they can be retried.

        Args:
            work_queue: The shared DistributedWorkQueue to requeue work on.

        Returns:
            Number of work items requeued.
        """
        requeued = work_queue.requeue_failed()
        if requeued:
            logger.info(
                "Failure recovery: requeued %d items from dead instances", requeued
            )
        return requeued
