import re
import pytest
from src.config_parser import parse_config
from src.format_pipeline import get_format_updates, apply_formats, run_format_pipeline

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

SQL_NO_FMT = """\
/*FACTORY
TITLE: T
THEME(1:a): 1
DB(1:A 2:B 3:C): 1

1.CNT(max5): ①ID ②③④⑤
2.SUM(max10): ①Revenue ②③④⑤⑥⑦⑧⑨⑩
3.AVG(max5): ①Rate ②③④⑤
4.DATE: "Date"
5.KEY(max10): ①Dept ②③④⑤⑥⑦⑧⑨⑩
6.OTHER: Notes
*/

SELECT Revenue, Rate, Date, Dept, Notes FROM T
"""

# Minimal TMDL with one SUM (has formatString) and one AVG (no formatString)
SAMPLE_FORMAT_TMDL = (
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
    "\tcolumn AVG_Measure_1\n"
    "\t\tdataType: double\n"
    "\t\tlineageTag: tag-avg-1\n"
    "\t\tsummarizeBy: sum\n"
    "\t\tsourceColumn: AVG_Measure_1\n"
    "\n"
    '\t\tannotation PBI_FormatHint = {"isGeneralNumber":true}\n'
    "\n"
)


@pytest.fixture
def cfg_csv():
    return parse_config(SQL_HR_CSV)


@pytest.fixture
def cfg_no_fmt():
    return parse_config(SQL_NO_FMT)


class TestGetFormatUpdates:
    def test_sum_currency_specifier(self, cfg_csv):
        assert get_format_updates(cfg_csv)["SUM_Measure_1"] == "$#,0"

    def test_sum_integer_specifier(self, cfg_csv):
        assert get_format_updates(cfg_csv)["SUM_Measure_2"] == "#,0"

    def test_sum_inactive_slot_absent(self, cfg_csv):
        updates = get_format_updates(cfg_csv)
        for i in range(3, 11):
            assert f"SUM_Measure_{i}" not in updates

    def test_avg_one_dp_specifier(self, cfg_csv):
        assert get_format_updates(cfg_csv)["AVG_Measure_1"] == "#,0.0"

    def test_avg_inactive_slots_absent(self, cfg_csv):
        updates = get_format_updates(cfg_csv)
        for i in range(2, 6):
            assert f"AVG_Measure_{i}" not in updates

    def test_sum_default_when_no_specifier(self, cfg_no_fmt):
        assert get_format_updates(cfg_no_fmt)["SUM_Measure_1"] == "#,0.00"

    def test_avg_no_explicit_specifier_absent(self, cfg_no_fmt):
        assert "AVG_Measure_1" not in get_format_updates(cfg_no_fmt)

    def test_cnt_columns_absent(self, cfg_csv):
        updates = get_format_updates(cfg_csv)
        for i in range(1, 6):
            assert f"CNT_Measure_{i}" not in updates

    def test_two_dp_specifier(self):
        sql = """\
/*FACTORY
TITLE: T
THEME(1:a): 1
DB(1:A 2:B 3:C): 1

1.CNT(max5): ①ID ②③④⑤
2.SUM(max10): ①Amount(#.00) ②③④⑤⑥⑦⑧⑨⑩
3.AVG(max5): ①②③④⑤
4.DATE: "Date"
5.KEY(max10): ①Dept ②③④⑤⑥⑦⑧⑨⑩
6.OTHER: Notes
*/
SELECT * FROM T
"""
        cfg = parse_config(sql)
        assert get_format_updates(cfg)["SUM_Measure_1"] == "#,0.00"

    def test_percent_specifier(self):
        sql = """\
/*FACTORY
TITLE: T
THEME(1:a): 1
DB(1:A 2:B 3:C): 1

1.CNT(max5): ①ID ②③④⑤
2.SUM(max10): ①Rate(%) ②③④⑤⑥⑦⑧⑨⑩
3.AVG(max5): ①②③④⑤
4.DATE: "Date"
5.KEY(max10): ①Dept ②③④⑤⑥⑦⑧⑨⑩
6.OTHER: Notes
*/
SELECT * FROM T
"""
        cfg = parse_config(sql)
        assert get_format_updates(cfg)["SUM_Measure_1"] == "0.00%"

    def test_custom_format_passthrough_sum(self):
        sql = """\
/*FACTORY
TITLE: T
THEME(1:a): 1
DB(1:A 2:B 3:C): 1

1.CNT(max5): ①ID ②③④⑤
2.SUM(max10): ①Amount($#,0.00) ②③④⑤⑥⑦⑧⑨⑩
3.AVG(max5): ①②③④⑤
4.DATE: "Date"
5.KEY(max10): ①Dept ②③④⑤⑥⑦⑧⑨⑩
6.OTHER: Notes
*/
SELECT * FROM T
"""
        cfg = parse_config(sql)
        assert get_format_updates(cfg)["SUM_Measure_1"] == "$#,0.00"


