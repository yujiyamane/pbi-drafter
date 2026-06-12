import pytest
from src.config_parser import parse_config
from src.mquery_generator import generate_mquery, _remove_step

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

SQL_HR_EXCEL = r"""/*FACTORY
TITLE: Staff Excel
THEME(1:nsw-blue 2:nsw-red 3:oracle): 1
DB(1:Oracle 2:PostgreSQL 3:Snowflake 4:CSV 5:Excel): 5
SOURCE: C:\data\staff.xlsx

1.CNT(max5): ①Employee_ID ②③④⑤
2.SUM(max10): ①Budget($) ②③④⑤⑥⑦⑧⑨⑩
3.AVG(max5): ①②③④⑤
4.DATE: Report_Date
5.KEY(max10): ①Department ②③④⑤⑥⑦⑧⑨⑩
6.OTHER: Notes
*/
"""

SQL_ORACLE = """\
/*FACTORY
TITLE: Oracle Dashboard
THEME(1:nsw-blue 2:nsw-red 3:oracle): 3
DB(1:Oracle 2:PostgreSQL 3:Snowflake): 1

1.CNT(max5): ①"Patient ID" ②③④⑤
2.SUM(max10): ①Budget($) ②③④⑤⑥⑦⑧⑨⑩
3.AVG(max5): ①②③④⑤
4.DATE: "Date Reported"
5.KEY(max10): ①Department ②③④⑤⑥⑦⑧⑨⑩
6.OTHER: Notes
*/

SELECT Budget, Patient_ID AS "Patient ID", Date_Reported AS "Date Reported", Department, Notes
FROM SCHEMA.TABLE_A
"""


@pytest.fixture
def cfg_csv():
    return parse_config(SQL_HR_CSV)


@pytest.fixture
def cfg_excel():
    return parse_config(SQL_HR_EXCEL)


@pytest.fixture
def cfg_oracle():
    return parse_config(SQL_ORACLE)


class TestCSVMQuery:
    def test_returns_string(self, cfg_csv):
        assert isinstance(generate_mquery(cfg_csv), str)

    def test_is_let_in_expression(self, cfg_csv):
        mq = generate_mquery(cfg_csv)
        assert mq.strip().startswith("let")
        assert "\nin\n" in mq or "\nin " in mq

    def test_uses_csv_document(self, cfg_csv):
        assert "Csv.Document" in generate_mquery(cfg_csv)

    def test_file_contents_with_csv_path(self, cfg_csv):
        assert r'File.Contents("C:\data\hr_data.csv")' in generate_mquery(cfg_csv)

    def test_promotes_headers(self, cfg_csv):
        assert "Table.PromoteHeaders" in generate_mquery(cfg_csv)

    def test_rename_step_present(self, cfg_csv):
        assert "Table.RenameColumns" in generate_mquery(cfg_csv)

    def test_renames_budget(self, cfg_csv):
        assert '{"Budget", "Total Budget"}' in generate_mquery(cfg_csv)

    def test_renames_rating(self, cfg_csv):
        assert '{"Rating", "Avg Rating"}' in generate_mquery(cfg_csv)

    def test_renames_report_date(self, cfg_csv):
        assert '{"Report_Date", "Date Reported"}' in generate_mquery(cfg_csv)

    def test_renames_month_name(self, cfg_csv):
        assert '{"Month_Name", "Month Name"}' in generate_mquery(cfg_csv)

    def test_renames_staff_name(self, cfg_csv):
        assert '{"Staff_Name", "Staff Name"}' in generate_mquery(cfg_csv)

    def test_no_rename_entry_for_headcount(self, cfg_csv):
        assert '{"Headcount", "' not in generate_mquery(cfg_csv)

    def test_no_rename_entry_for_notes(self, cfg_csv):
        assert '{"Notes", "' not in generate_mquery(cfg_csv)

    def test_no_rename_entry_for_department(self, cfg_csv):
        assert '{"Department", "' not in generate_mquery(cfg_csv)


class TestExcelMQuery:
    def test_returns_string(self, cfg_excel):
        assert isinstance(generate_mquery(cfg_excel), str)

    def test_uses_excel_workbook(self, cfg_excel):
        assert "Excel.Workbook" in generate_mquery(cfg_excel)

    def test_file_contents_with_excel_path(self, cfg_excel):
        assert r'File.Contents("C:\data\staff.xlsx")' in generate_mquery(cfg_excel)

    def test_promotes_headers(self, cfg_excel):
        assert "Table.PromoteHeaders" in generate_mquery(cfg_excel)

    def test_no_rename_step_when_no_mappings(self, cfg_excel):
        assert "Table.RenameColumns" not in generate_mquery(cfg_excel)

    def test_is_let_in_expression(self, cfg_excel):
        mq = generate_mquery(cfg_excel)
        assert mq.strip().startswith("let")
        assert "in" in mq


class TestCSVMQueryTypeConversion:
    def test_has_changed_type_step(self, cfg_csv):
        assert "Table.TransformColumnTypes" in generate_mquery(cfg_csv)


class TestExcelMQueryTypeConversion:
    def test_has_changed_type_step(self, cfg_excel):
        assert "Table.TransformColumnTypes" in generate_mquery(cfg_excel)

    def test_changed_type_uses_promoted_headers(self, cfg_excel):
        assert 'Table.TransformColumnTypes(#"Promoted Headers"' in generate_mquery(cfg_excel)


