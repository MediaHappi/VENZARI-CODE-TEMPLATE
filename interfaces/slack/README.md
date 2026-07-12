# VENZARI CODE — Slack Integration

Two ways to connect VENZARI CODE with Slack. Start with Tier 1.

---

## Tier 1 — Outbound Notifications (2 minutes, no app required)

Get notified in Slack when tasks complete, goals finish, or the agent gets blocked.
Uses Incoming Webhooks — the simplest Slack integration. No bot token, no Python, no Redis.

### Setup

**Step 1 — Create a webhook URL (60 seconds)**

1. Go to https://api.slack.com/apps
2. Click **"Create New App"** → **"From scratch"**
3. Name it "VENZARI CODE", pick your workspace → **"Create App"**
4. In the sidebar: **Features → Incoming Webhooks** → Toggle **On**
5. Click **"Add New Webhook to Workspace"** → pick your `#venzari-notifications` channel → **"Allow"**
6. Copy the webhook URL (`https://hooks.slack.com/services/T.../B.../...`)

> **Tip:** There's also a one-click shortcut at https://api.slack.com/incoming-webhooks — click
> "Add to Slack" button to create a webhook without building a full app.

**Step 2 — Configure VENZARI CODE**

```bash
venzari-code slack configure --webhook https://hooks.slack.com/services/T.../B.../...
venzari-code slack test       # sends a test message to verify
venzari-code slack status     # shows current config
```

**Step 3 — You're done.** VENZARI CODE will now post to Slack when:
- ✅ A task is completed
- 🎯 A goal run finishes
- ⚠️ The agent gets blocked and needs attention
- 💰 API cost crosses your threshold (configurable)

### Optional: Set alert channel and thresholds

```bash
venzari-code slack configure \
  --webhook https://hooks.slack.com/services/... \
  --channel "#engineering-alerts"
```

Edit `~/.venzari/slack.json` for fine-grained control:
```json
{
  "webhookUrl": "https://hooks.slack.com/services/...",
  "alertChannel": "#engineering-alerts",
  "notifyOnTaskComplete": true,
  "notifyOnGoalComplete": true,
  "notifyOnBlock": true,
  "notifyOnCostAlert": true,
  "costAlertThreshold": 1.00
}
```

### Sending custom messages

```bash
venzari-code slack notify "Deployment complete — all 42 tasks passed"
venzari-code slack notify "Sprint review ready" --channel "#product"
```

---

## Tier 2 — Full Slack Bot with Slash Commands (Optional, 15 minutes)

Lets your team trigger VENZARI CODE from Slack with slash commands:

```
/venzari update all API documentation
/venzari-goal "refactor the auth module to use JWT"
/venzari-tasks
/venzari-status
```

This requires a running `venzari-code serve --port 4001` and a more complete Slack app setup.

### When to use Tier 2

- You have a team using Slack as their primary interface
- You want to trigger agents from Slack without opening a terminal
- You're comfortable running a background Python process

### Setup

**Prerequisites:**
- Python 3.11+
- Redis (for session tracking)
- `venzari-code serve --port 4001` running
- Slack workspace admin access (to install the app)

**Install dependencies:**
```bash
cd interfaces/slack
pip install -r requirements.txt
```

**Create the Slack app:**

1. Go to https://api.slack.com/apps → New App → From scratch
2. **Socket Mode** (Features → Socket Mode → Enable → create App-Level Token `xapp-...`)
3. **Slash Commands** (Features → Slash Commands):
   - `/venzari` — command for VENZARI CODE
   - `/venzari-goal` — run a goal
   - `/venzari-tasks` — list tasks
   - `/venzari-status` — agent status
4. **OAuth & Permissions** → Bot Token Scopes: `chat:write`, `app_mentions:read`, `im:history`, `commands`
5. **Install to workspace** → copy Bot Token (`xoxb-...`)
6. **Event Subscriptions** → Subscribe to: `app_mention`, `message.im`

**Configure:**
```bash
export SLACK_BOT_TOKEN="xoxb-..."
export SLACK_APP_TOKEN="xapp-..."
export VENZARI_ACP_URL="http://localhost:4001"
export REDIS_URL="redis://localhost:6379"
```

**Run:**
```bash
python -m interfaces.slack.bot
```

**Or with Docker:**
```bash
docker build -f interfaces/slack/Dockerfile -t venzari-slack .
docker run -e SLACK_BOT_TOKEN=xoxb-... -e SLACK_APP_TOKEN=xapp-... venzari-slack
```

---

## Files in this directory

| File | Purpose |
|------|---------|
| `bot.py` | Full Slack bot (Tier 2) — slash commands, mentions, DMs |
| `alert_sender.py` | Alert helpers (task complete, agent blocked) |
| `message_formatter.py` | Block Kit formatting utilities |
| `requirements.txt` | Python dependencies for Tier 2 |
| `Dockerfile` | Container for Tier 2 bot |
| `../shared/venzari_client.py` | HTTP client to venzari-code ACP server |
| `../shared/session_manager.py` | Redis session tracking |
| `../shared/event_publisher.py` | Redis event bus |

---

## Troubleshooting

**Test webhook delivery:**
```bash
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"VENZARI CODE test"}' \
  YOUR_WEBHOOK_URL
```

**Webhook not working:**
- Verify URL is exactly as copied from Slack (no trailing spaces)
- The URL should look like: `https://hooks.slack.com/services/T.../B.../...`
- Channel must exist and the webhook app must be a member

**Questions:** support@venzari.dev
