import json
import re
from pathlib import Path

import pytest

from src.config_parser import parse_config
from src.factory import _sanitize_name, _build_rename_map, _write_partition_source, _update_source_columns, run_factory

TEMPLATE_DIR = Path(__file__).parent.parent / "template"

# CSV config with 2 active keys + 1 ORDER column
SQL_FACTORY_CSV = r"""/*FACTORY
TITLE: HR Dashboard
THEME(1:nsw-blue): 1
DB(1:Oracle 2:PostgreSQL 3:Snowflake 4:CSV 5:Excel): 4
SOURCE: C:\data\hr_data.csv

1.CNT(max5): ①Employee_ID AS "Record Count" ②③④⑤
2.SUM(max10): ①Budget AS "Total Budget"($) ②③④⑤⑥⑦⑧⑨⑩
3.AVG(max5): ①Rating AS "Avg Rating"(#.0) ②③④⑤
4.DATE: Report_Date AS "Date Reported"
5.KEY(max10): ①Department ②Month_Name AS "Month Name" ③④⑤⑥⑦⑧⑨⑩
6.OTHER: Staff_Name AS "Staff Name", Notes
*/
SELECT Employee_ID, Budget, Rating, Report_Date, Department, Month_Name AS "Month Name",
       Month_Order AS "ORDER Month Name", Staff_Name, Notes FROM T
"""

# Minimal TMDL with partition source block for unit tests
MINI_TMDL_WITH_SOURCE = (
    "table Fact\n"
    "\tlineageTag: abc-123\n"
    "\n"
    "\tcolumn SUM_Measure_1\n"
    "\t\tdataType: int64\n"
    "\t\tlineageTag: col-tag\n"
    "\n"
    "\tpartition Fact = m\n"
    "\t\tmode: import\n"
    "\t\tsource =\n"
    "\t\t\t\tlet\n"
    "\t\t\t\t    Source = OldSource\n"
    "\t\t\t\tin\n"
    "\t\t\t\t    Source\n"
    "\n"
    "\tannotation PBI_ResultType = Table\n"
)


@pytest.fixture
def cfg():
    return parse_config(SQL_FACTORY_CSV)


class TestSanitizeName:
    def test_spaces_become_underscores(self):
        assert _sanitize_name("HR Dashboard") == "HR_Dashboard"

    def test_no_spaces_unchanged(self):
        assert _sanitize_name("MyReport") == "MyReport"

    def test_multiple_spaces(self):
        assert _sanitize_name("My Big Report") == "My_Big_Report"


class TestBuildRenameMap:
    def test_active_sum_slot_renamed(self, cfg):
        rm = _build_rename_map(cfg)
        assert rm["SUM_Measure_1"] == "Total Budget"

    def test_inactive_sum_slot_absent(self, cfg):
        rm = _build_rename_map(cfg)
        for i in range(2, 11):
            assert f"SUM_Measure_{i}" not in rm

    def test_active_cnt_slot_renamed(self, cfg):
        rm = _build_rename_map(cfg)
        assert rm["CNT_Measure_1"] == "Record Count"

    def test_active_avg_slot_renamed(self, cfg):
        rm = _build_rename_map(cfg)
        assert rm["AVG_Measure_1"] == "Avg Rating"

    def test_active_key_slots_renamed(self, cfg):
        rm = _build_rename_map(cfg)
        assert rm["Key_Dim_1"] == "Department"
        assert rm["Key_Dim_2"] == "Month Name"

    def test_order_col_assigned_to_overflow_key_dim(self, cfg):
        rm = _build_rename_map(cfg)
        assert rm["Key_Dim_3"] == "ORDER Month Name"

    def test_date_key_renamed(self, cfg):
        rm = _build_rename_map(cfg)
        assert rm["DateKey"] == "Date Reported"

    def test_other_fields_promoted_to_key_dim(self, cfg):
        # 2 active keys + 1 ORDER col → Other promoted to Key_Dim_4, Key_Dim_5
        rm = _build_rename_map(cfg)
        assert rm["Key_Dim_4"] == "Staff Name"
        assert rm["Key_Dim_5"] == "Notes"

    def test_other_field_slots_absent_when_promoted(self, cfg):
        rm = _build_rename_map(cfg)
        assert "Other_Field_1" not in rm
        assert "Other_Field_2" not in rm

    def test_no_order_cols_other_promoted_to_key_dim3(self):
        # No ORDER col → Other fields promoted starting at Key_Dim_3
        cfg_no_order = parse_config(SQL_FACTORY_CSV.replace(
            'Month_Order AS "ORDER Month Name", ', ""
        ))
        rm = _build_rename_map(cfg_no_order)
        assert rm["Key_Dim_3"] == "Staff Name"


