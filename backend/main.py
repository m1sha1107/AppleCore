# backend/main.py
from datetime import datetime, timezone, date
import logging
import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from google.cloud import bigquery
from dotenv import load_dotenv

from backend import load_classroom_to_bq
from backend import ingest_submissions
from backend import ingest_enrollments
from backend import dashboard_refresh
from backend.gemini_client import generate_text, generate_sql
from backend import gemini_client

from fastapi.middleware.cors import CORSMiddleware



# ---- load env + basic logging ----
load_dotenv()

logger = logging.getLogger("cloudreign")
logging.basicConfig(level=logging.INFO)

PROJECT_ID = os.getenv("PROJECT_ID")
DATASET_ID = os.getenv("DATASET_ID", "workspace_analytics")
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")

app = FastAPI()

# ---------- CORS (required for frontend) ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # for dev only, ok now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------- MODELS ---------
class SyncRequest(BaseModel):
    app: str


class QueryCheckpointRequest(BaseModel):
    app: str = "classroom"
    limit: int = 50  # rows from dashboard_temp


class GeminiTestRequest(BaseModel):
    prompt: str


class QueryRunRequest(BaseModel):
    app: str = "classroom"
    question: str
    max_rows: int = 100

class NLQueryRequest(BaseModel):
    app: str = "classroom"
    question: str
    max_rows: int = 100

class CourseTimeseriesRequest(BaseModel):
    app: str = "classroom"
    course_id: str 
    days: int = 30

class CourseDetailRequest(BaseModel):
    app: str = "classroom"
    course_id: str
    days: int = 30  # window for rollup metrics


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
    
def rows_to_json_safe(rows):
    """
    Convert BigQuery Row objects into JSON-serializable dicts.
    """
    out = []
    for row in rows:
        record = {}
        for k, v in dict(row).items():
            if isinstance(v, (datetime, date)):
                record[k] = v.isoformat()
            else:
                record[k] = v
        out.append(record)
    return out


def row_to_serializable(row: bigquery.table.Row) -> dict:
    """
    Convert a BigQuery Row into a JSON-serializable dict.
    Handles date / datetime / timestamp.
    """
    out = {}
    for k, v in row.items():
        if isinstance(v, (datetime, date)):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


def get_bq_client() -> bigquery.Client:
    """
    Use the same service account JSON file you use for ingest.
    """
    return bigquery.Client.from_service_account_json(
        SERVICE_ACCOUNT_FILE,
        project=PROJECT_ID,
    )


# --------- ROUTES: HEALTH ---------
@app.get("/")
def root():
    return {"message": "Backend is running", "service": "CloudReign backend"}


# --------- ROUTES: SYNC (Week 2) ---------
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


# --------- QUERY CHECKPOINT (Week 2) ---------
@app.post("/query/checkpoint")
def query_checkpoint(body: QueryCheckpointRequest):
    """
    Simple read from dashboard_temp so you can test backend -> BigQuery -> JSON.
    """
    if body.app != "classroom":
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": f"Unsupported app: {body.app}"},
        )

    client = get_bq_client()

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

    result = [row_to_serializable(r) for r in rows]

    return JSONResponse(
        {
            "status": "ok",
            "app": body.app,
            "row_count": len(result),
            "data": result,
        }
    )


# --------- GEMINI TEST (Week 3 sanity check) ---------
@app.post("/gemini/test")
def gemini_test(body: GeminiTestRequest):
    """
    Quick check that Gemini API + key are working.
    """
    try:
        answer = generate_text(body.prompt)
        return JSONResponse({"status": "ok", "answer": answer})
    except Exception as e:
        logger.exception("[GEMINI TEST ERROR]")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


