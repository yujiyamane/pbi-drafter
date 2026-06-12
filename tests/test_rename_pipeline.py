import shutil
import pytest
from pathlib import Path

from src.rename_pipeline import rename_tmdl, rename_visual_json, rename_pipeline, rename_field_parameters

PROJECT_ROOT = Path(__file__).parent.parent

FACT_TMDL = (
    "table Fact\n"
    "\tlineageTag: 616005fd-9e09-4f2a-ad83-165711332d18\n"
    "\n"
    "\tmeasure SUM_M1 = SUM(Fact[SUM_Measure_1])\n"
    "\t\tformatString: 0\n"
    "\t\tlineageTag: 7687101d-765d-43a7-99b5-9acc8456989d\n"
    "\n"
    "\tmeasure AVG_M1 = AVERAGE(Fact[AVG_Measure_1])\n"
    "\t\tlineageTag: bc056291-5b76-4dc2-b21c-0dc25f62f741\n"
    "\n"
    "\tcolumn SUM_Measure_1\n"
    "\t\tdataType: int64\n"
    "\t\tformatString: 0\n"
    "\t\tlineageTag: c178d5a1-2e73-4e54-a478-7a8e1809c3e8\n"
    "\t\tsummarizeBy: sum\n"
    "\t\tsourceColumn: SUM_Measure_1\n"
    "\n"
    "\tcolumn Key_Dim_1\n"
    "\t\tdataType: string\n"
    "\t\tlineageTag: 5b017b4b-0714-44b5-b133-8208deeb08e1\n"
    "\t\tsummarizeBy: none\n"
    "\t\tsourceColumn: Key_Dim_1\n"
)

RENAME_MAP = {
    "SUM_Measure_1": "Total Budget",
    "SUM_Measure_2": "Headcount",
    "CNT_Measure_1": "Record ID",
    "AVG_Measure_1": "Avg Rating",
    "Key_Dim_1": "Department",
    "Key_Dim_2": "Month",
}

_MEASURE_JSON = (
    '{"field": {"Measure": {"Expression": {"SourceRef": {"Entity": "Fact"}}, '
    '"Property": "SUM_M1"}}, "queryRef": "Fact.SUM_M1", "nativeQueryRef": "SUM_M1"}'
)

_COLUMN_JSON = (
    '{"field": {"Column": {"Expression": {"SourceRef": {"Entity": "Fact"}}, '
    '"Property": "Key_Dim_1"}}, "queryRef": "Fact.Key_Dim_1", "nativeQueryRef": "Key_Dim_1"}'
)

_RIBBON_SERIES_JSON = (
    '{"field": {"Column": {"Expression": {"SourceRef": {"Entity": "Fact"}}, '
    '"Property": "Key_Dim_1"}}, "queryRef": "Fact.Key_Dim_1", '
    '"nativeQueryRef": "Key_Dim_1", "displayName": "Key_Dim_1"}'
)

_AGG_JSON = (
    '{"field": {"Aggregation": {"Expression": {"Column": {'
    '"Expression": {"SourceRef": {"Entity": "Fact"}}, "Property": "SUM_Measure_1"}}, '
    '"Function": 0}}, "queryRef": "Sum(Fact.SUM_Measure_1)", '
    '"nativeQueryRef": "Sum of SUM_Measure_1"}'
)

_AVG_AGG_JSON = (
    '{"field": {"Aggregation": {"Expression": {"Column": {'
    '"Expression": {"SourceRef": {"Entity": "Fact"}}, "Property": "AVG_Measure_1"}}, '
    '"Function": 1}}, "queryRef": "Sum(Fact.AVG_Measure_1)", '
    '"nativeQueryRef": "Average of AVG_Measure_1"}'
)

_FILTER_MEASURE_JSON = (
    '{"filterConfig": {"filters": [{"field": {"Measure": {'
    '"Expression": {"SourceRef": {"Entity": "Fact"}}, "Property": "SUM_M1"}}}]}}'
)

_FILTER_COLUMN_JSON = (
    '{"filterConfig": {"filters": [{"field": {"Column": {'
    '"Expression": {"SourceRef": {"Entity": "Fact"}}, "Property": "Key_Dim_1"}}}]}}'
)