SQL_OTHER_PROMOTION_NO_ORDER = r"""/*FACTORY
TITLE: Promo Test
THEME(1:nsw-blue): 1
DB(1:Oracle 2:PostgreSQL 3:Snowflake 4:CSV 5:Excel): 4
SOURCE: C:\data\test.csv

1.CNT(max5): ①ID ②③④⑤
2.SUM(max10): ①Amount($) ②③④⑤⑥⑦⑧⑨⑩
3.AVG(max5): ①②③④⑤
4.DATE: Report_Date
5.KEY(max10): ①Department ②Region ③④⑤⑥⑦⑧⑨⑩
6.OTHER: "Client Name", "Invoice Ref", Notes
*/
"""

SQL_KEY_DIM_FULL_OTHER = r"""/*FACTORY
TITLE: Full Keys Test
THEME(1:nsw-blue): 1
DB(1:Oracle 2:PostgreSQL 3:Snowflake 4:CSV 5:Excel): 4
SOURCE: C:\data\test.csv

1.CNT(max5): ①ID ②③④⑤
2.SUM(max10): ①Amount($) ②③④⑤⑥⑦⑧⑨⑩
3.AVG(max5): ①②③④⑤
4.DATE: Report_Date
5.KEY(max10): ①F1 ②F2 ③F3 ④F4 ⑤F5 ⑥F6 ⑦F7 ⑧F8 ⑨F9 ⑩F10
6.OTHER: Extra
*/
"""

SQL_FINANCE = r"""/*FACTORY
TITLE: Finance Dashboard
THEME(1:nsw-blue): 1
DB(1:Oracle 2:PostgreSQL 3:Snowflake 4:CSV 5:Excel): 4
SOURCE: C:\data\finance_dummy_data.csv

1.CNT(max5): ①invoice_id AS "Invoice Count" ②client_id AS "Client Count" ③④⑤
2.SUM(max10): ①revenue AS "Total Revenue"($) ②cost AS "Total Cost"($) ③profit AS "Total Profit"($) ④tax AS "Total Tax"($) ⑤⑥⑦⑧⑨⑩
3.AVG(max5): ①margin AS "Avg Margin"(%) ②days_to_pay AS "Avg Days to Pay"(#.0) ③④⑤
4.DATE: invoice_date AS "Date Invoiced"
5.KEY(max10): ①business_unit AS "Business Unit" ②region AS "Region" ③account_type AS "Account Type" ④payment_method AS "Payment Method" ⑤⑥⑦⑧⑨⑩
6.OTHER: client_name AS "Client Name", invoice_ref AS "Invoice Ref", notes AS "Notes"
*/
"""


@pytest.fixture
def cfg_promo_no_order():
    return parse_config(SQL_OTHER_PROMOTION_NO_ORDER)


@pytest.fixture
def cfg_key_dim_full():
    return parse_config(SQL_KEY_DIM_FULL_OTHER)


@pytest.fixture
def cfg_finance():
    return parse_config(SQL_FINANCE)


class TestBuildRenameMapOtherPromotion:
    def test_first_other_promoted_to_key_dim3(self, cfg_promo_no_order):
        rm = _build_rename_map(cfg_promo_no_order)
        assert rm["Key_Dim_3"] == "Client Name"

    def test_second_other_promoted_to_key_dim4(self, cfg_promo_no_order):
        rm = _build_rename_map(cfg_promo_no_order)
        assert rm["Key_Dim_4"] == "Invoice Ref"

    def test_third_other_promoted_to_key_dim5(self, cfg_promo_no_order):
        rm = _build_rename_map(cfg_promo_no_order)
        assert rm["Key_Dim_5"] == "Notes"

    def test_other_field_slots_absent_when_fully_promoted(self, cfg_promo_no_order):
        rm = _build_rename_map(cfg_promo_no_order)
        assert "Other_Field_1" not in rm
        assert "Other_Field_2" not in rm
        assert "Other_Field_3" not in rm

    def test_key_dim_full_other_stays_in_other_field_1(self, cfg_key_dim_full):
        rm = _build_rename_map(cfg_key_dim_full)
        assert rm["Other_Field_1"] == "Extra"

    def test_key_dim_full_no_overflow_beyond_slot_10(self, cfg_key_dim_full):
        rm = _build_rename_map(cfg_key_dim_full)
        assert "Key_Dim_11" not in rm


