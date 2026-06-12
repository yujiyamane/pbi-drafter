import json
import re
import pytest
from src.config_parser import parse_config
from src.visibility_pipeline import get_hidden_columns, apply_visibility, run_visibility_pipeline, remove_hidden_from_visuals, remove_hidden_from_drillthrough_pages

SQL_HR_CSV = r"""/*FACTORY
TITLE: HR Dashboard
THEME(1:nsw-blue 2:nsw-red 3:oracle): 1
DB(1:Oracle 2:PostgreSQL 3:Snowflake 4:CSV 5:Excel): 4
SOURCE: C:\data\hr_data.csv

1.CNT(max5): ①Employee_ID+Month_Name AS "Record ID" ②③④⑤
2.SUM(max10): ①Budget AS "Total Budget"($) ②Headcount(#) ③④⑤⑥⑦⑧⑨⑩
3.AVG(max5): ①Rating AS "Avg Rating"(#.0) ②③④⑤
4.DATE: Report_Date AS "Date Reported"
5.KEY(max10): ①Department ②Month_Name AS "Month Name" ③④⑤⑥⑦⑧⑨⑩
6.OTHER: Staff_Name AS "Staff Name", Notes
*/
"""

SAMPLE_FACT_TMDL = (
    "table Fact\n"
    "\tlineageTag: table-tag\n"
    "\n"
    "\tcolumn SUM_Measure_1\n"
    "\t\tdataType: int64\n"
    "\t\tformatString: 0\n"
    "\t\tlineageTag: tag-sum-1\n"
    "\t\tsummarizeBy: sum\n"
    "\t\tsourceColumn: SUM_Measure_1\n"
    "\n"
    "\t\tannotation SummarizationSetBy = Automatic\n"
    "\n"
    "\tcolumn SUM_Measure_2\n"
    "\t\tdataType: int64\n"
    "\t\tformatString: 0\n"
    "\t\tlineageTag: tag-sum-2\n"
    "\t\tsummarizeBy: sum\n"
    "\t\tsourceColumn: SUM_Measure_2\n"
    "\n"
    "\t\tannotation SummarizationSetBy = Automatic\n"
    "\n"
    "\tcolumn SUM_Measure_3\n"
    "\t\tdataType: int64\n"
    "\t\tformatString: 0\n"
    "\t\tlineageTag: tag-sum-3\n"
    "\t\tsummarizeBy: sum\n"
    "\t\tsourceColumn: SUM_Measure_3\n"
    "\n"
    "\t\tannotation SummarizationSetBy = Automatic\n"
    "\n"
)


@pytest.fixture
def cfg_csv():
    return parse_config(SQL_HR_CSV)


class TestGetHiddenColumns:
    def test_unused_sum_slots_hidden(self, cfg_csv):
        hidden = get_hidden_columns(cfg_csv)
        for i in range(3, 11):
            assert f"SUM_Measure_{i}" in hidden

    def test_active_sum_slots_visible(self, cfg_csv):
        hidden = get_hidden_columns(cfg_csv)
        assert "SUM_Measure_1" not in hidden
        assert "SUM_Measure_2" not in hidden

    def test_unused_cnt_slots_hidden(self, cfg_csv):
        hidden = get_hidden_columns(cfg_csv)
        for i in range(2, 6):
            assert f"CNT_Measure_{i}" in hidden

    def test_active_cnt_slot_visible(self, cfg_csv):
        hidden = get_hidden_columns(cfg_csv)
        assert "CNT_Measure_1" not in hidden

    def test_unused_avg_slots_hidden(self, cfg_csv):
        hidden = get_hidden_columns(cfg_csv)
        for i in range(2, 6):
            assert f"AVG_Measure_{i}" in hidden

    def test_active_avg_slot_visible(self, cfg_csv):
        hidden = get_hidden_columns(cfg_csv)
        assert "AVG_Measure_1" not in hidden

    def test_unused_key_slots_hidden(self, cfg_csv):
        hidden = get_hidden_columns(cfg_csv)
        for i in range(3, 11):
            assert f"Key_Dim_{i}" in hidden

    def test_active_key_slots_visible(self, cfg_csv):
        hidden = get_hidden_columns(cfg_csv)
        assert "Key_Dim_1" not in hidden
        assert "Key_Dim_2" not in hidden

    def test_unused_other_slots_hidden(self, cfg_csv):
        hidden = get_hidden_columns(cfg_csv)
        for i in range(3, 11):
            assert f"Other_Field_{i}" in hidden

    def test_active_other_slots_visible(self, cfg_csv):
        hidden = get_hidden_columns(cfg_csv)
        assert "Other_Field_1" not in hidden
        assert "Other_Field_2" not in hidden

    def test_date_key_never_hidden(self, cfg_csv):
        hidden = get_hidden_columns(cfg_csv)
        assert "DateKey" not in hidden


