import pytest
from src.config_parser import parse_config, extract_factory_block

SQL_HR = """\
/*FACTORY
TITLE: HR Dashboard
THEME(1:nsw-blue 2:nsw-red 3:oracle): 1
DB(1:Oracle 2:PostgreSQL 3:Snowflake): 2

1.CNT(max5): ①"Employee ID"+"Month Name" ②③④⑤
2.SUM(max10): ①Budget($) ②Headcount(#) ③④⑤⑥⑦⑧⑨⑩
3.AVG(max5): ①②③④⑤
4.DATE: "Date Reported"
5.KEY(max10): ①Department ②"Month Name" ③④⑤⑥⑦⑧⑨⑩
6.OTHER: Notes
*/

SELECT
    Budget,
    Headcount,
    Employee_ID AS "Employee ID",
    Report_Date AS "Date Reported",
    Department,
    Month_Name AS "Month Name",
    Month_Number AS "ORDER Month Name",
    Notes
FROM HR.VW_DASHBOARD
"""

SQL_ED = """\
/*FACTORY
TITLE: ED Wait Times
THEME(1:nsw-blue 2:nsw-red 3:oracle): 1
DB(1:Oracle 2:PostgreSQL 3:Snowflake): 2

1.CNT(max5): ①"Patient ID"+"Date Presented" ②"Doctor ID" ③④⑤
2.SUM(max10): ①Budget($) ②Presentations(#) ③"Hours Worked"(#.0) ④⑤⑥⑦⑧⑨⑩
3.AVG(max5): ①"Wait Time Min"(#.0) ②③④⑤
4.DATE: "Date Presented"
5.KEY(max10): ①Hospital ②"Triage Category" ③Ward ④"Month Name" ⑤⑥⑦⑧⑨⑩
6.OTHER: "Staff Name", "Date Discharged", Notes
*/

SELECT
    Budget,
    Presentations,
    Hours_Worked AS "Hours Worked",
    Patient_ID AS "Patient ID",
    Presentation_Date AS "Date Presented",
    Doctor_ID AS "Doctor ID",
    Wait_Time_Min AS "Wait Time Min",
    Hospital,
    Triage_Category AS "Triage Category",
    Ward,
    Month_Name AS "Month Name",
    Month_Number AS "ORDER Month Name",
    Staff_Name AS "Staff Name",
    Discharge_Date AS "Date Discharged",
    Notes
FROM SCHEMA.TABLE_A
"""


@pytest.fixture
def hr():
    return parse_config(SQL_HR)


@pytest.fixture
def ed():
    return parse_config(SQL_ED)


class TestExtractFactoryBlock:
    def test_returns_content_between_markers(self):
        block = extract_factory_block(SQL_HR)
        assert "TITLE: HR Dashboard" in block

    def test_does_not_include_select(self):
        block = extract_factory_block(SQL_HR)
        assert "SELECT" not in block

    def test_does_not_include_factory_markers(self):
        block = extract_factory_block(SQL_HR)
        assert "/*FACTORY" not in block
        assert "*/" not in block

    def test_raises_on_missing_block(self):
        with pytest.raises(ValueError, match="FACTORY"):
            extract_factory_block("SELECT 1 FROM dual")


class TestHeader:
    def test_parses_title(self, hr):
        assert hr["title"] == "HR Dashboard"

    def test_parses_theme_index(self, hr):
        assert hr["theme"] == 1

    def test_parses_db_index(self, hr):
        assert hr["db"] == 2

    def test_ed_title(self, ed):
        assert ed["title"] == "ED Wait Times"


class TestCntSlots:
    def test_slot1_fields_are_list(self, hr):
        assert hr["cnt"][0]["fields"] == ["Employee ID", "Month Name"]

    def test_slot1_composite_flag(self, hr):
        assert hr["cnt"][0]["composite"] is True

    def test_slot1_format_is_none(self, hr):
        assert hr["cnt"][0]["format"] is None

    def test_slots_2_to_5_are_none(self, hr):
        for i in range(1, 5):
            assert hr["cnt"][i] is None

    def test_total_slots_is_5(self, hr):
        assert len(hr["cnt"]) == 5

    def test_ed_two_composite_fields(self, ed):
        assert ed["cnt"][0]["fields"] == ["Patient ID", "Date Presented"]

    def test_ed_slot2_single_field_not_composite(self, ed):
        slot = ed["cnt"][1]
        assert slot["fields"] == ["Doctor ID"]
        assert slot["composite"] is False