# --------- NL QUERY -> SQL -> BigQuery (Week 3 core) ---------
@app.post("/query/run")
def query_run(body: QueryRunRequest):
    """
    Week 3:
      - Take a natural language question
      - Ask Gemini to generate a BigQuery SQL query (for classroom dashboard)
      - Run SQL
      - Return rows + SQL text
    """
    if body.app != "classroom":
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": f"Unsupported app: {body.app}"},
        )

    # 1) Build prompt for Gemini
    #    You can refine this prompt later.
    prompt = f"""
You are an expert data analyst. Generate a valid BigQuery SQL query for the
`{PROJECT_ID}.{DATASET_ID}.dashboard_temp` table.

The schema of dashboard_temp is:

- app STRING
- metric_date DATE
- course_id STRING
- course_name STRING
- section STRING
- primary_teacher_email STRING
- total_students INT64
- total_submissions INT64
- turned_in_submissions INT64
- returned_submissions INT64
- late_submissions INT64
- avg_grade BIGNUMERIC
- max_grade FLOAT64
- ingestion_time TIMESTAMP

Rules:
- Only query from `{PROJECT_ID}.{DATASET_ID}.dashboard_temp`.
- Always filter `app = 'classroom'`.
- Return at most {body.max_rows} rows using LIMIT.
- Use standard SQL, no legacy syntax.
- Wrap ONLY the SQL in a ```sql ... ``` block.

User question:
\"\"\"{body.question}\"\"\".
"""

    try:
        sql = generate_sql(prompt)
        logger.info(f"[QUERY RUN] Generated SQL:\n{sql}")

        client = get_bq_client()
        query_job = client.query(sql)
        rows = list(query_job.result())
        result = [row_to_serializable(r) for r in rows]

        return JSONResponse(
            {
                "status": "ok",
                "app": body.app,
                "question": body.question,
                "sql": sql,
                "row_count": len(result),
                "data": result,
            }
        )
    except Exception as e:
        logger.exception("[QUERY RUN ERROR]")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "app": body.app,
                "question": body.question,
                "error": str(e),
            },
        )


@app.post("/query/nl")
def query_nl(body: NLQueryRequest):
    """
    Simpler NL -> SQL endpoint (same idea as /query/run, but more direct).
    """
    if body.app != "classroom":
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": f"Unsupported app: {body.app}"},
        )

    # 1) Build prompt for Gemini – same constraints as /query/run
    prompt = f"""
You are an expert data analyst. Generate a valid BigQuery SQL query for the
`{PROJECT_ID}.{DATASET_ID}.dashboard_temp` table.

The schema of dashboard_temp is:

- app STRING
- metric_date DATE
- course_id STRING
- course_name STRING
- section STRING
- primary_teacher_email STRING
- total_students INT64
- total_submissions INT64
- turned_in_submissions INT64
- returned_submissions INT64
- late_submissions INT64
- avg_grade BIGNUMERIC
- max_grade FLOAT64
- ingestion_time TIMESTAMP

Rules:
- Only query from `{PROJECT_ID}.{DATASET_ID}.dashboard_temp`.
- Always filter app = 'classroom'.
- Return at most {body.max_rows} rows using LIMIT.
- Use standard SQL only.
- Wrap ONLY the SQL in a ```sql ... ``` block.

User question:
\"\"\"{body.question}\"\"\".
"""

    # 2) Ask Gemini for SQL
    sql = generate_sql(prompt)
    logger.info(f"[NL QUERY] question={body.question!r} sql={sql!r}")

    # 3) Safety: must be SELECT
    if not sql.strip().upper().startswith("SELECT"):
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "Generated SQL does not start with SELECT",
                "sql": sql,
            },
        )

    # 4) Run query against BigQuery
    client = get_bq_client()
    job = client.query(sql)
    rows = list(job.result())
    data = [row_to_serializable(r) for r in rows]

    return JSONResponse(
        {
            "status": "ok",
            "app": body.app,
            "sql": sql,
            "row_count": len(data),
            "data": data,
        }
    )


@app.get("/analytics/courses")
def analytics_courses():
    """
    Return distinct classroom courses that appear in dashboard_temp.
    Used to populate the course dropdown in the frontend.
    """
    client = get_bq_client()

    sql = f"""
    SELECT
      course_id,
      ANY_VALUE(course_name) AS course_name,
      ANY_VALUE(section) AS section,
      ANY_VALUE(primary_teacher_email) AS primary_teacher_email
    FROM `{PROJECT_ID}.{DATASET_ID}.dashboard_temp`
    WHERE app = 'classroom'
    GROUP BY course_id
    ORDER BY course_name
    """

    job = client.query(sql)
    rows = list(job.result())
    data = [row_to_serializable(r) for r in rows]

    return JSONResponse(
        {
            "status": "ok",
            "row_count": len(data),
            "courses": data,
        }
    )




