---
name: pbi-drafter
description: "Generate a Power BI dashboard PBIP from a /*FACTORY*/ Config Block using the Dashboard Drafter pipeline. Takes a ready config block, runs parse_config → run_factory, outputs a PBIP dashboard. Use when user says: 'generate dashboard', 'run dashboard drafter', 'build dashboard from config', 'run factory', 'create dashboard', 'PBI dashboard generator', 'ダッシュボード生成', or provides a /*FACTORY*/ config block with generation intent."
---

# PBI Drafter

## Overview

Execute the Dashboard Drafter pipeline from a `/*FACTORY ... */` Config Block and produce a ready-to-open PBIP dashboard. This skill **only generates** — it does not draft configs. Use `pbi-drafter-configurator` first if you don't have a config block yet.

Trigger phrases: `generate dashboard`, `run dashboard drafter`, `build dashboard from config`, `run factory`, `create dashboard`, `PBI dashboard generator`, `ダッシュボード生成`, or a `/*FACTORY ... */` block with generation intent.

---

## Step 1 — Validate Input

- Confirm the input contains a `/*FACTORY ... */` block. If not, tell the user to run `pbi-drafter-configurator` first.
- Check that the `SOURCE:` file exists at the specified path. If not, report the missing path and stop.
- Verify the config uses **actual CSV column names** before `AS` (e.g. `amount AS "Amount"`, not `SUM_Measure_1 AS "Amount"`). If slot placeholder names are used as source columns, warn the user:

  > ⚠️ The config uses template slot names (e.g. `SUM_Measure_1 AS "Amount"`) as source columns. This will cause Power BI to error with "column not found" on refresh. Use `pbi-drafter-configurator` to regenerate the config with actual CSV column names, or manually replace the slot names with the real CSV column headers.

---

## Step 2 — Pre-flight

- Remind the user: **"Close PBI Desktop before generation to avoid file-lock errors."**
- Verify the template folder exists at `pbi-drafter/template/` relative to the repo root.
  - If missing, stop and report the path.

---

## Step 3 — Generate

Working directory: `<repo-root>/pbi-drafter/`

Before running, sanitise the TITLE from the config block:
- Replace `&` with `and`
- Remove any character in `< > : " / \ | ? *`

These characters are invalid in Windows folder names and will cause `run_factory` to fail silently or produce a broken output path. If sanitisation changes the title, inform the user: *"TITLE sanitised: 'Profit & Loss' → 'Profit and Loss'"*.

Run the following Python (inline, no separate script file needed):

```python
import sys, shutil, re
from pathlib import Path

repo_root = Path(r"<repo-root>")
drafter = repo_root / "pbi-drafter"
sys.path.insert(0, str(drafter))

from src.config_parser import parse_config
from src.factory import run_factory

config_text = r'''<paste the full /*FACTORY ... */ block here>'''

cfg = parse_config(config_text)

raw_title = cfg['title']
safe_title = raw_title.replace('&', 'and')
safe_title = re.sub(r'[<>:"/\\|?*]', '', safe_title).strip()
if safe_title != raw_title:
    cfg['title'] = safe_title
    print(f'TITLE sanitised: {raw_title!r} -> {safe_title!r}')

title = cfg['title'].replace(' ', '_')
out = drafter / 'output' / title
if out.exists():
    shutil.rmtree(out)
result = run_factory(
    drafter / 'template',
    drafter / 'output',
    cfg,
)
print('Generated:', result)
```

If generation fails, show the **full error traceback** — do not suppress or summarise it.

---

## Step 4 — Verify Output

After successful generation:

1. **Output first 20 lines of `Fact.tmdl`** from `pbi-drafter/output/<Title>/<Title>.SemanticModel/definition/tables/Fact.tmdl`
2. **Check no template slot names remain** in visible `sourceColumn:` entries (lines without `isHidden`). Template slot names are: `SUM_Measure_1`–`10`, `CNT_Measure_1`–`5`, `AVG_Measure_1`–`5`, `Key_Dim_1`–`10`, `Other_Field_1`–`10`, `DateKey`.
3. **Verify format strings** — SUM columns with `$` format → `formatString: $#,0.00`; `#` → integer; `%` → percentage; `#.0` → one decimal.
4. **Report hidden field count**: count lines containing `isHidden` in Fact.tmdl.

---

## Step 5 — Report to User

```
✅ Dashboard generated at:
   pbi-drafter/output/<Title>/<Title>.pbip

Open in PBI Desktop and click "Refresh" to load data.

[first 20 lines of Fact.tmdl]
[any verification warnings]
```

---

## Critical Rules

| Rule | Detail |
|---|---|
| **Working directory** | `<repo-root>/pbi-drafter/` |
| **Never modify template/** | The template is the golden master. All output goes to `output/`. |
| **Delete before regenerate** | Always `shutil.rmtree(out)` before `run_factory` to avoid stale artefacts. |
| **TITLE must be Windows filename-safe** | Forbidden characters in TITLE: `& < > : " / \ | ? *`. Replace `&` with `and`; strip all others. Sanitise before calling `run_factory`. |
| **Actual CSV column names** | Source token before `AS` must be the real CSV column name. Slot placeholder names cause "column not found" in Power BI. |
| **CNT columns → type text** | CNT source columns (used for DISTINCTCOUNT) load as `type text`. ID fields like `E00001` or `INV-12345` are strings — this is intentional and correct. |
| **DAX_ measures excluded from M Query** | The `DAX_` prefix measures are TMDL artefacts only — they are never part of the M Query `field_map`. |
| **en-US.tmdl untouched** | Never read or write `en-US.tmdl` — PBI Desktop auto-regenerates it. |
| **sourceColumn = M Query output name** | After the rename step, `sourceColumn` in TMDL must match the business display name the M Query outputs. |
| **Date categoricals excluded from KEY** | Month, Quarter, Year, FY, MonthName, Period, Week columns should NOT be in KEY slots. |
| **Full traceback on failure** | If `run_factory` or `parse_config` raises, show the complete traceback — never summarise. |
| **350 TDD tests** | All pipeline steps are covered. Run `python -m pytest tests/ -q` in `pbi-drafter/` if something seems broken. |