class TestApplyFormats:
    def test_replaces_sum_format_string(self):
        result = apply_formats(SAMPLE_FORMAT_TMDL, {"SUM_Measure_1": "$#,0"})
        assert "\t\tformatString: $#,0\n" in result

    def test_old_sum_format_removed_from_block(self):
        result = apply_formats(SAMPLE_FORMAT_TMDL, {"SUM_Measure_1": "$#,0"})
        sum1_block = result.split("\tcolumn ")[1]  # block after first "column "
        assert "formatString: 0" not in sum1_block
        assert "formatString: $#,0" in sum1_block

    def test_sum2_format_unchanged_when_not_in_updates(self):
        result = apply_formats(SAMPLE_FORMAT_TMDL, {"SUM_Measure_1": "$#,0"})
        parts = result.split("\tcolumn ")
        sum2_block = [p for p in parts if p.startswith("SUM_Measure_2\n")][0]
        assert "formatString: 0" in sum2_block

    def test_inserts_format_string_for_avg(self):
        result = apply_formats(SAMPLE_FORMAT_TMDL, {"AVG_Measure_1": "#,0.0"})
        assert "\t\tformatString: #,0.0\n" in result

    def test_avg_format_inserted_after_datatype(self):
        result = apply_formats(SAMPLE_FORMAT_TMDL, {"AVG_Measure_1": "#,0.0"})
        dt_pos = result.find("\t\tdataType: double\n")
        fs_pos = result.find("\t\tformatString: #,0.0\n")
        assert 0 < dt_pos < fs_pos

    def test_avg_no_duplicate_format_string(self):
        result = apply_formats(SAMPLE_FORMAT_TMDL, {"AVG_Measure_1": "#,0.0"})
        assert result.count("\t\tformatString: #,0.0\n") == 1

    def test_empty_updates_returns_unchanged(self):
        assert apply_formats(SAMPLE_FORMAT_TMDL, {}) == SAMPLE_FORMAT_TMDL

    def test_col_not_in_tmdl_ignored(self):
        result = apply_formats(SAMPLE_FORMAT_TMDL, {"SUM_Measure_99": "#,0"})
        assert result == SAMPLE_FORMAT_TMDL


class TestRunFormatPipeline:
    def test_sum_format_written_to_file(self, tmp_path, cfg_csv):
        tmdl_file = tmp_path / "Fact.tmdl"
        tmdl_file.write_text(SAMPLE_FORMAT_TMDL, encoding="utf-8")
        run_format_pipeline(tmdl_file, cfg_csv)
        assert "\t\tformatString: $#,0\n" in tmdl_file.read_text(encoding="utf-8")

    def test_avg_format_written_to_file(self, tmp_path, cfg_csv):
        tmdl_file = tmp_path / "Fact.tmdl"
        tmdl_file.write_text(SAMPLE_FORMAT_TMDL, encoding="utf-8")
        run_format_pipeline(tmdl_file, cfg_csv)
        assert "\t\tformatString: #,0.0\n" in tmdl_file.read_text(encoding="utf-8")
