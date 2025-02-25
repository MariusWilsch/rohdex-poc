from rich.console import Console
from rich.logging import RichHandler
import logging
import sys  # Added for sys.exc_info
from app.core.config import get_settings


class LoggerSingleton:
    _instance = None
    _console = None
    _logger = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._setup_logger()
        return cls._instance

    @classmethod
    def _setup_logger(cls):
        settings = get_settings()
        log_level = getattr(settings, "LOG_LEVEL", "INFO")

        cls._console = Console()
        logging.basicConfig(
            level=log_level,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(console=cls._console, rich_tracebacks=True)],
        )
        cls._logger = logging.getLogger("rich")
        # Extend logger with auto-traceback capabilities
        cls._extend_logger()

    @classmethod
    def _extend_logger(cls):
        """Add custom methods to automatically include exception info"""
        original_error = cls._logger.error

        # Override error method to automatically include exception info if available
        def auto_traceback_error(msg, *args, **kwargs):
            if "exc_info" not in kwargs and sys.exc_info()[0] is not None:
                kwargs["exc_info"] = True
            return original_error(msg, *args, **kwargs)

        cls._logger.error = auto_traceback_error

        # Add a convenience method for errors with tracebacks
        cls._logger.error_with_tb = lambda msg, *args, **kwargs: original_error(
            msg, *args, **{**kwargs, "exc_info": True}
        )

    @classmethod
    def get_logger(cls):
        if cls._instance is None:
            cls()
        return cls._logger

    @classmethod
    def get_console(cls):
        if cls._instance is None:
            cls()
        return cls._console
