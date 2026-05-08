# DuckDB Query Benchmark

This project is a small FastAPI + DuckDB app for comparing two query configurations on the US Wildfire dataset.

The frontend lets you:
- build Query A and Query B with guided controls
- preview query results with pagination
- run benchmarks across multiple dataset sizes
- compare execution time with charts and a summary table

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```
Download the DuckDB database file from [this link](https://drive.google.com/file/d/15uZnGvRmYrgOsn1JZU2BoKv-zi2EyVab/view?usp=drive_link) and place it in the `datasets` directory:


## Run

Start the app from the project root:

```bash
python -m backend.app.main
```

Then open:

```text
http://127.0.0.1:8000
```

## Data

Original data source: https://www.kaggle.com/datasets/rtatman/188-million-us-wildfires?resource=download

Original data source is of format sqlite, but we converted it to duckdb for the purpose of this project. 

