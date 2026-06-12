# Changelog

## [Unreleased]

### Planned
- SQL source pipeline: Oracle, PostgreSQL, Snowflake end-to-end on live databases
- CLI interface (`dashboard-drafter generate config.txt`)
- Multi-template support (different page layouts per use case)
- Theme swap — swap colour theme without regenerating the full dashboard
- CI/CD integration for automated dashboard deployment

---

## [1.0.0] — 2026-05-23 — Initial Public Release

### Phase 1: Full Template + CSV Pipeline

**342 tests. All passing.**

#### Modules delivered
- `config_parser.py` — Parses the `/*FACTORY*/` config block; extracts title, theme, DB type, and all 6 slot categories (CNT, SUM, AVG, DATE, KEY, OTHER)
- `mquery_generator.py` — Generates Power Query M code for CSV, Excel, Oracle, PostgreSQL, and Snowflake sources
- `rename_pipeline.py` — Renames all field references across TMDL, DAX bodies, relationships, Field Parameter tables (NAMEOF refs + row labels + index renumbering), and visual JSON files (queryRef, displayName, Property, drillthrough filter configs)
- `visibility_pipeline.py` — Sets unused slots to `isHidden` + `isAvailableInMDX: false` in TMDL; purges unused-slot entries from visual projection arrays and drillthrough page configs
- `format_pipeline.py` — Applies `formatString` metadata to active measures and columns ($, #, #.0, #.00, %)
- `sort_pipeline.py` — Wires `sortByColumn` for ORDER columns; hides ORDER columns from visuals
- `factory.py` — Orchestrates the full pipeline end-to-end: template copy → directory rename → `.pbip` patch → M Query write → sourceColumn update → visibility → format → rename → sort → hidden purge

#### Template
- 40-column production template (SUM ×10, CNT ×5, AVG ×5, Key Dimension ×10, Other Field ×10, DateKey ×1)
- Field Parameter tables: `Select Dimension`, `Select 2nd Dimension`, `Select Measure`
- LastRefresh table with `DateTime.LocalNow()`
- 5 pages: Summary, Adhoc, Details, Visual Objects (hidden), Colour Palette (hidden)
- Auto date/time disabled

#### Key milestones
- `rename_pipeline` — safe rename without breaking visual bindings (lineageTag-preserving)
- `visibility_pipeline` — unused slots auto-disappear from all visuals
- `format_pipeline` — `$`, `#`, `#.0`, `#.00`, `%` format string support
- `sort_pipeline` — `"ORDER [FieldName]"` convention for sort column wiring
- `factory.py` orchestrator — single-call end-to-end pipeline
- Field Parameter support — dynamic chart switching via `Select Dimension` and `Select Measure`
- Drillthrough support — `page.json` filter config rename for drillthrough pages

#### E2E validated
- HR Dashboard (CSV source) — opens in Power BI Desktop with zero errors
- Finance Dashboard (CSV source) — opens in Power BI Desktop with zero errors

---

## [0.1.0] — 2026-05 — Phase 0: Proof of Concept

**4 technical assumptions validated. 224 tests established.**

#### Validated assumptions
1. **Rename without breaking visuals** — `lineageTag` (GUID) survives rename; visual bindings remain intact
2. **Unused slot removal** — `Table.RemoveColumns` in M Query + `isHidden` in TMDL eliminates empty columns without errors
3. **sourceColumn tracking** — updating `sourceColumn` to match M Query output column names correctly links TMDL metadata to data
4. **Full pipeline integration** — `config_parser` → `rename_pipeline` → `visibility` → `format` → `sort` → `factory` runs end-to-end without conflict

#### POC PBIP
- Mini template: SUM ×2, CNT ×1, AVG ×1, Key_Dim ×2
- Opens in Power BI Desktop with zero errors
