---
type: threat-model
status: active
owner: project
last_verified: <YYYY-MM-DD>
source_of_truth: repository
---

# Threat Model

## Scope and Assets

- Что защищаем и что не входит в модель?

## Trust Boundaries and Data Flows

- Компоненты, внешние субъекты, хранилища и переходы границ доверия.

## Threats

| Threat | Impact | Likelihood | Mitigation | Verification |
|---|---|---|---|---|

## Software Supply Chain

- Зафиксируйте внешние dependencies, CI actions, package registries и
  credentials, пересекающие trust boundary.
- Для каждого контроля укажите pin/lock/provenance, механизм обновления и
  проверяемый rollback. Не считайте mutable tag или branch immutable source.

## Assumptions and Residual Risks

- Проверяемые предположения и принятые остаточные риски.
