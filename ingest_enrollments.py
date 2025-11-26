# load_classroom_enrollments_to_bq.py
from dotenv import load_dotenv
import os
from datetime import datetime, timezone

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.cloud import bigquery
from google.cloud.bigquery import Dataset, Table, SchemaField

def run():
    load_dotenv()

    PROJECT_ID = os.getenv("PROJECT_ID")
    DATASET_ID = os.getenv("DATASET_ID")
    SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")
    DELEGATED_ADMIN = os.getenv("DELEGATED_ADMIN")
    BQ_LOCATION = os.getenv("BQ_LOCATION", "US")
    ENROLLMENTS_TABLE_ID = os.getenv("ENROLLMENTS_TABLE_ID", "classroom_enrollments")

    # scopes must be granted in DWD
    CLASSROOM_SCOPES = [
        "https://www.googleapis.com/auth/classroom.courses.readonly",
        "https://www.googleapis.com/auth/classroom.rosters.readonly",
    ]

    sa_creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=CLASSROOM_SCOPES,
    )
    delegated_creds = sa_creds.with_subject(DELEGATED_ADMIN)

    classroom = build("classroom", "v1", credentials=delegated_creds)

    # fetch all courses
    courses = []
    page_token = None
    while True:
        resp = classroom.courses().list(pageSize=100, pageToken=page_token).execute()
        courses.extend(resp.get("courses", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    print(f"Fetched {len(courses)} courses")

    # build enrollment rows
    rows = []
    ingestion_time = datetime.now(timezone.utc).isoformat()

    for c in courses:
        course_id = c.get("id")
        course_name = c.get("name")
        section = c.get("section")
        course_state = c.get("courseState")
        course_creation_time = c.get("creationTime")
        owner_id = c.get("ownerId")

        # students
        stud_page = None
        while True:
            try:
                s_resp = classroom.courses().students().list(
                    courseId=course_id,
                    pageToken=stud_page,
                    pageSize=100,
                ).execute()
            except Exception:
                break

            for s in s_resp.get("students", []):
                profile = s.get("profile", {})
                user_id = profile.get("id") or s.get("userId")
                email = profile.get("emailAddress")
                domain = email.split("@", 1)[1] if email and "@" in email else None

                rows.append(
                    {
                        "course_id": course_id,
                        "course_name": course_name,
                        "section": section,
                        "course_state": course_state,
                        "course_creation_time": course_creation_time,
                        "user_id": user_id,
                        "user_email": email,
                        "role": "STUDENT",
                        "enrollment_time": None,
                        "primary_teacher": False,
                        "domain": domain,
                        "ingestion_time": ingestion_time,
                    }
                )

            stud_page = s_resp.get("nextPageToken")
            if not stud_page:
                break

        # teachers
        teach_page = None
        while True:
            try:
                t_resp = classroom.courses().teachers().list(
                    courseId=course_id,
                    pageToken=teach_page,
                    pageSize=100,
                ).execute()
            except Exception:
                break

            for t in t_resp.get("teachers", []):
                profile = t.get("profile", {})
                user_id = profile.get("id") or t.get("userId")
                email = profile.get("emailAddress")
                domain = email.split("@", 1)[1] if email and "@" in email else None

                is_owner = (owner_id is not None) and (user_id == owner_id)
                role = "OWNER" if is_owner else "TEACHER"

                rows.append(
                    {
                        "course_id": course_id,
                        "course_name": course_name,
                        "section": section,
                        "course_state": course_state,
                        "course_creation_time": course_creation_time,
                        "user_id": user_id,
                        "user_email": email,
                        "role": role,
                        "enrollment_time": None,
                        "primary_teacher": is_owner,
                        "domain": domain,
                        "ingestion_time": ingestion_time,
                    }
                )

            teach_page = t_resp.get("nextPageToken")
            if not teach_page:
                break

    print(f"Built {len(rows)} enrollment rows")

    # BigQuery load
    bq_client = bigquery.Client.from_service_account_json(
        SERVICE_ACCOUNT_FILE,
        project=PROJECT_ID,
    )

    dataset_ref = f"{PROJECT_ID}.{DATASET_ID}"
    table_ref = f"{dataset_ref}.{ENROLLMENTS_TABLE_ID}"

    # dataset ensure
    try:
        dataset = Dataset(dataset_ref)
        dataset.location = BQ_LOCATION
        bq_client.create_dataset(dataset, exists_ok=True)
    except Exception as e:
        print("Dataset create/check error:", e)

    # schema must match existing table; we only need it if table might not exist
    schema = [
        SchemaField("course_id", "STRING"),
        SchemaField("course_name", "STRING"),
        SchemaField("section", "STRING"),
        SchemaField("course_state", "STRING"),
        SchemaField("course_creation_time", "TIMESTAMP"),
        SchemaField("user_id", "STRING"),
        SchemaField("user_email", "STRING"),
        SchemaField("role", "STRING"),
        SchemaField("enrollment_time", "TIMESTAMP"),
        SchemaField("primary_teacher", "BOOL"),
        SchemaField("domain", "STRING"),
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
        print("No enrollments to insert.")
        return 0


if __name__ == "__main__":
    run()