class TestFinanceDashboardPromotion:
    def test_client_name_promoted_to_key_dim5(self, cfg_finance):
        rm = _build_rename_map(cfg_finance)
        assert rm["Key_Dim_5"] == "Client Name"

    def test_invoice_ref_promoted_to_key_dim6(self, cfg_finance):
        rm = _build_rename_map(cfg_finance)
        assert rm["Key_Dim_6"] == "Invoice Ref"

    def test_notes_promoted_to_key_dim7(self, cfg_finance):
        rm = _build_rename_map(cfg_finance)
        assert rm["Key_Dim_7"] == "Notes"

    def test_other_field_slots_absent(self, cfg_finance):
        rm = _build_rename_map(cfg_finance)
        assert "Other_Field_1" not in rm
        assert "Other_Field_2" not in rm
        assert "Other_Field_3" not in rm

    def test_key_dim8_thru_10_not_in_rename_map(self, cfg_finance):
        rm = _build_rename_map(cfg_finance)
        assert "Key_Dim_8" not in rm
        assert "Key_Dim_9" not in rm
        assert "Key_Dim_10" not in rm


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
def cfg_template_slots():
    return parse_config(SQL_TEMPLATE_SLOT_OTHER)


class TestBuildRenameMapTemplateSlotOther:
    def test_slot1_renamed(self, cfg_template_slots):
        rm = _build_rename_map(cfg_template_slots)
        assert rm["Other_Field_1"] == "Full Name"

    def test_slot3_renamed(self, cfg_template_slots):
        rm = _build_rename_map(cfg_template_slots)
        assert rm["Other_Field_3"] == "Notes"

    def test_slot2_absent_from_rename_map(self, cfg_template_slots):
        rm = _build_rename_map(cfg_template_slots)
        assert "Other_Field_2" not in rm


class TestBuildRenameMapDaxMeasures:
    def test_active_sum_slot_has_dax_entry(self, cfg):
        rm = _build_rename_map(cfg)
        assert rm["DAX_SUM_Measure_1"] == "DAX_Total_Budget"

    def test_inactive_sum_slot_no_dax_entry(self, cfg):
        rm = _build_rename_map(cfg)
        assert "DAX_SUM_Measure_2" not in rm

    def test_active_cnt_slot_has_dax_entry(self, cfg):
        rm = _build_rename_map(cfg)
        assert rm["DAX_CNT_Measure_1"] == "DAX_Record_Count"

    def test_inactive_cnt_slot_no_dax_entry(self, cfg):
        rm = _build_rename_map(cfg)
        assert "DAX_CNT_Measure_2" not in rm

    def test_dax_name_singleword(self):
        cfg_single = parse_config("""/*FACTORY
TITLE: T
THEME(1:nsw-blue): 1
DB(1:Oracle 2:PostgreSQL 3:Snowflake 4:CSV 5:Excel): 4
SOURCE: C:\\data\\t.csv
1.CNT(max5): ①ID ②③④⑤
2.SUM(max10): ①Budget($) ②③④⑤⑥⑦⑧⑨⑩
3.AVG(max5): ①②③④⑤
4.DATE: D
5.KEY(max10): ①K ②③④⑤⑥⑦⑧⑨⑩
6.OTHER:
*/""")
        rm = _build_rename_map(cfg_single)
        assert rm["DAX_SUM_Measure_1"] == "DAX_Budget"

    def test_dax_name_multiword_spaces_become_underscores(self):
        cfg_mw = parse_config("""/*FACTORY
TITLE: T
THEME(1:nsw-blue): 1
DB(1:Oracle 2:PostgreSQL 3:Snowflake 4:CSV 5:Excel): 4
SOURCE: C:\\data\\t.csv
1.CNT(max5): ①ID AS "Record ID" ②③④⑤
2.SUM(max10): ①Budget AS "Total Budget"($) ②③④⑤⑥⑦⑧⑨⑩
3.AVG(max5): ①②③④⑤
4.DATE: D
5.KEY(max10): ①K ②③④⑤⑥⑦⑧⑨⑩
6.OTHER:
*/""")
        rm = _build_rename_map(cfg_mw)
        assert rm["DAX_SUM_Measure_1"] == "DAX_Total_Budget"
        assert rm["DAX_CNT_Measure_1"] == "DAX_Record_ID"

    def test_finance_two_cnt_slots(self, cfg_finance):
        rm = _build_rename_map(cfg_finance)
        assert rm["DAX_CNT_Measure_1"] == "DAX_Invoice_Count"
        assert rm["DAX_CNT_Measure_2"] == "DAX_Client_Count"

    def test_finance_all_active_sum_slots_have_dax_entries(self, cfg_finance):
        rm = _build_rename_map(cfg_finance)
        assert rm["DAX_SUM_Measure_1"] == "DAX_Total_Revenue"
        assert rm["DAX_SUM_Measure_2"] == "DAX_Total_Cost"
        assert rm["DAX_SUM_Measure_3"] == "DAX_Total_Profit"
        assert rm["DAX_SUM_Measure_4"] == "DAX_Total_Tax"

    def test_finance_inactive_sum_slots_no_dax_entries(self, cfg_finance):
        rm = _build_rename_map(cfg_finance)
        assert "DAX_SUM_Measure_5" not in rm


