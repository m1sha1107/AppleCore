# backend/dashboard_refresh.py
import os
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
DATASET_ID = os.getenv("DATASET_ID", "workspace_analytics")
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")

DASHBOARD_REFRESH_SQL = f"""
CREATE OR REPLACE TABLE `{PROJECT_ID}.{DATASET_ID}.dashboard_temp`
PARTITION BY DATE(ingestion_time)
OPTIONS(
  description = "App-specific daily metrics for dashboards"
)
AS
WITH base AS (
  SELECT
    s.course_id,
    ANY_VALUE(e.course_name) AS course_name,
    ANY_VALUE(e.section) AS section,
    ANY_VALUE(IF(e.role IN ('TEACHER', 'OWNER'), e.user_email, NULL)) AS primary_teacher_email,
    DATE(s.assigned_time) AS metric_date,
    COUNT(*) AS total_submissions,
    COUNTIF(s.state = 'TURNED_IN') AS turned_in_submissions,
    COUNTIF(s.state = 'RETURNED') AS returned_submissions,
    COUNTIF(s.late IS TRUE) AS late_submissions,
    AVG(SAFE_CAST(s.grade AS BIGNUMERIC)) AS avg_grade,
    MAX(s.max_grade) AS max_grade,
    COUNT(DISTINCT IF(e.role = 'STUDENT', e.user_id, NULL)) AS total_students
  FROM
    `{PROJECT_ID}.{DATASET_ID}.classroom_submissions` AS s
  LEFT JOIN
    `{PROJECT_ID}.{DATASET_ID}.classroom_enrollments` AS e
  ON
    s.course_id = e.course_id
  GROUP BY
    course_id,
    metric_date
)
SELECT
  'classroom' AS app,
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
  CURRENT_TIMESTAMP() AS ingestion_time
FROM
  base;
"""

def run() -> int:
    """
    Rebuilds dashboard_temp and returns row count.
    """
    client = bigquery.Client.from_service_account_json(
        SERVICE_ACCOUNT_FILE,
        project=PROJECT_ID,
    )

    job = client.query(DASHBOARD_REFRESH_SQL)
    job.result()  # wait for completion

    table_ref = f"{PROJECT_ID}.{DATASET_ID}.dashboard_temp"
    table = client.get_table(table_ref)
    return table.num_rows
