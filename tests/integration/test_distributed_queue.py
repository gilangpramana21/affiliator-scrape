"""Integration tests for DistributedWorkQueue using fakeredis.

Tests cover:
- push/pop round-trip
- complete_work removes item from processing queue
- requeue_failed moves items back to pending
- is_completed returns True when both queues are empty
- get_queue_size reflects pending queue length
"""

import pytest
import fakeredis

from src.core.distributed_queue import (
    DistributedWorkQueue,
    PENDING_KEY,
    PROCESSING_KEY,
    COMPLETED_KEY,
)


@pytest.fixture
def redis_client():
    """Provide an isolated fakeredis client for each test."""
    client = fakeredis.FakeRedis(decode_responses=True)
    yield client
    client.flushall()
    client.close()


@pytest.fixture
def queue(redis_client):
    """Provide a DistributedWorkQueue backed by fakeredis."""
    return DistributedWorkQueue(redis_client)


# ---------------------------------------------------------------------------
# 22.3 push_work
# ---------------------------------------------------------------------------

class TestPushWork:
    def test_push_adds_item_to_pending(self, queue, redis_client):
        queue.push_work({"url": "https://example.com/1"})
        assert redis_client.llen(PENDING_KEY) == 1

    def test_push_multiple_items(self, queue, redis_client):
        for i in range(5):
            queue.push_work({"index": i})
        assert redis_client.llen(PENDING_KEY) == 5

    def test_push_preserves_dict_fields(self, queue, redis_client):
        item = {"url": "https://example.com", "page": 3, "extra": None}
        queue.push_work(item)
        # Peek at the raw value stored in Redis
        raw = redis_client.lrange(PENDING_KEY, 0, -1)
        assert len(raw) == 1
        import json
        stored = json.loads(raw[0])
        assert stored["url"] == item["url"]
        assert stored["page"] == item["page"]


# ---------------------------------------------------------------------------
# 22.4 pop_work
# ---------------------------------------------------------------------------

class TestPopWork:
    def test_pop_returns_pushed_item(self, queue):
        item = {"url": "https://example.com/affiliator/1"}
        queue.push_work(item)
        popped = queue.pop_work(timeout=1)
        assert popped == item

    def test_pop_moves_item_to_processing(self, queue, redis_client):
        queue.push_work({"task": "scrape"})
        queue.pop_work(timeout=1)
        assert redis_client.llen(PENDING_KEY) == 0
        assert redis_client.llen(PROCESSING_KEY) == 1

    def test_pop_returns_none_on_timeout(self, queue):
        result = queue.pop_work(timeout=1)
        assert result is None

    def test_pop_fifo_order(self, queue):
        """Items pushed first should be popped first (FIFO)."""
        items = [{"seq": i} for i in range(3)]
        for item in items:
            queue.push_work(item)
        for expected in items:
            assert queue.pop_work(timeout=1) == expected

    def test_push_pop_round_trip(self, queue):
        """Full round-trip: push then pop returns identical dict."""
        original = {"username": "affiliator_xyz", "page": 7, "retries": 0}
        queue.push_work(original)
        recovered = queue.pop_work(timeout=1)
        assert recovered == original


# ---------------------------------------------------------------------------
# 22.5 complete_work
# ---------------------------------------------------------------------------

class TestCompleteWork:
    def test_complete_removes_from_processing(self, queue, redis_client):
        item = {"url": "https://example.com/done"}
        queue.push_work(item)
        queue.pop_work(timeout=1)
        queue.complete_work(item)
        assert redis_client.llen(PROCESSING_KEY) == 0

    def test_complete_adds_to_completed_set(self, queue, redis_client):
        import json
        item = {"url": "https://example.com/done"}
        queue.push_work(item)
        queue.pop_work(timeout=1)
        queue.complete_work(item)
        members = redis_client.smembers(COMPLETED_KEY)
        assert json.dumps(item, ensure_ascii=False) in members

    def test_complete_does_not_affect_pending(self, queue, redis_client):
        item1 = {"url": "https://example.com/1"}
        item2 = {"url": "https://example.com/2"}
        queue.push_work(item1)
        queue.push_work(item2)
        queue.pop_work(timeout=1)
        queue.complete_work(item1)
        # item2 is still pending
        assert redis_client.llen(PENDING_KEY) == 1

    def test_complete_multiple_items(self, queue, redis_client):
        items = [{"id": i} for i in range(3)]
        for item in items:
            queue.push_work(item)
        popped = [queue.pop_work(timeout=1) for _ in items]
        for item in popped:
            queue.complete_work(item)
        assert redis_client.llen(PROCESSING_KEY) == 0
        assert redis_client.scard(COMPLETED_KEY) == 3


# ---------------------------------------------------------------------------
# 22.6 requeue_failed
# ---------------------------------------------------------------------------

class TestRequeueFailed:
    def test_requeue_moves_processing_to_pending(self, queue, redis_client):
        item = {"url": "https://example.com/retry"}
        queue.push_work(item)
        queue.pop_work(timeout=1)
        # Simulate crash: item is stuck in processing
        assert redis_client.llen(PROCESSING_KEY) == 1
        count = queue.requeue_failed()
        assert count == 1
        assert redis_client.llen(PROCESSING_KEY) == 0
        assert redis_client.llen(PENDING_KEY) == 1

    def test_requeue_returns_count(self, queue):
        for i in range(4):
            queue.push_work({"id": i})
            queue.pop_work(timeout=1)
        count = queue.requeue_failed()
        assert count == 4

    def test_requeue_empty_processing_returns_zero(self, queue):
        count = queue.requeue_failed()
        assert count == 0

    def test_requeued_items_can_be_popped_again(self, queue):
        item = {"url": "https://example.com/retry"}
        queue.push_work(item)
        queue.pop_work(timeout=1)
        queue.requeue_failed()
        recovered = queue.pop_work(timeout=1)
        assert recovered == item


# ---------------------------------------------------------------------------
# 22.7 is_completed
# ---------------------------------------------------------------------------

class TestIsCompleted:
    def test_empty_queues_returns_true(self, queue):
        assert queue.is_completed() is True

    def test_pending_items_returns_false(self, queue):
        queue.push_work({"url": "https://example.com/1"})
        assert queue.is_completed() is False

    def test_processing_items_returns_false(self, queue):
        queue.push_work({"url": "https://example.com/1"})
        queue.pop_work(timeout=1)
        assert queue.is_completed() is False

    def test_all_completed_returns_true(self, queue):
        item = {"url": "https://example.com/1"}
        queue.push_work(item)
        queue.pop_work(timeout=1)
        queue.complete_work(item)
        assert queue.is_completed() is True

    def test_mixed_state_returns_false(self, queue):
        """One item completed, one still processing → not done."""
        item1 = {"id": 1}
        item2 = {"id": 2}
        queue.push_work(item1)
        queue.push_work(item2)
        queue.pop_work(timeout=1)
        queue.pop_work(timeout=1)
        queue.complete_work(item1)
        # item2 still in processing
        assert queue.is_completed() is False


# ---------------------------------------------------------------------------
# get_queue_size
# ---------------------------------------------------------------------------

class TestGetQueueSize:
    def test_empty_queue_size_is_zero(self, queue):
        assert queue.get_queue_size() == 0

    def test_size_reflects_pending_count(self, queue):
        for i in range(7):
            queue.push_work({"id": i})
        assert queue.get_queue_size() == 7

    def test_size_decreases_after_pop(self, queue):
        queue.push_work({"id": 1})
        queue.push_work({"id": 2})
        queue.pop_work(timeout=1)
        assert queue.get_queue_size() == 1
