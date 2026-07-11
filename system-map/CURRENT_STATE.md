# CURRENT STATE — [PROJECT NAME]

> This file describes the live state of all running systems.
> Update it after every infrastructure change.
> VENZARI CODE reads this at every session start.

**Last updated:** [FILL IN: date]
**Updated by:** [FILL IN: who/what made this change]

---

## System Overview

[FILL IN: 1-2 sentence summary of the system state. e.g., "All services nominal. Migration to PostgreSQL 16 complete."]

---

## Running Services

[FILL IN: List every service, its status, port, and any notes.]

| Service | Status | Port | Notes |
|---------|--------|------|-------|
| [e.g., nginx] | ✅ running | [e.g., 80, 443] | [e.g., SSL cert expires 2027-01] |
| [e.g., postgres] | ✅ running | [e.g., 5432] | [e.g., v16, 3 databases] |
| [e.g., redis] | ✅ running | [e.g., 6379] | [e.g., in-memory only, no persistence] |
| [e.g., your-app] | ✅ running | [e.g., 3000] | [e.g., v1.2.0, last deployed 2026-07-01] |

---

## Infrastructure

[FILL IN: Describe servers, cloud resources, volumes, etc.]

### Servers / VMs

| Host | Role | OS | CPU | RAM | Disk |
|------|------|----|-----|-----|------|
| [FILL IN] | [e.g., primary] | [e.g., Ubuntu 24.04] | [e.g., 8 cores] | [e.g., 32GB] | [e.g., 500GB SSD] |

### Storage

[FILL IN: Databases, volumes, S3 buckets, etc.]

- **[Database name]** — [engine + version], [size], [backup schedule]
- **[Volume name]** — [size], [mount point], [what uses it]

---

## Environment Variables Required

[FILL IN: List all required env vars by name only — NO VALUES.]

| Variable | Required | Used By |
|----------|----------|---------|
| `[FILL IN]` | ✅ yes | [FILL IN] |
| `[FILL IN]` | ⚠️ optional | [FILL IN] |

---

## Recent Changes

[FILL IN: What changed recently? Most recent first.]

| Date | Change | Author |
|------|--------|--------|
| [FILL IN] | [e.g., "Added Redis for session caching"] | [FILL IN] |

---

## Known Issues / Watch Items

[FILL IN: Anything fragile, degraded, or being monitored.]

- [FILL IN: e.g., "Disk at 72% — clean up logs before next deploy"]
- [FILL IN: e.g., "SSL cert for api.example.com expires in 30 days"]

---

## Backup Status

[FILL IN: When was the last backup? Where is it stored?]

| Resource | Last Backup | Location | Verified |
|----------|------------|----------|---------|
| [FILL IN] | [FILL IN] | [FILL IN] | [FILL IN] |

---

*Keep this file current. Out-of-date state information causes incorrect VENZARI CODE decisions.*
