---
name: business-automation
description: |
  Manage n8n workflows and HubSpot/social media automations. Use for workflow changes, webhook configuration, and business automation tasks on Venzari VPS.
version: "2.0"
compatible-roles:
  - backend
  - infrastructure
min-claude-version: claude-sonnet-4-5
allowed-tools: Bash, Read
---

# Skill: Business Automation

> **Version:** 2.0 | **Last verified:** 2026-05-30 | **Format:** Brief/Detail/Reference

---

## Brief
### Overview

Manage HubSpot CRM workflows, n8n automations, and lead pipeline operations for
Venzari AI. Covers CRM data, workflow triggers, and business process automation.

---

### When to Use

- Setting up or debugging n8n workflows
- HubSpot CRM data sync issues
- Lead pipeline automation not triggering
- Adding new automation workflows
- Checking n8n execution history
- Social media posting automation

---

### Key Facts

| Item | Value |
|---|---|
| n8n instance | Venzari VPS :5678, `http://[your-domain.com]/n8n` |
| n8n container | `n8n` (Venzari VPS) |
| HubSpot runbook | `03-workflow/HUBSPOT.md` |
| Social media runbook | `03-workflow/SOCIAL_MEDIA.md` |
| Content engine runbook | `03-workflow/CONTENT_ENGINE.md` |
| AI content API | Venzari VPS :5001 |
| Business goal | $5K MRR — see `docs/context/BILLY-PROFILE.md` |

---

---

## Detail

### Process

### Check n8n health

```bash
# HTTP check
curl -s -o /dev/null -w "%{http_code}" http://[your-domain.com]/n8n
# Must be 200 or 301

# Container check
"docker ps | grep n8n && docker logs n8n --tail 20"
```

### Trigger an n8n workflow manually

```bash
# Via n8n webhook (replace with actual webhook URL)
curl -s -X POST "http://[your-domain.com]/n8n/webhook/<workflow-id>" \
  -H "Content-Type: application/json" \
  -d '{"trigger": "manual", "source": "jeanne-agent"}'
```

### Check content engine API

```bash
# Health
curl -s "http://localhost:5001/health" -H "X-API-Key: ${CONTENT_ENGINE_API_KEY}"

# Test content generation
curl -s -X POST "http://localhost:5001/generate" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${CONTENT_ENGINE_API_KEY}" \
  -d '{"topic": "AI business tools", "format": "social_post"}'
```

### Debug HubSpot integration

```bash
# Check runbook for current CRM state
cat /opt/YOUR-PROJECT/03-workflow/HUBSPOT.md

# Verify n8n HubSpot workflows are active
# Log into n8n UI at [your-domain.com]/n8n → check workflow status
```

---

### Runbooks

- `03-workflow/HUBSPOT.md` — Full HubSpot CRM runbook
- `03-workflow/SOCIAL_MEDIA.md` — Social automation runbook
- `03-workflow/CONTENT_ENGINE.md` — Content generation runbook

---

### Verification

```bash
curl -s -o /dev/null -w "n8n: %{http_code}\n" http://[your-domain.com]/n8n
"docker ps | grep -E 'n8n|ai-content' | grep Up"
```

---

## Reference

### Failure Runbook

| Symptom | Fix |
|---|---|
| n8n not accessible | `"docker restart n8n"`, verify :5678 |
| Workflow not triggering | Check n8n execution log, verify webhook URL |
| HubSpot sync failing | Check n8n HubSpot node credentials, re-auth if needed |
| Content API 401 | Check CONTENT_ENGINE_API_KEY env var |

---

