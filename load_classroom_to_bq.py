from dotenv import load_dotenv
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.cloud import bigquery

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
DATASET_ID = os.getenv("DATASET_ID")
TABLE_ID = os.getenv("TABLE_ID")
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")
DELEGATED_ADMIN = os.getenv("DELEGATED_ADMIN")
BQ_LOCATION = os.getenv("BQ_LOCATION")

SCOPES = os.getenv("SCOPES").split(',')

# Classroom scopes needed
CLASSROOM_SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.rosters.readonly"
]

# BigQuery scope (not strictly necessary here; bigquery client will use google auth library)
BQ_SCOPES = ["https://www.googleapis.com/auth/bigquery"]

# === Authenticate ===
sa_creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=CLASSROOM_SCOPES + BQ_SCOPES
)
delegated_creds = sa_creds.with_subject(DELEGATED_ADMIN)

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
    rows.append({
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
        "alternate_link": c.get("alternateLink")
    })

# === BigQuery client ===
# Use service account creds (no subject needed for BigQuery ops) — reuse sa_creds
bq_client = bigquery.Client(project=PROJECT_ID, credentials=sa_creds)

dataset_ref = f"{PROJECT_ID}.{DATASET_ID}"
# create dataset if not exists
from google.cloud.bigquery import Dataset, Table, SchemaField
try:
    dataset = bigquery.Dataset(dataset_ref)
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

# Insert rows (streaming insert)
if rows:
    errors = bq_client.insert_rows_json(table_ref, rows, row_ids=[None]*len(rows))
    if errors:
        print("Errors inserting rows:", errors)
    else:
        print(f"Inserted {len(rows)} rows into {table_ref}")
else:
    print("No rows to insert.")
