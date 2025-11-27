# backend/nl_to_sql.py
from typing import Tuple

SUPPORTED_APP = "classroom"

def nl_to_sql(app: str, question: str) -> Tuple[str, dict]:
    """
    TEMP STUB for Week 3:
    - Given app + NL question, return (sql_string, params_dict)
    - Later you will replace the body with a Gemini call.
    """
    if app != SUPPORTED_APP:
        raise ValueError(f"Unsupported app for NL -> SQL: {app}")

    q_lower = question.lower().strip()

    # Very dumb router just so you can test end-to-end
    if "late" in q_lower and "submissions" in q_lower:
        sql = """
        SELECT
          course_id,
          course_name,
          metric_date,
          late_submissions,
          total_submissions
        FROM `{project}.{dataset}.dashboard_temp`
        WHERE app = @app
        ORDER BY late_submissions DESC
        LIMIT @limit
        """
        return sql, {}

    if "most active" in q_lower and "course" in q_lower:
        sql = """
        SELECT
          course_id,
          course_name,
          total_submissions
        FROM `{project}.{dataset}.dashboard_temp`
        WHERE app = @app
        ORDER BY total_submissions DESC
        LIMIT @limit
        """
        return sql, {}

    # default: just give top courses by submissions
    sql = """
    SELECT
      course_id,
      course_name,
      total_submissions
    FROM `{project}.{dataset}.dashboard_temp`
    WHERE app = @app
    ORDER BY total_submissions DESC
    LIMIT @limit
    """
    return sql, {}