SQL_TEMPLATE_SLOT_OTHER = r"""/*FACTORY
TITLE: Slot Test
THEME(1:nsw-blue): 1
DB(1:Oracle 2:PostgreSQL 3:Snowflake 4:CSV 5:Excel): 4
SOURCE: C:\data\test.csv

1.CNT(max5): ①ID ②③④⑤
2.SUM(max10): ①Budget AS "Budget"($) ②③④⑤⑥⑦⑧⑨⑩
3.AVG(max5): ①②③④⑤
4.DATE: ReportDate
5.KEY(max10): ①Category ②③④⑤⑥⑦⑧⑨⑩
6.OTHER: Other_Field_1 AS "Full Name", Other_Field_3 AS "Notes"
*/SELECT ID, Budget, ReportDate, Category FROM T
"""


@pytest.fixture
def cfg_template_slot_other():
    return parse_config(SQL_TEMPLATE_SLOT_OTHER)


class TestGetHiddenColumnsTemplateSlotOther:
    def test_slot1_not_hidden(self, cfg_template_slot_other):
        hidden = get_hidden_columns(cfg_template_slot_other)
        assert "Other_Field_1" not in hidden

    def test_slot3_not_hidden(self, cfg_template_slot_other):
        hidden = get_hidden_columns(cfg_template_slot_other)
        assert "Other_Field_3" not in hidden

    def test_slot2_is_hidden(self, cfg_template_slot_other):
        hidden = get_hidden_columns(cfg_template_slot_other)
        assert "Other_Field_2" in hidden

    def test_slot4_through_10_are_hidden(self, cfg_template_slot_other):
        hidden = get_hidden_columns(cfg_template_slot_other)
        for i in range(4, 11):
            assert f"Other_Field_{i}" in hidden


class TestApplyVisibility:
    def test_adds_is_hidden_to_hidden_column(self):
        result = apply_visibility(SAMPLE_FACT_TMDL, {"SUM_Measure_3"})
        assert "\t\tisHidden\n" in result

    def test_adds_is_available_in_mdx_false(self):
        result = apply_visibility(SAMPLE_FACT_TMDL, {"SUM_Measure_3"})
        assert "\t\tisAvailableInMDX: false\n" in result

    def test_inserts_after_lineage_tag(self):
        result = apply_visibility(SAMPLE_FACT_TMDL, {"SUM_Measure_3"})
        lt_pos = result.find("tag-sum-3")
        hidden_pos = result.find("\t\tisHidden\n")
        assert 0 < lt_pos < hidden_pos

    def test_active_column_has_no_is_hidden(self):
        result = apply_visibility(SAMPLE_FACT_TMDL, {"SUM_Measure_3"})
        lines = result.split("\n")
        in_sum1 = False
        for line in lines:
            if re.match(r"\tcolumn SUM_Measure_1$", line):
                in_sum1 = True
            elif re.match(r"\tcolumn ", line):
                in_sum1 = False
            if in_sum1 and "isHidden" in line:
                pytest.fail("SUM_Measure_1 should not contain isHidden")

    def test_multiple_hidden_columns(self):
        result = apply_visibility(SAMPLE_FACT_TMDL, {"SUM_Measure_2", "SUM_Measure_3"})
        assert result.count("\t\tisHidden\n") == 2

    def test_empty_hidden_set_returns_unchanged(self):
        result = apply_visibility(SAMPLE_FACT_TMDL, set())
        assert result == SAMPLE_FACT_TMDL

    def test_column_not_in_tmdl_is_ignored(self):
        result = apply_visibility(SAMPLE_FACT_TMDL, {"SUM_Measure_99"})
        assert result == SAMPLE_FACT_TMDL


