# backend/main.py
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# ingestion modules (each should expose a run() function)
import backend.load_classroom_to_bq as load_classroom_to_bq
import backend.ingest_enrollments as ingest_enrollments
import backend.ingest_submissions as ingest_submissions
import backend.dashboard_refresh as dashboard_refresh  # this has refresh_dashboard_temp()

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Backend is running", "service": "CloudReign backend"}

@app.get("/health")
def health():
    return {"status": "ok", "service": "CloudReign backend"}

@app.post("/sync/classroom/courses")
def sync_classroom_courses():
    count = load_classroom_to_bq.run()
    return JSONResponse(
        {"status": "ok", "task": "classroom_courses", "rows_loaded": count}
    )

@app.post("/sync/classroom/enrollments")
def sync_classroom_enrollments():
    count = ingest_enrollments.run()
    return JSONResponse(
        {"status": "ok", "task": "classroom_enrollments", "rows_loaded": count}
    )

@app.post("/sync/classroom/submissions")
def sync_classroom_submissions():
    count = ingest_submissions.run()
    return JSONResponse(
        {"status": "ok", "task": "classroom_submissions", "rows_loaded": count}
    )

@app.post("/sync/classroom/dashboard")
def sync_classroom_dashboard():
    count = dashboard_refresh.refresh_dashboard_temp()
    return JSONResponse(
        {"status": "ok", "task": "dashboard_temp", "rows_loaded": count}
    )

@app.post("/sync/classroom/all")
def sync_classroom_all():
    c_courses = load_classroom_to_bq.run()
    c_enroll = ingest_enrollments.run()
    c_sub = ingest_submissions.run()
    c_dash = dashboard_refresh.refresh_dashboard_temp()

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