_FILTER_AGG_JSON = (
    '{"filterConfig": {"filters": [{"field": {"Aggregation": {"Expression": {"Column": {'
    '"Expression": {"SourceRef": {"Entity": "Fact"}}, "Property": "SUM_Measure_1"}}, '
    '"Function": 0}}}]}}'
)

_DRILLTHROUGH_PAGE_JSON = (
    '{"filterConfig": {"filters": ['
    '{"field": {"Column": {"Expression": {"SourceRef": {"Entity": "Fact"}}, "Property": "Key_Dim_1"}},'
    '"filter": {"Where": [{"Condition": {"In": {"Expressions": ['
    '{"Column": {"Expression": {"SourceRef": {"Source": "f"}}, "Property": "Key_Dim_1"}}],'
    '"Values": [[{"Literal": {"Value": "\'Engineering\'"}}]]}}}]},'
    '"howCreated": "Drillthrough"},'
    '{"field": {"Column": {"Expression": {"SourceRef": {"Entity": "Fact"}}, "Property": "SUM_Measure_1"}},'
    '"howCreated": "Drillthrough"}]},'
    '"pageBinding": {"type": "Drillthrough", "parameters": ['
    '{"fieldExpr": {"Column": {"Expression": {"SourceRef": {"Entity": "Fact"}}, "Property": "Key_Dim_1"}}},'
    '{"fieldExpr": {"Column": {"Expression": {"SourceRef": {"Entity": "Fact"}}, "Property": "SUM_Measure_1"}}}]}}'
)


_DAX_BODY_TMDL = (
    "table Fact\n"
    "\tlineageTag: abc-123\n"
    "\n"
    "\tmeasure DAX_SUM_Measure_1 = SUM('Fact'[SUM_Measure_1])\n"
    "\t\tformatString: 0\n"
    "\t\tlineageTag: tag-sum1\n"
    "\n"
    "\tmeasure DAX_CNT_Measure_1 = DISTINCTCOUNT('Fact'[CNT_Measure_1])\n"
    "\t\tformatString: 0\n"
    "\t\tlineageTag: tag-cnt1\n"
    "\n"
    "\tcolumn SUM_Measure_1\n"
    "\t\tdataType: int64\n"
    "\t\tlineageTag: col-tag\n"
    "\t\tsourceColumn: SUM_Measure_1\n"
)


class TestRenameTmdlDaxBodyRefs:
    def test_sum_column_ref_updated(self):
        result = rename_tmdl(_DAX_BODY_TMDL, {"SUM_Measure_1": "Total Budget"})
        assert "SUM('Fact'[Total Budget])" in result

    def test_sum_old_ref_gone(self):
        result = rename_tmdl(_DAX_BODY_TMDL, {"SUM_Measure_1": "Total Budget"})
        assert "SUM('Fact'[SUM_Measure_1])" not in result

    def test_distinctcount_ref_updated(self):
        result = rename_tmdl(_DAX_BODY_TMDL, {"CNT_Measure_1": "Record ID"})
        assert "DISTINCTCOUNT('Fact'[Record ID])" in result

    def test_distinctcount_old_ref_gone(self):
        result = rename_tmdl(_DAX_BODY_TMDL, {"CNT_Measure_1": "Record ID"})
        assert "DISTINCTCOUNT('Fact'[CNT_Measure_1])" not in result

    def test_multiword_new_name_no_extra_quotes_in_brackets(self):
        result = rename_tmdl(_DAX_BODY_TMDL, {"SUM_Measure_1": "Total Budget"})
        assert "'Fact'[Total Budget]" in result

    def test_source_column_not_affected(self):
        result = rename_tmdl(_DAX_BODY_TMDL, {"SUM_Measure_1": "Total Budget"})
        assert "sourceColumn: SUM_Measure_1" in result

    def test_unquoted_fact_ref_unchanged(self):
        tmdl = "measure M1 = SUM(Fact[SUM_Measure_1])\n"
        result = rename_tmdl(tmdl, {"SUM_Measure_1": "Total Budget"})
        assert "SUM(Fact[SUM_Measure_1])" in result


