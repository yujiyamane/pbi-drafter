import re
from pathlib import Path


def _tmdl_name(name):
    return f"'{name}'" if " " in name else name


def apply_sort(tmdl_text, order_columns):
    if not order_columns:
        return tmdl_text

    sort_targets = {_tmdl_name(t): _tmdl_name(s) for t, s in order_columns.items()}
    order_col_names = {_tmdl_name(s) for s in order_columns.values()}

    result = []
    current_col = None
    in_sort_target = False
    in_order_col = False
    inserted = False

    for line in tmdl_text.splitlines(keepends=True):
        m = re.match(r"\tcolumn (.+)$", line.rstrip("\n"))
        if m:
            current_col = m.group(1).strip()
            in_sort_target = current_col in sort_targets
            in_order_col = current_col in order_col_names
            inserted = False

        result.append(line)

        if (in_sort_target or in_order_col) and not inserted:
            if re.match(r"\t\tlineageTag:", line):
                if in_sort_target:
                    result.append(f"\t\tsortByColumn: {sort_targets[current_col]}\n")
                if in_order_col:
                    result.append("\t\tisHidden\n")
                    result.append("\t\tisAvailableInMDX: false\n")
                inserted = True

    return "".join(result)


def run_sort_pipeline(tmdl_path, config):
    path = Path(tmdl_path)
    text = path.read_text(encoding="utf-8")
    modified = apply_sort(text, config.get("order_columns", {}))
    path.write_text(modified, encoding="utf-8")
