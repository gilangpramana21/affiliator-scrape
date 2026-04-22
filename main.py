"""CLI entrypoint for running the affiliator scraper safely."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from src.core.scraper_orchestrator import ScraperOrchestrator
from src.models.config import Configuration
from src.models.models import Checkpoint
from src.utils.logging_setup import configure_logging


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tokopedia/TikTok affiliate scraper runner")
    parser.add_argument(
        "--config",
        default="config/config.template.json",
        help="Path to JSON configuration file",
    )
    parser.add_argument(
        "--resume-checkpoint",
        default="",
        help="Optional checkpoint JSON path to resume from",
    )
    return parser.parse_args()


async def _run() -> int:
    args = _parse_args()
    config = Configuration.from_file(args.config)
    errors = config.validate()
    if errors:
        print("Invalid configuration:")
        for error in errors:
            print(f"- {error}")
        return 2

    configure_logging(config.log_level, config.log_file)
    logger = logging.getLogger("main")
    orchestrator = ScraperOrchestrator(config)

    if args.resume_checkpoint:
        logger.info("Resuming from checkpoint: %s", args.resume_checkpoint)
        checkpoint = Checkpoint.load(args.resume_checkpoint)
        result = await orchestrator.resume(checkpoint)
    else:
        result = await orchestrator.start()

    logger.info(
        "Run completed | total=%d unique=%d dup=%d errors=%d captchas=%d duration=%.2fs",
        result.total_scraped,
        result.unique_affiliators,
        result.duplicates_found,
        result.errors,
        result.captchas_encountered,
        result.duration,
    )
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"Fatal error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

