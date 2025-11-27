from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime, timezone  # for timestamps

from backend import load_classroom_to_bq
from backend import ingest_submissions
from backend import ingest_enrollments
from backend import dashboard_refresh

app = FastAPI()


# ---- Request models ----
class SyncRequest(BaseModel):
    app: str


@app.get("/")
def root():
    return {"message": "Backend is running", "service": "CloudReign backend"}


@app.post("/sync/classroom/courses")
def sync_classroom_courses():
    count = load_classroom_to_bq.run()
    return JSONResponse({"status": "ok", "task": "classroom_courses", "rows_loaded": count})


@app.post("/sync/classroom/enrollments")
def sync_classroom_enrollments():
    count = ingest_enrollments.run()
    return JSONResponse({"status": "ok", "task": "classroom_enrollments", "rows_loaded": count})


@app.post("/sync/classroom/submissions")
def sync_classroom_submissions():
    count = ingest_submissions.run()
    return JSONResponse({"status": "ok", "task": "classroom_submissions", "rows_loaded": count})


@app.post("/sync/classroom/dashboard")
def sync_classroom_dashboard():
    count = dashboard_refresh.run()
    return JSONResponse({"status": "ok", "task": "dashboard_temp", "rows_loaded": count})


@app.post("/sync/classroom/all")
def sync_classroom_all():
    c_courses = load_classroom_to_bq.run()
    c_enroll = ingest_enrollments.run()
    c_sub = ingest_submissions.run()
    c_dash = dashboard_refresh.run()

    return JSONResponse(
        {
            "status": "ok",
            "task": "classroom_all",
            "rows_loaded": {
                "courses": c_courses,
                "enrollments": c_enroll,
                "submissions": c_sub,
                "dashboard_temp": c_dash,
            },
        }
    )


@app.post("/sync/app")
def sync_app(body: SyncRequest):
    if body.app != "classroom":
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": f"Unsupported app: {body.app}"},
        )

    started_at = datetime.now(timezone.utc)

    # --- run all classroom tasks ---
    c_courses = load_classroom_to_bq.run()
    c_enroll = ingest_enrollments.run()
    c_sub = ingest_submissions.run()
    c_dash = dashboard_refresh.run()

    finished_at = datetime.now(timezone.utc)
    duration_ms = (finished_at - started_at).total_seconds() * 1000.0

    print(
        f"[SYNC] app=classroom started_at={started_at.isoformat()} "
        f"finished_at={finished_at.isoformat()} duration_ms={duration_ms:.2f} "
        f"rows={{courses:{c_courses}, enrollments:{c_enroll}, "
        f"submissions:{c_sub}, dashboard_temp:{c_dash}}}"
    )

    return JSONResponse(
        {
            "status": "ok",
            "app": "classroom",
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_ms": duration_ms,
            "rows_loaded": {
                "courses": c_courses,
                "enrollments": c_enroll,
                "submissions": c_sub,
                "dashboard_temp": c_dash,
            },
        }
    )