class TestUpdateSourceColumns:
    def test_single_slot_updated(self):
        tmdl = "\t\tsourceColumn: SUM_Measure_1\n"
        result = _update_source_columns(tmdl, {"SUM_Measure_1": "Total Budget"})
        assert "sourceColumn: Total Budget\n" in result
        assert "sourceColumn: SUM_Measure_1" not in result

    def test_multiple_slots_updated(self):
        tmdl = "\t\tsourceColumn: SUM_Measure_1\n\t\tsourceColumn: Key_Dim_1\n"
        result = _update_source_columns(tmdl, {"SUM_Measure_1": "Revenue", "Key_Dim_1": "Department"})
        assert "sourceColumn: Revenue\n" in result
        assert "sourceColumn: Department\n" in result

    def test_empty_map_unchanged(self):
        tmdl = "\t\tsourceColumn: SUM_Measure_1\n"
        result = _update_source_columns(tmdl, {})
        assert result == tmdl

    def test_non_matching_slot_unchanged(self):
        tmdl = "\t\tsourceColumn: SUM_Measure_2\n"
        result = _update_source_columns(tmdl, {"SUM_Measure_1": "Total Budget"})
        assert "sourceColumn: SUM_Measure_2\n" in result


class TestWritePartitionSource:
    def test_new_mquery_embedded(self):
        new_mq = "let\n    Source = NewSource\nin\n    Source"
        result = _write_partition_source(MINI_TMDL_WITH_SOURCE, new_mq)
        assert "\t\t\t\tlet\n" in result
        assert "\t\t\t\t    Source = NewSource\n" in result

    def test_old_mquery_removed(self):
        new_mq = "let\n    Source = NewSource\nin\n    Source"
        result = _write_partition_source(MINI_TMDL_WITH_SOURCE, new_mq)
        assert "OldSource" not in result

    def test_annotation_preserved(self):
        new_mq = "let\n    Source = NewSource\nin\n    Source"
        result = _write_partition_source(MINI_TMDL_WITH_SOURCE, new_mq)
        assert "\tannotation PBI_ResultType = Table\n" in result

    def test_column_block_outside_partition_preserved(self):
        new_mq = "let\n    Source = NewSource\nin\n    Source"
        result = _write_partition_source(MINI_TMDL_WITH_SOURCE, new_mq)
        assert "\tcolumn SUM_Measure_1\n" in result


