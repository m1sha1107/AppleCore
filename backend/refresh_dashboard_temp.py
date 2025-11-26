# refresh_dashboard_temp.py
from dotenv import load_dotenv
import os
from google.cloud import bigquery

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")

def run() -> int:
    """
    Rebuilds the dashboard_temp table for Classroom.
    Returns: number of rows in dashboard_temp after rebuild.
    """
    client = bigquery.Client.from_service_account_json(
        SERVICE_ACCOUNT_FILE,
        project=PROJECT_ID,
    )

    sql = f"""
    CREATE OR REPLACE TABLE `{PROJECT_ID}.workspace_analytics.dashboard_temp`
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
        COUNTIF(s.late IS TRUE) AS late_submissions,          -- BOOL expression
        AVG(SAFE_CAST(s.grade AS BIGNUMERIC)) AS avg_grade,
        MAX(s.max_grade) AS max_grade,
        COUNT(DISTINCT IF(e.role = 'STUDENT', e.user_id, NULL)) AS total_students
      FROM
        `{PROJECT_ID}.workspace_analytics.classroom_submissions` AS s
      LEFT JOIN
        `{PROJECT_ID}.workspace_analytics.classroom_enrollments` AS e
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

    job = client.query(sql)
    job.result()  # wait for completion

    # Get row count from the rebuilt table
    table = client.get_table(f"{PROJECT_ID}.workspace_analytics.dashboard_temp")
    return table.num_rows

if __name__ == "__main__":
    n = run()
    print(f"dashboard_temp rebuilt, {n} rows")
