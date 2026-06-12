import re
from pathlib import Path

_DATE_TABLE_PREFIXES = ("DateTableTemplate", "LocalDateTable")

_FIELD_PARAM_SOURCE_RE = re.compile(
    r"([ \t]+source =\n[ \t]+\{)(.*?)(\n[ \t]+\})",
    re.DOTALL,
)
_FIELD_PARAM_ROW_RE = re.compile(
    r"^([ \t]+)\(\"([^\"]+)\",\s*NAMEOF\('Fact'\[([^\]]+)\]\),\s*\d+\),?\s*$",
    re.MULTILINE,
)


def _tmdl_name(name: str) -> str:
    return f"'{name}'" if " " in name else name


def rename_tmdl(tmdl_text: str, rename_map: dict) -> str:
    for old, new in rename_map.items():
        new_q = _tmdl_name(new)
        tmdl_text = re.sub(rf"\bcolumn {re.escape(old)}\b", f"column {new_q}", tmdl_text)
        tmdl_text = re.sub(rf"\bmeasure {re.escape(old)}\b", f"measure {new_q}", tmdl_text)
        for rel_prop in ("fromColumn", "toColumn"):
            tmdl_text = re.sub(
                rf"({rel_prop}:\s+\w+\.){re.escape(old)}\b",
                lambda m, nq=new_q: m.group(1) + nq,
                tmdl_text,
            )
        tmdl_text = re.sub(
            rf"'Fact'\[{re.escape(old)}\]",
            f"'Fact'[{new}]",
            tmdl_text,
        )
    return tmdl_text


def rename_visual_json(json_text: str, rename_map: dict) -> str:
    for old, new in rename_map.items():
        json_text = (
            json_text
            .replace(f'"Property": "{old}"', f'"Property": "{new}"')
            .replace(f'"queryRef": "Fact.{old}"', f'"queryRef": "Fact.{new}"')
            .replace(f'"queryRef": "Sum(Fact.{old})"', f'"queryRef": "Sum(Fact.{new})"')
            .replace(f'"displayName": "{old}"', f'"displayName": "{new}"')
        )
        json_text = re.sub(
            rf'"nativeQueryRef": "([^"]*){re.escape(old)}"',
            rf'"nativeQueryRef": "\g<1>{new}"',
            json_text,
        )
    return json_text


def rename_field_parameters(tmdl_text: str, rename_map: dict) -> str:
    if "NAMEOF('Fact'[" not in tmdl_text:
        return tmdl_text

    def _process_block(m: re.Match) -> str:
        open_part = m.group(1)
        body = m.group(2)
        close_part = m.group(3)

        rows = _FIELD_PARAM_ROW_RE.findall(body)
        if not rows:
            return m.group(0)

        indent = rows[0][0]
        kept: list[tuple[str, str]] = []
        for _, label, nameof_ref in rows:
            if label not in rename_map:
                continue
            new_label = rename_map[label]
            new_ref = rename_map.get(nameof_ref, nameof_ref)
            kept.append((new_label, new_ref))

        if not kept:
            return m.group(0)

        lines = []
        for i, (lbl, ref) in enumerate(kept):
            comma = "," if i < len(kept) - 1 else ""
            lines.append(f'{indent}("{lbl}", NAMEOF(\'Fact\'[{ref}]), {i}){comma}')

        new_body = "\n" + "\n".join(lines)
        return f"{open_part}{new_body}{close_part}"

    return _FIELD_PARAM_SOURCE_RE.sub(_process_block, tmdl_text)


def rename_pipeline(pbip_root: str, rename_map: dict) -> dict:
    root = Path(pbip_root)
    modified: dict = {"tmdl": [], "visual": [], "page": []}

    semantic_root = next(root.glob("*.SemanticModel"), None) or root
    report_root = next(root.glob("*.Report"), None) or root

    for path in semantic_root.rglob("*.tmdl"):
        if any(path.name.startswith(p) for p in _DATE_TABLE_PREFIXES):
            continue
        text = path.read_text(encoding="utf-8")
        updated = rename_tmdl(text, rename_map)
        updated = rename_field_parameters(updated, rename_map)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            modified["tmdl"].append(str(path))

    for path in report_root.rglob("visual.json"):
        text = path.read_text(encoding="utf-8")
        updated = rename_visual_json(text, rename_map)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            modified["visual"].append(str(path))

    for path in report_root.rglob("page.json"):
        text = path.read_text(encoding="utf-8")
        updated = rename_visual_json(text, rename_map)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            modified["page"].append(str(path))

    return modified
