---
type: promotion-candidate
id: PC-2026-609cfa13c4bb
status: implemented
source: "Best Practices: practices/tools/PC-2026-850607ffdb29-pinned-cross-repo-contract.md"
observation: "NPR local test suite passed green while the sibling Best Practices repo kept dangling references to a skill deleted in NPR, and a Phase 3 change contradicted ADR-0003's own version-bump requirement."
generalized_lesson: "A change spanning coupled repositories or touching a decision record cannot be verified by the local test loop; before finalizing, sweep the sibling repo for stale references, re-read the relevant ADR consequences, and check governance state. Enforce it with an executable cross-repo contract check instead of manual discipline."
scope: "Any multi-repository standard or knowledge system that keeps decision records (ADRs) and coupled sibling repositories."
evidence: "Accepted BP practice PC-2026-850607ffdb29 (E2); NPR PR #4/#5; scripts/test-best-practices-contract.py negative fixtures; phase 7 live pin-drift detection"
artifact_type: test
proposed_target: "config/best-practices-contract.json; scripts/check_best_practices_contract.py; scripts/test-best-practices-contract.py; CI workflows"
created: 2026-07-07
last_verified: 2026-07-07
implemented_commit: ee4677a
---

# Verify cross-repo and ADR consistency, not just the local test loop

## Notes

Одобрено пользователем 2026-07-07. Реализовано исполняемым pinned contract,
negative fixtures и CI на Linux, Windows и macOS. Текстовое правило в
`AGENTS.md` не добавлялось: исполняемая проверка удерживает инвариант точнее и
не расходует instruction budget.
