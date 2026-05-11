"""
Logging utilities for the Clinical Research Assistant
"""
import os
import sys
from datetime import datetime
from loguru import logger
from config import settings

def setup_logger():
    """Setup logger with file and console handlers"""
    # Remove default handler
    logger.remove()
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Add console handler
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL,
        colorize=True
    )
    
    # Add file handler
    logger.add(
        "logs/cra.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.LOG_LEVEL,
        rotation="10 MB",
        retention="7 days",
        compression="zip"
    )
    
    return logger

def log_query(query: str, user_id: str = None):
    """Log a new query"""
    logger.info(f"New query received: {query[:100]}... | User: {user_id or 'anonymous'}")

def log_api_call(api_name: str, endpoint: str, status_code: int, response_time: float):
    """Log API call details"""
    logger.info(f"API Call: {api_name} | Endpoint: {endpoint} | Status: {status_code} | Time: {response_time:.2f}s")

def log_error(error: Exception, context: str = ""):
    """Log error with context"""
    logger.error(f"Error in {context}: {str(error)}")

def log_performance(operation: str, duration: float):
    """Log performance metrics"""
    logger.info(f"Performance: {operation} completed in {duration:.2f}s")

def log_cache_hit(key: str):
    """Log cache hit"""
    logger.debug(f"Cache hit for key: {key}")

def log_cache_miss(key: str):
    """Log cache miss"""
    logger.debug(f"Cache miss for key: {key}")

# Initialize logger
setup_logger() 