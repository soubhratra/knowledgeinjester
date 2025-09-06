"""
Centralized logging configuration for the knowledge injester.
"""
import logging
import sys
from typing import Optional

from django.conf import settings


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        level: Optional log level override
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # Create console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(handler)
    
    # Set level
    try:
        log_level = level or getattr(settings, 'LOG_LEVEL', 'INFO')
    except Exception:
        log_level = level or 'INFO'
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    return logger
