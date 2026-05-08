import re
import time
import uuid
from math import ceil
from statistics import median

import duckdb

from backend.app.api.routes.models import QueryConfig


COLUMN_OPTIONS = [
    {"value": "FIRE_YEAR", "label": "Fire Year"},
    {"value": "STATE", "label": "State"},
    {"value": "FIRE_SIZE", "label": "Fire Size"},
    {"value": "STAT_CAUSE_DESCR", "label": "Cause Description"},
]

GROUP_BY_OPTIONS = [
    {"value": "FIRE_YEAR", "label": "Fire Year"},
    {"value": "STATE", "label": "State"},
    {"value": "STAT_CAUSE_DESCR", "label": "Cause Description"},
]

AGGREGATION_OPTIONS = [
    {"value": "none", "label": "No aggregation"},
    {"value": "count", "label": "Count rows"},
    {"value": "avg_fire_size", "label": "Average fire size"},
]

ALLOWED_COLUMNS = {item["value"] for item in COLUMN_OPTIONS}
ALLOWED_GROUP_BY = {item["value"] for item in GROUP_BY_OPTIONS}
ALLOWED_AGGREGATIONS = {item["value"] for item in AGGREGATION_OPTIONS}


def run_query_once(con, query: str):
    cursor = con.execute(query)
    columns = [column[0] for column in (cursor.description or [])]
    return columns, cursor.fetchall()


def unique_in_order(values: list[str]) -> list[str]:
    seen = set()
    ordered = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def validate_query_config(config: QueryConfig):
    invalid_columns = set(config.selected_columns) - ALLOWED_COLUMNS
    if invalid_columns:
        raise ValueError(f"invalid selected columns: {sorted(invalid_columns)}")

    invalid_group_by = set(config.group_by) - ALLOWED_GROUP_BY
    if invalid_group_by:
        raise ValueError(f"invalid group by columns: {sorted(invalid_group_by)}")

    if config.aggregation not in ALLOWED_AGGREGATIONS:
        raise ValueError("invalid aggregation")

    if config.aggregation == "none" and config.group_by:
        raise ValueError("group by requires an aggregation")


def build_query(config: QueryConfig, table_name: str) -> str:
    validate_query_config(config)

    selected_columns = unique_in_order(config.selected_columns)
    group_by_columns = unique_in_order(config.group_by)
    filters = []

    if config.state_filter_enabled:
        state_value = config.state_filter_value.replace("'", "''")
        filters.append(f"STATE = '{state_value}'")

    if config.year_filter_enabled:
        filters.append(f"FIRE_YEAR = {int(config.year_filter_value)}")

    if config.aggregation == "none":
        select_parts = ["*"] if config.select_all or not selected_columns else selected_columns
    else:
        aggregate_sql = {
            "count": "COUNT(*) AS ROW_COUNT",
            "avg_fire_size": "AVG(FIRE_SIZE) AS AVG_FIRE_SIZE",
        }[config.aggregation]
        select_parts = [*group_by_columns, aggregate_sql]

    query_parts = [
        f"SELECT {', '.join(select_parts)}",
        f"FROM {table_name}",
    ]

    if filters:
        query_parts.append(f"WHERE {' AND '.join(filters)}")

    if config.aggregation != "none" and group_by_columns:
        query_parts.append(f"GROUP BY {', '.join(group_by_columns)}")

    return "\n".join(query_parts)


def get_query_builder_options(db_path: str, source_table: str):
    con = duckdb.connect(db_path)
    try:
        states = [
            row[0]
            for row in con.execute(
                f"SELECT DISTINCT STATE FROM {source_table} WHERE STATE IS NOT NULL ORDER BY STATE"
            ).fetchall()
        ]
        years = [
            row[0]
            for row in con.execute(
                f"SELECT DISTINCT FIRE_YEAR FROM {source_table} WHERE FIRE_YEAR IS NOT NULL ORDER BY FIRE_YEAR"
            ).fetchall()
        ]
        return {
            "column_options": COLUMN_OPTIONS,
            "group_by_options": GROUP_BY_OPTIONS,
            "aggregation_options": AGGREGATION_OPTIONS,
            "state_options": states,
            "year_options": years,
        }
    finally:
        con.close()


def benchmark_query(
    con,
    query: str,
    runs: int = 5,
    warmup: int = 1,
):
    for _ in range(warmup):
        run_query_once(con, query)

    times = []
    for _ in range(runs):
        start = time.perf_counter()
        run_query_once(con, query)
        end = time.perf_counter()
        times.append(end - start)

    return {
        "query": query,
        "runs": runs,
        "warmup": warmup,
        "avg_time": sum(times) / len(times),
        "min_time": min(times),
        "max_time": max(times),
        "median_time": median(times),
        "all_times": times,
    }


def rewrite_query_for_table(query: str, source_table: str, target_table: str) -> str:
    pattern = rf"\b{source_table}\b"
    return re.sub(pattern, target_table, query)


def preview_query(
    con,
    query: str,
    page: int = 1,
    page_size: int = 10,
):
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    offset = (page - 1) * page_size
    preview_rows_sql = (
        f"SELECT * FROM ({query}) AS preview_query LIMIT {page_size} OFFSET {offset}"
    )
    preview_count_sql = f"SELECT COUNT(*) FROM ({query}) AS preview_query_count"
    columns, rows = run_query_once(con, preview_rows_sql)
    row_count = con.execute(preview_count_sql).fetchone()[0]
    total_pages = max(1, ceil(row_count / page_size)) if row_count else 1
    return {
        "query": query,
        "columns": columns,
        "rows": [list(row) for row in rows],
        "row_count": row_count,
        "truncated": page < total_pages,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def get_query_preview(
    db_path: str,
    source_table: str,
    query_config: QueryConfig,
    page: int = 1,
    page_size: int = 10,
):
    con = duckdb.connect(db_path)
    try:
        query = build_query(query_config, source_table)
        return preview_query(con=con, query=query, page=page, page_size=page_size)
    finally:
        con.close()


def create_subset_table(con, source_table: str, subset_table: str, size: int):
    con.execute(f"DROP TABLE IF EXISTS {subset_table}")
    con.execute(f"""
        CREATE TABLE {subset_table} AS
        SELECT *
        FROM {source_table}
        LIMIT {size}
    """)

def benchmark(
    db_path: str,
    source_table: str,
    query_config: QueryConfig,
    sizes: list[int],
    runs: int = 5,
    warmup: int = 1,
):
    con = duckdb.connect(db_path)
    results = []

    request_id = uuid.uuid4().hex[:8]

    try:
        query = build_query(query_config, source_table)

        for size in sizes:
            subset_table = f"{source_table}_{size}_{request_id}"

            create_subset_table(
                con=con,
                source_table=source_table,
                subset_table=subset_table,
                size=size
            )

            benchmark_sql = rewrite_query_for_table(query, source_table, subset_table)

            benchmark_result = benchmark_query(
                con=con,
                query=benchmark_sql,
                runs=runs,
                warmup=warmup
            )

            results.append({
                "size": size,
                "table": subset_table,
                "query": benchmark_sql,
                **benchmark_result
            })

        return {
            "query": query,
            "results": results,
        }
    finally:
        for size in sizes:
            subset_table = f"{source_table}_{size}_{request_id}"
            con.execute(f"DROP TABLE IF EXISTS {subset_table}")
        con.close()

