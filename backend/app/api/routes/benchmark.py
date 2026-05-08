from fastapi import APIRouter, HTTPException

from backend.app.api.routes.models import (
    BenchmarkPoint,
    BenchmarkRequest,
    BenchmarkResult,
    PreviewRequest,
    PreviewResponse,
    QueryBuilderOptions,
)
from backend.app.services.benchmark import benchmark, get_query_builder_options, get_query_preview

router = APIRouter(prefix="/benchmark", tags=["benchmark"])
DB_PATH = "datasets/wildfires.duckdb"
SOURCE_TABLE = "fires"


@router.get("/options", response_model=QueryBuilderOptions)
def get_benchmark_options():
    return QueryBuilderOptions(**get_query_builder_options(DB_PATH, SOURCE_TABLE))


@router.post("/preview", response_model=PreviewResponse)
def preview_benchmark_query(payload: PreviewRequest):
    try:
        preview = get_query_preview(
            db_path=DB_PATH,
            source_table=SOURCE_TABLE,
            query_config=payload.query_config,
            page=payload.page,
            page_size=payload.page_size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PreviewResponse(preview=preview)


@router.post("/run", response_model=BenchmarkResult)
def run_size_benchmark(payload: BenchmarkRequest):
    try:
        benchmark_response = benchmark(
            db_path=DB_PATH,
            source_table=SOURCE_TABLE,
            query_config=payload.query_config,
            sizes=payload.sizes,
            runs=payload.runs,
            warmup=payload.warmup,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    results = [BenchmarkPoint(**r) for r in benchmark_response["results"]]

    return BenchmarkResult(
        query=benchmark_response["query"],
        sizes=payload.sizes,
        runs=payload.runs,
        warmup=payload.warmup,
        results=results,
    )