class TestRunVisibilityPipeline:
    def test_writes_hidden_flag_to_file(self, tmp_path, cfg_csv):
        tmdl_file = tmp_path / "Fact.tmdl"
        tmdl_file.write_text(SAMPLE_FACT_TMDL, encoding="utf-8")
        run_visibility_pipeline(tmdl_file, cfg_csv)
        result = tmdl_file.read_text(encoding="utf-8")
        assert "\t\tisHidden\n" in result

    def test_active_column_unchanged_in_file(self, tmp_path, cfg_csv):
        tmdl_file = tmp_path / "Fact.tmdl"
        tmdl_file.write_text(SAMPLE_FACT_TMDL, encoding="utf-8")
        run_visibility_pipeline(tmdl_file, cfg_csv)
        result = tmdl_file.read_text(encoding="utf-8")
        lines = result.split("\n")
        in_sum1 = False
        for line in lines:
            if re.match(r"\tcolumn SUM_Measure_1$", line):
                in_sum1 = True
            elif re.match(r"\tcolumn ", line):
                in_sum1 = False
            if in_sum1 and "isHidden" in line:
                pytest.fail("SUM_Measure_1 should not be hidden in file output")


def _make_visual_json(projections: list) -> dict:
    return {
        "$schema": "https://example.com/schema",
        "name": "test-visual",
        "position": {},
        "visual": {
            "visualType": "tableEx",
            "query": {
                "queryState": {
                    "Values": {"projections": projections}
                }
            },
        },
    }


def _col_proj(prop: str) -> dict:
    return {
        "field": {
            "Column": {
                "Expression": {"SourceRef": {"Entity": "Fact"}},
                "Property": prop,
            }
        },
        "queryRef": f"Fact.{prop}",
        "nativeQueryRef": prop,
    }


def _agg_proj(prop: str) -> dict:
    return {
        "field": {
            "Aggregation": {
                "Expression": {
                    "Column": {
                        "Expression": {"SourceRef": {"Entity": "Fact"}},
                        "Property": prop,
                    }
                },
                "Function": 0,
            }
        },
        "queryRef": f"Sum(Fact.{prop})",
        "nativeQueryRef": f"Sum of {prop}",
    }


def _measure_proj(prop: str) -> dict:
    return {
        "field": {
            "Measure": {
                "Expression": {"SourceRef": {"Entity": "Fact"}},
                "Property": prop,
            }
        },
        "queryRef": f"Fact.{prop}",
        "nativeQueryRef": prop,
    }


