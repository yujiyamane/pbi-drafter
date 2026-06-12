import re
from pathlib import Path

FORMAT_MAP = {
    "$":    "$#,0",
    "#":    "#,0",
    "#.0":  "#,0.0",
    "#.00": "#,0.00",
    "%":    "0.00%",
}
DEFAULT_FORMAT = "#,0.00"


def _resolve_format(fmt):
    if fmt is None:
        return DEFAULT_FORMAT
    return FORMAT_MAP.get(fmt, fmt)


def get_format_updates(config):
    updates = {}
    for i, slot in enumerate(config.get("sum", []), start=1):
        if slot is not None:
            updates[f"SUM_Measure_{i}"] = _resolve_format(slot.get("format"))
    for i, slot in enumerate(config.get("avg", []), start=1):
        if slot is not None and slot.get("format"):
            updates[f"AVG_Measure_{i}"] = _resolve_format(slot["format"])
    return updates


def _col_has_format_string(tmdl_text, col_name):
    in_col = False
    for line in tmdl_text.splitlines():
        if re.match(rf"\tcolumn {re.escape(col_name)}$", line):
            in_col = True
        elif in_col and re.match(r"\tcolumn ", line):
            return False
        elif in_col and re.match(r"\t\tformatString:", line):
            return True
    return False


def apply_formats(tmdl_text, format_updates):
    if not format_updates:
        return tmdl_text

    has_fmt = {col: _col_has_format_string(tmdl_text, col) for col in format_updates}

    result = []
    current_col = None
    in_target = False
    done = False

    for line in tmdl_text.splitlines(keepends=True):
        m = re.match(r"\tcolumn (\S+)", line)
        if m:
            current_col = m.group(1)
            in_target = current_col in format_updates
            done = False

        if in_target and not done:
            fmt_str = format_updates[current_col]

            if has_fmt[current_col]:
                if re.match(r"\t\tformatString:", line):
                    result.append(f"\t\tformatString: {fmt_str}\n")
                    done = True
                    continue
            else:
                if re.match(r"\t\tdataType:", line):
                    result.append(line)
                    result.append(f"\t\tformatString: {fmt_str}\n")
                    done = True
                    continue

        result.append(line)

    return "".join(result)


def run_format_pipeline(tmdl_path, config):
    path = Path(tmdl_path)
    text = path.read_text(encoding="utf-8")
    updates = get_format_updates(config)
    modified = apply_formats(text, updates)
    path.write_text(modified, encoding="utf-8")