_SELECT_DIM_TMDL = (
    "table 'Select Dimension'\n"
    "\tlineageTag: aebb6f46-61a1-4ac0-94bb-1daa401e6f6c\n"
    "\n"
    "\tpartition 'Select Dimension' = calculated\n"
    "\t\tmode: import\n"
    "\t\tsource =\n"
    "\t\t\t\t{\n"
    "\t\t\t\t    (\"Key_Dim_1\", NAMEOF('Fact'[Key_Dim_1]), 0),\n"
    "\t\t\t\t    (\"Key_Dim_2\", NAMEOF('Fact'[Key_Dim_2]), 1),\n"
    "\t\t\t\t    (\"Key_Dim_3\", NAMEOF('Fact'[Key_Dim_3]), 2),\n"
    "\t\t\t\t    (\"Key_Dim_4\", NAMEOF('Fact'[Key_Dim_4]), 3),\n"
    "\t\t\t\t    (\"Key_Dim_5\", NAMEOF('Fact'[Key_Dim_5]), 4)\n"
    "\t\t\t\t}\n"
)

_SELECT_MEASURE_TMDL = (
    "table 'Select Measure'\n"
    "\tlineageTag: 7af15d22-62c5-4efa-a44a-eb72ca1f4e1a\n"
    "\n"
    "\tpartition 'Select Measure' = calculated\n"
    "\t\tmode: import\n"
    "\t\tsource =\n"
    "\t\t\t\t{\n"
    "\t\t\t\t    (\"SUM_Measure_1\", NAMEOF('Fact'[DAX_SUM_Measure_1]), 0),\n"
    "\t\t\t\t    (\"SUM_Measure_2\", NAMEOF('Fact'[DAX_SUM_Measure_2]), 1),\n"
    "\t\t\t\t    (\"CNT_Measure_1\", NAMEOF('Fact'[DAX_CNT_Measure_1]), 2),\n"
    "\t\t\t\t    (\"CNT_Measure_2\", NAMEOF('Fact'[DAX_CNT_Measure_2]), 3)\n"
    "\t\t\t\t}\n"
)

_DIM_RENAME_MAP = {
    "Key_Dim_1": "Department",
    "Key_Dim_2": "Month Name",
    "Key_Dim_3": "City",
    "Key_Dim_4": "Level",
}

_MEASURE_RENAME_MAP = {
    "SUM_Measure_1": "Total Budget",
    "SUM_Measure_2": "Headcount",
    "CNT_Measure_1": "Record ID",
}


class TestRenameFieldParametersDimension:
    def test_active_label_renamed(self):
        result = rename_field_parameters(_SELECT_DIM_TMDL, _DIM_RENAME_MAP)
        assert '"Department"' in result

    def test_active_nameof_ref_renamed(self):
        result = rename_field_parameters(_SELECT_DIM_TMDL, _DIM_RENAME_MAP)
        assert "NAMEOF('Fact'[Department])" in result

    def test_old_label_gone(self):
        result = rename_field_parameters(_SELECT_DIM_TMDL, _DIM_RENAME_MAP)
        assert '"Key_Dim_1"' not in result

    def test_old_nameof_ref_gone(self):
        result = rename_field_parameters(_SELECT_DIM_TMDL, _DIM_RENAME_MAP)
        assert "NAMEOF('Fact'[Key_Dim_1])" not in result

    def test_multiword_label_in_output(self):
        result = rename_field_parameters(_SELECT_DIM_TMDL, _DIM_RENAME_MAP)
        assert '"Month Name"' in result

    def test_multiword_ref_in_nameof(self):
        result = rename_field_parameters(_SELECT_DIM_TMDL, _DIM_RENAME_MAP)
        assert "NAMEOF('Fact'[Month Name])" in result

    def test_unused_row_deleted(self):
        result = rename_field_parameters(_SELECT_DIM_TMDL, _DIM_RENAME_MAP)
        assert '"Key_Dim_5"' not in result
        assert "NAMEOF('Fact'[Key_Dim_5])" not in result

    def test_order_renumbered_after_deletion(self):
        result = rename_field_parameters(_SELECT_DIM_TMDL, _DIM_RENAME_MAP)
        assert "]), 0)," in result
        assert "]), 1)," in result
        assert "]), 2)," in result
        assert "]), 3)" in result
        assert "]), 4)" not in result

    def test_last_row_no_trailing_comma(self):
        result = rename_field_parameters(_SELECT_DIM_TMDL, _DIM_RENAME_MAP)
        assert '"Level", NAMEOF(\'Fact\'[Level]), 3)' in result
        assert '"Level", NAMEOF(\'Fact\'[Level]), 3),' not in result

    def test_non_last_row_has_comma(self):
        result = rename_field_parameters(_SELECT_DIM_TMDL, _DIM_RENAME_MAP)
        assert '"Department", NAMEOF(\'Fact\'[Department]), 0),' in result