class TestSumSlots:
    def test_slot1_currency_format(self, hr):
        assert hr["sum"][0] == {"field": "Budget", "format": "$"}

    def test_slot2_integer_format(self, hr):
        assert hr["sum"][1] == {"field": "Headcount", "format": "#"}

    def test_slots_3_to_10_are_none(self, hr):
        for i in range(2, 10):
            assert hr["sum"][i] is None

    def test_total_slots_is_10(self, hr):
        assert len(hr["sum"]) == 10

    def test_ed_slot3_one_dp_format(self, ed):
        assert ed["sum"][2] == {"field": "Hours Worked", "format": "#.0"}


class TestAvgSlots:
    def test_all_slots_none_when_empty(self, hr):
        assert all(s is None for s in hr["avg"])

    def test_total_slots_is_5(self, hr):
        assert len(hr["avg"]) == 5

    def test_ed_slot1_with_format(self, ed):
        assert ed["avg"][0] == {"field": "Wait Time Min", "format": "#.0"}

    def test_ed_slots_2_to_5_are_none(self, ed):
        for i in range(1, 5):
            assert ed["avg"][i] is None


class TestDate:
    def test_parses_quoted_date_field(self, hr):
        assert hr["date"] == "Date Reported"

    def test_ed_date_field(self, ed):
        assert ed["date"] == "Date Presented"


class TestKeySlots:
    def test_slot1_single_word_no_format(self, hr):
        assert hr["key"][0] == {"field": "Department", "format": None}

    def test_slot2_quoted_multi_word(self, hr):
        assert hr["key"][1] == {"field": "Month Name", "format": None}

    def test_slots_3_to_10_are_none(self, hr):
        for i in range(2, 10):
            assert hr["key"][i] is None

    def test_total_slots_is_10(self, hr):
        assert len(hr["key"]) == 10

    def test_ed_four_active_key_slots(self, ed):
        assert ed["key"][0]["field"] == "Hospital"
        assert ed["key"][1]["field"] == "Triage Category"
        assert ed["key"][2]["field"] == "Ward"
        assert ed["key"][3]["field"] == "Month Name"
        assert ed["key"][4] is None


class TestOther:
    def test_single_unquoted_field(self, hr):
        assert hr["other"] == ["Notes"]

    def test_ed_multiple_mixed_fields(self, ed):
        assert ed["other"] == ["Staff Name", "Date Discharged", "Notes"]


class TestOrderColumns:
    def test_order_column_maps_target_to_alias(self, hr):
        assert hr["order_columns"]["Month Name"] == "ORDER Month Name"

    def test_non_order_fields_absent(self, hr):
        assert "Budget" not in hr["order_columns"]
        assert "Department" not in hr["order_columns"]

    def test_ed_order_column(self, ed):
        assert ed["order_columns"]["Month Name"] == "ORDER Month Name"


# ── CSV / Excel fixtures ──────────────────────────────────────────────────────

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


@pytest.fixture
def hr_csv():
    return parse_config(SQL_HR_CSV)


@pytest.fixture
def hr_excel():
    return parse_config(SQL_HR_EXCEL)


