---
type: promotion-candidate
id: PC-2026-001
status: implemented
source: "new-project-rules: DEFECTS #25 and #27"
observation: "После исправления defect-tracking contract часть связанных rule layers и templates осталась на старой формулировке."
generalized_lesson: "Reusable rule contract нужно закреплять во всех производных слоях и автоматической проверкой coverage."
scope: "Проекты, где стандарт разворачивается в rules, templates, guides или agent bridges."
evidence: "commits 97ae46f and fb079d3; enhanced test-skills literal coverage"
artifact_type: test
proposed_target: "scripts/test-skills.sh and scripts/test-skills.ps1"
created: 2026-06-30
last_verified: 2026-07-06
implemented_commit: fb079d3
---

# Coverage производных слоёв reusable rule contract

## Notes

Реализовано: skill checks требуют обязательные policy literals в mirrored rule
contracts.
