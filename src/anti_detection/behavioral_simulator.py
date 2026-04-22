"""Behavioral simulator for realistic human-like browser interactions."""

from __future__ import annotations

import asyncio
import random
from typing import List, NamedTuple, Tuple

from playwright.async_api import Page


class Point(NamedTuple):
    """A 2D point with x and y coordinates."""
    x: float
    y: float


def _bezier_curve(
    p0: Point,
    p1: Point,
    p2: Point,
    p3: Point,
    steps: int = 20,
) -> List[Point]:
    """Generate points along a cubic Bezier curve.

    Args:
        p0: Start point.
        p1: First control point.
        p2: Second control point.
        p3: End point.
        steps: Number of intermediate points to generate.

    Returns:
        List of Points along the curve (including start and end).
    """
    points: List[Point] = []
    for i in range(steps + 1):
        t = i / steps
        mt = 1 - t
        x = (
            mt ** 3 * p0.x
            + 3 * mt ** 2 * t * p1.x
            + 3 * mt * t ** 2 * p2.x
            + t ** 3 * p3.x
        )
        y = (
            mt ** 3 * p0.y
            + 3 * mt ** 2 * t * p1.y
            + 3 * mt * t ** 2 * p2.y
            + t ** 3 * p3.y
        )
        points.append(Point(x, y))
    return points


