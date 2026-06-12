import re
import shutil
from pathlib import Path

from .config_parser import parse_config
from .mquery_generator import generate_mquery, _ALL_SLOTS
from .visibility_pipeline import get_hidden_columns, apply_visibility, remove_hidden_from_visuals, remove_hidden_from_drillthrough_pages
from .format_pipeline import get_format_updates, apply_formats
from .rename_pipeline import rename_pipeline
from .sort_pipeline import run_sort_pipeline


def _sanitize_name(title: str) -> str:
    return re.sub(r"\s+", "_", title)


def _dax_name(business_name: str) -> str:
    return "DAX_" + business_name.replace(" ", "_")


def _build_rename_map(config: dict) -> dict:
    rename_map = {}

    for i, slot in enumerate(config.get("sum", []), start=1):
        if slot is not None:
            rename_map[f"SUM_Measure_{i}"] = slot["field"]
            rename_map[f"DAX_SUM_Measure_{i}"] = _dax_name(slot["field"])

    for i, slot in enumerate(config.get("cnt", []), start=1):
        if slot is not None:
            rename_map[f"CNT_Measure_{i}"] = slot["fields"][0]
            rename_map[f"DAX_CNT_Measure_{i}"] = _dax_name(slot["fields"][0])

    for i, slot in enumerate(config.get("avg", []), start=1):
        if slot is not None:
            rename_map[f"AVG_Measure_{i}"] = slot["field"]

    active_keys = [k for k in config.get("key", []) if k is not None]
    for i, slot in enumerate(active_keys, start=1):
        rename_map[f"Key_Dim_{i}"] = slot["field"]

    next_key_slot = len(active_keys) + 1
    for order_col_display in config.get("order_columns", {}).values():
        rename_map[f"Key_Dim_{next_key_slot}"] = order_col_display
        next_key_slot += 1

    if config.get("date"):
        rename_map["DateKey"] = config["date"]

    other_template_slots = {
        k: v for k, v in config.get("field_map", {}).items()
        if re.match(r"Other_Field_\d+$", k)
    }
    if other_template_slots:
        rename_map.update(other_template_slots)
    else:
        other_field_idx = 1
        for field in config.get("other", []):
            if next_key_slot <= 10:
                rename_map[f"Key_Dim_{next_key_slot}"] = field
                next_key_slot += 1
            else:
                rename_map[f"Other_Field_{other_field_idx}"] = field
                other_field_idx += 1

    return rename_map


def _update_source_columns(tmdl_text: str, rename_map: dict) -> str:
    for old, new in rename_map.items():
        tmdl_text = re.sub(
            rf"\bsourceColumn:\s+{re.escape(old)}\b",
            f"sourceColumn: {new}",
            tmdl_text,
        )
    return tmdl_text


def _embed_mquery(mquery: str) -> str:
    return "\n".join("\t\t\t\t" + line for line in mquery.splitlines())


def _write_partition_source(tmdl_text: str, mquery: str) -> str:
    embedded = _embed_mquery(mquery)
    return re.sub(
        r"(\t\tsource =\n).*?(\n\n\tannotation)",
        lambda m: m.group(1) + embedded + m.group(2),
        tmdl_text,
        flags=re.DOTALL,
    )


def _get_order_col_slots(config: dict) -> set:
    active_key_count = sum(1 for k in config.get("key", []) if k is not None)
    return {
        f"Key_Dim_{active_key_count + i + 1}"
        for i in range(len(config.get("order_columns", {})))
    }


def run_factory(template_dir, output_dir, config: dict) -> Path:
    name = _sanitize_name(config["title"])
    template = Path(template_dir)
    out_root = Path(output_dir) / name

    if out_root.exists():
        shutil.rmtree(out_root)
    shutil.copytree(template, out_root)

    for item in list(out_root.iterdir()):
        if item.name == "Template.Report":
            item.rename(out_root / f"{name}.Report")
        elif item.name == "Template.SemanticModel":
            item.rename(out_root / f"{name}.SemanticModel")
        elif item.name == "Template.pbip":
            new_pbip = out_root / f"{name}.pbip"
            item.rename(new_pbip)
            content = new_pbip.read_text(encoding="utf-8")
            content = re.sub(
                r'"path":\s*"template\.Report"',
                f'"path": "{name}.Report"',
                content,
            )
            new_pbip.write_text(content, encoding="utf-8")

    report_dir = out_root / f"{name}.Report"
    semantic_dir_name = f"{name}.SemanticModel"

    # definition.pbir: update SemanticModel path reference
    pbir = report_dir / "definition.pbir"
    content = pbir.read_text(encoding="utf-8")
    content = re.sub(r'"\.\.\/template\.SemanticModel"', f'"../{semantic_dir_name}"', content)
    pbir.write_text(content, encoding="utf-8")

    # .platform files: update displayName
    for platform_file in [report_dir / ".platform", out_root / semantic_dir_name / ".platform"]:
        content = platform_file.read_text(encoding="utf-8")
        content = content.replace('"displayName": "template"', f'"displayName": "{name}"')
        platform_file.write_text(content, encoding="utf-8")

    semantic_dir = out_root / f"{name}.SemanticModel"
    fact_tmdl = semantic_dir / "definition" / "tables" / "Fact.tmdl"

    rename_map = _build_rename_map(config)
    if config.get("db", 0) in (4, 5):
        mquery = generate_mquery(config)
    else:
        unused_slots = [s for s in _ALL_SLOTS if s not in rename_map]
        mquery_field_map = {k: v for k, v in rename_map.items() if not k.startswith("DAX_")}
        mquery = generate_mquery({**config, "field_map": mquery_field_map, "unused_slots": unused_slots})
    text = fact_tmdl.read_text(encoding="utf-8")
    text = _write_partition_source(text, mquery)
    text = _update_source_columns(text, rename_map)
    fact_tmdl.write_text(text, encoding="utf-8")

    text = fact_tmdl.read_text(encoding="utf-8")
    hidden = get_hidden_columns(config) - _get_order_col_slots(config)

    field_map = config.get("field_map", {})
    has_other_template_slots = any(re.match(r"Other_Field_\d+$", k) for k in field_map)
    if not has_other_template_slots:
        active_key_count = sum(1 for k in config.get("key", []) if k is not None)
        order_col_count = len(config.get("order_columns", {}))
        next_slot = active_key_count + order_col_count + 1
        for i, _field in enumerate(config.get("other", []), start=1):
            if next_slot <= 10:
                hidden.discard(f"Key_Dim_{next_slot}")
                hidden.add(f"Other_Field_{i}")
                next_slot += 1
            else:
                break

    text = apply_visibility(text, hidden)
    fact_tmdl.write_text(text, encoding="utf-8")

    text = fact_tmdl.read_text(encoding="utf-8")
    text = apply_formats(text, get_format_updates(config))
    fact_tmdl.write_text(text, encoding="utf-8")

    rename_pipeline(str(out_root), rename_map)
    remove_hidden_from_visuals(report_dir, hidden)
    remove_hidden_from_drillthrough_pages(report_dir, hidden)

    order_columns = config.get("order_columns", {})
    if order_columns:
        run_sort_pipeline(fact_tmdl, {"order_columns": order_columns})

    cache_abf = semantic_dir / ".pbi" / "cache.abf"
    if cache_abf.exists():
        cache_abf.unlink()

    return out_root
