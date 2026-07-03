"""Logging configuration for Where's My Context backend."""
import logging
import sys
from datetime import datetime

def setup_logger(name: str) -> logging.Logger:
    """Configure a logger with consistent formatting."""
    logger = logging.getLogger(name)
    
    if logger.hasHandlers():
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    # Console handler with color-coded output
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

# Module-level logger
log = setup_logger("where-my-context")
