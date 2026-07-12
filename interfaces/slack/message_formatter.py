"""
interfaces/slack/message_formatter.py

Format VENZARI CODE responses for Slack using Block Kit where beneficial.
Falls back to plain text for simple responses.
"""

import re


_BLOCK_THRESHOLD = 400  # chars above which we use blocks


def format_response(text: str, session_id: str = None) -> dict:
    """
    Format a VENZARI CODE response for Slack.

    Returns a dict suitable for passing as **kwargs to say() or chat_postMessage().
    Uses Block Kit for longer/structured responses, plain text otherwise.
    """
    if not text:
        return {"text": "_VENZARI CODE returned an empty response._"}

    if len(text) <= _BLOCK_THRESHOLD and not _has_markdown_structure(text):
        return {"text": text}

    # Use blocks for richer formatting
    blocks = _build_blocks(text)
    return {
        "text": text[:150] + ("..." if len(text) > 150 else ""),  # fallback for notifications
        "blocks": blocks,
    }


def format_error(message: str) -> dict:
    return {
        "text": f":warning: {message}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":warning: *Error:* {message}",
                },
            }
        ],
    }


def format_thinking() -> dict:
    return {"text": "_VENZARI CODE is thinking..._"}


def _has_markdown_structure(text: str) -> bool:
    patterns = [r"^#{1,3} ", r"^[-*] ", r"^```", r"\n\n", r"\*\*"]
    return any(re.search(p, text, re.MULTILINE) for p in patterns)


def _build_blocks(text: str) -> list:
    # Slack mrkdwn max per section: 3000 chars
    chunks = _split_text(text, 2800)
    blocks = []
    for chunk in chunks:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": _to_slack_mrkdwn(chunk)},
        })
    blocks.append({"type": "divider"})
    return blocks


def _split_text(text: str, max_len: int) -> list:
    if len(text) <= max_len:
        return [text]
    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = max_len
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks


def _to_slack_mrkdwn(text: str) -> str:
    # Convert basic markdown to Slack mrkdwn
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)       # bold
    text = re.sub(r"__(.+?)__", r"_\1_", text)             # italic
    text = re.sub(r"^#{1,3} (.+)$", r"*\1*", text, flags=re.MULTILINE)  # headers
    return text
