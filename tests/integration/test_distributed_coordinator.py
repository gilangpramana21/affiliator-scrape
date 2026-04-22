"""Integration tests for DistributedCoordinator using fakeredis.

Tests cover:
- acquire_lock prevents double-locking (only one instance wins)
- release_lock frees the resource so another instance can acquire it
- release_lock is a no-op when the caller does not own the lock
- register_instance / deregister_instance lifecycle
- get_active_instances returns registered instances
- heartbeat refreshes the TTL
- check_health returns True for a live Redis connection
- recover_failed_instances requeues stuck work items
"""

import time

import fakeredis
import pytest

from src.core.distributed_coordinator import (
    DistributedCoordinator,
    LOCK_PREFIX,
    INSTANCE_PREFIX,
)
from src.core.distributed_queue import DistributedWorkQueue


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def redis_client():
    """Isolated fakeredis client for each test."""
    client = fakeredis.FakeRedis(decode_responses=True)
    yield client
    client.flushall()
    client.close()


@pytest.fixture
def coordinator(redis_client):
    """DistributedCoordinator for instance 'instance-A'."""
    return DistributedCoordinator(redis_client, instance_id="instance-A", ttl=30)


@pytest.fixture
def coordinator_b(redis_client):
    """Second DistributedCoordinator for instance 'instance-B' (same Redis)."""
    return DistributedCoordinator(redis_client, instance_id="instance-B", ttl=30)


@pytest.fixture
def work_queue(redis_client):
    """DistributedWorkQueue backed by the same fakeredis client."""
    return DistributedWorkQueue(redis_client)


# ---------------------------------------------------------------------------
# 23.1 Distributed locking
# ---------------------------------------------------------------------------


class TestAcquireLock:
    def test_acquire_returns_true_when_free(self, coordinator):
        assert coordinator.acquire_lock("affiliator-xyz") is True

    def test_acquire_sets_key_in_redis(self, coordinator, redis_client):
        coordinator.acquire_lock("affiliator-xyz")
        assert redis_client.exists(f"{LOCK_PREFIX}affiliator-xyz") == 1

    def test_acquire_stores_instance_id_as_value(self, coordinator, redis_client):
        coordinator.acquire_lock("affiliator-xyz")
        value = redis_client.get(f"{LOCK_PREFIX}affiliator-xyz")
        assert value == "instance-A"

    def test_acquire_prevents_double_locking(self, coordinator, coordinator_b):
        """First instance acquires; second instance must fail."""
        assert coordinator.acquire_lock("affiliator-xyz", timeout=0) is True
        assert coordinator_b.acquire_lock("affiliator-xyz", timeout=0) is False

    def test_acquire_same_instance_twice_fails(self, coordinator):
        """Acquiring the same lock twice from the same instance also fails (NX)."""
        assert coordinator.acquire_lock("affiliator-xyz", timeout=0) is True
        assert coordinator.acquire_lock("affiliator-xyz", timeout=0) is False

    def test_acquire_different_resources_independent(self, coordinator, coordinator_b):
        """Locks on different resource keys are independent."""
        assert coordinator.acquire_lock("resource-1", timeout=0) is True
        assert coordinator_b.acquire_lock("resource-2", timeout=0) is True


class TestReleaseLock:
    def test_release_returns_true_when_owner(self, coordinator):
        coordinator.acquire_lock("affiliator-xyz", timeout=0)
        assert coordinator.release_lock("affiliator-xyz") is True

    def test_release_removes_key_from_redis(self, coordinator, redis_client):
        coordinator.acquire_lock("affiliator-xyz", timeout=0)
        coordinator.release_lock("affiliator-xyz")
        assert redis_client.exists(f"{LOCK_PREFIX}affiliator-xyz") == 0

    def test_release_allows_reacquisition(self, coordinator, coordinator_b):
        """After release, another instance can acquire the lock."""
        coordinator.acquire_lock("affiliator-xyz", timeout=0)
        coordinator.release_lock("affiliator-xyz")
        assert coordinator_b.acquire_lock("affiliator-xyz", timeout=0) is True

    def test_release_returns_false_when_not_owner(self, coordinator, coordinator_b):
        """Instance B cannot release a lock held by instance A."""
        coordinator.acquire_lock("affiliator-xyz", timeout=0)
        assert coordinator_b.release_lock("affiliator-xyz") is False

    def test_release_returns_false_when_lock_absent(self, coordinator):
        assert coordinator.release_lock("nonexistent-resource") is False

    def test_release_does_not_remove_others_lock(self, coordinator, coordinator_b, redis_client):
        """Attempting to release another instance's lock leaves it intact."""
        coordinator.acquire_lock("affiliator-xyz", timeout=0)
        coordinator_b.release_lock("affiliator-xyz")
        assert redis_client.exists(f"{LOCK_PREFIX}affiliator-xyz") == 1