class TestRunFactory:
    def test_output_directory_created(self, tmp_path, cfg):
        run_factory(TEMPLATE_DIR, tmp_path, cfg)
        assert (tmp_path / "HR_Dashboard").is_dir()

    def test_semantic_model_dir_renamed(self, tmp_path, cfg):
        run_factory(TEMPLATE_DIR, tmp_path, cfg)
        out = tmp_path / "HR_Dashboard"
        assert (out / "HR_Dashboard.SemanticModel").is_dir()
        assert not (out / "Template.SemanticModel").exists()

    def test_report_dir_renamed(self, tmp_path, cfg):
        run_factory(TEMPLATE_DIR, tmp_path, cfg)
        out = tmp_path / "HR_Dashboard"
        assert (out / "HR_Dashboard.Report").is_dir()
        assert not (out / "Template.Report").exists()

    def test_pbip_renamed(self, tmp_path, cfg):
        run_factory(TEMPLATE_DIR, tmp_path, cfg)
        out = tmp_path / "HR_Dashboard"
        assert (out / "HR_Dashboard.pbip").is_file()
        assert not (out / "Template.pbip").exists()

    def test_pbip_references_new_report_path(self, tmp_path, cfg):
        run_factory(TEMPLATE_DIR, tmp_path, cfg)
        pbip = (tmp_path / "HR_Dashboard" / "HR_Dashboard.pbip").read_text(encoding="utf-8")
        assert "HR_Dashboard.Report" in pbip
        assert "template.Report" not in pbip

    def test_fact_tmdl_has_csv_mquery(self, tmp_path, cfg):
        run_factory(TEMPLATE_DIR, tmp_path, cfg)
        fact = (tmp_path / "HR_Dashboard" / "HR_Dashboard.SemanticModel"
                / "definition" / "tables" / "Fact.tmdl").read_text(encoding="utf-8")
        assert "Csv.Document" in fact

    def test_fact_tmdl_has_correct_source_path(self, tmp_path, cfg):
        run_factory(TEMPLATE_DIR, tmp_path, cfg)
        fact = (tmp_path / "HR_Dashboard" / "HR_Dashboard.SemanticModel"
                / "definition" / "tables" / "Fact.tmdl").read_text(encoding="utf-8")
        assert r"C:\data\hr_data.csv" in fact

    def test_fact_tmdl_columns_renamed(self, tmp_path, cfg):
        run_factory(TEMPLATE_DIR, tmp_path, cfg)
        fact = (tmp_path / "HR_Dashboard" / "HR_Dashboard.SemanticModel"
                / "definition" / "tables" / "Fact.tmdl").read_text(encoding="utf-8")
        assert "\tcolumn 'Total Budget'\n" in fact
        assert "\tcolumn Department\n" in fact

    def test_fact_tmdl_has_format_string(self, tmp_path, cfg):
        run_factory(TEMPLATE_DIR, tmp_path, cfg)
        fact = (tmp_path / "HR_Dashboard" / "HR_Dashboard.SemanticModel"
                / "definition" / "tables" / "Fact.tmdl").read_text(encoding="utf-8")
        assert "\t\tformatString: $#,0\n" in fact

    def test_fact_tmdl_has_hidden_columns(self, tmp_path, cfg):
        run_factory(TEMPLATE_DIR, tmp_path, cfg)
        fact = (tmp_path / "HR_Dashboard" / "HR_Dashboard.SemanticModel"
                / "definition" / "tables" / "Fact.tmdl").read_text(encoding="utf-8")
        assert "\t\tisHidden\n" in fact

    def test_fact_tmdl_has_sort_by_column(self, tmp_path, cfg):
        run_factory(TEMPLATE_DIR, tmp_path, cfg)
        fact = (tmp_path / "HR_Dashboard" / "HR_Dashboard.SemanticModel"
                / "definition" / "tables" / "Fact.tmdl").read_text(encoding="utf-8")
        assert "\t\tsortByColumn: 'ORDER Month Name'\n" in fact

    def test_cache_abf_deleted(self, tmp_path, cfg):
        run_factory(TEMPLATE_DIR, tmp_path, cfg)
        cache = (tmp_path / "HR_Dashboard" / "HR_Dashboard.SemanticModel"
                 / ".pbi" / "cache.abf")
        assert not cache.exists()

    def test_definition_pbir_references_new_semantic_model(self, tmp_path, cfg):
        run_factory(TEMPLATE_DIR, tmp_path, cfg)
        pbir = (tmp_path / "HR_Dashboard" / "HR_Dashboard.Report"
                / "definition.pbir").read_text(encoding="utf-8")
        assert "../HR_Dashboard.SemanticModel" in pbir
        assert "template.SemanticModel" not in pbir

    def test_report_platform_displayname_updated(self, tmp_path, cfg):
        run_factory(TEMPLATE_DIR, tmp_path, cfg)
        platform = (tmp_path / "HR_Dashboard" / "HR_Dashboard.Report"
                    / ".platform").read_text(encoding="utf-8")
        assert '"HR_Dashboard"' in platform
        assert '"template"' not in platform

    def test_semantic_model_platform_displayname_updated(self, tmp_path, cfg):
        run_factory(TEMPLATE_DIR, tmp_path, cfg)
        platform = (tmp_path / "HR_Dashboard" / "HR_Dashboard.SemanticModel"
                    / ".platform").read_text(encoding="utf-8")
        assert '"HR_Dashboard"' in platform
        assert '"template"' not in platform

    def test_fact_tmdl_mquery_has_table_rename_columns(self, tmp_path, cfg):
        run_factory(TEMPLATE_DIR, tmp_path, cfg)
        fact = (tmp_path / "HR_Dashboard" / "HR_Dashboard.SemanticModel"
                / "definition" / "tables" / "Fact.tmdl").read_text(encoding="utf-8")
        assert "Table.RenameColumns" in fact

    def test_fact_tmdl_source_column_updated_to_business_name(self, tmp_path, cfg):
        run_factory(TEMPLATE_DIR, tmp_path, cfg)
        fact = (tmp_path / "HR_Dashboard" / "HR_Dashboard.SemanticModel"
                / "definition" / "tables" / "Fact.tmdl").read_text(encoding="utf-8")
        assert "sourceColumn: Total Budget" in fact

    def test_fact_tmdl_source_column_not_template_slot(self, tmp_path, cfg):
        run_factory(TEMPLATE_DIR, tmp_path, cfg)
        fact = (tmp_path / "HR_Dashboard" / "HR_Dashboard.SemanticModel"
                / "definition" / "tables" / "Fact.tmdl").read_text(encoding="utf-8")
        # Use exact line match to avoid false positive from SUM_Measure_10
        assert "\t\tsourceColumn: SUM_Measure_1\n" not in fact

    def test_hidden_columns_removed_from_visual_projections(self, tmp_path, cfg):
        run_factory(TEMPLATE_DIR, tmp_path, cfg)
        report = tmp_path / "HR_Dashboard" / "HR_Dashboard.Report"
        for vpath in report.rglob("visual.json"):
            d = json.loads(vpath.read_text(encoding="utf-8"))
            qs = d.get("visual", {}).get("query", {}).get("queryState", {})
            for section_val in qs.values():
                for proj in section_val.get("projections", []):
                    field = proj.get("field", {})
                    if "Column" in field:
                        prop = field["Column"].get("Property", "")
                        assert not re.match(
                            r"^(SUM_Measure_[3-9]|SUM_Measure_10|CNT_Measure_[2-5]|AVG_Measure_[2-5]|Key_Dim_[3-9]|Key_Dim_10|Other_Field_[3-9]|Other_Field_10)$",
                            prop,
                        ), f"Hidden column still in projection: {prop} in {vpath}"
                    if "Aggregation" in field:
                        prop = field["Aggregation"].get("Expression", {}).get("Column", {}).get("Property", "")
                        assert not re.match(
                            r"^(SUM_Measure_[3-9]|SUM_Measure_10|CNT_Measure_[2-5]|AVG_Measure_[2-5])$",
                            prop,
                        ), f"Hidden aggregation still in projection: {prop} in {vpath}"

    def test_mquery_does_not_include_dax_measure_names(self, tmp_path, cfg):
        run_factory(TEMPLATE_DIR, tmp_path, cfg)
        fact = (tmp_path / "HR_Dashboard" / "HR_Dashboard.SemanticModel"
                / "definition" / "tables" / "Fact.tmdl").read_text(encoding="utf-8")
        rename_block_match = re.search(
            r"Table\.RenameColumns\(.*?\}\)",
            fact,
            re.DOTALL,
        )
        assert rename_block_match, "Table.RenameColumns not found in M Query"
        rename_block = rename_block_match.group(0)
        assert "DAX_SUM_Measure_1" not in rename_block
        assert "DAX_CNT_Measure_1" not in rename_block

    def test_dax_measures_renamed_in_tmdl(self, tmp_path, cfg):
        run_factory(TEMPLATE_DIR, tmp_path, cfg)
        fact = (tmp_path / "HR_Dashboard" / "HR_Dashboard.SemanticModel"
                / "definition" / "tables" / "Fact.tmdl").read_text(encoding="utf-8")
        assert "\tmeasure DAX_Total_Budget" in fact
        assert "\tmeasure DAX_SUM_Measure_1 " not in fact

    def test_select_dimension_field_parameters_renamed(self, tmp_path, cfg):
        run_factory(TEMPLATE_DIR, tmp_path, cfg)
        tmdl = (tmp_path / "HR_Dashboard" / "HR_Dashboard.SemanticModel"
                / "definition" / "tables" / "Select Dimension.tmdl").read_text(encoding="utf-8")
        assert '"Department"' in tmdl
        assert '"Key_Dim_1"' not in tmdl
        assert "NAMEOF('Fact'[Department])" in tmdl
        assert "NAMEOF('Fact'[Key_Dim_1])" not in tmdl

    def test_select_dimension_unused_rows_deleted(self, tmp_path, cfg):
        run_factory(TEMPLATE_DIR, tmp_path, cfg)
        tmdl = (tmp_path / "HR_Dashboard" / "HR_Dashboard.SemanticModel"
                / "definition" / "tables" / "Select Dimension.tmdl").read_text(encoding="utf-8")
        assert '"Key_Dim_6"' not in tmdl
        assert "NAMEOF('Fact'[Key_Dim_6])" not in tmdl

    def test_select_measure_field_parameters_renamed(self, tmp_path, cfg):
        run_factory(TEMPLATE_DIR, tmp_path, cfg)
        tmdl = (tmp_path / "HR_Dashboard" / "HR_Dashboard.SemanticModel"
                / "definition" / "tables" / "Select Measure.tmdl").read_text(encoding="utf-8")
        assert '"Total Budget"' in tmdl
        assert '"SUM_Measure_1"' not in tmdl
        assert "NAMEOF('Fact'[DAX_Total_Budget])" in tmdl
        assert "NAMEOF('Fact'[DAX_SUM_Measure_1])" not in tmdl

    def test_select_measure_unused_rows_deleted(self, tmp_path, cfg):
        run_factory(TEMPLATE_DIR, tmp_path, cfg)
        tmdl = (tmp_path / "HR_Dashboard" / "HR_Dashboard.SemanticModel"
                / "definition" / "tables" / "Select Measure.tmdl").read_text(encoding="utf-8")
        assert '"SUM_Measure_2"' not in tmdl
        assert "NAMEOF('Fact'[DAX_SUM_Measure_2])" not in tmdl

    def test_fact_tmdl_mquery_renames_csv_col_not_slot(self, tmp_path, cfg):
        run_factory(TEMPLATE_DIR, tmp_path, cfg)
        fact = (tmp_path / "HR_Dashboard" / "HR_Dashboard.SemanticModel"
                / "definition" / "tables" / "Fact.tmdl").read_text(encoding="utf-8")
        assert '"Budget", "Total Budget"' in fact
        assert '"SUM_Measure_1", "Total Budget"' not in fact

    def test_fact_tmdl_mquery_rename_uses_promoted_headers(self, tmp_path, cfg):
        run_factory(TEMPLATE_DIR, tmp_path, cfg)
        fact = (tmp_path / "HR_Dashboard" / "HR_Dashboard.SemanticModel"
                / "definition" / "tables" / "Fact.tmdl").read_text(encoding="utf-8")
        assert 'Table.RenameColumns(#"Promoted Headers"' in fact

    def test_fact_tmdl_mquery_types_by_business_name(self, tmp_path, cfg):
        run_factory(TEMPLATE_DIR, tmp_path, cfg)
        fact = (tmp_path / "HR_Dashboard" / "HR_Dashboard.SemanticModel"
                / "definition" / "tables" / "Fact.tmdl").read_text(encoding="utf-8")
        assert '{"Total Budget", Int64.Type}' in fact
        assert '{"Date Reported", type date}' in fact
        assert '{"SUM_Measure_1", Int64.Type}' not in fact
        assert '{"DateKey", type date}' not in fact
