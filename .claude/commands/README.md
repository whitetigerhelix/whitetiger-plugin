# WhiteTiger Plugin Claude Commands

This folder contains interactive command skills used to support the AI Groove Writer workflow.

## Available skills

- `groove.md`
  - Groove writing, prompt crafting, rhythm/style guidance, musical analysis
- `llm-config.md`
  - Local `.env` provider/secret setup, mock/real toggling, validation checks
- `cloud-provider.md`
  - Azure/provider onboarding and provider-side troubleshooting guidance
- `whitetiger-plugin-assistant.md`
  - Top-level orchestrator that routes to specialized skills

## Design principle

Skills should **reference source-of-truth docs** instead of duplicating technical details.

Primary references:

- `Docs/Setup_Guide.md`
- `Docs/Architecture.md`
- `Docs/JSON_Contract.md`
- `Docs/AI_Groove_Writer_Project_Plan.md`
- `Docs/Work_Plan.md`

When implementation details change, update docs first, then keep skills thin and aligned by linking to the updated docs.

## Notes

- Keep security boundaries explicit: secrets in `service/.env`, localhost service only.
- Prefer Windows-native commands in examples, with Bash alternatives where helpful.
