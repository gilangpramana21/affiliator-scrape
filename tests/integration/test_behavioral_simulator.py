"""Integration tests for BehavioralSimulator."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.anti_detection.behavioral_simulator import (
    BehavioralSimulator,
    Point,
    _bezier_curve,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_page(bounding_box: dict | None = None) -> MagicMock:
    """Create a mock Playwright Page with async mouse/keyboard/evaluate."""
    page = MagicMock()
    page.mouse = MagicMock()
    page.mouse.move = AsyncMock()
    page.mouse.click = AsyncMock()
    page.keyboard = MagicMock()
    page.keyboard.type = AsyncMock()
    page.keyboard.press = AsyncMock()
    page.evaluate = AsyncMock()
    page.click = AsyncMock()

    # query_selector returns an element mock
    element = MagicMock()
    element.bounding_box = AsyncMock(
        return_value=bounding_box or {"x": 100.0, "y": 200.0, "width": 120.0, "height": 40.0}
    )
    page.query_selector = AsyncMock(return_value=element)
    return page


# ---------------------------------------------------------------------------
# Unit tests for _bezier_curve helper
# ---------------------------------------------------------------------------


class TestBezierCurve:
    def test_returns_correct_number_of_points(self):
        p0, p1, p2, p3 = Point(0, 0), Point(50, 100), Point(150, 100), Point(200, 0)
        points = _bezier_curve(p0, p1, p2, p3, steps=10)
        assert len(points) == 11  # steps + 1

    def test_starts_at_p0(self):
        p0, p1, p2, p3 = Point(0, 0), Point(50, 100), Point(150, 100), Point(200, 0)
        points = _bezier_curve(p0, p1, p2, p3, steps=10)
        assert points[0].x == pytest.approx(0.0)
        assert points[0].y == pytest.approx(0.0)

    def test_ends_at_p3(self):
        p0, p1, p2, p3 = Point(0, 0), Point(50, 100), Point(150, 100), Point(200, 0)
        points = _bezier_curve(p0, p1, p2, p3, steps=10)
        assert points[-1].x == pytest.approx(200.0)
        assert points[-1].y == pytest.approx(0.0)

    def test_single_step_returns_two_points(self):
        p0, p1, p2, p3 = Point(0, 0), Point(1, 1), Point(2, 2), Point(3, 3)
        points = _bezier_curve(p0, p1, p2, p3, steps=1)
        assert len(points) == 2

    def test_straight_line_bezier(self):
        """When all control points are collinear, curve should be a straight line."""
        p0, p1, p2, p3 = Point(0, 0), Point(100, 0), Point(200, 0), Point(300, 0)
        points = _bezier_curve(p0, p1, p2, p3, steps=5)
        for pt in points:
            assert pt.y == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# BehavioralSimulator tests
# ---------------------------------------------------------------------------


class TestMoveMouse:
    @pytest.mark.asyncio
    async def test_move_mouse_calls_mouse_move_multiple_times(self):
        page = _make_page()
        sim = BehavioralSimulator()
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await sim.move_mouse(page, Point(0, 0), Point(500, 400))
        # Should have called mouse.move at least steps+1 times (15-30 steps)
        assert page.mouse.move.call_count >= 16

    @pytest.mark.asyncio
    async def test_move_mouse_first_call_near_start(self):
        page = _make_page()
        sim = BehavioralSimulator()
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await sim.move_mouse(page, Point(0, 0), Point(500, 400))
        first_call_args = page.mouse.move.call_args_list[0]
        x, y = first_call_args[0]
        # First point should be at or very near the start (t=0 on Bezier = p0)
        assert x == pytest.approx(0.0, abs=1e-6)
        assert y == pytest.approx(0.0, abs=1e-6)

    @pytest.mark.asyncio
    async def test_move_mouse_last_call_near_destination(self):
        """The last move before any overshoot correction should be at to_pos."""
        page = _make_page()
        sim = BehavioralSimulator()
        # Disable overshoot by fixing random
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch("random.random", return_value=0.5):  # > 0.2, no overshoot
                await sim.move_mouse(page, Point(0, 0), Point(500, 400))
        last_call_args = page.mouse.move.call_args_list[-1]
        x, y = last_call_args[0]
        assert x == pytest.approx(500.0, abs=1e-6)
        assert y == pytest.approx(400.0, abs=1e-6)


class TestScrollPage:
    @pytest.mark.asyncio
    async def test_scroll_page_calls_evaluate(self):
        page = _make_page()
        sim = BehavioralSimulator()
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await sim.scroll_page(page)
        assert page.evaluate.call_count >= 1

    @pytest.mark.asyncio
    async def test_scroll_page_down_pattern(self):
        page = _make_page()
        sim = BehavioralSimulator()
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await sim.scroll_page(page, scroll_pattern="down")
        assert page.evaluate.call_count >= 3

    @pytest.mark.asyncio
    async def test_scroll_page_up_pattern(self):
        page = _make_page()
        sim = BehavioralSimulator()
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await sim.scroll_page(page, scroll_pattern="up")
        assert page.evaluate.call_count == 1
        call_arg = page.evaluate.call_args[0][0]
        assert "-" in call_arg  # negative scroll amount

    @pytest.mark.asyncio
    async def test_scroll_page_random_pattern_scrolls_down(self):
        page = _make_page()
        sim = BehavioralSimulator()
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch("random.random", return_value=0.5):  # no scroll-up
                await sim.scroll_page(page, scroll_pattern="random")
        # All evaluate calls should scroll down (positive amounts)
        for call in page.evaluate.call_args_list:
            arg = call[0][0]
            assert "scrollBy" in arg


class TestClickElement:
    @pytest.mark.asyncio
    async def test_click_element_calls_mouse_click(self):
        page = _make_page()
        sim = BehavioralSimulator()
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch("random.random", return_value=0.5):  # no misclick
                await sim.click_element(page, "#btn")
        page.mouse.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_click_element_within_bounding_box(self):
        bbox = {"x": 100.0, "y": 200.0, "width": 120.0, "height": 40.0}
        page = _make_page(bounding_box=bbox)
        sim = BehavioralSimulator()
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch("random.random", return_value=0.5):  # no misclick
                await sim.click_element(page, "#btn")
        click_x, click_y = page.mouse.click.call_args[0]
        assert bbox["x"] <= click_x <= bbox["x"] + bbox["width"]
        assert bbox["y"] <= click_y <= bbox["y"] + bbox["height"]

    @pytest.mark.asyncio
    async def test_click_element_raises_when_not_found(self):
        page = _make_page()
        page.query_selector = AsyncMock(return_value=None)
        sim = BehavioralSimulator()
        with pytest.raises(ValueError, match="Element not found"):
            await sim.click_element(page, "#missing")

    @pytest.mark.asyncio
    async def test_click_element_raises_when_no_bounding_box(self):
        page = _make_page()
        element = MagicMock()
        element.bounding_box = AsyncMock(return_value=None)
        page.query_selector = AsyncMock(return_value=element)
        sim = BehavioralSimulator()
        with pytest.raises(ValueError, match="no bounding box"):
            await sim.click_element(page, "#hidden")


class TestTypeText:
    @pytest.mark.asyncio
    async def test_type_text_types_each_character(self):
        page = _make_page()
        sim = BehavioralSimulator()
        text = "hello"
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch("random.random", return_value=0.5):  # no typos
                await sim.type_text(page, "#input", text)
        # keyboard.type called once per character (no typos)
        assert page.keyboard.type.call_count == len(text)

    @pytest.mark.asyncio
    async def test_type_text_delays_between_chars(self):
        page = _make_page()
        sim = BehavioralSimulator()
        sleep_calls = []

        async def fake_sleep(delay):
            sleep_calls.append(delay)

        with patch("asyncio.sleep", side_effect=fake_sleep):
            with patch("random.random", return_value=0.5):  # no typos
                await sim.type_text(page, "#input", "hi")

        # Should have sleep calls for each character (plus initial click delay)
        assert len(sleep_calls) >= 2
        # Per-character delays should be in 0.2-0.4 range
        char_delays = sleep_calls[1:]  # skip initial click delay
        for delay in char_delays:
            assert 0.2 <= delay <= 0.4

    @pytest.mark.asyncio
    async def test_type_text_clicks_selector_first(self):
        page = _make_page()
        sim = BehavioralSimulator()
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch("random.random", return_value=0.5):
                await sim.type_text(page, "#input", "x")
        page.click.assert_called_once_with("#input")


class TestIdleBehavior:
    @pytest.mark.asyncio
    async def test_idle_behavior_moves_mouse(self):
        page = _make_page()
        sim = BehavioralSimulator()

        call_count = 0
        total_sleep = 0.0

        async def fake_sleep(delay):
            nonlocal total_sleep, call_count
            total_sleep += delay
            call_count += 1
            # Stop after enough time has passed
            if total_sleep >= 2.0:
                raise asyncio.CancelledError

        with patch("asyncio.sleep", side_effect=fake_sleep):
            try:
                await sim.idle_behavior(page, duration=2.0)
            except asyncio.CancelledError:
                pass

        assert page.mouse.move.call_count >= 1

    @pytest.mark.asyncio
    async def test_idle_behavior_respects_duration(self):
        """idle_behavior should stop after duration seconds."""
        page = _make_page()
        sim = BehavioralSimulator()

        # Use real asyncio.sleep but with very short duration
        with patch("random.uniform", return_value=0.01):
            await sim.idle_behavior(page, duration=0.05)

        # Should have made at least a few mouse moves
        assert page.mouse.move.call_count >= 1


class TestThinkTime:
    @pytest.mark.asyncio
    async def test_think_time_sleeps_within_range(self):
        sim = BehavioralSimulator()
        sleep_delays = []

        async def fake_sleep(delay):
            sleep_delays.append(delay)

        with patch("asyncio.sleep", side_effect=fake_sleep):
            await sim.think_time(min_seconds=3.0, max_seconds=8.0)

        assert len(sleep_delays) == 1
        assert 3.0 <= sleep_delays[0] <= 8.0

    @pytest.mark.asyncio
    async def test_think_time_default_range(self):
        sim = BehavioralSimulator()
        sleep_delays = []

        async def fake_sleep(delay):
            sleep_delays.append(delay)

        with patch("asyncio.sleep", side_effect=fake_sleep):
            await sim.think_time()

        assert len(sleep_delays) == 1
        assert 3.0 <= sleep_delays[0] <= 8.0

    @pytest.mark.asyncio
    async def test_think_time_custom_range(self):
        sim = BehavioralSimulator()
        sleep_delays = []

        async def fake_sleep(delay):
            sleep_delays.append(delay)

        with patch("asyncio.sleep", side_effect=fake_sleep):
            await sim.think_time(min_seconds=1.0, max_seconds=2.0)

        assert 1.0 <= sleep_delays[0] <= 2.0