@app.post("/analytics/course_timeseries")
def analytics_course_timeseries(body: CourseTimeseriesRequest):
    if body.app != "classroom":
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": f"Unsupported app: {body.app}"},
        )

    client = get_bq_client()

    sql = f"""
    SELECT
      metric_date,
      total_submissions,
      turned_in_submissions,
      returned_submissions,
      late_submissions,
      avg_grade,
      max_grade
    FROM `{PROJECT_ID}.{DATASET_ID}.dashboard_temp`
    WHERE app = @app
      -- cast to STRING to be safe regardless of underlying type
      AND CAST(course_id AS STRING) = @course_id
      AND metric_date >= DATE_SUB(CURRENT_DATE(), INTERVAL @days DAY)
    ORDER BY metric_date
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("app", "STRING", body.app),
            # IMPORTANT: treat course_id as STRING
            bigquery.ScalarQueryParameter("course_id", "STRING", str(body.course_id)),
            bigquery.ScalarQueryParameter("days", "INT64", body.days),
        ]
    )

    job = client.query(sql, job_config=job_config)
    rows = list(job.result())

    data = rows_to_json_safe(rows)

    return JSONResponse(
        {
            "status": "ok",
            "app": body.app,
            "course_id": body.course_id,
            "row_count": len(data),
            "data": data,
        }
    )

@app.post("/analytics/course_detail")
def analytics_course_detail(body: CourseDetailRequest):
    """
    Course Detail:
      - basic course metadata
      - windowed rollup metrics from dashboard_temp
      - recent assignments from classroom_submissions
    """
    if body.app != "classroom":
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": f"Unsupported app: {body.app}"},
        )

    client = get_bq_client()

    # --- 1) Course metadata (from dashboard_temp, latest metric_date) ---
    sql_meta = f"""
    SELECT
      course_id,
      ANY_VALUE(course_name) AS course_name,
      ANY_VALUE(section) AS section,
      ANY_VALUE(primary_teacher_email) AS primary_teacher_email,
      MAX(metric_date) AS latest_metric_date
    FROM `{PROJECT_ID}.{DATASET_ID}.dashboard_temp`
    WHERE app = @app
      AND course_id = @course_id
    GROUP BY course_id
    """

    job_meta = client.query(
        sql_meta,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("app", "STRING", body.app),
                bigquery.ScalarQueryParameter("course_id", "STRING", body.course_id),
            ]
        ),
    )
    meta_rows = list(job_meta.result())
    course_meta = rows_to_json_safe(meta_rows)[0] if meta_rows else None

    # --- 2) Windowed rollup over last N days in dashboard_temp ---
    sql_metrics = f"""
    SELECT
      SUM(total_submissions) AS total_submissions,
      SUM(turned_in_submissions) AS turned_in_submissions,
      SUM(returned_submissions) AS returned_submissions,
      SUM(late_submissions) AS late_submissions,
      AVG(avg_grade) AS avg_grade,
      MAX(max_grade) AS max_grade,
      MIN(metric_date) AS window_start,
      MAX(metric_date) AS window_end
    FROM `{PROJECT_ID}.{DATASET_ID}.dashboard_temp`
    WHERE app = @app
      AND course_id = @course_id
      AND metric_date >= DATE_SUB(CURRENT_DATE(), INTERVAL @days DAY)
    """

    job_metrics = client.query(
        sql_metrics,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("app", "STRING", body.app),
                bigquery.ScalarQueryParameter("course_id", "STRING", body.course_id),
                bigquery.ScalarQueryParameter("days", "INT64", body.days),
            ]
        ),
    )
    metrics_rows = list(job_metrics.result())
    metrics_window = rows_to_json_safe(metrics_rows)[0] if metrics_rows else None

    # --- 3) Recent assignments from classroom_submissions ---
    sql_assignments = f"""
    SELECT
      course_work_id,
      ANY_VALUE(course_work_title) AS course_work_title,
      MIN(assigned_time) AS first_assigned_time,
      MAX(due_time) AS due_time,
      COUNT(*) AS submissions,
      COUNTIF(state = 'TURNED_IN') AS turned_in,
      COUNTIF(late IS TRUE) AS late_submissions,
      AVG(grade) AS avg_grade,
      MAX(max_grade) AS max_grade
    FROM `{PROJECT_ID}.{DATASET_ID}.classroom_submissions`
    WHERE course_id = @course_id
    GROUP BY course_work_id
    ORDER BY due_time DESC
    LIMIT 20
    """

    job_assign = client.query(
        sql_assignments,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("course_id", "STRING", body.course_id),
            ]
        ),
    )
    assign_rows = list(job_assign.result())
    recent_assignments = rows_to_json_safe(assign_rows)

    return JSONResponse(
        {
            "status": "ok",
            "app": body.app,
            "course_id": body.course_id,
            "days": body.days,
            "course": course_meta,
            "metrics_window": metrics_window,
            "recent_assignments": recent_assignments,
        }
    )
