# backend/main.py
from datetime import datetime, timezone, date
import logging
import os
import decimal

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from google.cloud import bigquery
from dotenv import load_dotenv

from backend import load_classroom_to_bq
from backend import ingest_submissions
from backend import ingest_enrollments
from backend import dashboard_refresh

# ---- load env + basic logging ----
load_dotenv()

logger = logging.getLogger("cloudreign")
logging.basicConfig(level=logging.INFO)

PROJECT_ID = os.getenv("PROJECT_ID")
DATASET_ID = os.getenv("DATASET_ID", "workspace_analytics")
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")

app = FastAPI()


# --------- MODELS ---------
class SyncRequest(BaseModel):
    app: str


class QueryCheckpointRequest(BaseModel):
    app: str = "classroom"
    limit: int = 50  # how many rows from dashboard_temp


# --------- HELPERS ---------
def run_step(name: str, fn):
    """
    Run a pipeline step, catch errors, and return a structured result.
    """
    try:
        rows = fn()
        logger.info(f"[STEP OK] {name} rows={rows}")
        return {"ok": True, "rows": rows, "error": None}
    except Exception as e:
        logger.exception(f"[STEP ERROR] {name} failed")
        return {"ok": False, "rows": 0, "error": str(e)}


def row_to_dict(row: bigquery.table.Row) -> dict:
    """
    Convert a BigQuery Row to a JSON-serializable dict.
    Handles date/datetime and Decimal.
    """
    out = {}
    for k, v in row.items():
        if isinstance(v, (datetime, date)):
            out[k] = v.isoformat()
        elif isinstance(v, decimal.Decimal):
            out[k] = float(v)
        else:
            out[k] = v
    return out


# --------- ROUTES ---------
@app.get("/")
def root():
    return {"message": "Backend is running", "service": "CloudReign backend"}


@app.post("/sync/classroom/courses")
def sync_classroom_courses():
    result = run_step("classroom_courses", load_classroom_to_bq.run)
    status_code = 200 if result["ok"] else 500
    return JSONResponse(
        {
            "status": "ok" if result["ok"] else "error",
            "task": "classroom_courses",
            "rows_loaded": result["rows"],
            "error": result["error"],
        },
        status_code=status_code,
    )


@app.post("/sync/classroom/enrollments")
def sync_classroom_enrollments():
    result = run_step("classroom_enrollments", ingest_enrollments.run)
    status_code = 200 if result["ok"] else 500
    return JSONResponse(
        {
            "status": "ok" if result["ok"] else "error",
            "task": "classroom_enrollments",
            "rows_loaded": result["rows"],
            "error": result["error"],
        },
        status_code=status_code,
    )


@app.post("/sync/classroom/submissions")
def sync_classroom_submissions():
    result = run_step("classroom_submissions", ingest_submissions.run)
    status_code = 200 if result["ok"] else 500
    return JSONResponse(
        {
            "status": "ok" if result["ok"] else "error",
            "task": "classroom_submissions",
            "rows_loaded": result["rows"],
            "error": result["error"],
        },
        status_code=status_code,
    )


@app.post("/sync/classroom/dashboard")
def sync_classroom_dashboard():
    result = run_step("dashboard_temp", dashboard_refresh.run)
    status_code = 200 if result["ok"] else 500
    return JSONResponse(
        {
            "status": "ok" if result["ok"] else "error",
            "task": "dashboard_temp",
            "rows_loaded": result["rows"],
            "error": result["error"],
        },
        status_code=status_code,
    )


@app.post("/sync/classroom/all")
def sync_classroom_all():
    started_at = datetime.now(timezone.utc)

    steps = {
        "courses": run_step("classroom_courses", load_classroom_to_bq.run),
        "enrollments": run_step("classroom_enrollments", ingest_enrollments.run),
        "submissions": run_step("classroom_submissions", ingest_submissions.run),
        "dashboard_temp": run_step("dashboard_temp", dashboard_refresh.run),
    }

    finished_at = datetime.now(timezone.utc)
    duration_ms = (finished_at - started_at).total_seconds() * 1000.0

    all_ok = all(s["ok"] for s in steps.values())

    logger.info(
        f"[SYNC ALL] app=classroom ok={all_ok} "
        f"started_at={started_at.isoformat()} finished_at={finished_at.isoformat()} "
        f"duration_ms={duration_ms:.2f} steps={steps}"
    )

    status_code = 200 if all_ok else 500

    return JSONResponse(
        {
            "status": "ok" if all_ok else "error",
            "app": "classroom",
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_ms": duration_ms,
            "steps": steps,
        },
        status_code=status_code,
    )


# --------- WEEK 2 QUERY CHECKPOINT ---------
@app.post("/sync/app")
def sync_app(body: SyncRequest):
    """
    Generic sync entrypoint (for now only app='classroom').
    """
    if body.app != "classroom":
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": f"Unsupported app: {body.app}"},
        )

    started_at = datetime.now(timezone.utc)

    steps = {
        "courses": run_step("classroom_courses", load_classroom_to_bq.run),
        "enrollments": run_step("classroom_enrollments", ingest_enrollments.run),
        "submissions": run_step("classroom_submissions", ingest_submissions.run),
        "dashboard_temp": run_step("dashboard_temp", dashboard_refresh.run),
    }

    finished_at = datetime.now(timezone.utc)
    duration_ms = (finished_at - started_at).total_seconds() * 1000.0
    all_ok = all(s["ok"] for s in steps.values())

    logger.info(
        f"[SYNC APP] app={body.app} ok={all_ok} "
        f"started_at={started_at.isoformat()} finished_at={finished_at.isoformat()} "
        f"duration_ms={duration_ms:.2f} steps={steps}"
    )

    status_code = 200 if all_ok else 500

    return JSONResponse(
        {
            "status": "ok" if all_ok else "error",
            "app": body.app,
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_ms": duration_ms,
            "steps": steps,
        },
        status_code=status_code,
    )


@app.post("/query/checkpoint")
def query_checkpoint(body: QueryCheckpointRequest):
    """
    Week 2 'query checkpoint':
    Simple read from dashboard_temp so you can test backend -> BigQuery -> JSON.
    """
    if body.app != "classroom":
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": f"Unsupported app: {body.app}"},
        )

    client = bigquery.Client.from_service_account_json(
        SERVICE_ACCOUNT_FILE,
        project=PROJECT_ID,
    )

    sql = f"""
    SELECT
      app,
      metric_date,
      course_id,
      course_name,
      section,
      primary_teacher_email,
      total_students,
      total_submissions,
      turned_in_submissions,
      returned_submissions,
      late_submissions,
      avg_grade,
      max_grade,
      ingestion_time
    FROM `{PROJECT_ID}.{DATASET_ID}.dashboard_temp`
    WHERE app = @app
    ORDER BY metric_date DESC
    LIMIT @limit
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("app", "STRING", body.app),
            bigquery.ScalarQueryParameter("limit", "INT64", body.limit),
        ]
    )

    query_job = client.query(sql, job_config=job_config)
    rows = list(query_job.result())

    # convert to JSON-serializable dicts
    result = [row_to_dict(row) for row in rows]

    return JSONResponse(
        {
            "status": "ok",
            "app": body.app,
            "row_count": len(result),
            "data": result,
        }
    )