class TestRenameFieldParametersMeasure:
    def test_measure_label_renamed(self):
        result = rename_field_parameters(_SELECT_MEASURE_TMDL, _MEASURE_RENAME_MAP)
        assert '"Total Budget"' in result

    def test_measure_nameof_ref_unchanged(self):
        result = rename_field_parameters(_SELECT_MEASURE_TMDL, _MEASURE_RENAME_MAP)
        assert "NAMEOF('Fact'[DAX_SUM_Measure_1])" in result

    def test_unused_measure_row_deleted(self):
        result = rename_field_parameters(_SELECT_MEASURE_TMDL, _MEASURE_RENAME_MAP)
        assert '"CNT_Measure_2"' not in result
        assert "NAMEOF('Fact'[DAX_CNT_Measure_2])" not in result

    def test_measure_order_renumbered(self):
        result = rename_field_parameters(_SELECT_MEASURE_TMDL, _MEASURE_RENAME_MAP)
        assert "]), 0)," in result
        assert "]), 1)," in result
        assert "]), 2)" in result
        assert "]), 3)" not in result


_SELECT_2ND_DIM_TMDL = (
    "table 'Select 2nd Dimension'\n"
    "\tlineageTag: bbcc7a12-9abc-4def-1234-5678901e2f3a\n"
    "\n"
    "\tpartition 'Select 2nd Dimension' = calculated\n"
    "\t\tmode: import\n"
    "\t\tsource =\n"
    "\t\t\t\t{\n"
    "\t\t\t\t    (\"Key_Dim_1\", NAMEOF('Fact'[Key_Dim_1]), 0),\n"
    "\t\t\t\t    (\"Key_Dim_2\", NAMEOF('Fact'[Key_Dim_2]), 1),\n"
    "\t\t\t\t    (\"Key_Dim_3\", NAMEOF('Fact'[Key_Dim_3]), 2),\n"
    "\t\t\t\t    (\"Key_Dim_4\", NAMEOF('Fact'[Key_Dim_4]), 3),\n"
    "\t\t\t\t    (\"Key_Dim_5\", NAMEOF('Fact'[Key_Dim_5]), 4)\n"
    "\t\t\t\t}\n"
)


class TestRenameFieldParametersSelectSecondDimension:
    def test_active_label_renamed(self):
        result = rename_field_parameters(_SELECT_2ND_DIM_TMDL, _DIM_RENAME_MAP)
        assert '"Department"' in result
        assert '"Key_Dim_1"' not in result

    def test_nameof_ref_renamed(self):
        result = rename_field_parameters(_SELECT_2ND_DIM_TMDL, _DIM_RENAME_MAP)
        assert "NAMEOF('Fact'[Department])" in result
        assert "NAMEOF('Fact'[Key_Dim_1])" not in result

    def test_unused_row_deleted(self):
        result = rename_field_parameters(_SELECT_2ND_DIM_TMDL, _DIM_RENAME_MAP)
        assert '"Key_Dim_5"' not in result
        assert "NAMEOF('Fact'[Key_Dim_5])" not in result

    def test_order_renumbered_after_deletion(self):
        result = rename_field_parameters(_SELECT_2ND_DIM_TMDL, _DIM_RENAME_MAP)
        assert "]), 3)" in result
        assert "]), 4)" not in result


