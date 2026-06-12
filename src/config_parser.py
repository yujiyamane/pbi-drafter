import re

_CIRCLE_NUMS = "①②③④⑤⑥⑦⑧⑨⑩"
_SLOT_RE = re.compile(f"[{_CIRCLE_NUMS}]")
_AS_RE = re.compile(r'^(\S+)\s+AS\s+"([^"]+)"\s*(?:\(([^)]+)\))?\s*$', re.IGNORECASE)
_AS_BARE_RE = re.compile(r'^(\S+)\s+AS\s+"([^"]+)"\s*$', re.IGNORECASE)


def extract_factory_block(sql_text):
    match = re.search(r"/\*FACTORY\s*(.*?)\*/", sql_text, re.DOTALL)
    if not match:
        raise ValueError("No FACTORY block found in SQL text")
    return match.group(1)


def _split_slots(slot_content, max_slots):
    parts = _SLOT_RE.split(slot_content)
    result = []
    for i in range(1, max_slots + 1):
        if i < len(parts):
            content = parts[i].strip()
            result.append(content if content else None)
        else:
            result.append(None)
    return result


def _parse_field_with_format(content):
    if not content:
        return None
    stripped = content.strip()
    m = _AS_RE.match(stripped)
    if m:
        result = {"field": m.group(2).strip(), "format": m.group(3)}
        result["source_column"] = m.group(1).strip()
        return result
    fmt_match = re.match(r"^(.*?)\(([^)]+)\)\s*$", stripped)
    if fmt_match:
        field_part = fmt_match.group(1).strip()
        fmt = fmt_match.group(2)
    else:
        field_part = stripped
        fmt = None
    return {"field": field_part.strip('"'), "format": fmt}


def _parse_cnt_slot(content):
    if not content:
        return None
    stripped = content.strip()
    m = _AS_BARE_RE.match(stripped)
    if m:
        sources_part = m.group(1).strip()
        display = m.group(2).strip()
        if "+" in sources_part:
            source_columns = [p.strip() for p in sources_part.split("+")]
            return {"fields": [display], "composite": True, "format": None, "source_columns": source_columns}
        return {"fields": [display], "composite": False, "format": None, "source_columns": [sources_part]}
    if "+" in stripped:
        fields = [p.strip().strip('"') for p in stripped.split("+")]
        return {"fields": fields, "composite": True, "format": None}
    return {"fields": [stripped.strip('"')], "composite": False, "format": None}


def _parse_other(content):
    parts = [p.strip() for p in content.strip().split(",")]
    display_list = []
    source_map = {}
    for p in parts:
        if not p:
            continue
        m = _AS_BARE_RE.match(p)
        if m:
            src, disp = m.group(1).strip(), m.group(2).strip()
            display_list.append(disp)
            source_map[src] = disp
        else:
            display_list.append(p.strip('"'))
    return display_list, source_map


def _parse_order_columns(sql_text):
    order_cols = {}
    for m in re.finditer(r'AS\s+"ORDER\s+([^"]+)"', sql_text):
        target = m.group(1).strip()
        order_cols[target] = f"ORDER {target}"
    return order_cols


def _slot_line(block, n):
    m = re.search(rf"^{n}\.\w+\([^)]+\):\s*(.+)$", block, re.MULTILINE)
    return m.group(1) if m else ""


def _parse_date(raw):
    if not raw:
        return None, None
    stripped = raw.strip()
    m = _AS_BARE_RE.match(stripped)
    if m:
        return m.group(2).strip(), m.group(1).strip()
    return stripped.strip('"'), None


def parse_config(sql_text):
    block = extract_factory_block(sql_text)

    title = re.search(r"^TITLE:\s*(.+)$", block, re.MULTILINE).group(1).strip()
    theme = int(re.search(r"^THEME\([^)]+\):\s*(\d+)", block, re.MULTILINE).group(1))
    db = int(re.search(r"^DB\([^)]+\):\s*(\d+)", block, re.MULTILINE).group(1))

    source_m = re.search(r"^SOURCE:\s*(.+)$", block, re.MULTILINE)
    source = source_m.group(1).strip() if source_m else None

    cnt = [_parse_cnt_slot(s) for s in _split_slots(_slot_line(block, 1), 5)]
    sum_ = [_parse_field_with_format(s) for s in _split_slots(_slot_line(block, 2), 10)]
    avg = [_parse_field_with_format(s) for s in _split_slots(_slot_line(block, 3), 5)]

    date_m = re.search(r"^4\.DATE:\s*(.+)$", block, re.MULTILINE)
    date, date_source_column = _parse_date(date_m.group(1) if date_m else None)

    key = [_parse_field_with_format(s) for s in _split_slots(_slot_line(block, 5), 10)]

    other_m = re.search(r"^6\.OTHER:\s*(.+)$", block, re.MULTILINE)
    if other_m:
        other, other_source_map = _parse_other(other_m.group(1))
    else:
        other, other_source_map = [], {}

    field_map = {}
    for slot in cnt:
        if slot and not slot.get("composite") and "source_columns" in slot:
            field_map[slot["source_columns"][0]] = slot["fields"][0]
    for section in (sum_, avg, key):
        for slot in section:
            if slot and "source_column" in slot:
                field_map[slot["source_column"]] = slot["field"]
    if date_source_column:
        field_map[date_source_column] = date
    field_map.update(other_source_map)

    result = {
        "title": title,
        "theme": theme,
        "db": db,
        "source": source,
        "cnt": cnt,
        "sum": sum_,
        "avg": avg,
        "date": date,
        "key": key,
        "other": other,
        "field_map": field_map,
        "order_columns": _parse_order_columns(sql_text),
    }
    if date_source_column:
        result["date_source_column"] = date_source_column
    return result
