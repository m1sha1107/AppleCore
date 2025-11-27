from fastapi import FastAPI
from fastapi.responses import JSONResponse

from backend import load_classroom_to_bq
from backend import ingest_submissions
from backend import ingest_enrollments
from backend import dashboard_refresh

app = FastAPI()

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

    return JSONResponse({
        "status": "ok",
        "task": "classroom_all",
        "rows_loaded": {
            "courses": c_courses,
            "enrollments": c_enroll,
            "submissions": c_sub,
            "dashboard_temp": c_dash,
        },
    })
