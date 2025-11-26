from dotenv import load_dotenv
import os
from google.cloud import bigquery
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.cloud.bigquery import Dataset, Table, SchemaField


def run() -> int:
    """
    Sync Classroom courses into BigQuery.
    Returns number of rows in the destination table after load.
    """
    load_dotenv()

    PROJECT_ID = os.getenv("PROJECT_ID")
    DATASET_ID = os.getenv("DATASET_ID")
    TABLE_ID = os.getenv("TABLE_ID")
    SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")
    DELEGATED_ADMIN = os.getenv("DELEGATED_ADMIN")
    BQ_LOCATION = os.getenv("BQ_LOCATION")

    # Classroom scopes needed (these MUST match DWD scopes in Admin Console)
    CLASSROOM_SCOPES = [
        "https://www.googleapis.com/auth/classroom.courses.readonly",
        "https://www.googleapis.com/auth/classroom.rosters.readonly",
    ]

    # === Authenticate for Classroom (with DWD) ===
    sa_classroom_creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=CLASSROOM_SCOPES,
    )
    delegated_creds = sa_classroom_creds.with_subject(DELEGATED_ADMIN)

    # Classroom service (impersonated)
    classroom = build("classroom", "v1", credentials=delegated_creds)

    # Fetch all courses (paged)
    courses = []
    page_token = None
    while True:
        resp = classroom.courses().list(pageSize=100, pageToken=page_token).execute()
        courses.extend(resp.get("courses", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    print(f"Fetched {len(courses)} courses")

    # Transform records into BigQuery-friendly rows
    rows = []
    for c in courses:
        rows.append(
            {
                "course_id": c.get("id"),
                "name": c.get("name"),
                "section": c.get("section"),
                "description": c.get("description"),
                "room": c.get("room"),
                "owner_id": c.get("ownerId"),
                "creation_time": c.get("creationTime"),
                "update_time": c.get("updateTime"),
                "enrollment_code": c.get("enrollmentCode"),
                "course_state": c.get("courseState"),
                "alternate_link": c.get("alternateLink"),
            }
        )

    # === BigQuery client (no DWD needed here) ===
    # BigQuery just needs normal service account IAM perms on the project/dataset
    bq_client = bigquery.Client.from_service_account_json(
        SERVICE_ACCOUNT_FILE,
        project=PROJECT_ID,
    )

    dataset_ref = f"{PROJECT_ID}.{DATASET_ID}"

    # create dataset if not exists
    try:
        dataset = Dataset(dataset_ref)
        dataset.location = BQ_LOCATION
        bq_client.create_dataset(dataset, exists_ok=True)
        print("Dataset ready:", dataset_ref)
    except Exception as e:
        print("Dataset create/check error:", e)

    # define schema
    schema = [
        SchemaField("course_id", "STRING"),
        SchemaField("name", "STRING"),
        SchemaField("section", "STRING"),
        SchemaField("description", "STRING"),
        SchemaField("room", "STRING"),
        SchemaField("owner_id", "STRING"),
        SchemaField("creation_time", "TIMESTAMP"),
        SchemaField("update_time", "TIMESTAMP"),
        SchemaField("enrollment_code", "STRING"),
        SchemaField("course_state", "STRING"),
        SchemaField("alternate_link", "STRING"),
    ]

    table_ref = f"{dataset_ref}.{TABLE_ID}"
    table = Table(table_ref, schema=schema)
    try:
        bq_client.create_table(table, exists_ok=True)
        print("Table ready:", table_ref)
    except Exception as e:
        print("Table create error (maybe existed):", e)

    # Insert rows using a load job (works on free tier)
    if rows:
        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE  # overwrite table each run
        )

        load_job = bq_client.load_table_from_json(
            rows,
            table_ref,  # "project.dataset.table"
            job_config=job_config,
        )

        load_job.result()  # wait for job to finish

        dest_table = bq_client.get_table(table_ref)
        print(f"Loaded {dest_table.num_rows} rows into {table_ref}")
        return dest_table.num_rows
    else:
        print("No rows to insert.")
        return 0


if __name__ == "__main__":
    count = run()
    print(f"Done. Rows in table: {count}")
