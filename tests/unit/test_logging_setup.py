"""Unit tests for src/utils/logging_setup.py"""

import logging
import logging.handlers
import os
import tempfile

import pytest
import structlog

from src.utils.logging_setup import configure_logging, get_logger, log_progress


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_logging() -> None:
    """Remove all handlers from the root logger between tests."""
    root = logging.getLogger()
    root.handlers.clear()
    structlog.reset_defaults()


# ---------------------------------------------------------------------------
# configure_logging
# ---------------------------------------------------------------------------

class TestConfigureLogging:
    def setup_method(self):
        _reset_logging()

    def teardown_method(self):
        _reset_logging()

    def test_creates_console_and_file_handlers(self, tmp_path):
        log_file = str(tmp_path / "test.log")
        configure_logging("INFO", log_file)

        root = logging.getLogger()
        handler_types = [type(h) for h in root.handlers]
        assert logging.StreamHandler in handler_types
        assert logging.handlers.RotatingFileHandler in handler_types

    def test_log_file_is_created(self, tmp_path):
        log_file = str(tmp_path / "scraper.log")
        configure_logging("INFO", log_file)

        logger = get_logger("test")
        logger.info("hello")

        assert os.path.exists(log_file)

    def test_debug_level_sets_root_logger(self, tmp_path):
        log_file = str(tmp_path / "debug.log")
        configure_logging("DEBUG", log_file)

        assert logging.getLogger().level == logging.DEBUG

    def test_warning_level_sets_root_logger(self, tmp_path):
        log_file = str(tmp_path / "warn.log")
        configure_logging("WARNING", log_file)

        assert logging.getLogger().level == logging.WARNING

    def test_error_level_sets_root_logger(self, tmp_path):
        log_file = str(tmp_path / "error.log")
        configure_logging("ERROR", log_file)

        assert logging.getLogger().level == logging.ERROR

    def test_rotating_file_handler_max_bytes(self, tmp_path):
        log_file = str(tmp_path / "rotate.log")
        configure_logging("INFO", log_file)

        root = logging.getLogger()
        rfh = next(
            h for h in root.handlers if isinstance(h, logging.handlers.RotatingFileHandler)
        )
        assert rfh.maxBytes == 10 * 1024 * 1024  # 10 MB

    def test_rotating_file_handler_backup_count(self, tmp_path):
        log_file = str(tmp_path / "rotate.log")
        configure_logging("INFO", log_file)

        root = logging.getLogger()
        rfh = next(
            h for h in root.handlers if isinstance(h, logging.handlers.RotatingFileHandler)
        )
        assert rfh.backupCount == 5

    def test_reconfigure_does_not_duplicate_handlers(self, tmp_path):
        log_file = str(tmp_path / "dup.log")
        configure_logging("INFO", log_file)
        configure_logging("INFO", log_file)

        root = logging.getLogger()
        # Should still have exactly 2 handlers (console + file)
        assert len(root.handlers) == 2


# ---------------------------------------------------------------------------
# get_logger
# ---------------------------------------------------------------------------

class TestGetLogger:
    def setup_method(self):
        _reset_logging()

    def teardown_method(self):
        _reset_logging()

    def test_returns_bound_logger(self, tmp_path):
        configure_logging("INFO", str(tmp_path / "test.log"))
        logger = get_logger("my_component")
        # structlog returns a BoundLoggerLazyProxy that wraps a BoundLogger
        assert hasattr(logger, "info") and hasattr(logger, "error")

    def test_different_names_return_different_loggers(self, tmp_path):
        configure_logging("INFO", str(tmp_path / "test.log"))
        logger_a = get_logger("component_a")
        logger_b = get_logger("component_b")
        # They should be distinct objects (or at least bound to different names)
        assert logger_a is not logger_b

    def test_logger_can_log_without_error(self, tmp_path):
        configure_logging("INFO", str(tmp_path / "test.log"))
        logger = get_logger("test_component")
        # Should not raise
        logger.info("test message", key="value")


# ---------------------------------------------------------------------------
# log_progress
# ---------------------------------------------------------------------------

class TestLogProgress:
    def setup_method(self):
        _reset_logging()

    def teardown_method(self):
        _reset_logging()

    def test_log_progress_does_not_raise(self, tmp_path):
        configure_logging("INFO", str(tmp_path / "test.log"))
        # Should not raise
        log_progress(10, 100, "scraper")

    def test_log_progress_zero_total_does_not_raise(self, tmp_path):
        configure_logging("INFO", str(tmp_path / "test.log"))
        log_progress(0, 0, "scraper")

    def test_log_progress_writes_to_file(self, tmp_path):
        log_file = str(tmp_path / "progress.log")
        configure_logging("INFO", log_file)
        log_progress(5, 10, "scraper")

        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()

        assert "progress" in content

    def test_log_progress_full_completion(self, tmp_path):
        log_file = str(tmp_path / "progress.log")
        configure_logging("INFO", log_file)
        log_progress(100, 100, "scraper")

        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()

        assert "100" in content

    def test_log_progress_includes_component(self, tmp_path):
        log_file = str(tmp_path / "progress.log")
        configure_logging("INFO", log_file)
        log_progress(3, 30, "my_scraper_component")

        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()

        assert "my_scraper_component" in content
