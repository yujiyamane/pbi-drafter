import json
import re
from pathlib import Path


def get_hidden_columns(config):
    hidden = set()
    for i, slot in enumerate(config.get("sum", []), start=1):
        if slot is None:
            hidden.add(f"SUM_Measure_{i}")
    for i, slot in enumerate(config.get("cnt", []), start=1):
        if slot is None:
            hidden.add(f"CNT_Measure_{i}")
    for i, slot in enumerate(config.get("avg", []), start=1):
        if slot is None:
            hidden.add(f"AVG_Measure_{i}")
    for i, slot in enumerate(config.get("key", []), start=1):
        if slot is None:
            hidden.add(f"Key_Dim_{i}")
    other_template_slots = {
        k for k in config.get("field_map", {})
        if re.match(r"Other_Field_\d+$", k)
    }
    if other_template_slots:
        active_other_nums = {int(re.search(r"\d+", k).group()) for k in other_template_slots}
        for i in range(1, 11):
            if i not in active_other_nums:
                hidden.add(f"Other_Field_{i}")
    else:
        active_other = len(config.get("other", []))
        for i in range(active_other + 1, 11):
            hidden.add(f"Other_Field_{i}")
    return hidden


def apply_visibility(tmdl_text, hidden_columns):
    if not hidden_columns:
        return tmdl_text

    result = []
    in_hidden_col = False
    inserted = False

    for line in tmdl_text.splitlines(keepends=True):
        m = re.match(r"\tcolumn (\S+)", line)
        if m:
            in_hidden_col = m.group(1) in hidden_columns
            inserted = False

        result.append(line)

        if in_hidden_col and not inserted and re.match(r"\t\tlineageTag:", line):
            result.append("\t\tisHidden\n")
            result.append("\t\tisAvailableInMDX: false\n")
            inserted = True

    return "".join(result)


def run_visibility_pipeline(tmdl_path, config):
    path = Path(tmdl_path)
    text = path.read_text(encoding="utf-8")
    hidden = get_hidden_columns(config)
    modified = apply_visibility(text, hidden)
    path.write_text(modified, encoding="utf-8")


def _projection_column_property(proj: dict):
    field = proj.get("field", {})
    if "Column" in field:
        return field["Column"].get("Property")
    if "Aggregation" in field:
        return field["Aggregation"].get("Expression", {}).get("Column", {}).get("Property")
    return None


def remove_hidden_from_visuals(report_root, hidden_columns: set) -> list:
    root = Path(report_root)
    modified = []
    for path in root.rglob("visual.json"):
        text = path.read_text(encoding="utf-8")
        d = json.loads(text)
        qs = d.get("visual", {}).get("query", {}).get("queryState", {})
        changed = False
        for section_val in qs.values():
            projs = section_val.get("projections", [])
            new_projs = [p for p in projs if _projection_column_property(p) not in hidden_columns]
            if len(new_projs) != len(projs):
                section_val["projections"] = new_projs
                changed = True
        if changed:
            path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
            modified.append(str(path))
    return modified


def _filter_column_property(f: dict):
    return f.get("field", {}).get("Column", {}).get("Property")


def remove_hidden_from_drillthrough_pages(report_root, hidden_columns: set) -> list:
    root = Path(report_root)
    modified = []
    for path in root.rglob("page.json"):
        text = path.read_text(encoding="utf-8")
        d = json.loads(text)
        filters = d.get("filterConfig", {}).get("filters")
        if filters is None:
            continue
        removed_names = {
            f["name"] for f in filters
            if _filter_column_property(f) in hidden_columns
        }
        if not removed_names:
            continue
        d["filterConfig"]["filters"] = [
            f for f in filters if f["name"] not in removed_names
        ]
        params = d.get("pageBinding", {}).get("parameters")
        if params is not None:
            d["pageBinding"]["parameters"] = [
                p for p in params if p.get("boundFilter") not in removed_names
            ]
        path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        modified.append(str(path))
    return modified