# ---------------------------------------------------------------------------
# 23.2 Instance registration
# ---------------------------------------------------------------------------


class TestInstanceRegistration:
    def test_register_creates_key(self, coordinator, redis_client):
        coordinator.register_instance()
        assert redis_client.exists(f"{INSTANCE_PREFIX}instance-A") == 1

    def test_register_key_has_ttl(self, coordinator, redis_client):
        coordinator.register_instance()
        ttl = redis_client.ttl(f"{INSTANCE_PREFIX}instance-A")
        assert ttl > 0

    def test_deregister_removes_key(self, coordinator, redis_client):
        coordinator.register_instance()
        coordinator.deregister_instance()
        assert redis_client.exists(f"{INSTANCE_PREFIX}instance-A") == 0

    def test_get_active_instances_returns_registered(self, coordinator, coordinator_b):
        coordinator.register_instance()
        coordinator_b.register_instance()
        active = coordinator.get_active_instances()
        assert "instance-A" in active
        assert "instance-B" in active

    def test_get_active_instances_excludes_deregistered(self, coordinator, coordinator_b):
        coordinator.register_instance()
        coordinator_b.register_instance()
        coordinator_b.deregister_instance()
        active = coordinator.get_active_instances()
        assert "instance-A" in active
        assert "instance-B" not in active

    def test_get_active_instances_empty_when_none_registered(self, coordinator):
        assert coordinator.get_active_instances() == []

    def test_heartbeat_refreshes_ttl(self, coordinator, redis_client):
        """Heartbeat should keep the TTL from reaching zero."""
        coordinator.register_instance()
        key = f"{INSTANCE_PREFIX}instance-A"
        # Manually reduce TTL to 1 second
        redis_client.expire(key, 1)
        coordinator.heartbeat()
        ttl_after = redis_client.ttl(key)
        # TTL should have been reset to the full ttl (30s)
        assert ttl_after > 1


# ---------------------------------------------------------------------------
# 23.3 Health checking
# ---------------------------------------------------------------------------


class TestHealthCheck:
    def test_check_health_returns_true_for_live_redis(self, coordinator):
        assert coordinator.check_health() is True

    def test_check_health_returns_false_for_dead_redis(self):
        """Simulate a dead connection by mocking ping to raise a ConnectionError."""
        from unittest.mock import MagicMock
        client = MagicMock()
        client.ping.side_effect = ConnectionError("Connection refused")
        coord = DistributedCoordinator(client, instance_id="dead-instance")
        assert coord.check_health() is False


# ---------------------------------------------------------------------------
# 23.4 Failure recovery
# ---------------------------------------------------------------------------


class TestFailureRecovery:
    def test_recover_requeues_stuck_items(self, coordinator, work_queue, redis_client):
        """Items stuck in processing (simulating a crash) are requeued."""
        work_queue.push_work({"affiliator": "user1"})
        work_queue.push_work({"affiliator": "user2"})
        # Simulate two instances that crashed mid-processing
        work_queue.pop_work(timeout=1)
        work_queue.pop_work(timeout=1)
        assert work_queue.get_queue_size() == 0

        count = coordinator.recover_failed_instances(work_queue)
        assert count == 2
        assert work_queue.get_queue_size() == 2

    def test_recover_returns_zero_when_nothing_stuck(self, coordinator, work_queue):
        count = coordinator.recover_failed_instances(work_queue)
        assert count == 0

    def test_recover_requeued_items_can_be_processed(self, coordinator, work_queue):
        item = {"affiliator": "user1"}
        work_queue.push_work(item)
        work_queue.pop_work(timeout=1)
        coordinator.recover_failed_instances(work_queue)
        recovered = work_queue.pop_work(timeout=1)
        assert recovered == item

    def test_recover_does_not_affect_completed_items(self, coordinator, work_queue, redis_client):
        """Completed items should not be requeued."""
        item = {"affiliator": "done-user"}
        work_queue.push_work(item)
        popped = work_queue.pop_work(timeout=1)
        work_queue.complete_work(popped)
        count = coordinator.recover_failed_instances(work_queue)
        assert count == 0
        assert work_queue.get_queue_size() == 0
