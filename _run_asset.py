import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))

from src.config_parser import parse_config
from src.factory import run_factory
from pathlib import Path

config_text = r'''/*FACTORY
TITLE: HR Dashboard
THEME(1:nsw-blue): 1
DB(1:Oracle 2:PostgreSQL 3:Snowflake 4:CSV 5:Excel): 4
SOURCE: C:\Users\Admin\Documents\Life\projects\pbi-dashboard-factory\phase1_dummy_data.csv

1.CNT(max5): ①employee_id AS "Record ID" ②③④⑤
2.SUM(max10): ①budget AS "Total Budget"($#,0.00) ②headcount AS "Headcount"(#) ③hours_worked AS "Hours Worked"(#.0) ④⑤⑥⑦⑧⑨⑩
3.AVG(max5): ①rating AS "Avg Rating"(#.0) ②③④⑤
4.DATE: report_date AS "Date Reported"
5.KEY(max10): ①department AS "Department" ②office_location AS "Office Location" ③employment_type AS "Employment Type" ④grade AS "Grade" ⑤⑥⑦⑧⑨⑩
6.OTHER: full_name AS "Full Name", email AS "Email", notes AS "Notes"
*/'''

base = Path(__file__).parent
config = parse_config(config_text)
out = run_factory(base / "template", base / "output", config)
print(f"Generated: {out}")