class TestRenameFieldParametersEdgeCases:
    def test_no_nameof_returns_unchanged(self):
        plain_tmdl = "table Fact\n\tcolumn Key_Dim_1\n\t\tsourceColumn: Key_Dim_1\n"
        result = rename_field_parameters(plain_tmdl, _DIM_RENAME_MAP)
        assert result == plain_tmdl

    def test_mquery_source_block_not_affected(self):
        mquery_tmdl = (
            "\tpartition Fact = m\n"
            "\t\tmode: import\n"
            "\t\tsource =\n"
            "\t\t\t\t\t\tlet\n"
            "\t\t\t\t\t\t    Source = Csv.Document(File.Contents(\"data.csv\"))\n"
            "\t\t\t\t\t\tin\n"
            "\t\t\t\t\t\t    Source\n"
        )
        result = rename_field_parameters(mquery_tmdl, _DIM_RENAME_MAP)
        assert result == mquery_tmdl

    def test_lineage_tags_not_modified(self):
        result = rename_field_parameters(_SELECT_DIM_TMDL, _DIM_RENAME_MAP)
        assert "lineageTag: aebb6f46-61a1-4ac0-94bb-1daa401e6f6c" in result


@pytest.fixture
def pbip_copy(tmp_path):
    src = PROJECT_ROOT / "tests" / "fixtures" / "poc"
    shutil.copytree(src / "poc.SemanticModel", tmp_path / "poc.SemanticModel")
    shutil.copytree(src / "poc.Report", tmp_path / "poc.Report")
    return tmp_path


class TestRenameTmdlColumns:
    def test_multi_word_new_name_gets_single_quotes(self):
        result = rename_tmdl(FACT_TMDL, {"SUM_Measure_1": "Total Budget"})
        assert "\tcolumn 'Total Budget'\n" in result

    def test_single_word_new_name_no_quotes(self):
        result = rename_tmdl(FACT_TMDL, {"Key_Dim_1": "Department"})
        assert "\tcolumn Department\n" in result

    def test_source_column_not_modified(self):
        result = rename_tmdl(FACT_TMDL, {"SUM_Measure_1": "Total Budget"})
        assert "sourceColumn: SUM_Measure_1" in result

    def test_lineage_tag_not_modified(self):
        result = rename_tmdl(FACT_TMDL, {"SUM_Measure_1": "Total Budget"})
        assert "lineageTag: c178d5a1-2e73-4e54-a478-7a8e1809c3e8" in result

    def test_dax_column_ref_not_modified(self):
        result = rename_tmdl(FACT_TMDL, {"SUM_Measure_1": "Total Budget"})
        assert "SUM(Fact[SUM_Measure_1])" in result

    def test_old_declaration_removed(self):
        result = rename_tmdl(FACT_TMDL, {"SUM_Measure_1": "Total Budget"})
        assert "\tcolumn SUM_Measure_1\n" not in result


class TestRenameTmdlMeasures:
    def test_multi_word_new_name_gets_single_quotes(self):
        result = rename_tmdl(FACT_TMDL, {"SUM_M1": "Total Budget"})
        assert "\tmeasure 'Total Budget' = SUM(Fact[SUM_Measure_1])" in result

    def test_dax_expression_body_not_modified(self):
        result = rename_tmdl(FACT_TMDL, {"SUM_M1": "Total Budget"})
        assert "= SUM(Fact[SUM_Measure_1])" in result

    def test_measure_lineage_tag_not_modified(self):
        result = rename_tmdl(FACT_TMDL, {"SUM_M1": "Total Budget"})
        assert "lineageTag: 7687101d-765d-43a7-99b5-9acc8456989d" in result

    def test_unrenamed_measure_not_touched(self):
        result = rename_tmdl(FACT_TMDL, {"SUM_M1": "Total Budget"})
        assert "\tmeasure AVG_M1 = AVERAGE(Fact[AVG_Measure_1])" in result


RELATIONSHIP_TMDL = (
    "relationship c09e4ef1-4e16-bc37-7385-34c16dfb2f20\n"
    "\tfromColumn: Fact.DateKey\n"
    "\ttoColumn: Date.Date\n"
    "\n"
    "relationship b36b636d-d12c-42ee-b043-8b593ae58394\n"
    "\tfromColumn: Date.Date\n"
    "\ttoColumn: LocalDateTable_abc.Date\n"
)


