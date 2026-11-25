# TradeSight Export Analytics — Checkpoint 2

## Purpose
A repeatable Python + SQLite baseline pipeline for the currently available `da_b2b_orders.csv` dataset.

## Project structure
- `data/da_b2b_orders.csv` — supplied source data
- `scripts/run_pipeline.py` — repeatable cleaning, validation, KPI and summary pipeline
- `sql/baseline_queries.sql` — SQL queries for baseline metrics and grouped analysis
- `outputs/` — generated metrics, quality report, summaries and SQLite database

## Requirements
- Python 3.9+
- pandas

Install:
```bash
python -m pip install pandas
```

## Run the pipeline
From this project folder:
```bash
python scripts/run_pipeline.py
```
The script regenerates the files in `outputs/` and creates `outputs/tradesight.db`.

## Baseline metrics included
- Total orders and total order value (INR)
- Average order value
- Total quantity
- Average delivery days
- On-time delivery rate
- Return quantity and return-to-quantity rate
- Repeat-buyer order rate
- Unique buyers, sellers and categories

## SQL
Open `outputs/tradesight.db` with DB Browser for SQLite and run statements from `sql/baseline_queries.sql`.

## Version control with Git
Initialize and commit the project:
```bash
git init
git add .
git commit -m "Add TradeSight baseline data pipeline"
```
Create a new repository on GitHub named `tradesight-export-analytics`, then connect and push:
```bash
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/tradesight-export-analytics.git
git push -u origin main
```
Replace `YOUR-USERNAME` with your actual GitHub username. Do not submit this placeholder URL. Submit the real repository URL after pushing.

## Data scope and limitations
Only `da_b2b_orders.csv` was available for this checkpoint. The product catalogue and customer profiles files were not downloadable, so no unsupported joins or assumptions have been made. The available orders file does not contain country, transaction currency, exchange rates, compliance status, costs or profit fields. Therefore, 12-country analysis, FX impact, compliance exceptions and client profitability are not yet calculable from this file alone. These requirements remain pending until the missing data is obtained or the project owner supplies equivalent verified fields.

## Reproducibility note
The pipeline retains all input rows, converts date/numeric columns, writes a data-quality report, produces baseline metrics and partner/category summaries, and loads tables into SQLite. Data-quality findings are reported rather than silently deleting rows.
