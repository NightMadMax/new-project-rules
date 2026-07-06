---
type: promotion-candidate
id: PC-2026-e6f54a0fe78a
status: triaged
source: "jira-analytics agent-defect-log D-004; new-project-rules THREAT_MODEL and sync_global_agents.py"
observation: "Широкий рекурсивный поиск по пользовательскому профилю вывел historical credential из state/session files."
generalized_lesson: "Диагностика чувствительных профилей должна начинаться с allowlist файлов, исключать state/backups/sessions/logs и редактировать вывод до отображения."
scope: "Agent tooling, integrations и migration scripts, читающие конфиги вне repository."
evidence: "jira-analytics D-004 and secret-safe structural diff regression coverage in new-project-rules"
artifact_type: rule
proposed_target: "GLOBAL_AGENT_INSTRUCTIONS.md, AGENTS template and policy tests"
created: 2026-07-06
last_verified: 2026-07-06
---

# Secret-safe inspection пользовательских профилей

## Notes

Очищено от credentials и private paths. Требует отдельного approval.