class TestRenameTmdlRelationships:
    def test_from_column_renamed_multi_word(self):
        result = rename_tmdl(RELATIONSHIP_TMDL, {"DateKey": "Date Reported"})
        assert "fromColumn: Fact.'Date Reported'" in result

    def test_from_column_old_name_removed(self):
        result = rename_tmdl(RELATIONSHIP_TMDL, {"DateKey": "Date Reported"})
        assert "Fact.DateKey" not in result

    def test_to_column_renamed(self):
        tmdl = "relationship r1\n\tfromColumn: Fact.SomeCol\n\ttoColumn: Fact.DateKey\n"
        result = rename_tmdl(tmdl, {"DateKey": "Date Reported"})
        assert "toColumn: Fact.'Date Reported'" in result

    def test_unrelated_relationship_column_unchanged(self):
        result = rename_tmdl(RELATIONSHIP_TMDL, {"DateKey": "Date Reported"})
        assert "fromColumn: Date.Date" in result

    def test_single_word_rename_no_quotes(self):
        result = rename_tmdl(RELATIONSHIP_TMDL, {"DateKey": "DateReported"})
        assert "fromColumn: Fact.DateReported" in result


class TestRenameVisualJsonMeasure:
    def test_property_renamed(self):
        result = rename_visual_json(_MEASURE_JSON, {"SUM_M1": "Total Budget"})
        assert '"Property": "Total Budget"' in result

    def test_query_ref_renamed(self):
        result = rename_visual_json(_MEASURE_JSON, {"SUM_M1": "Total Budget"})
        assert '"queryRef": "Fact.Total Budget"' in result

    def test_native_query_ref_renamed(self):
        result = rename_visual_json(_MEASURE_JSON, {"SUM_M1": "Total Budget"})
        assert '"nativeQueryRef": "Total Budget"' in result

    def test_old_property_gone(self):
        result = rename_visual_json(_MEASURE_JSON, {"SUM_M1": "Total Budget"})
        assert '"Property": "SUM_M1"' not in result


class TestRenameVisualJsonColumn:
    def test_property_renamed(self):
        result = rename_visual_json(_COLUMN_JSON, {"Key_Dim_1": "Department"})
        assert '"Property": "Department"' in result

    def test_query_ref_renamed(self):
        result = rename_visual_json(_COLUMN_JSON, {"Key_Dim_1": "Department"})
        assert '"queryRef": "Fact.Department"' in result

    def test_native_query_ref_renamed(self):
        result = rename_visual_json(_COLUMN_JSON, {"Key_Dim_1": "Department"})
        assert '"nativeQueryRef": "Department"' in result


class TestRenameVisualJsonRibbonDisplayName:
    def test_display_name_renamed(self):
        result = rename_visual_json(_RIBBON_SERIES_JSON, {"Key_Dim_1": "Department"})
        assert '"displayName": "Department"' in result

    def test_old_display_name_gone(self):
        result = rename_visual_json(_RIBBON_SERIES_JSON, {"Key_Dim_1": "Department"})
        assert '"displayName": "Key_Dim_1"' not in result

    def test_property_still_renamed(self):
        result = rename_visual_json(_RIBBON_SERIES_JSON, {"Key_Dim_1": "Department"})
        assert '"Property": "Department"' in result

    def test_unrelated_display_name_unchanged(self):
        json_text = '"displayName": "Some Other Label"'
        result = rename_visual_json(json_text, {"Key_Dim_1": "Department"})
        assert '"displayName": "Some Other Label"' in result


class TestRenameVisualJsonAggregation:
    def test_column_property_renamed(self):
        result = rename_visual_json(_AGG_JSON, {"SUM_Measure_1": "Total Budget"})
        assert '"Property": "Total Budget"' in result

    def test_query_ref_sum_format(self):
        result = rename_visual_json(_AGG_JSON, {"SUM_Measure_1": "Total Budget"})
        assert '"queryRef": "Sum(Fact.Total Budget)"' in result

    def test_native_query_ref_sum_of_format(self):
        result = rename_visual_json(_AGG_JSON, {"SUM_Measure_1": "Total Budget"})
        assert '"nativeQueryRef": "Sum of Total Budget"' in result

    def test_old_sum_query_ref_gone(self):
        result = rename_visual_json(_AGG_JSON, {"SUM_Measure_1": "Total Budget"})
        assert '"queryRef": "Sum(Fact.SUM_Measure_1)"' not in result


