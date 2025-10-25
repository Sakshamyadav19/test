"""Structured logging for CloudWatch."""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def log_event(level: str, message: str, context: Dict[str, Any] = None):
    """
    Log a structured event with context.
    
    Args:
        level: Log level (INFO, WARNING, ERROR, DEBUG)
        message: Log message
        context: Additional context dictionary
    """
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "level": level,
        "message": message,
    }
    
    if context:
        log_entry["context"] = context
    
    logger.log(getattr(logging, level.upper(), logging.INFO), json.dumps(log_entry))


def info(message: str, context: Dict[str, Any] = None):
    """Log info level message."""
    log_event("INFO", message, context)


def warning(message: str, context: Dict[str, Any] = None):
    """Log warning level message."""
    log_event("WARNING", message, context)


def error(message: str, context: Dict[str, Any] = None):
    """Log error level message."""
    log_event("ERROR", message, context)


def debug(message: str, context: Dict[str, Any] = None):
    """Log debug level message."""
    log_event("DEBUG", message, context)


def redact_secrets(value: Any) -> Any:
    """
    Redact secrets from logs.
    
    Args:
        value: Value to redact
    
    Returns:
        Redacted value
    """
    if isinstance(value, dict):
        redacted = {}
        for k, v in value.items():
            if any(secret in k.lower() for secret in ["key", "password", "secret", "token", "api_key"]):
                redacted[k] = "***REDACTED***"
            else:
                redacted[k] = redact_secrets(v)
        return redacted
    elif isinstance(value, list):
        return [redact_secrets(item) for item in value]
    elif isinstance(value, str) and any(secret in value.lower() for secret in ["key", "secret"]):
        return "***REDACTED***"
    else:
        return value


def log_request(method: str, path: str, body: Dict = None):
    """Log incoming request."""
    context = {"method": method, "path": path}
    if body:
        context["body"] = redact_secrets(body)
    info(f"Request: {method} {path}", context)


def log_response(status_code: int, body: Dict = None):
    """Log outgoing response."""
    context = {"status_code": status_code}
    if body:
        context["body"] = redact_secrets(body)
    info(f"Response: {status_code}", context)

