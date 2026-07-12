# [YOUR-AI-NAME] Agent Skills

Skills are reusable engineering behaviors that agents load when performing specific tasks.
Each skill has 6 sections: Overview, When to Use, Process, Rationalizations, Red Flags, Verification.

Skills are workflows agents follow — not reference docs they read passively.
Load one skill at a time. Complete it fully. Do not auto-chain into the next skill.

## Active Skills

| Skill | Slug | Use for |
|---|---|---|
| Infrastructure Operations | infra | SSH, tunnel, containers, cron |
| Telegram Debug | debug-telegram | Diagnosing Telegram/OpenClaw failures |
| Script Deployment | deploy-script | Deploying scripts to /usr/local/bin/ |
| VenzariAI Router Config | venzarai-router-config | Editing VenzariAI Router config safely |

## Skill Anatomy

Every skill MUST have these 6 sections:

1. **Overview** — one sentence describing what this skill does
2. **When to Use** — explicit trigger conditions (not "whenever needed")
3. **Process** — numbered steps with checkpoints; each step has a verifiable outcome
4. **Rationalizations** — excuses agents commonly make, each paired with a rebuttal
5. **Red Flags** — conditions that require stopping and escalating to Billy immediately
6. **Verification** — non-negotiable evidence format (curl output, docker ps output — never prose)

## Governing Principles

- Verification is evidence, not assertion. "It should work" is not verification.
- Rationalizations section exists to pre-empt the shortcuts agents take under time pressure.
- Red flags are hard stops. Three identical failures = escalate to Billy (GOLDEN RULE 8).
- Skills do not invoke other skills automatically. The agent or task decides the next step.
