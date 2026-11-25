#!/usr/bin/env python3
"""
TradeSight Export Analytics - repeatable baseline pipeline.
Input: data/da_b2b_orders.csv
Outputs: cleaned CSV, data-quality report, baseline KPIs, category and partner summaries,
and a SQLite database.
Run from the project root: python scripts/run_pipeline.py
"""
from pathlib import Path
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "da_b2b_orders.csv"
OUT = ROOT / "outputs"
DB = OUT / "tradesight.db"

REQUIRED = [
    "order_id", "buyer_id", "seller_id", "category", "order_date",
    "quantity_units", "unit_price_inr", "total_value_inr", "payment_terms",
    "delivery_days", "on_time_delivery", "return_qty", "repeat_buyer"
]

def main():
    OUT.mkdir(exist_ok=True)
    if not DATA.exists():
        raise FileNotFoundError(f"Input file not found: {DATA}")

    raw = pd.read_csv(DATA)
    missing_columns = sorted(set(REQUIRED) - set(raw.columns))
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    df = raw.copy()
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    numeric = ["quantity_units", "unit_price_inr", "total_value_inr",
               "delivery_days", "on_time_delivery", "return_qty", "repeat_buyer"]
    for col in numeric:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Keep all rows for traceability; report invalid fields rather than silently dropping rows.
    duplicate_rows = int(df.duplicated().sum())
    duplicate_order_ids = int(df["order_id"].duplicated().sum())
    missing_cells = int(df.isna().sum().sum())
    invalid_dates = int(df["order_date"].isna().sum())
    invalid_on_time = int((~df["on_time_delivery"].isin([0, 1])).sum())
    return_gt_quantity = int((df["return_qty"] > df["quantity_units"]).sum())
    negative_values = int((df[["quantity_units", "unit_price_inr", "total_value_inr",
                               "delivery_days", "return_qty"]] < 0).sum().sum())

    df.to_csv(OUT / "cleaned_orders.csv", index=False, date_format="%Y-%m-%d")

    total_orders = int(len(df))
    total_value = float(df["total_value_inr"].sum())
    avg_order_value = float(df["total_value_inr"].mean())
    avg_delivery = float(df["delivery_days"].mean())
    on_time_pct = float(df["on_time_delivery"].mean() * 100)
    total_units = int(df["quantity_units"].sum())
    total_returns = int(df["return_qty"].sum())
    return_rate_pct = float(total_returns / total_units * 100) if total_units else 0.0
    repeat_order_pct = float(df["repeat_buyer"].mean() * 100)
    buyers = int(df["buyer_id"].nunique())
    sellers = int(df["seller_id"].nunique())
    categories = int(df["category"].nunique())
    date_min = df["order_date"].min()
    date_max = df["order_date"].max()

    metrics = [
        ("Total orders", total_orders, "orders"),
        ("Total order value", round(total_value, 2), "INR"),
        ("Average order value", round(avg_order_value, 2), "INR/order"),
        ("Total quantity", total_units, "units"),
        ("Average delivery days", round(avg_delivery, 2), "days"),
        ("On-time delivery rate", round(on_time_pct, 2), "% of order rows"),
        ("Return quantity", total_returns, "units"),
        ("Return-to-quantity rate", round(return_rate_pct, 2), "% of units"),
        ("Repeat-buyer order rate", round(repeat_order_pct, 2), "% of order rows"),
        ("Unique buyers", buyers, "buyers"),
        ("Unique sellers", sellers, "sellers"),
        ("Product categories", categories, "categories"),
    ]
    pd.DataFrame(metrics, columns=["metric", "value", "unit"]).to_csv(OUT / "baseline_metrics.csv", index=False)

    category = (df.groupby("category", dropna=False)
                  .agg(orders=("order_id", "count"),
                       total_value_inr=("total_value_inr", "sum"),
                       avg_delivery_days=("delivery_days", "mean"),
                       on_time_rate_pct=("on_time_delivery", lambda x: x.mean()*100),
                       return_qty=("return_qty", "sum"))
                  .reset_index()
                  .sort_values("total_value_inr", ascending=False))
    category.to_csv(OUT / "category_summary.csv", index=False)

    seller = (df.groupby("seller_id", dropna=False)
                .agg(orders=("order_id", "count"),
                     total_value_inr=("total_value_inr", "sum"),
                     avg_delivery_days=("delivery_days", "mean"))
                .reset_index()
                .sort_values("total_value_inr", ascending=False))
    seller.to_csv(OUT / "seller_summary.csv", index=False)

    buyer = (df.groupby("buyer_id", dropna=False)
               .agg(orders=("order_id", "count"),
                    total_value_inr=("total_value_inr", "sum"),
                    repeat_buyer_order_rate_pct=("repeat_buyer", lambda x: x.mean()*100))
               .reset_index()
               .sort_values("total_value_inr", ascending=False))
    buyer.to_csv(OUT / "buyer_summary.csv", index=False)

    quality = [
        ("Rows", total_orders, "Observed row count"),
        ("Columns", len(df.columns), "Observed column count"),
        ("Missing cells", missing_cells, "Across all fields after type conversion"),
        ("Exact duplicate rows", duplicate_rows, "Exact row duplicates"),
        ("Duplicate order IDs", duplicate_order_ids, "Order ID uniqueness check"),
        ("Invalid/unparsed order dates", invalid_dates, "Could not parse order_date"),
        ("Invalid on_time_delivery values", invalid_on_time, "Expected 0 or 1"),
        ("Rows where return_qty > quantity_units", return_gt_quantity, "Requires source/business validation"),
        ("Negative numeric values", negative_values, "Across selected quantity/value/day fields"),
        ("Date start", str(date_min.date()) if pd.notna(date_min) else "N/A", "Earliest parsed order date"),
        ("Date end", str(date_max.date()) if pd.notna(date_max) else "N/A", "Latest parsed order date"),
    ]
    pd.DataFrame(quality, columns=["check", "result", "notes"]).to_csv(OUT / "data_quality_report.csv", index=False)

    # Load repeatable outputs into SQLite.
    with sqlite3.connect(DB) as conn:
        df.to_sql("orders", conn, if_exists="replace", index=False)
        pd.DataFrame(metrics, columns=["metric", "value", "unit"]).to_sql(
            "baseline_metrics", conn, if_exists="replace", index=False)
        category.to_sql("category_summary", conn, if_exists="replace", index=False)
        seller.to_sql("seller_summary", conn, if_exists="replace", index=False)
        buyer.to_sql("buyer_summary", conn, if_exists="replace", index=False)

    print(f"Pipeline completed. {total_orders} orders processed.")
    print(f"Outputs saved in: {OUT}")

if __name__ == "__main__":
    main()
