"""Generate sample CSV files for Dashboard Drafter examples."""

import csv
import random
from datetime import date

DEPARTMENTS = ["Engineering", "Finance", "Marketing", "Operations", "HR", "Sales"]
MONTHS = [
    ("January", 1), ("February", 2), ("March", 3), ("April", 4),
    ("May", 5), ("June", 6), ("July", 7), ("August", 8),
    ("September", 9), ("October", 10), ("November", 11), ("December", 12),
]
BUSINESS_UNITS = ["APAC", "EMEA", "Americas", "Corporate"]
REGIONS = ["Sydney", "Melbourne", "Brisbane", "Perth", "Auckland"]
CATEGORIES = ["Software", "Hardware", "Services", "Consulting", "Licensing"]


def generate_hr_data(output_path: str = "examples/sample_hr_data.csv", rows: int = 500):
    random.seed(42)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "SUM_Measure_1", "SUM_Measure_2", "AVG_Measure_1",
            "CNT_Measure_1", "DateKey", "Key_Dim_1", "Key_Dim_2",
            "Other_Field_1",
        ])
        for i in range(rows):
            dept = random.choice(DEPARTMENTS)
            month_name, month_num = random.choice(MONTHS)
            year = random.choice([2024, 2025])
            report_date = date(year, month_num, random.randint(1, 28))
            writer.writerow([
                random.randint(50000, 500000),
                random.randint(5, 80),
                round(random.uniform(1.0, 5.0), 1),
                i + 1001,
                report_date.isoformat(),
                dept,
                month_name,
                random.choice(["", "", "", "High performer", "On leave"]),
            ])
    print(f"Generated {rows} rows -> {output_path}")


def generate_finance_data(output_path: str = "examples/sample_finance_data.csv", rows: int = 500):
    random.seed(99)
    quarters = [("Q1", 1), ("Q2", 2), ("Q3", 3), ("Q4", 4)]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "SUM_Measure_1", "SUM_Measure_2", "SUM_Measure_3", "SUM_Measure_4",
            "AVG_Measure_1", "CNT_Measure_1", "CNT_Measure_2",
            "DateKey", "Key_Dim_1", "Key_Dim_2", "Key_Dim_3", "Key_Dim_4",
            "Other_Field_1",
        ])
        for i in range(rows):
            revenue = random.randint(10000, 1_000_000)
            cost = int(revenue * random.uniform(0.4, 0.85))
            profit = revenue - cost
            budget = int(revenue * random.uniform(0.9, 1.2))
            margin = round(profit / revenue * 100, 1)
            quarter_name, quarter_num = random.choice(quarters)
            year = random.choice([2024, 2025])
            month = (quarter_num - 1) * 3 + random.randint(1, 3)
            tx_date = date(year, month, random.randint(1, 28))
            writer.writerow([
                revenue, cost, profit, budget, margin,
                i + 10001,
                random.randint(1, 4),
                tx_date.isoformat(),
                random.choice(BUSINESS_UNITS),
                random.choice(REGIONS),
                quarter_name,
                random.choice(CATEGORIES),
                random.choice(["", "", "", "Approved", "Pending review"]),
            ])
    print(f"Generated {rows} rows -> {output_path}")


if __name__ == "__main__":
    generate_hr_data()
    generate_finance_data()
    print("Sample data generation complete.")