class TestCSVConfig:
    def test_db_is_4(self, hr_csv):
        assert hr_csv["db"] == 4

    def test_source_path(self, hr_csv):
        assert hr_csv["source"] == r"C:\data\hr_data.csv"

    def test_sql_source_is_none(self, hr):
        assert hr["source"] is None

    def test_cnt_composite_as_fields(self, hr_csv):
        assert hr_csv["cnt"][0]["fields"] == ["Record ID"]

    def test_cnt_composite_as_source_columns(self, hr_csv):
        assert hr_csv["cnt"][0]["source_columns"] == ["Employee_ID", "Month_Name"]

    def test_cnt_composite_flag(self, hr_csv):
        assert hr_csv["cnt"][0]["composite"] is True

    def test_cnt_empty_slots(self, hr_csv):
        for i in range(1, 5):
            assert hr_csv["cnt"][i] is None

    def test_sum_slot1_display_name(self, hr_csv):
        assert hr_csv["sum"][0]["field"] == "Total Budget"

    def test_sum_slot1_format(self, hr_csv):
        assert hr_csv["sum"][0]["format"] == "$"

    def test_sum_slot1_source_column(self, hr_csv):
        assert hr_csv["sum"][0]["source_column"] == "Budget"

    def test_sum_slot2_no_as_field(self, hr_csv):
        assert hr_csv["sum"][1]["field"] == "Headcount"

    def test_sum_slot2_no_as_no_source_column_key(self, hr_csv):
        assert "source_column" not in hr_csv["sum"][1]

    def test_avg_slot1_display_name(self, hr_csv):
        assert hr_csv["avg"][0]["field"] == "Avg Rating"

    def test_avg_slot1_format(self, hr_csv):
        assert hr_csv["avg"][0]["format"] == "#.0"

    def test_avg_slot1_source_column(self, hr_csv):
        assert hr_csv["avg"][0]["source_column"] == "Rating"

    def test_date_display_name(self, hr_csv):
        assert hr_csv["date"] == "Date Reported"

    def test_date_source_column(self, hr_csv):
        assert hr_csv["date_source_column"] == "Report_Date"

    def test_sql_date_source_column_absent(self, hr):
        assert hr.get("date_source_column") is None

    def test_key_slot1_no_as(self, hr_csv):
        assert hr_csv["key"][0] == {"field": "Department", "format": None}

    def test_key_slot2_display_name(self, hr_csv):
        assert hr_csv["key"][1]["field"] == "Month Name"

    def test_key_slot2_source_column(self, hr_csv):
        assert hr_csv["key"][1]["source_column"] == "Month_Name"

    def test_key_slot2_no_format(self, hr_csv):
        assert hr_csv["key"][1]["format"] is None

    def test_other_display_names(self, hr_csv):
        assert hr_csv["other"] == ["Staff Name", "Notes"]

    def test_field_map_sum_rename(self, hr_csv):
        assert hr_csv["field_map"]["Budget"] == "Total Budget"

    def test_field_map_avg_rename(self, hr_csv):
        assert hr_csv["field_map"]["Rating"] == "Avg Rating"

    def test_field_map_date_rename(self, hr_csv):
        assert hr_csv["field_map"]["Report_Date"] == "Date Reported"

    def test_field_map_key_rename(self, hr_csv):
        assert hr_csv["field_map"]["Month_Name"] == "Month Name"

    def test_field_map_other_rename(self, hr_csv):
        assert hr_csv["field_map"]["Staff_Name"] == "Staff Name"

    def test_field_map_excludes_no_as_fields(self, hr_csv):
        assert "Headcount" not in hr_csv["field_map"]
        assert "Notes" not in hr_csv["field_map"]
        assert "Department" not in hr_csv["field_map"]

    def test_sql_field_map_empty(self, hr):
        assert hr["field_map"] == {}


class TestExcelConfig:
    def test_db_is_5(self, hr_excel):
        assert hr_excel["db"] == 5

    def test_source_path(self, hr_excel):
        assert hr_excel["source"] == r"C:\data\staff.xlsx"

    def test_date_no_as_no_date_source_column(self, hr_excel):
        assert hr_excel["date"] == "Report_Date"
        assert hr_excel.get("date_source_column") is None

    def test_other_single_field(self, hr_excel):
        assert hr_excel["other"] == ["Notes"]


SQL_SIMPLE_CNT_CSV = r"""/*FACTORY
TITLE: Simple CNT
THEME(1:nsw-blue): 1
DB(1:Oracle 2:PostgreSQL 3:Snowflake 4:CSV 5:Excel): 4
SOURCE: C:\data\test.csv

1.CNT(max5): ①transaction_id AS "Transaction Count" ②③④⑤
2.SUM(max10): ①amount AS "Amount"($) ②③④⑤⑥⑦⑧⑨⑩
3.AVG(max5): ①②③④⑤
4.DATE: txn_date AS "Transaction Date"
5.KEY(max10): ①category AS "Category" ②③④⑤⑥⑦⑧⑨⑩
6.OTHER: notes
*/
"""


class TestCSVConfigSingleCNTAlias:
    @pytest.fixture
    def cfg(self):
        return parse_config(SQL_SIMPLE_CNT_CSV)

    def test_cnt_slot_fields(self, cfg):
        assert cfg["cnt"][0]["fields"] == ["Transaction Count"]

    def test_cnt_slot_source_columns(self, cfg):
        assert cfg["cnt"][0]["source_columns"] == ["transaction_id"]

    def test_field_map_includes_cnt_rename(self, cfg):
        assert cfg["field_map"]["transaction_id"] == "Transaction Count"
