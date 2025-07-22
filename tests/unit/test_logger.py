"""
Unit tests for NetArchon logging infrastructure.
"""

import json
import logging
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.netarchon.utils.logger import (
    LogLevel,
    StructuredFormatter,
    NetArchonLogger,
    get_logger,
    configure_logging
)


class TestLogLevel:
    """Test LogLevel enumeration."""
    
    def test_log_levels(self):
        """Test all log levels are defined."""
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"
        assert LogLevel.CRITICAL.value == "CRITICAL"


class TestStructuredFormatter:
    """Test structured log formatter."""
    
    def test_basic_formatting(self):
        """Test basic log record formatting."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.module = "test_module"
        record.funcName = "test_function"
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test"
        assert log_data["message"] == "Test message"
        assert log_data["module"] == "test_module"
        assert log_data["function"] == "test_function"
        assert log_data["line"] == 10
        assert "timestamp" in log_data
    
    def test_formatting_with_extra_fields(self):
        """Test formatting with extra fields."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.module = "test_module"
        record.funcName = "test_function"
        record.extra_fields = {"device_id": "router1", "operation": "connect"}
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data["device_id"] == "router1"
        assert log_data["operation"] == "connect"


class TestNetArchonLogger:
    """Test NetArchonLogger class."""
    
    def test_logger_creation(self):
        """Test logger creation."""
        logger = NetArchonLogger("test_logger")
        assert logger.name == "test_logger"
        assert logger.logger.name == "test_logger"
        assert not logger._configured
    
    def test_logger_configuration(self):
        """Test logger configuration."""
        logger = NetArchonLogger("test_config")
        logger.configure(level=LogLevel.DEBUG)
        
        assert logger._configured
        assert logger.logger.level == logging.DEBUG
        assert len(logger.logger.handlers) == 1  # Console handler
    
    def test_file_logging_configuration(self):
        """Test file logging configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            logger = NetArchonLogger("test_file")
            logger.configure(level=LogLevel.INFO, log_file=str(log_file))
            
            assert logger._configured
            assert len(logger.logger.handlers) == 2  # Console + file handlers
            assert log_file.parent.exists()
    
    def test_logging_methods(self):
        """Test logging methods."""
        logger = NetArchonLogger("test_methods")
        logger.configure(level=LogLevel.DEBUG)
        
        with patch.object(logger.logger, 'log') as mock_log:
            logger.debug("Debug message")
            mock_log.assert_called_with(logging.DEBUG, "Debug message", extra={})
            
            logger.info("Info message")
            mock_log.assert_called_with(logging.INFO, "Info message", extra={})
            
            logger.warning("Warning message")
            mock_log.assert_called_with(logging.WARNING, "Warning message", extra={})
            
            logger.error("Error message")
            mock_log.assert_called_with(logging.ERROR, "Error message", extra={})
            
            logger.critical("Critical message")
            mock_log.assert_called_with(logging.CRITICAL, "Critical message", extra={})
    
    def test_logging_with_extra_fields(self):
        """Test logging with extra fields."""
        logger = NetArchonLogger("test_extra")
        logger.configure(level=LogLevel.INFO)
        
        with patch.object(logger.logger, 'log') as mock_log:
            logger.info("Test message", device="router1", port=22)
            mock_log.assert_called_with(
                logging.INFO, 
                "Test message", 
                extra={"extra_fields": {"device": "router1", "port": 22}}
            )
    
    def test_double_configuration_ignored(self):
        """Test that double configuration is ignored."""
        logger = NetArchonLogger("test_double")
        logger.configure(level=LogLevel.INFO)
        initial_handlers = len(logger.logger.handlers)
        
        logger.configure(level=LogLevel.DEBUG)  # Should be ignored
        assert len(logger.logger.handlers) == initial_handlers


class TestGlobalFunctions:
    """Test global logger functions."""
    
    def test_get_logger_default(self):
        """Test getting default logger."""
        logger = get_logger()
        assert logger.name == "netarchon"
    
    def test_get_logger_named(self):
        """Test getting named logger."""
        logger = get_logger("custom_name")
        assert logger.name == "custom_name"
    
    def test_configure_logging(self):
        """Test global logging configuration."""
        with patch('src.netarchon.utils.logger.logger.configure') as mock_configure:
            configure_logging(level=LogLevel.DEBUG, structured=False)
            mock_configure.assert_called_once_with(
                level=LogLevel.DEBUG, 
                log_file=None, 
                structured=False
            )