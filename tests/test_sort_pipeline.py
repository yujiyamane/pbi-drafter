import re
import pytest
from src.config_parser import parse_config
from src.sort_pipeline import apply_sort, run_sort_pipeline

# Post-rename TMDL: columns already have display names
SAMPLE_SORT_TMDL = (
    "table Fact\n"
    "\tlineageTag: table-tag\n"
    "\n"
    "\tcolumn Department\n"
    "\t\tdataType: string\n"
    "\t\tlineageTag: tag-dept\n"
    "\t\tsummarizeBy: none\n"
    "\t\tsourceColumn: Key_Dim_1\n"
    "\n"
    "\tcolumn 'Month Name'\n"
    "\t\tdataType: string\n"
    "\t\tlineageTag: tag-month\n"
    "\t\tsummarizeBy: none\n"
    "\t\tsourceColumn: Key_Dim_2\n"
    "\n"
    "\tcolumn 'ORDER Month Name'\n"
    "\t\tdataType: int64\n"
    "\t\tlineageTag: tag-order-month\n"
    "\t\tsummarizeBy: sum\n"
    "\t\tsourceColumn: Key_Dim_3\n"
    "\n"
)

ORDER_COLS = {"Month Name": "ORDER Month Name"}


class TestApplySort:
    def test_adds_sort_by_column_to_target(self):
        result = apply_sort(SAMPLE_SORT_TMDL, ORDER_COLS)
        assert "\t\tsortByColumn: 'ORDER Month Name'\n" in result

    def test_sort_by_column_after_lineage_tag(self):
        result = apply_sort(SAMPLE_SORT_TMDL, ORDER_COLS)
        lt_pos = result.find("tag-month")
        sbc_pos = result.find("\t\tsortByColumn:")
        assert 0 < lt_pos < sbc_pos

    def test_order_col_gets_is_hidden(self):
        result = apply_sort(SAMPLE_SORT_TMDL, ORDER_COLS)
        assert "\t\tisHidden\n" in result

    def test_order_col_gets_is_available_in_mdx_false(self):
        result = apply_sort(SAMPLE_SORT_TMDL, ORDER_COLS)
        assert "\t\tisAvailableInMDX: false\n" in result

    def test_hidden_is_after_order_col_lineage_tag(self):
        result = apply_sort(SAMPLE_SORT_TMDL, ORDER_COLS)
        lt_pos = result.find("tag-order-month")
        hidden_pos = result.find("\t\tisHidden\n")
        assert 0 < lt_pos < hidden_pos

    def test_target_col_has_no_is_hidden(self):
        result = apply_sort(SAMPLE_SORT_TMDL, ORDER_COLS)
        parts = result.split("\tcolumn ")
        month_block = [p for p in parts if p.startswith("'Month Name'\n")][0]
        assert "isHidden" not in month_block

    def test_unrelated_col_unchanged(self):
        result = apply_sort(SAMPLE_SORT_TMDL, ORDER_COLS)
        parts = result.split("\tcolumn ")
        dept_block = [p for p in parts if p.startswith("Department\n")][0]
        assert "sortByColumn" not in dept_block
        assert "isHidden" not in dept_block

    def test_empty_order_columns_returns_unchanged(self):
        assert apply_sort(SAMPLE_SORT_TMDL, {}) == SAMPLE_SORT_TMDL

    def test_target_no_spaces_no_quotes_in_sort_ref(self):
        tmdl = (
            "table Fact\n"
            "\tcolumn Year\n"
            "\t\tdataType: int64\n"
            "\t\tlineageTag: tag-year\n"
            "\t\tsummarizeBy: none\n"
            "\t\tsourceColumn: Key_Dim_1\n"
            "\n"
            "\tcolumn 'ORDER Year'\n"
            "\t\tdataType: int64\n"
            "\t\tlineageTag: tag-order-year\n"
            "\t\tsummarizeBy: sum\n"
            "\t\tsourceColumn: Key_Dim_2\n"
            "\n"
        )
        result = apply_sort(tmdl, {"Year": "ORDER Year"})
        assert "\t\tsortByColumn: 'ORDER Year'\n" in result

    def test_multiple_sort_columns(self):
        tmdl = (
            "table Fact\n"
            "\tcolumn 'Month Name'\n"
            "\t\tdataType: string\n"
            "\t\tlineageTag: tag-month\n"
            "\t\tsummarizeBy: none\n"
            "\t\tsourceColumn: Key_Dim_1\n"
            "\n"
            "\tcolumn 'ORDER Month Name'\n"
            "\t\tdataType: int64\n"
            "\t\tlineageTag: tag-order-month\n"
            "\t\tsummarizeBy: sum\n"
            "\t\tsourceColumn: Key_Dim_2\n"
            "\n"
            "\tcolumn Quarter\n"
            "\t\tdataType: string\n"
            "\t\tlineageTag: tag-quarter\n"
            "\t\tsummarizeBy: none\n"
            "\t\tsourceColumn: Key_Dim_3\n"
            "\n"
            "\tcolumn 'ORDER Quarter'\n"
            "\t\tdataType: int64\n"
            "\t\tlineageTag: tag-order-quarter\n"
            "\t\tsummarizeBy: sum\n"
            "\t\tsourceColumn: Key_Dim_4\n"
            "\n"
        )
        result = apply_sort(tmdl, {
            "Month Name": "ORDER Month Name",
            "Quarter": "ORDER Quarter",
        })
        assert "\t\tsortByColumn: 'ORDER Month Name'\n" in result
        assert "\t\tsortByColumn: 'ORDER Quarter'\n" in result
        assert result.count("\t\tisHidden\n") == 2


class TestRunSortPipeline:
    def test_sort_by_column_written_to_file(self, tmp_path):
        tmdl_file = tmp_path / "Fact.tmdl"
        tmdl_file.write_text(SAMPLE_SORT_TMDL, encoding="utf-8")
        config = {"order_columns": ORDER_COLS}
        run_sort_pipeline(tmdl_file, config)
        assert "\t\tsortByColumn: 'ORDER Month Name'\n" in tmdl_file.read_text(encoding="utf-8")

    def test_order_col_hidden_in_file(self, tmp_path):
        tmdl_file = tmp_path / "Fact.tmdl"
        tmdl_file.write_text(SAMPLE_SORT_TMDL, encoding="utf-8")
        config = {"order_columns": ORDER_COLS}
        run_sort_pipeline(tmdl_file, config)
        assert "\t\tisHidden\n" in tmdl_file.read_text(encoding="utf-8")

    def test_empty_order_columns_file_unchanged(self, tmp_path):
        tmdl_file = tmp_path / "Fact.tmdl"
        tmdl_file.write_text(SAMPLE_SORT_TMDL, encoding="utf-8")
        run_sort_pipeline(tmdl_file, {"order_columns": {}})
        assert tmdl_file.read_text(encoding="utf-8") == SAMPLE_SORT_TMDL
