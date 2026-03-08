# WhiteTiger Plugin — Top-Level Claude Context

## Purpose

This file is the top-level context for the whole repository. It defines how assistants should reason about project scope, skill routing, and source-of-truth documentation.

## Project summary

WhiteTiger Plugin currently centers on **AI Groove Writer**:

- Max for Live MIDI device (`m4l/`) for UI, clip interaction, and post-processing
- Local Python FastAPI service (`service/`) for provider calls, validation, caching, and usage tracking
- Documentation-first workflow (`Docs/`) as the canonical source for technical behavior

## Source-of-truth rule

Do not duplicate canonical schemas, limits, endpoint contracts, or setup steps in assistant skills. Reference docs directly:

- [Docs/AI_Groove_Writer_Project_Plan.md](Docs/AI_Groove_Writer_Project_Plan.md)
- [Docs/Work_Plan.md](Docs/Work_Plan.md)
- [Docs/Architecture.md](Docs/Architecture.md)
- [Docs/JSON_Contract.md](Docs/JSON_Contract.md)
- [Docs/Setup_Guide.md](Docs/Setup_Guide.md)
- [Docs/M4L_Build_Guide.md](Docs/M4L_Build_Guide.md)
- [Docs/Plan_Server_Management.md](Docs/Plan_Server_Management.md)
- [Docs/Ideas_and_Brainstorm.md](Docs/Ideas_and_Brainstorm.md)

If docs and code diverge, align docs and code rather than embedding conflicting guidance in skill files.

## Skill routing map

Interactive skills live under `.claude/commands/`:

- `whitetiger-plugin-assistant.md` — top-level orchestrator for all requests
- `groove.md` — groove writing, musical prompting, preset and rhythm guidance
- `llm-config.md` — local provider config, secrets handling, mock/real toggle, validation
- `cloud-provider.md` — Azure/provider onboarding and provider-side troubleshooting

Commands index: `.claude/commands/README.md`

## Core engineering constraints

- Keep secrets in `service/.env` only (never in `.amxd` or committed files)
- Service must bind to `127.0.0.1` only
- Provider access must go through `service/llm_provider.py` abstraction
- Post-processing (swing/humanize/velocity jitter) stays in M4L, not LLM output logic
- Beat units are quarter-note beats per JSON contract

## Windows-first local workflow

Primary setup/config scripts:

- `service/setup.ps1` / `service/setup.cmd`
- `service/configure_env.ps1` / `service/configure_env.cmd`

Bash scripts remain optional compatibility paths.

## Assistant behavior expectations

- Keep changes clean, minimal, and test-verified
- Prefer simple, robust workflows over heavy complexity
- Be explicit about implemented vs planned functionality
- Guide users interactively with short, actionable steps and clear validation checks
