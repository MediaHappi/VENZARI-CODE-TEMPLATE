"""
interfaces/shared/session_manager.py

Redis-backed session tracking for all VENZARI CODE interfaces.
Uses venzari-dashboard-v5-redis-1 at localhost:6379.

Sessions expire after 24 hours of inactivity (TTL refreshed on each update).

Session ID format: "{interface}:{user_id}"
  Examples: "slack:U01ABCDEF", "discord:123456789", "api:key123:uuid4", "voice:socket_abc"

Environment variables:
    REDIS_URL — Redis connection URL (default: redis://localhost:6379)
"""

import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

SESSION_TTL = 86400  # 24 hours in seconds
SESSION_PREFIX = "venzari:session:"

try:
    import redis as _redis
    _r = _redis.Redis.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379"),
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
    )
    # Verify connection is functional
    _r.ping()
    logger.info("Session manager: Redis connected")
except Exception as e:
    logger.error(f"Session manager: Redis unavailable — {e}")
    _r = None


def _key(session_id: str) -> str:
    return f"{SESSION_PREFIX}{session_id}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_session(interface: str, user_id: str, metadata: dict = None) -> dict:
    """
    Create a new session for a user on a given interface.

    Args:
        interface: Interface name (e.g. "slack", "discord", "api", "voice", "dashboard")
        user_id:   User identifier on that interface
        metadata:  Optional extra data (e.g. slack_channel, guild_id)

    Returns:
        Session dict. Returns minimal dict if Redis is unavailable.
    """
    session_id = f"{interface}:{user_id}"
    session = {
        "session_id": session_id,
        "interface": interface,
        "user_id": str(user_id),
        "created_at": _now_iso(),
        "last_active": _now_iso(),
        "message_count": 0,
        "metadata": metadata or {},
    }

    if _r is not None:
        try:
            _r.setex(_key(session_id), SESSION_TTL, json.dumps(session))
            logger.debug(f"Session created: {session_id}")
        except Exception as e:
            logger.error(f"Failed to write session {session_id} to Redis: {e}")

    return session


def get_session(session_id: str) -> dict | None:
    """
    Retrieve an active session by session_id.

    Returns:
        Session dict if found and not expired, else None.
    """
    if _r is None:
        return None
    try:
        data = _r.get(_key(session_id))
        if data is None:
            return None
        return json.loads(data)
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {e}")
        return None


def update_session(session_id: str, data: dict) -> dict | None:
    """
    Update session fields and refresh the 24h TTL.

    Args:
        session_id: The session identifier.
        data:       Dict of fields to update (merged into existing session).

    Returns:
        Updated session dict, or None if session not found.
    """
    session = get_session(session_id)
    if session is None:
        logger.warning(f"update_session: session {session_id} not found")
        return None

    session.update(data)
    session["last_active"] = _now_iso()

    if _r is not None:
        try:
            _r.setex(_key(session_id), SESSION_TTL, json.dumps(session))
        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {e}")

    return session


def end_session(session_id: str) -> bool:
    """
    End a session by removing it from Redis.

    Returns:
        True if session was found and removed, False otherwise.
    """
    if _r is None:
        return False
    try:
        deleted = _r.delete(_key(session_id))
        if deleted:
            logger.debug(f"Session ended: {session_id}")
        return deleted > 0
    except Exception as e:
        logger.error(f"Failed to end session {session_id}: {e}")
        return False


def increment_message_count(session_id: str) -> int:
    """
    Increment the message count for a session.

    Returns:
        New message count, or 0 if session not found.
    """
    session = get_session(session_id)
    if session is None:
        return 0
    count = session.get("message_count", 0) + 1
    update_session(session_id, {"message_count": count})
    return count


def get_or_create_session(interface: str, user_id: str, metadata: dict = None) -> dict:
    """
    Get existing session or create a new one.

    Convenience wrapper combining get_session + create_session.
    """
    session_id = f"{interface}:{user_id}"
    existing = get_session(session_id)
    if existing:
        return existing
    return create_session(interface, user_id, metadata=metadata)