class BehavioralSimulator:
    """Simulates realistic human-like browser interactions to avoid bot detection."""

    # ------------------------------------------------------------------
    # Mouse movement
    # ------------------------------------------------------------------

    async def move_mouse(
        self,
        page: Page,
        from_pos: Point,
        to_pos: Point,
    ) -> None:
        """Simulate realistic mouse movement using Bezier curves.

        Generates a cubic Bezier path with random control points to produce
        natural-looking curved movement with acceleration/deceleration.
        Occasionally overshoots the target and corrects.

        Args:
            page: Playwright Page instance.
            from_pos: Starting position.
            to_pos: Target position.
        """
        dx = to_pos.x - from_pos.x
        dy = to_pos.y - from_pos.y

        # Random control points that create a natural curve
        cp1 = Point(
            from_pos.x + dx * random.uniform(0.1, 0.4) + random.uniform(-50, 50),
            from_pos.y + dy * random.uniform(0.1, 0.4) + random.uniform(-50, 50),
        )
        cp2 = Point(
            from_pos.x + dx * random.uniform(0.6, 0.9) + random.uniform(-50, 50),
            from_pos.y + dy * random.uniform(0.6, 0.9) + random.uniform(-50, 50),
        )

        steps = random.randint(15, 30)
        path = _bezier_curve(from_pos, cp1, cp2, to_pos, steps=steps)

        for point in path:
            await page.mouse.move(point.x, point.y)
            # Acceleration/deceleration: shorter delays in the middle
            await asyncio.sleep(random.uniform(0.005, 0.02))

        # Occasional overshoot and correction (~20% chance)
        if random.random() < 0.2:
            overshoot = Point(
                to_pos.x + random.uniform(-15, 15),
                to_pos.y + random.uniform(-15, 15),
            )
            await page.mouse.move(overshoot.x, overshoot.y)
            await asyncio.sleep(random.uniform(0.05, 0.15))
            await page.mouse.move(to_pos.x, to_pos.y)

    # ------------------------------------------------------------------
    # Scrolling
    # ------------------------------------------------------------------

    async def scroll_page(
        self,
        page: Page,
        scroll_pattern: str = "random",
    ) -> None:
        """Simulate realistic scrolling behavior.

        Scrolls down in variable-sized chunks, occasionally scrolls back up,
        and pauses between chunks to simulate reading.

        Args:
            page: Playwright Page instance.
            scroll_pattern: "random", "down", or "up".
        """
        if scroll_pattern == "up":
            scroll_amount = -random.randint(200, 600)
            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await asyncio.sleep(random.uniform(0.3, 0.8))
            return

        if scroll_pattern == "down":
            chunks = random.randint(3, 6)
            for _ in range(chunks):
                amount = random.randint(150, 400)
                await page.evaluate(f"window.scrollBy(0, {amount})")
                await asyncio.sleep(random.uniform(0.3, 1.2))
            return

        # "random" pattern: scroll down with occasional scroll-up and pauses
        total_chunks = random.randint(4, 8)
        for i in range(total_chunks):
            # Occasionally scroll up a bit (~25% chance after first chunk)
            if i > 0 and random.random() < 0.25:
                up_amount = random.randint(50, 200)
                await page.evaluate(f"window.scrollBy(0, -{up_amount})")
                await asyncio.sleep(random.uniform(0.2, 0.6))

            # Scroll down a chunk
            down_amount = random.randint(150, 450)
            await page.evaluate(f"window.scrollBy(0, {down_amount})")

            # Pause to simulate reading "interesting" content
            await asyncio.sleep(random.uniform(0.4, 1.5))

    # ------------------------------------------------------------------
    # Clicking
    # ------------------------------------------------------------------

    async def click_element(self, page: Page, selector: str) -> None:
        """Simulate realistic click with random position within element.

        Gets the element's bounding box and clicks at a random position
        within it (not always the center). Occasionally misclicks near
        the target and then corrects.

        Args:
            page: Playwright Page instance.
            selector: CSS selector for the target element.
        """
        element = await page.query_selector(selector)
        if element is None:
            raise ValueError(f"Element not found: {selector}")

        box = await element.bounding_box()
        if box is None:
            raise ValueError(f"Element has no bounding box: {selector}")

        # Random position within the element (avoid edges by 5px)
        margin = 5.0
        click_x = box["x"] + margin + random.uniform(0, max(0, box["width"] - 2 * margin))
        click_y = box["y"] + margin + random.uniform(0, max(0, box["height"] - 2 * margin))

        # Occasional misclick (~10% chance): click near but not on target, then correct
        if random.random() < 0.1:
            miss_x = click_x + random.uniform(-20, 20)
            miss_y = click_y + random.uniform(-20, 20)
            await page.mouse.move(miss_x, miss_y)
            await asyncio.sleep(random.uniform(0.1, 0.3))

        await page.mouse.move(click_x, click_y)
        await asyncio.sleep(random.uniform(0.05, 0.15))
        await page.mouse.click(click_x, click_y)

    # ------------------------------------------------------------------
    # Typing
    # ------------------------------------------------------------------

    async def type_text(self, page: Page, selector: str, text: str) -> None:
        """Simulate realistic typing with variable speed.

        Types character by character with 200-400ms delays and random
        variations. Occasionally types a wrong character and backspaces.

        Args:
            page: Playwright Page instance.
            selector: CSS selector for the input element.
            text: Text to type.
        """
        await page.click(selector)
        await asyncio.sleep(random.uniform(0.1, 0.3))

        for char in text:
            # Occasional typo and correction (~5% per character)
            if random.random() < 0.05:
                typo = random.choice("abcdefghijklmnopqrstuvwxyz")
                await page.keyboard.type(typo)
                await asyncio.sleep(random.uniform(0.2, 0.4))
                await page.keyboard.press("Backspace")
                await asyncio.sleep(random.uniform(0.1, 0.2))

            await page.keyboard.type(char)
            await asyncio.sleep(random.uniform(0.2, 0.4))

    # ------------------------------------------------------------------
    # Idle behavior
    # ------------------------------------------------------------------

    async def idle_behavior(self, page: Page, duration: float) -> None:
        """Simulate idle human behavior (random mouse movements, pauses).

        For the given duration, makes small random mouse movements and
        occasionally hovers over elements to simulate a human reading.

        Args:
            page: Playwright Page instance.
            duration: How long (in seconds) to simulate idle behavior.
        """
        elapsed = 0.0
        while elapsed < duration:
            # Small random mouse movement
            x = random.uniform(100, 1200)
            y = random.uniform(100, 700)
            await page.mouse.move(x, y)

            pause = random.uniform(0.5, 2.0)
            await asyncio.sleep(pause)
            elapsed += pause

    # ------------------------------------------------------------------
    # Think time
    # ------------------------------------------------------------------

    async def think_time(
        self,
        min_seconds: float = 3.0,
        max_seconds: float = 8.0,
    ) -> None:
        """Simulate human thinking time with a random delay.

        Args:
            min_seconds: Minimum delay in seconds.
            max_seconds: Maximum delay in seconds.
        """
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)
