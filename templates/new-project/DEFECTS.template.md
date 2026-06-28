---
type: defect-log
status: active
owner: ""
last_verified: ""
related: []
---

# Defects

All discovered defects, bugs, and known issues are recorded here.
Do not delete entries — update their status instead.

## Open

| # | Title | Discovered | Component | Description |
|---|-------|-----------|-----------|-------------|
| 1 | _Example: null pointer on empty input_ | YYYY-MM-DD | `src/parser` | Parser crashes when the input string is empty. Root cause: missing guard before `str[0]` access. |

## Fixed

| # | Title | Discovered | Fixed | Commit | Root Cause |
|---|-------|-----------|-------|--------|-----------|
| — | | | | | |

## Won't Fix

| # | Title | Discovered | Reason |
|---|-------|-----------|--------|
| — | | | |

---

### Entry format

When adding a new defect, copy one row into the appropriate table and fill in:

- **#** — sequential number (never reuse)
- **Title** — short imperative phrase describing the symptom
- **Discovered** — ISO date (`YYYY-MM-DD`)
- **Component** — file, module, or subsystem path
- **Description** — one or two sentences: what happens, how to reproduce, root cause if known
- **Fixed** (Fixed table only) — ISO date the fix landed
- **Commit** (Fixed table only) — short commit SHA or PR reference
