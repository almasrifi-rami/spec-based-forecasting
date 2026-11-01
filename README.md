# Spec-Based Procurement Forecasting (`spec-based-forecasting`)

An end-to-end Analytics Engineering & Applied ML pipeline that solves a classic B2B supply chain problem: **why naive SKU-level moving averages fail during stockouts, product substitutions, and new SKU launches**.

Instead of forecasting each SKU in isolation, this project models **product specifications** (`material`, `size`, `color`, `weight_grams`, and normalized `order_uom`) alongside **B2B customer segment & concentration dynamics** inside **dbt** and **DuckDB** to capture cross-SKU demand pooling and substitution before generating actionable procurement replenishment proposals.

## Architecture & Tech Stack (Local-First OLAP)

* **Warehouse Engine:** [DuckDB](https://duckdb.org/) (`data/warehouse.duckdb` — local columnar OLAP engine, portable to Snowflake/Databricks)
* **Transformation & Data Quality:** [dbt Core](https://docs.getdbt.com/) (`dbt-duckdb`)
* **Environment & Package Management:** [uv](https://github.com/astral-sh/uv) (Python 3.12)
* **Forecasting Engine (Milestone 4):** Python (`LightGBM` / `mlforecast`) vs. 3-Month Moving Average Baseline

## Quickstart: Raw ERP Ingestion & dbt Setup

1. **Create the virtual environment and install locked dependencies:**

```bash
uv sync
```

2. Create the virtual environment and install locked dependencies

`uv sync`

3. Generate the 5 raw ERP tables in data/warehouse.duckdb (raw_erp schema):

`uv run python scripts/generate_erp_data.py`

4. Run dbt models and source data quality tests:

```bash
cd dbt_spec_forecast
uv run dbt debug
uv run dbt build
```
