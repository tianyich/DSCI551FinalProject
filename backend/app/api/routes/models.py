from typing import Any, List, Literal

from pydantic import BaseModel, Field


class OptionItem(BaseModel):
    value: str
    label: str


class QueryConfig(BaseModel):
    select_all: bool = False
    selected_columns: List[str] = Field(default_factory=list)
    state_filter_enabled: bool = False
    state_filter_value: str = "CA"
    year_filter_enabled: bool = False
    year_filter_value: int = 2015
    aggregation: Literal["none", "count", "avg_fire_size"] = "none"
    group_by: List[str] = Field(default_factory=list)


class QueryBuilderOptions(BaseModel):
    column_options: List[OptionItem]
    group_by_options: List[OptionItem]
    aggregation_options: List[OptionItem]
    state_options: List[str]
    year_options: List[int]


class BenchmarkRequest(BaseModel):
    query_config: QueryConfig
    sizes: List[int]
    runs: int = 5
    warmup: int = 1


class PreviewRequest(BaseModel):
    query_config: QueryConfig
    page: int = 1
    page_size: int = 10


class BenchmarkPoint(BaseModel):
    size: int
    table: str
    query: str
    avg_time: float
    min_time: float
    max_time: float
    median_time: float
    all_times: List[float]


class QueryPreview(BaseModel):
    query: str
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    truncated: bool
    page: int
    page_size: int
    total_pages: int


class BenchmarkResult(BaseModel):
    query: str
    sizes: List[int]
    runs: int
    warmup: int
    results: List[BenchmarkPoint]


class PreviewResponse(BaseModel):
    preview: QueryPreview