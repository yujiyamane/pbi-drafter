_ALL_SLOTS = (
    [f"SUM_Measure_{i}" for i in range(1, 11)] +
    [f"CNT_Measure_{i}" for i in range(1, 6)] +
    [f"AVG_Measure_{i}" for i in range(1, 6)] +
    [f"Key_Dim_{i}" for i in range(1, 11)] +
    [f"Other_Field_{i}" for i in range(1, 11)] +
    ["DateKey"]
)


def generate_mquery(config):
    db = config["db"]
    if db == 4:
        return _csv_mquery(config)
    if db == 5:
        return _excel_mquery(config)
    raise NotImplementedError(f"M Query generation not yet supported for DB type {db}")


def _build_csv_type_map(config):
    """Build {business_name: M_Query_type_string} from config structure."""
    type_map = {}
    for slot in config.get("sum", []):
        if slot:
            type_map[slot["field"]] = "Int64.Type"
    for slot in config.get("cnt", []):
        if slot:
            type_map[slot["fields"][0]] = "type text"
    for slot in config.get("avg", []):
        if slot:
            type_map[slot["field"]] = "type number"
    date = config.get("date")
    if date:
        type_map[date] = "type date"
    for slot in config.get("key", []):
        if slot:
            type_map[slot["field"]] = "type text"
    for field in config.get("other", []):
        type_map[field] = "type text"
    return type_map


def _active_type_step(prev_step, type_map):
    if not type_map:
        return prev_step, None
    pairs = ", ".join(f'{{"{col}", {typ}}}' for col, typ in type_map.items())
    step = (
        f'    #"Changed Type" = Table.TransformColumnTypes({prev_step}, '
        f'{{{pairs}}})'
    )
    return '#"Changed Type"', step


def _remove_step(prev_step, unused_slots):
    if not unused_slots:
        return prev_step, None
    cols = ", ".join(f'"{s}"' for s in unused_slots)
    step = (
        f'    #"Removed Columns" = Table.RemoveColumns({prev_step}, {{{cols}}})'
    )
    return '#"Removed Columns"', step


def _rename_step(prev_step, field_map):
    if not field_map:
        return prev_step, None
    pairs = ",\n        ".join(
        f'{{"{src}", "{disp}"}}'
        for src, disp in field_map.items()
    )
    step = (
        f'    #"Renamed Columns" = Table.RenameColumns({prev_step}, {{\n'
        f'        {pairs}\n'
        f'    }})'
    )
    return '#"Renamed Columns"', step


def _csv_mquery(config):
    path = config["source"]
    field_map = config.get("field_map", {})

    source_expr = (
        f'    Source = Csv.Document(File.Contents("{path}"), '
        f'[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None])'
    )
    promote_expr = (
        '    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true])'
    )
    rename_final, rename_expr = _rename_step('#"Promoted Headers"', field_map)
    type_map = _build_csv_type_map(config)
    final_step, type_expr = _active_type_step(rename_final, type_map)

    steps = [source_expr, promote_expr]
    if rename_expr:
        steps.append(rename_expr)
    if type_expr:
        steps.append(type_expr)

    return "let\n" + ",\n".join(steps) + "\nin\n    " + final_step


def _excel_mquery(config):
    path = config["source"]
    field_map = config.get("field_map", {})

    source_expr = (
        f'    Source = Excel.Workbook(File.Contents("{path}"), null, true)'
    )
    sheet_expr = '    FirstSheet = Source{0}[Data]'
    promote_expr = (
        '    #"Promoted Headers" = Table.PromoteHeaders(FirstSheet, [PromoteAllScalars=true])'
    )
    rename_final, rename_expr = _rename_step('#"Promoted Headers"', field_map)
    type_map = _build_csv_type_map(config)
    final_step, type_expr = _active_type_step(rename_final, type_map)

    steps = [source_expr, sheet_expr, promote_expr]
    if rename_expr:
        steps.append(rename_expr)
    if type_expr:
        steps.append(type_expr)

    return "let\n" + ",\n".join(steps) + "\nin\n    " + final_step
