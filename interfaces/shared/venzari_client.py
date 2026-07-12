"""
interfaces/shared/venzari_client.py

HTTP client to the VENZARI CODE ACP server (JSON-RPC).
Replaces jeanne_client.py for projects using VENZARI CODE CLI.

The ACP server runs when you start:
  venzari-code serve --port 4001

Set VENZARI_ACP_URL in your environment to override the default.
"""

import asyncio
import logging
import os
import aiohttp

logger = logging.getLogger(__name__)

VENZARI_ACP_URL = os.environ.get("VENZARI_ACP_URL", "http://localhost:4001")


async def query_venzari(message: str, session_id: str | None = None) -> str | None:
    """
    Send a message to the VENZARI CODE ACP server and return the response.

    Args:
        message: The user's message/prompt
        session_id: Optional session ID for continuity (e.g. "slack:U01ABCDEF")

    Returns:
        The AI response string, or None on failure
    """
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "chat",
        "params": {
            "message": message,
            **({"sessionId": session_id} if session_id else {}),
        },
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{VENZARI_ACP_URL}/acp",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                if resp.status != 200:
                    logger.error(f"ACP server returned HTTP {resp.status}")
                    return None
                data = await resp.json()
                if "error" in data:
                    logger.error(f"ACP error: {data['error'].get('message', 'unknown')}")
                    return None
                result = data.get("result", {})
                return result.get("content") or result.get("response") or str(result)
    except asyncio.TimeoutError:
        logger.error("ACP request timed out after 120s")
        return None
    except aiohttp.ClientConnectorError:
        logger.error(
            f"Cannot connect to VENZARI CODE ACP server at {VENZARI_ACP_URL}. "
            "Start it with: venzari-code serve --port 4001"
        )
        return None
    except Exception as e:
        logger.exception(f"Unexpected error calling VENZARI ACP: {e}")
        return None


async def run_goal(goal: str, repo_path: str | None = None) -> dict:
    """
    Trigger a goal run via the ACP server.
    Returns the goal result dict or empty dict on failure.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "goal.run",
        "params": {
            "goal": goal,
            **({"repoPath": repo_path} if repo_path else {}),
        },
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{VENZARI_ACP_URL}/acp",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=300),
            ) as resp:
                data = await resp.json()
                return data.get("result", {})
    except Exception as e:
        logger.exception(f"goal.run failed: {e}")
        return {}


async def get_tasks(repo_path: str | None = None) -> list:
    """List tasks from the ACP server."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tasks.list",
        "params": {**({"repoPath": repo_path} if repo_path else {})},
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{VENZARI_ACP_URL}/acp", json=payload,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                data = await resp.json()
                return data.get("result", [])
    except Exception:
        return []


async def check_health() -> bool:
    """Check if the ACP server is reachable."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{VENZARI_ACP_URL}/app",
                timeout=aiohttp.ClientTimeout(total=3),
            ) as resp:
                return resp.status == 200
    except Exception:
        return False