class TestRemoveHiddenFromVisuals:
    def _write_visual(self, tmp_path, projections, name="visual1"):
        vdir = tmp_path / name
        vdir.mkdir(parents=True, exist_ok=True)
        vpath = vdir / "visual.json"
        vpath.write_text(json.dumps(_make_visual_json(projections)), encoding="utf-8")
        return vpath

    def _read_props(self, vpath):
        d = json.loads(vpath.read_text(encoding="utf-8"))
        projs = d["visual"]["query"]["queryState"]["Values"]["projections"]
        col_props = [p["field"]["Column"]["Property"] for p in projs if "Column" in p["field"]]
        agg_props = [
            p["field"]["Aggregation"]["Expression"]["Column"]["Property"]
            for p in projs if "Aggregation" in p["field"]
        ]
        return col_props, agg_props

    def test_hidden_column_projection_removed(self, tmp_path):
        vpath = self._write_visual(tmp_path, [_col_proj("Business Unit"), _col_proj("Key_Dim_5")])
        remove_hidden_from_visuals(tmp_path, {"Key_Dim_5"})
        col_props, _ = self._read_props(vpath)
        assert "Key_Dim_5" not in col_props

    def test_active_column_projection_kept(self, tmp_path):
        vpath = self._write_visual(tmp_path, [_col_proj("Business Unit"), _col_proj("Key_Dim_5")])
        remove_hidden_from_visuals(tmp_path, {"Key_Dim_5"})
        col_props, _ = self._read_props(vpath)
        assert "Business Unit" in col_props

    def test_hidden_aggregation_projection_removed(self, tmp_path):
        vpath = self._write_visual(tmp_path, [_agg_proj("Invoice Count"), _agg_proj("CNT_Measure_3")])
        remove_hidden_from_visuals(tmp_path, {"CNT_Measure_3"})
        _, agg_props = self._read_props(vpath)
        assert "CNT_Measure_3" not in agg_props

    def test_active_aggregation_projection_kept(self, tmp_path):
        vpath = self._write_visual(tmp_path, [_agg_proj("Invoice Count"), _agg_proj("CNT_Measure_3")])
        remove_hidden_from_visuals(tmp_path, {"CNT_Measure_3"})
        _, agg_props = self._read_props(vpath)
        assert "Invoice Count" in agg_props

    def test_measure_projection_always_kept(self, tmp_path):
        vpath = self._write_visual(tmp_path, [_measure_proj("My Measure")])
        remove_hidden_from_visuals(tmp_path, {"My Measure"})
        d = json.loads(vpath.read_text(encoding="utf-8"))
        projs = d["visual"]["query"]["queryState"]["Values"]["projections"]
        assert len(projs) == 1

    def test_no_hidden_means_no_change(self, tmp_path):
        vpath = self._write_visual(tmp_path, [_col_proj("Business Unit")])
        original = vpath.read_text(encoding="utf-8")
        remove_hidden_from_visuals(tmp_path, {"Key_Dim_5"})
        assert vpath.read_text(encoding="utf-8") == original

    def test_returns_modified_paths(self, tmp_path):
        self._write_visual(tmp_path, [_col_proj("Business Unit"), _col_proj("Key_Dim_5")], "vis1")
        self._write_visual(tmp_path, [_col_proj("Quarter")], "vis2")
        result = remove_hidden_from_visuals(tmp_path, {"Key_Dim_5"})
        assert len(result) == 1
        assert result[0].endswith("visual.json")

    def test_visual_without_query_not_affected(self, tmp_path):
        vdir = tmp_path / "textbox"
        vdir.mkdir()
        vpath = vdir / "visual.json"
        vpath.write_text(json.dumps({"visual": {"visualType": "textbox"}}), encoding="utf-8")
        remove_hidden_from_visuals(tmp_path, {"Key_Dim_5"})

    def test_multiple_hidden_across_sections(self, tmp_path):
        visual = {
            "$schema": "", "name": "t", "position": {},
            "visual": {
                "visualType": "tableEx",
                "query": {
                    "queryState": {
                        "Values": {"projections": [_col_proj("Total Revenue"), _agg_proj("SUM_Measure_5")]},
                        "Rows": {"projections": [_col_proj("Business Unit"), _col_proj("Key_Dim_6")]},
                    }
                },
            },
        }
        vdir = tmp_path / "multi"
        vdir.mkdir()
        vpath = vdir / "visual.json"
        vpath.write_text(json.dumps(visual), encoding="utf-8")
        remove_hidden_from_visuals(tmp_path, {"SUM_Measure_5", "Key_Dim_6"})
        d = json.loads(vpath.read_text(encoding="utf-8"))
        qs = d["visual"]["query"]["queryState"]
        vals = [p["field"]["Aggregation"]["Expression"]["Column"]["Property"] for p in qs["Values"]["projections"] if "Aggregation" in p["field"]]
        rows = [p["field"]["Column"]["Property"] for p in qs["Rows"]["projections"] if "Column" in p["field"]]
        assert "SUM_Measure_5" not in vals
        assert "Key_Dim_6" not in rows
        assert "Business Unit" in rows


def _dt_filter(name: str, prop: str) -> dict:
    return {
        "name": name,
        "field": {"Column": {"Expression": {"SourceRef": {"Entity": "Fact"}}, "Property": prop}},
        "type": "Categorical",
        "howCreated": "Drillthrough",
    }


def _dt_param(name: str, bound_filter: str, prop: str) -> dict:
    return {
        "name": name,
        "boundFilter": bound_filter,
        "asAggregation": False,
        "fieldExpr": {"Column": {"Expression": {"SourceRef": {"Entity": "Fact"}}, "Property": prop}},
    }


def _make_drillthrough_page(filters: list, parameters: list) -> dict:
    return {
        "filterConfig": {"filters": filters},
        "pageBinding": {"type": "Drillthrough", "parameters": parameters},
    }


