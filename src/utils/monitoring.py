"""Production Monitoring System"""

import logging
import time
from datetime import datetime


class ComponentLogger:
    """Production logger for components"""

    def __init__(self, component_name):
        self.component_name = component_name
        self.logger = logging.getLogger(f"ScreenTranslator.{component_name}")
        self.logger.setLevel(logging.INFO)

    def log_operation(self, operation, success=True, duration=0):
        """Log component operation"""
        self.logger.info(f"{operation} - Success: {success}, Duration: {duration:.3f}s")

    def log_error(self, error, operation=None):
        """Log component error"""
        self.logger.error(f"Error in {operation}: {str(error)}")


def get_logger(component_name):
    """Get component logger"""
    return ComponentLogger(component_name)