class TestSQLNotImplemented:
    def test_oracle_raises_not_implemented(self, cfg_oracle):
        with pytest.raises(NotImplementedError):
            generate_mquery(cfg_oracle)


class TestRemoveStep:
    def test_no_step_when_empty(self):
        prev, step = _remove_step('#"Changed Type"', [])
        assert prev == '#"Changed Type"'
        assert step is None

    def test_returns_removed_columns_step_name(self):
        prev, _ = _remove_step('#"Changed Type"', ["SUM_Measure_2"])
        assert prev == '#"Removed Columns"'

    def test_generates_table_remove_columns(self):
        _, step = _remove_step('#"Changed Type"', ["SUM_Measure_2"])
        assert "Table.RemoveColumns" in step

    def test_step_uses_prev_step_as_input(self):
        _, step = _remove_step('#"Changed Type"', ["SUM_Measure_2"])
        assert 'Table.RemoveColumns(#"Changed Type"' in step

    def test_step_includes_each_unused_column(self):
        _, step = _remove_step('#"Changed Type"', ["SUM_Measure_2", "Key_Dim_3"])
        assert '"SUM_Measure_2"' in step
        assert '"Key_Dim_3"' in step


class TestCSVMQueryNoRemoveStep:
    def test_no_remove_step_in_csv_mquery(self, cfg_csv):
        assert "Table.RemoveColumns" not in generate_mquery(cfg_csv)


class TestCSVMQueryRenameFirst:
    """CSV path: rename CSV col names → business names first, type-cast by business name after."""

    def test_sum_business_name_typed_as_int64(self, cfg_csv):
        assert '{"Total Budget", Int64.Type}' in generate_mquery(cfg_csv)

    def test_no_sum_slot_name_in_mquery(self, cfg_csv):
        assert '{"SUM_Measure_1"' not in generate_mquery(cfg_csv)

    def test_cnt_business_name_typed_as_text(self, cfg_csv):
        assert '{"Record ID", type text}' in generate_mquery(cfg_csv)

    def test_cnt_business_name_not_typed_as_int64(self, cfg_csv):
        assert '{"Record ID", Int64.Type}' not in generate_mquery(cfg_csv)

    def test_no_cnt_slot_name_in_mquery(self, cfg_csv):
        assert '{"CNT_Measure_1"' not in generate_mquery(cfg_csv)

    def test_avg_business_name_typed_as_number(self, cfg_csv):
        assert '{"Avg Rating", type number}' in generate_mquery(cfg_csv)

    def test_no_avg_slot_name_in_mquery(self, cfg_csv):
        assert '{"AVG_Measure_1"' not in generate_mquery(cfg_csv)

    def test_date_business_name_typed_as_date(self, cfg_csv):
        assert '{"Date Reported", type date}' in generate_mquery(cfg_csv)

    def test_no_datekey_in_mquery(self, cfg_csv):
        assert '{"DateKey"' not in generate_mquery(cfg_csv)

    def test_rename_step_before_type_step(self, cfg_csv):
        mq = generate_mquery(cfg_csv)
        assert mq.index("Table.RenameColumns") < mq.index("Table.TransformColumnTypes")

    def test_type_step_uses_renamed_columns_as_input(self, cfg_csv):
        assert 'Table.TransformColumnTypes(#"Renamed Columns"' in generate_mquery(cfg_csv)

    def test_rename_step_uses_promoted_headers_as_input(self, cfg_csv):
        assert 'Table.RenameColumns(#"Promoted Headers"' in generate_mquery(cfg_csv)

    def test_key_business_name_typed_as_text(self, cfg_csv):
        assert '{"Department", type text}' in generate_mquery(cfg_csv)

    def test_other_business_name_typed_as_text(self, cfg_csv):
        assert '{"Staff Name", type text}' in generate_mquery(cfg_csv)


class TestExcelMQueryRenameFirst:
    """Excel path: date column uses CSV name in type step (no alias in SQL_HR_EXCEL)."""

    def test_date_csv_col_typed_as_date(self, cfg_excel):
        assert '{"Report_Date", type date}' in generate_mquery(cfg_excel)

    def test_no_datekey_in_excel_mquery(self, cfg_excel):
        assert '{"DateKey"' not in generate_mquery(cfg_excel)


SQL_SIMPLE_CNT_CSV = r"""/*FACTORY
TITLE: Asset Dashboard
THEME(1:nsw-blue): 1
DB(1:Oracle 2:PostgreSQL 3:Snowflake 4:CSV 5:Excel): 4
SOURCE: C:\data\test.csv

1.CNT(max5): ①transaction_id AS "Transaction Count" ②③④⑤
2.SUM(max10): ①amount AS "Amount"($#,0.00) ②③④⑤⑥⑦⑧⑨⑩
3.AVG(max5): ①②③④⑤
4.DATE: txn_date AS "Transaction Date"
5.KEY(max10): ①category AS "Category" ②③④⑤⑥⑦⑧⑨⑩
6.OTHER: notes
*/
"""


@pytest.fixture
def cfg_cnt():
    return parse_config(SQL_SIMPLE_CNT_CSV)


class TestCSVMQueryCNTRename:
    def test_cnt_csv_col_in_rename_step(self, cfg_cnt):
        assert '{"transaction_id", "Transaction Count"}' in generate_mquery(cfg_cnt)

    def test_transaction_count_typed_as_text(self, cfg_cnt):
        assert '{"Transaction Count", type text}' in generate_mquery(cfg_cnt)
