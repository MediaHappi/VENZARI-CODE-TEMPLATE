"""
interfaces/shared/event_publisher.py

Redis pub/sub event publisher for all VENZARI CODE interfaces.
Channel: venzari:events

Event types:
    message_received  — User sent a message
    response_sent     — VENZARI CODE returned a response
    tool_called       — A tool was invoked
    memory_written    — Memory written to L3
    session_started   — New session created
    session_ended     — Session ended

Environment variables:
    REDIS_URL — Redis connection URL (default: redis://localhost:6379)
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

CHANNEL = "venzari:events"

# Valid event types
EVENT_TYPES = {
    "message_received",
    "response_sent",
    "tool_called",
    "memory_written",
    "session_started",
    "session_ended",
    "error",
    "health_check",
}

try:
    import redis as _redis
    _r = _redis.Redis.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379"),
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
    )
    _r.ping()
    logger.info("Event publisher: Redis connected")
except Exception as e:
    logger.warning(f"Event publisher: Redis unavailable — events will be dropped: {e}")
    _r = None


def publish(
    event_type: str,
    data: dict,
    interface: str = None,
    session_id: str = None,
) -> bool:
    """
    Publish an event to the venzari:events Redis channel.

    Args:
        event_type: One of the EVENT_TYPES constants.
        data:       Event-specific payload dict.
        interface:  Interface that generated the event (e.g. "slack", "api").
        session_id: Associated session ID if applicable.

    Returns:
        True if published successfully, False if Redis unavailable or error.
    """
    if _r is None:
        logger.debug(f"Event bus unavailable — dropping {event_type} event")
        return False

    if event_type not in EVENT_TYPES:
        logger.warning(f"Unknown event_type '{event_type}' — publishing anyway")

    event = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "interface": interface,
        "session_id": session_id,
        "data": data,
    }

    try:
        _r.publish(CHANNEL, json.dumps(event))
        logger.debug(f"Published event: {event_type} / session={session_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to publish event {event_type}: {e}")
        return False


# Convenience functions for common event types

def message_received(interface: str, session_id: str, user_id: str, message: str, **extra) -> bool:
    return publish(
        "message_received",
        {"user": user_id, "message": message[:500], **extra},
        interface=interface,
        session_id=session_id,
    )


def response_sent(interface: str, session_id: str, response_length: int, model: str = None, latency_ms: int = None) -> bool:
    return publish(
        "response_sent",
        {"response_length": response_length, "model": model, "latency_ms": latency_ms},
        interface=interface,
        session_id=session_id,
    )


def memory_written(interface: str, session_id: str, content_preview: str, tags: list = None) -> bool:
    return publish(
        "memory_written",
        {"content_preview": content_preview[:100], "tags": tags or []},
        interface=interface,
        session_id=session_id,
    )


def session_started(interface: str, session_id: str, user_id: str) -> bool:
    return publish(
        "session_started",
        {"interface": interface, "user_id": user_id},
        interface=interface,
        session_id=session_id,
    )


def session_ended(interface: str, session_id: str, message_count: int, duration_seconds: int = None) -> bool:
    return publish(
        "session_ended",
        {"message_count": message_count, "duration_seconds": duration_seconds},
        interface=interface,
        session_id=session_id,
    )


def error_event(interface: str, session_id: str, error: str, context: str = None, severity: str = "error") -> bool:
    return publish(
        "error",
        {"error": str(error)[:500], "context": context, "severity": severity},
        interface=interface,
        session_id=session_id,
    )
