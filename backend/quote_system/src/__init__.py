# src/__init__.py

# This file makes 'src' a Python package.

# Optionally configure logging here for the entire application
import logging
import sys

# Basic logging configuration
# Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
log_level = logging.INFO # Default level
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Get root logger
logger = logging.getLogger()

# Set level if not already configured by handlers
if not logger.hasHandlers():
    logger.setLevel(log_level)
    # Add a handler to output to stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    formatter = logging.Formatter(log_format)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.info(f"Root logger configured with level {logging.getLevelName(log_level)} and stdout handler.")
else:
    # If handlers exist, respect existing config but ensure root level is appropriate
    current_level = logger.getEffectiveLevel()
    if current_level > log_level: # If current level is more restrictive (e.g. WARNING > INFO)
         logger.setLevel(log_level)
         logger.info(f"Root logger level adjusted to {logging.getLevelName(log_level)}.")
    else:
        logger.info(f"Root logger already configured. Effective level: {logging.getLevelName(current_level)}")


# Expose key components if desired
# from .core.common_types import AnalysisInput, AnalysisResult
# from .services import AnalysisService
# from .config import load_config

# Define __all__ if you want to control `from src import *` behavior
# __all__ = ["AnalysisInput", "AnalysisResult", "AnalysisService", "load_config"] 