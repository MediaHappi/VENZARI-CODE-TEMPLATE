"""
interfaces/slack/bot.py

VENZARI CODE Slack bot — Bolt for Python, Socket Mode, async.

Handlers:
  /venzari <message>      — slash command in any channel
  @venzari <message>      — app_mention in channels/threads
  DM to @venzari          — direct message

Environment variables (required):
  SLACK_BOT_TOKEN        — Bot User OAuth Token (xoxb-...)
  SLACK_APP_TOKEN        — App-Level Token for Socket Mode (xapp-...)

Environment variables (optional):
  SLACK_ALERT_CHANNEL    — Channel for monitoring alerts (default: #venzari-tasks)
  SLACK_SIGNING_SECRET   — Request signing secret (used for HTTP mode; Socket Mode verifies via token)
  MASTER_KEY             — VenzariAI Router master key
  VENZARAI_ROUTER_URL    — Override default router URL (default: http://localhost:4001)
  REDIS_URL              — Redis URL (default: redis://localhost:6379)
  LOG_LEVEL              — Logging level (default: INFO)
"""

import asyncio
import logging
import os
import sys

logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO")),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


def _require_env(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        logger.error(f"Required environment variable {name} is not set. Cannot start.")
        sys.exit(1)
    return val


SLACK_BOT_TOKEN = _require_env("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = _require_env("SLACK_APP_TOKEN")

# Remove OAuth vars BEFORE importing Bolt — prevents auto-detection of OAuth mode
# when SLACK_CLIENT_ID is present in the environment.
os.environ.pop("SLACK_CLIENT_ID", None)
os.environ.pop("SLACK_CLIENT_SECRET", None)

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from interfaces.shared.venzari_client import query_venzari
from interfaces.shared.session_manager import get_or_create_session, increment_message_count
from interfaces.shared.event_publisher import publish
from interfaces.slack.message_formatter import format_response, format_error, format_thinking

# Explicitly pass token to force single-workspace mode.
# Bolt auto-enables OAuth when SLACK_CLIENT_ID is in env — we must override.
app = AsyncApp(
    token=SLACK_BOT_TOKEN,
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET", ""),
)


# ---------------------------------------------------------------------------
# /venzari slash command
# ---------------------------------------------------------------------------

@app.command("/venzari")
async def handle_slash_venzari(ack, body, say, logger):
    await ack()

    user_id = body.get("user_id", "unknown")
    message = body.get("text", "").strip()
    channel = body.get("channel_id", "")

    if not message or message.lower() in ("help", "--help", "-h", "?"):
        await say(
            text="VENZARI CODE Help",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*VENZARI CODE — Your AI assistant for VenzariAI* 🤖\n\n"
                                "*Usage:* `/venzari <your question>`\n\n"
                                "*Examples:*\n"
                                "• `/venzari What is our system status?`\n"
                                "• `/venzari Summarize our latest n8n workflow`\n"
                                "• `/venzari What tasks are pending in the repo?`\n"
                                "• `/venzari Check if all services are healthy`\n\n"
                                "You can also *@mention* me in any channel or *DM* me directly.",
                    },
                }
            ],
        )
        return

    session_id = f"slack:{user_id}"
    get_or_create_session("slack", user_id, metadata={"channel": channel})
    increment_message_count(session_id)

    publish("message_received", {
        "interface": "slack",
        "user": user_id,
        "channel": channel,
        "message": message[:200],
    })

    logger.info(f"Slash /venzari from {user_id}: {message[:80]}")

    response = query_venzari(message, session_id=session_id)

    if not response:
        # Check if router is reachable for diagnostic message
        router_url = os.environ.get("VENZARAI_ROUTER_URL", "http://localhost:4001")
        try:
            import requests as _req
            _req.get(f"{router_url}/health/liveliness", timeout=2)
            router_status = "router reachable but returned empty response"
        except Exception:
            router_status = f"router unreachable at {router_url}"
        await say(**format_error(f"No response from VENZARI CODE ({router_status}). Try again in a moment."))
        return

    publish("response_sent", {
        "interface": "slack",
        "session_id": session_id,
        "response_length": len(response),
    })

    await say(**format_response(response, session_id=session_id))


# ---------------------------------------------------------------------------
# @venzari mention
# ---------------------------------------------------------------------------

@app.event("app_mention")
async def handle_mention(event, say, logger):
    raw_text = event.get("text", "")
    # Strip the @venzari mention (format: <@UXXXXXXX> rest of message)
    message = raw_text.split(">", 1)[-1].strip() if ">" in raw_text else raw_text.strip()

    if not message:
        await say(
            text="Yes? Try mentioning me with a question, like `@venzari What is our uptime?`",
            thread_ts=event.get("ts"),
        )
        return

    user_id = event.get("user", "unknown")
    channel = event.get("channel", "")
    thread_ts = event.get("thread_ts") or event.get("ts")
    session_id = f"slack:{user_id}"

    get_or_create_session("slack", user_id, metadata={"channel": channel})
    increment_message_count(session_id)

    publish("message_received", {
        "interface": "slack",
        "user": user_id,
        "channel": channel,
        "message": message[:200],
        "thread": True,
    })

    logger.info(f"Mention from {user_id}: {message[:80]}")

    response = query_venzari(message, session_id=session_id)

    if not response:
        await say(
            **format_error("I didn't get a response. Please try again."),
            thread_ts=thread_ts,
        )
        return

    publish("response_sent", {
        "interface": "slack",
        "session_id": session_id,
        "response_length": len(response),
    })

    kwargs = format_response(response, session_id=session_id)
    kwargs["thread_ts"] = thread_ts
    await say(**kwargs)


# ---------------------------------------------------------------------------
# Direct messages
# ---------------------------------------------------------------------------

@app.event("message")
async def handle_dm(event, say, logger):
    # Only handle DMs (channel_type = "im"), not channel messages
    if event.get("channel_type") != "im":
        return
    # Ignore bot messages and message_changed events
    if event.get("bot_id") or event.get("subtype"):
        return

    message = event.get("text", "").strip()
    if not message:
        return

    user_id = event.get("user", "unknown")
    channel = event.get("channel", "")
    session_id = f"slack:{user_id}"

    get_or_create_session("slack", user_id, metadata={"channel": channel, "dm": True})
    increment_message_count(session_id)

    publish("message_received", {
        "interface": "slack",
        "user": user_id,
        "channel": channel,
        "message": message[:200],
        "dm": True,
    })

    logger.info(f"DM from {user_id}: {message[:80]}")

    response = query_venzari(message, session_id=session_id)

    if not response:
        await say(**format_error("I didn't get a response. Please try again."))
        return

    publish("response_sent", {
        "interface": "slack",
        "session_id": session_id,
        "response_length": len(response),
    })

    await say(**format_response(response, session_id=session_id))


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

async def main():
    logger.info("Starting VENZARI CODE Slack bot (Socket Mode)...")
    handler = AsyncSocketModeHandler(app, SLACK_APP_TOKEN)
    await handler.start_async()


if __name__ == "__main__":
    asyncio.run(main())
