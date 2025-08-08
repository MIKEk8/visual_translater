"""
Logging integration for infrastructure layer.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from ...utils.logger import logger as domain_logger


class InfrastructureLogger:
    """Logging integration for infrastructure components."""

    def __init__(self, log_level: str = "INFO", log_file: Optional[Path] = None):
        self.logger = logging.getLogger("infrastructure")
        self.logger.setLevel(getattr(logging, log_level.upper()))

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File handler if specified
        if log_file:
            log_file.parent.mkdir(exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

    def log_repository_operation(
        self, operation: str, entity_type: str, entity_id: str, **kwargs
    ) -> None:
        """Log repository operation."""
        self.logger.info(f"Repository {operation}: {entity_type} {entity_id}", extra=kwargs)

    def log_service_call(self, service: str, method: str, duration_ms: float, **kwargs) -> None:
        """Log external service call."""
        self.logger.info(f"Service call: {service}.{method} ({duration_ms:.2f}ms)", extra=kwargs)

    def log_adapter_conversion(self, source: str, target: str, success: bool, **kwargs) -> None:
        """Log adapter conversion."""
        status = "success" if success else "failed"
        self.logger.info(f"Adapter conversion {source} -> {target}: {status}", extra=kwargs)

    def log_cache_operation(self, operation: str, key: str, hit: bool = None, **kwargs) -> None:
        """Log cache operation."""
        if hit is not None:
            result = "hit" if hit else "miss"
            self.logger.debug(f"Cache {operation}: {key} ({result})", extra=kwargs)
        else:
            self.logger.debug(f"Cache {operation}: {key}", extra=kwargs)

    def log_error(self, component: str, operation: str, error: Exception, **kwargs) -> None:
        """Log infrastructure error."""
        self.logger.error(
            f"Infrastructure error in {component}.{operation}: {str(error)}",
            exc_info=True,
            extra=kwargs,
        )


# Global infrastructure logger instance
infrastructure_logger = InfrastructureLogger(log_file=Path("logs/infrastructure.log"))