class TestRemoveHiddenFromDrillthroughPages:
    def _write_page(self, tmp_path, page_dict, page_dir="dt_page"):
        pdir = tmp_path / "definition" / "pages" / page_dir
        pdir.mkdir(parents=True, exist_ok=True)
        ppath = pdir / "page.json"
        ppath.write_text(json.dumps(page_dict, indent=2), encoding="utf-8")
        return ppath

    def _read_page(self, ppath):
        return json.loads(ppath.read_text(encoding="utf-8"))

    def test_hidden_filter_removed_from_filterconfig(self, tmp_path):
        page = _make_drillthrough_page(
            filters=[_dt_filter("f1", "Department"), _dt_filter("f2", "Other_Field_9")],
            parameters=[_dt_param("p1", "f1", "Department"), _dt_param("p2", "f2", "Other_Field_9")],
        )
        ppath = self._write_page(tmp_path, page)
        remove_hidden_from_drillthrough_pages(tmp_path, {"Other_Field_9"})
        d = self._read_page(ppath)
        props = [f["field"]["Column"]["Property"] for f in d["filterConfig"]["filters"]]
        assert "Other_Field_9" not in props

    def test_active_filter_kept_in_filterconfig(self, tmp_path):
        page = _make_drillthrough_page(
            filters=[_dt_filter("f1", "Department"), _dt_filter("f2", "Other_Field_9")],
            parameters=[_dt_param("p1", "f1", "Department"), _dt_param("p2", "f2", "Other_Field_9")],
        )
        ppath = self._write_page(tmp_path, page)
        remove_hidden_from_drillthrough_pages(tmp_path, {"Other_Field_9"})
        d = self._read_page(ppath)
        props = [f["field"]["Column"]["Property"] for f in d["filterConfig"]["filters"]]
        assert "Department" in props

    def test_orphaned_parameter_removed_from_pagebinding(self, tmp_path):
        page = _make_drillthrough_page(
            filters=[_dt_filter("f1", "Department"), _dt_filter("f2", "Other_Field_9")],
            parameters=[_dt_param("p1", "f1", "Department"), _dt_param("p2", "f2", "Other_Field_9")],
        )
        ppath = self._write_page(tmp_path, page)
        remove_hidden_from_drillthrough_pages(tmp_path, {"Other_Field_9"})
        d = self._read_page(ppath)
        bound = [p["boundFilter"] for p in d["pageBinding"]["parameters"]]
        assert "f2" not in bound

    def test_active_parameter_kept_in_pagebinding(self, tmp_path):
        page = _make_drillthrough_page(
            filters=[_dt_filter("f1", "Department"), _dt_filter("f2", "Other_Field_9")],
            parameters=[_dt_param("p1", "f1", "Department"), _dt_param("p2", "f2", "Other_Field_9")],
        )
        ppath = self._write_page(tmp_path, page)
        remove_hidden_from_drillthrough_pages(tmp_path, {"Other_Field_9"})
        d = self._read_page(ppath)
        bound = [p["boundFilter"] for p in d["pageBinding"]["parameters"]]
        assert "f1" in bound

    def test_no_hidden_columns_no_change(self, tmp_path):
        page = _make_drillthrough_page(
            filters=[_dt_filter("f1", "Department")],
            parameters=[_dt_param("p1", "f1", "Department")],
        )
        original = json.dumps(page, indent=2)
        ppath = self._write_page(tmp_path, page)
        remove_hidden_from_drillthrough_pages(tmp_path, set())
        assert ppath.read_text(encoding="utf-8") == original

    def test_returns_modified_paths(self, tmp_path):
        page = _make_drillthrough_page(
            filters=[_dt_filter("f1", "Department"), _dt_filter("f2", "Other_Field_9")],
            parameters=[_dt_param("p1", "f1", "Department"), _dt_param("p2", "f2", "Other_Field_9")],
        )
        self._write_page(tmp_path, page)
        result = remove_hidden_from_drillthrough_pages(tmp_path, {"Other_Field_9"})
        assert any("page.json" in p for p in result)

    def test_page_without_filterconfig_not_affected(self, tmp_path):
        page = {"name": "plain_page", "displayName": "Overview"}
        ppath = self._write_page(tmp_path, page, page_dir="plain")
        remove_hidden_from_drillthrough_pages(tmp_path, {"Other_Field_9"})
        d = self._read_page(ppath)
        assert d == page

    def test_multiple_hidden_filters_all_removed(self, tmp_path):
        page = _make_drillthrough_page(
            filters=[
                _dt_filter("f1", "Department"),
                _dt_filter("f2", "Other_Field_9"),
                _dt_filter("f3", "Key_Dim_5"),
            ],
            parameters=[
                _dt_param("p1", "f1", "Department"),
                _dt_param("p2", "f2", "Other_Field_9"),
                _dt_param("p3", "f3", "Key_Dim_5"),
            ],
        )
        ppath = self._write_page(tmp_path, page)
        remove_hidden_from_drillthrough_pages(tmp_path, {"Other_Field_9", "Key_Dim_5"})
        d = self._read_page(ppath)
        props = [f["field"]["Column"]["Property"] for f in d["filterConfig"]["filters"]]
        assert "Other_Field_9" not in props
        assert "Key_Dim_5" not in props
        assert "Department" in props
        assert len(d["pageBinding"]["parameters"]) == 1