class TestRenameVisualJsonAverageAggregation:
    def test_property_renamed(self):
        result = rename_visual_json(_AVG_AGG_JSON, {"AVG_Measure_1": "Avg Rating"})
        assert '"Property": "Avg Rating"' in result

    def test_query_ref_sum_format(self):
        result = rename_visual_json(_AVG_AGG_JSON, {"AVG_Measure_1": "Avg Rating"})
        assert '"queryRef": "Sum(Fact.Avg Rating)"' in result

    def test_native_query_ref_average_of_format(self):
        result = rename_visual_json(_AVG_AGG_JSON, {"AVG_Measure_1": "Avg Rating"})
        assert '"nativeQueryRef": "Average of Avg Rating"' in result

    def test_old_average_native_query_ref_gone(self):
        result = rename_visual_json(_AVG_AGG_JSON, {"AVG_Measure_1": "Avg Rating"})
        assert '"nativeQueryRef": "Average of AVG_Measure_1"' not in result


class TestRenameVisualJsonFilterConfig:
    def test_filter_measure_property_renamed(self):
        result = rename_visual_json(_FILTER_MEASURE_JSON, {"SUM_M1": "Total Budget"})
        assert '"Property": "Total Budget"' in result
        assert '"Property": "SUM_M1"' not in result

    def test_filter_column_property_renamed(self):
        result = rename_visual_json(_FILTER_COLUMN_JSON, {"Key_Dim_1": "Department"})
        assert '"Property": "Department"' in result

    def test_filter_aggregation_property_renamed(self):
        result = rename_visual_json(_FILTER_AGG_JSON, {"SUM_Measure_1": "Total Budget"})
        assert '"Property": "Total Budget"' in result


