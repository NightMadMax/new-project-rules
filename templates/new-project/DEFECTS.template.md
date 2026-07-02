---
type: defect-log
status: active
owner: ""
last_verified: ""
related: []
---

# Defects

All discovered defects, bugs, and known issues are recorded here.
Do not delete entries. Status is represented by the section where the row
appears: `Open`, `Fixed`, or `Won't Fix`.

## Open

| # | Title | Discovered | Component | Description |
|---|-------|-----------|-----------|-------------|
| — | | | | |

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
- **Status** — represented by the table where the row lives, not by a separate column
- **Fixed** (Fixed table only) — ISO date the fix landed
- **Commit** (Fixed table only) — short commit SHA or PR reference

### Consolidation

When the `Fixed` table grows past ~30 rows, move entries fixed before the
latest release to `docs/quality/DEFECTS_ARCHIVE.md` (same format, content
unchanged) and keep a wikilink to the archive here. Never archive `Open` or
`Won't Fix` rows, and never reuse numbers.
