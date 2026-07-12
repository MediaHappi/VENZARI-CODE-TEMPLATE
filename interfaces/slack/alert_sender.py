"""
interfaces/slack/alert_sender.py

Send monitoring alerts from VENZARI CODE infrastructure to a Slack channel.
Default channel: #venzari-tasks

Call send_alert() from inference-monitor.sh hooks, cron scripts, or
any process that detects an infrastructure failure.
"""

import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_ALERT_CHANNEL = os.environ.get("SLACK_ALERT_CHANNEL", "#venzari-tasks")

_COLORS = {
    "info": "#36a64f",
    "warning": "#ff9f00",
    "error": "#e01e5a",
    "critical": "#7c0000",
}

_ICONS = {
    "info": ":information_source:",
    "warning": ":warning:",
    "error": ":red_circle:",
    "critical": ":sos:",
}


async def send_alert(
    app,
    title: str,
    message: str,
    level: str = "info",
    channel: str = None,
) -> bool:
    """
    Post a monitoring alert to Slack.

    Args:
        app:     slack_bolt AsyncApp instance
        title:   Short alert title (shown in bold)
        message: Alert body — supports mrkdwn
        level:   "info" | "warning" | "error" | "critical"
        channel: Override default alert channel

    Returns:
        True if posted successfully, False otherwise.
    """
    target = channel or _ALERT_CHANNEL
    icon = _ICONS.get(level, ":information_source:")
    color = _COLORS.get(level, "#36a64f")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    try:
        await app.client.chat_postMessage(
            channel=target,
            text=f"{icon} {title}",
            attachments=[
                {
                    "color": color,
                    "title": f"{icon} {title}",
                    "text": message,
                    "footer": f"VENZARI CODE | {ts}",
                    "mrkdwn_in": ["text"],
                }
            ],
        )
        logger.info(f"Alert posted to {target}: [{level}] {title}")
        return True
    except Exception as e:
        logger.error(f"Failed to post alert to {target}: {e}")
        return False


async def send_task_complete(app, task_id: str, summary: str, channel: str = None) -> bool:
    """Post a task completion notification."""
    return await send_alert(
        app,
        title=f"Task {task_id} Complete",
        message=summary,
        level="info",
        channel=channel,
    )


async def send_inference_down(app, service: str, details: str = "") -> bool:
    """Post an inference failure alert."""
    msg = f"*{service}* is not responding."
    if details:
        msg += f"\n{details}"
    return await send_alert(app, title="Inference Alert", message=msg, level="error")