class TestRenamePipeline:
    def test_fact_tmdl_column_renamed(self, pbip_copy):
        rename_pipeline(str(pbip_copy), {"SUM_Measure_1": "Total Budget"})
        fact = (pbip_copy / "poc.SemanticModel" / "definition" / "tables" / "Fact.tmdl").read_text(encoding="utf-8")
        assert "column 'Total Budget'" in fact

    def test_fact_tmdl_column_renamed_single_word(self, pbip_copy):
        rename_pipeline(str(pbip_copy), {"SUM_Measure_2": "Headcount"})
        fact = (pbip_copy / "poc.SemanticModel" / "definition" / "tables" / "Fact.tmdl").read_text(encoding="utf-8")
        assert "\tcolumn Headcount\n" in fact

    def test_fact_tmdl_source_columns_preserved(self, pbip_copy):
        rename_pipeline(str(pbip_copy), RENAME_MAP)
        fact = (pbip_copy / "poc.SemanticModel" / "definition" / "tables" / "Fact.tmdl").read_text(encoding="utf-8")
        assert "sourceColumn: SUM_Measure_1" in fact
        assert "sourceColumn: SUM_Measure_2" in fact
        assert "sourceColumn: CNT_Measure_1" in fact
        assert "sourceColumn: AVG_Measure_1" in fact
        assert "sourceColumn: Key_Dim_1" in fact
        assert "sourceColumn: Key_Dim_2" in fact

    def test_kpi_visual_aggregation_ref_renamed(self, pbip_copy):
        rename_pipeline(str(pbip_copy), {"SUM_Measure_1": "Total Budget"})
        visual = (
            pbip_copy / "poc.Report" / "definition" / "pages"
            / "344ff558a8c8d0a99173" / "visuals" / "4951ab63b1dd97c311e5" / "visual.json"
        ).read_text(encoding="utf-8")
        assert '"Property": "Total Budget"' in visual
        assert '"queryRef": "Sum(Fact.Total Budget)"' in visual
        assert '"nativeQueryRef": "Sum of Total Budget"' in visual
        assert '"Property": "SUM_Measure_1"' not in visual

    def test_table_visual_aggregation_renamed(self, pbip_copy):
        rename_pipeline(str(pbip_copy), {"SUM_Measure_1": "Total Budget"})
        visual = (
            pbip_copy / "poc.Report" / "definition" / "pages"
            / "344ff558a8c8d0a99173" / "visuals" / "d4831354e5a55ffe6a1d" / "visual.json"
        ).read_text(encoding="utf-8")
        assert '"queryRef": "Sum(Fact.Total Budget)"' in visual
        assert '"nativeQueryRef": "Sum of Total Budget"' in visual

    def test_combo_chart_average_native_query_ref_renamed(self, pbip_copy):
        rename_pipeline(str(pbip_copy), {"AVG_Measure_1": "Avg Rating"})
        visual = (
            pbip_copy / "poc.Report" / "definition" / "pages"
            / "344ff558a8c8d0a99173" / "visuals" / "d4712c4968debaa7694d" / "visual.json"
        ).read_text(encoding="utf-8")
        assert '"nativeQueryRef": "Average of Avg Rating"' in visual
        assert '"nativeQueryRef": "Average of AVG_Measure_1"' not in visual

    def test_date_tables_not_modified(self, pbip_copy):
        tables_src = PROJECT_ROOT / "tests" / "fixtures" / "poc" / "poc.SemanticModel" / "definition" / "tables"
        rename_pipeline(str(pbip_copy), RENAME_MAP)
        tables_dst = pbip_copy / "poc.SemanticModel" / "definition" / "tables"
        for prefix in ("DateTableTemplate", "LocalDateTable"):
            orig = next(tables_src.glob(f"{prefix}*.tmdl")).read_text(encoding="utf-8")
            copy = next(tables_dst.glob(f"{prefix}*.tmdl")).read_text(encoding="utf-8")
            assert orig == copy

    def test_returns_fact_tmdl_in_modified_list(self, pbip_copy):
        result = rename_pipeline(str(pbip_copy), RENAME_MAP)
        assert any("Fact.tmdl" in p for p in result["tmdl"])

    def test_returns_all_three_visual_files(self, pbip_copy):
        result = rename_pipeline(str(pbip_copy), RENAME_MAP)
        assert len(result["visual"]) == 3

    def test_drillthrough_page_json_column_property_renamed(self, pbip_copy):
        rename_pipeline(str(pbip_copy), {"Key_Dim_1": "Department"})
        page = (
            pbip_copy / "poc.Report" / "definition" / "pages"
            / "drillthrough_page" / "page.json"
        ).read_text(encoding="utf-8")
        assert '"Property": "Department"' in page
        assert '"Property": "Key_Dim_1"' not in page

    def test_drillthrough_page_json_sum_property_renamed(self, pbip_copy):
        rename_pipeline(str(pbip_copy), {"SUM_Measure_1": "Total Budget"})
        page = (
            pbip_copy / "poc.Report" / "definition" / "pages"
            / "drillthrough_page" / "page.json"
        ).read_text(encoding="utf-8")
        assert '"Property": "Total Budget"' in page
        assert '"Property": "SUM_Measure_1"' not in page

    def test_returns_page_in_modified_list(self, pbip_copy):
        result = rename_pipeline(str(pbip_copy), {"Key_Dim_1": "Department"})
        assert any("page.json" in p for p in result["page"])


class TestRenamePageJsonDrillthrough:
    def test_filter_field_column_property_renamed(self):
        result = rename_visual_json(_DRILLTHROUGH_PAGE_JSON, {"Key_Dim_1": "Department"})
        assert '"Property": "Department"' in result

    def test_filter_where_expression_property_renamed(self):
        result = rename_visual_json(_DRILLTHROUGH_PAGE_JSON, {"Key_Dim_1": "Department"})
        assert _DRILLTHROUGH_PAGE_JSON.count('"Property": "Key_Dim_1"') == 3
        assert result.count('"Property": "Department"') == 3
        assert '"Property": "Key_Dim_1"' not in result

    def test_page_binding_field_expr_property_renamed(self):
        result = rename_visual_json(_DRILLTHROUGH_PAGE_JSON, {"Key_Dim_1": "Department"})
        assert '"Property": "Key_Dim_1"' not in result

    def test_sum_measure_property_renamed(self):
        result = rename_visual_json(_DRILLTHROUGH_PAGE_JSON, {"SUM_Measure_1": "Total Budget"})
        assert '"Property": "Total Budget"' in result
        assert '"Property": "SUM_Measure_1"' not in result

    def test_unrelated_property_unchanged(self):
        result = rename_visual_json(_DRILLTHROUGH_PAGE_JSON, {"Key_Dim_1": "Department"})
        assert '"Property": "SUM_Measure_1"' in result
