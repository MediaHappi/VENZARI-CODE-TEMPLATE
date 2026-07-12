FROM python:3.12-slim

WORKDIR /app

COPY interfaces/slack/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY interfaces/ /app/interfaces/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Required env vars (set via docker run -e or docker-compose):
#   SLACK_BOT_TOKEN  — Bot User OAuth Token (xoxb-...)
#   SLACK_APP_TOKEN  — App-Level Token for Socket Mode (xapp-...)
#   VENZARI_ACP_URL  — venzari-code ACP server (default: http://localhost:4001)
#   REDIS_URL        — Redis for sessions (default: redis://localhost:6379)

CMD ["python", "-m", "interfaces.slack.bot"]
