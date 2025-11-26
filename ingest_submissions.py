# load_classroom_submissions_to_bq.py
from dotenv import load_dotenv
import os
from datetime import datetime, timezone

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.cloud import bigquery
from google.cloud.bigquery import Dataset, Table, SchemaField

def _due_timestamp(course_work):
    due_date = course_work.get("dueDate")
    due_time = course_work.get("dueTime")
    if not due_date or not isinstance(due_date, dict):
        return None

    year = due_date.get("year")
    month = due_date.get("month")
    day = due_date.get("day")
    if not (year and month and day):
        return None

    hours = 0
    minutes = 0
    seconds = 0
    if isinstance(due_time, dict):
        hours = due_time.get("hours", 0) or 0
        minutes = due_time.get("minutes", 0) or 0
        seconds = due_time.get("seconds", 0) or 0

    dt = datetime(year, month, day, hours, minutes, seconds, tzinfo=timezone.utc)
    return dt.isoformat()

def run():
    load_dotenv()

    PROJECT_ID = os.getenv("PROJECT_ID")
    DATASET_ID = os.getenv("DATASET_ID")
    SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")
    DELEGATED_ADMIN = os.getenv("DELEGATED_ADMIN")
    BQ_LOCATION = os.getenv("BQ_LOCATION", "US")
    SUBMISSIONS_TABLE_ID = os.getenv("SUBMISSIONS_TABLE_ID", "classroom_submissions")

    CLASSROOM_SCOPES = [
        "https://www.googleapis.com/auth/classroom.courses.readonly",
        "https://www.googleapis.com/auth/classroom.coursework.students.readonly",
        "https://www.googleapis.com/auth/classroom.student-submissions.students.readonly",
    ]

    sa_creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=CLASSROOM_SCOPES,
    )
    delegated_creds = sa_creds.with_subject(DELEGATED_ADMIN)

    classroom = build("classroom", "v1", credentials=delegated_creds)

    # list all courses
    courses = []
    page_token = None
    while True:
        resp = classroom.courses().list(pageSize=100, pageToken=page_token).execute()
        courses.extend(resp.get("courses", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    print(f"Fetched {len(courses)} courses")

    rows = []
    ingestion_time = datetime.now(timezone.utc).isoformat()

    # loop over courses -> coursework -> submissions
    for c in courses:
        course_id = c.get("id")

        cw_page = None
        while True:
            cw_resp = classroom.courses().courseWork().list(
                courseId=course_id,
                pageSize=100,
                pageToken=cw_page,
            ).execute()

            courseworks = cw_resp.get("courseWork", [])
            if not courseworks:
                break

            for cw in courseworks:
                course_work_id = cw.get("id")
                course_work_title = cw.get("title")
                assigned_time = cw.get("creationTime")
                due_time = _due_timestamp(cw)
                max_grade = cw.get("maxPoints")

                ss_page = None
                while True:
                    ss_resp = classroom.courses().courseWork().studentSubmissions().list(
                        courseId=course_id,
                        courseWorkId=course_work_id,
                        pageSize=100,
                        pageToken=ss_page,
                    ).execute()

                    submissions = ss_resp.get("studentSubmissions", [])
                    if not submissions:
                        break

                    for ss in submissions:
                        submission_id = ss.get("id")
                        student_id = ss.get("userId")
                        state = ss.get("state")
                        late = ss.get("late")
                        grade = ss.get("assignedGrade")
                        creation_time = ss.get("creationTime")
                        update_time = ss.get("updateTime")

                        rows.append(
                            {
                                "course_id": course_id,
                                "course_work_id": course_work_id,
                                "course_work_title": course_work_title,
                                "submission_id": submission_id,
                                "student_id": student_id,
                                "student_email": None,  # can be joined from enrollments/users later
                                "state": state,
                                "assigned_time": assigned_time,
                                "due_time": due_time,
                                "late": late,
                                "grade": grade,
                                "max_grade": max_grade,
                                "update_time": update_time,
                                "creation_time": creation_time,
                                "ingestion_time": ingestion_time,
                            }
                        )

                    ss_page = ss_resp.get("nextPageToken")
                    if not ss_page:
                        break

            cw_page = cw_resp.get("nextPageToken")
            if not cw_page:
                break

    print(f"Built {len(rows)} submission rows")

    # BigQuery load
    bq_client = bigquery.Client.from_service_account_json(
        SERVICE_ACCOUNT_FILE,
        project=PROJECT_ID,
    )

    dataset_ref = f"{PROJECT_ID}.{DATASET_ID}"
    table_ref = f"{dataset_ref}.{SUBMISSIONS_TABLE_ID}"

    try:
        dataset = Dataset(dataset_ref)
        dataset.location = BQ_LOCATION
        bq_client.create_dataset(dataset, exists_ok=True)
    except Exception as e:
        print("Dataset create/check error:", e)

    schema = [
        SchemaField("course_id", "STRING"),
        SchemaField("course_work_id", "STRING"),
        SchemaField("course_work_title", "STRING"),
        SchemaField("submission_id", "STRING"),
        SchemaField("student_id", "STRING"),
        SchemaField("student_email", "STRING"),
        SchemaField("state", "STRING"),
        SchemaField("assigned_time", "TIMESTAMP"),
        SchemaField("due_time", "TIMESTAMP"),
        SchemaField("late", "BOOL"),
        SchemaField("grade", "FLOAT"),
        SchemaField("max_grade", "FLOAT"),
        SchemaField("update_time", "TIMESTAMP"),
        SchemaField("creation_time", "TIMESTAMP"),
        SchemaField("ingestion_time", "TIMESTAMP"),
    ]

    try:
        table = Table(table_ref, schema=schema)
        bq_client.create_table(table, exists_ok=True)
    except Exception as e:
        print("Table create error (maybe existed):", e)

    if rows:
        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
        )
        load_job = bq_client.load_table_from_json(rows, table_ref, job_config=job_config)
        load_job.result()
        dest = bq_client.get_table(table_ref)
        print(f"Loaded {dest.num_rows} rows into {table_ref}")
        return dest.num_rows
    else:
        print("No submissions to insert.")
        return 0


if __name__ == "__main__":
    run()
