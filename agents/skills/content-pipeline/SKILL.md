---
name: content-pipeline
description: |
  Manage the AI content engine pipeline on Venzari VPS. Use for content generation API operations, worker management, and content pipeline troubleshooting.
version: "2.0"
compatible-roles:
  - backend
  - infrastructure
min-claude-version: claude-sonnet-4-5
allowed-tools: Bash, Read
---

# Skill: Content Pipeline

> **Version:** 2.0 | **Last verified:** 2026-05-30 | **Format:** Brief/Detail/Reference

---

## Brief
### Overview

Operate and debug the AI content generation pipeline: ai-content-engine-api, social media
scheduling, and content generation workflows. Generates posts, articles, and marketing content
using [Your-AI-Name]'s AI capabilities.

---

### When to Use

- Generating social media content via the API
- Debugging content engine failures
- Setting up content generation crons
- Running batch content jobs
- Integrating content generation into n8n workflows

---

### Key Facts

| Item | Value |
|---|---|
| Content API | Venzari VPS :5001 (`ai-content-engine-api` container) |
| Content worker | `ai-content-engine-worker` container |
| Runbook | `03-workflow/CONTENT_ENGINE.md` |
| Models used | [Your-AI-Name] VenzariAI Router → jeanne_primary_warm → Ollama (jeanne-primary:latest) |
| Social platforms | Instagram, Twitter/X, LinkedIn (via n8n) |

---

---

## Detail

### Process

### Generate content

```bash
# Health check
"curl -s http://localhost:5001/health"

# Generate a social post
'curl -s -X POST http://localhost:5001/generate \
  -H "Content-Type: application/json" \
  -d "{\"topic\": \"AI automation for small business\", \"format\": \"instagram_post\", \"tone\": \"professional\"}"'
```

### Check container health

```bash
"docker ps | grep ai-content && docker logs ai-content-engine-api --tail 30"
```

### Trigger batch content generation

```bash
# Via n8n webhook (set up in n8n for scheduled batch runs)
# Or directly via API:
'curl -s -X POST http://localhost:5001/batch \
  -H "Content-Type: application/json" \
  -d "{\"topics\": [\"AI tools\", \"SaaS growth\"], \"count\": 5}"'
```

### Debug content worker

```bash
"docker logs ai-content-engine-worker --tail 50"
# Look for: Celery task errors, model connection issues, queue stalls
```

---

### Runbook Reference

Full procedures: `03-workflow/CONTENT_ENGINE.md`

---

### Verification

```bash
"docker ps | grep ai-content | grep Up | wc -l"  # should be 2
"curl -s -o /dev/null -w '%{http_code}' http://localhost:5001/health"  # 200
```

---

## Reference

### Failure Runbook

| Symptom | Fix |
|---|---|
| API 500 | `docker logs ai-content-engine-api --tail 50`, check model connection |
| Worker not processing | Restart worker: `docker restart ai-content-engine-worker` |
| Slow generation | Check VenzariAI Router health, Ollama RAM, consider GPU fallback |
| Model errors | Verify jeanne_primary_warm → Ollama chain via `ai-model-ops` skill |

---

