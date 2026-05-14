"""
Logging utilities for the Clinical Research Assistant
"""
import os
import re
import sys
from datetime import datetime
from loguru import logger
from config import settings


def _redact_secrets_in_message(message: str) -> str:
    """Strip API keys and similar tokens from log lines (e.g. httpx error URLs)."""
    if not message:
        return message
    out = message
    # Google APIs / CSE (query string or odd quoting in httpx errors)
    out = re.sub(r"([?&])key=[^&\s'\"]+", r"\1key=<redacted>", out, flags=re.IGNORECASE)
    out = re.sub(r"([?&])cx=[^&\s'\"]+", r"\1cx=<redacted>", out, flags=re.IGNORECASE)
    out = re.sub(r"\bkey=AIza[\w-]{10,}", "key=<redacted>", out, flags=re.IGNORECASE)
    out = re.sub(
        r"https?://[^\s'\"<>]*googleapis\.com[^\s'\"<>]*",
        "<redacted-google-url>",
        out,
        flags=re.IGNORECASE,
    )
    return out


def _resolve_log_dir() -> str:
    """Writable directory for log files (EKS/Fargate runs uid 1000; /app/logs is often root-owned)."""
    custom = (os.environ.get("LOG_DIR") or "").strip()
    if custom:
        os.makedirs(custom, exist_ok=True)
        return custom
    for d in (
        os.path.join(os.getcwd(), "logs"),
        os.path.join(os.environ.get("HOME", "/tmp"), "logs"),
        "/tmp/regulatory-logs",
    ):
        try:
            os.makedirs(d, exist_ok=True)
            if os.access(d, os.W_OK):
                return d
        except OSError:
            continue
    return "/tmp"


def setup_logger():
    """Setup logger with file and console handlers"""
    # Remove default handler
    logger.remove()

    log_dir = _resolve_log_dir()
    log_path = os.path.join(log_dir, "cra.log")

    # Add console handler
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL,
        colorize=True,
    )

    # Add file handler
    logger.add(
        log_path,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.LOG_LEVEL,
        rotation="10 MB",
        retention="7 days",
        compression="zip",
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
    logger.error(f"Error in {context}: {_redact_secrets_in_message(str(error))}")


def log_warning(message: str):
    """Non-fatal operational warning (rate limits, retries, etc.)."""
    logger.warning(_redact_secrets_in_message(message))


def log_debug(message: str):
    """Verbose diagnostics (per-retry noise); respect LOG_LEVEL."""
    logger.debug(_redact_secrets_in_message(message))


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