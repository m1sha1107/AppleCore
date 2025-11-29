// src/components/CourseAnalytics.jsx
import { useEffect, useState } from "react";

const API_BASE = "http://127.0.0.1:8000"; // your FastAPI backend

export default function CourseAnalytics() {
  const [courses, setCourses] = useState([]);
  const [loadingCourses, setLoadingCourses] = useState(false);
  const [selectedCourseId, setSelectedCourseId] = useState("");
  const [timeseries, setTimeseries] = useState([]);
  const [loadingTS, setLoadingTS] = useState(false);
  const [error, setError] = useState("");

  // ---- 1. fetch list of courses on mount ----
  useEffect(() => {
    const fetchCourses = async () => {
      try {
        setLoadingCourses(true);
        setError("");

        const res = await fetch(`${API_BASE}/analytics/courses`);
        if (!res.ok) {
          const text = await res.text();
          throw new Error(`GET /analytics/courses failed: ${text}`);
        }

        const json = await res.json();
        setCourses(json.courses || []);

        if (json.courses && json.courses.length > 0) {
          setSelectedCourseId(json.courses[0].course_id);
        }
      } catch (err) {
        console.error(err);
        setError(err.message || "Failed to load courses");
      } finally {
        setLoadingCourses(false);
      }
    };

    fetchCourses();
  }, []);

  // ---- 2. whenever selectedCourseId changes, fetch timeseries ----
  useEffect(() => {
    if (!selectedCourseId) return;

    const fetchTimeseries = async () => {
      try {
        setLoadingTS(true);
        setError("");

        const res = await fetch(`${API_BASE}/analytics/course_timeseries`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            app: "classroom",
            course_id: selectedCourseId,
            days: 30, // last 30 days
          }),
        });

        if (!res.ok) {
          const text = await res.text();
          throw new Error(`POST /analytics/course_timeseries failed: ${text}`);
        }

        const json = await res.json();
        setTimeseries(json.data || []);
      } catch (err) {
        console.error(err);
        setError(err.message || "Failed to load timeseries");
      } finally {
        setLoadingTS(false);
      }
    };

    fetchTimeseries();
  }, [selectedCourseId]);

  // ---- helpers ----
  const selectedCourse = courses.find((c) => c.course_id === selectedCourseId);

  const latestPoint =
    timeseries.length > 0 ? timeseries[timeseries.length - 1] : null;

  return (
    <section style={{ marginTop: "24px" }}>
      <h2 style={{ marginBottom: "8px" }}>Course Analytics</h2>

      {/* error banner */}
      {error && (
        <div
          style={{
            marginBottom: "12px",
            padding: "8px 12px",
            backgroundColor: "#ffe5e5",
            border: "1px solid #ffb3b3",
            borderRadius: "4px",
            fontSize: "0.9rem",
          }}
        >
          {error}
        </div>
      )}

      {/* course selector */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "12px",
          marginBottom: "16px",
        }}
      >
        <label>
          Course:&nbsp;
          <select
            value={selectedCourseId}
            onChange={(e) => setSelectedCourseId(e.target.value)}
            disabled={loadingCourses || courses.length === 0}
          >
            {loadingCourses && <option>Loading...</option>}
            {!loadingCourses && courses.length === 0 && (
              <option>No courses found</option>
            )}
            {courses.map((course) => (
              <option key={course.course_id} value={course.course_id}>
                {course.course_name || "(no name)"}{" "}
                {course.section ? `– ${course.section}` : ""}
              </option>
            ))}
          </select>
        </label>

        {selectedCourse && (
          <span style={{ fontSize: "0.9rem", color: "#555" }}>
            Teacher: {selectedCourse.primary_teacher_email || "Unknown"}
          </span>
        )}
      </div>

      {/* quick stats card */}
      <div
        style={{
          display: "flex",
          gap: "16px",
          marginBottom: "20px",
          flexWrap: "wrap",
        }}
      >
        <StatCard
          label="Total submissions (last point)"
          value={latestPoint?.total_submissions ?? "–"}
        />
        <StatCard
          label="Turned in"
          value={latestPoint?.turned_in_submissions ?? "–"}
        />
        <StatCard
          label="Returned"
          value={latestPoint?.returned_submissions ?? "–"}
        />
        <StatCard
          label="Late"
          value={latestPoint?.late_submissions ?? "–"}
        />
        <StatCard
          label="Avg grade"
          value={
            latestPoint?.avg_grade != null
              ? Number(latestPoint.avg_grade).toFixed(2)
              : "–"
          }
        />
      </div>

      {/* timeseries table */}
      <div style={{ maxHeight: "320px", overflowY: "auto" }}>
        {loadingTS ? (
          <p>Loading timeseries…</p>
        ) : timeseries.length === 0 ? (
          <p>No data for this course in the selected window.</p>
        ) : (
          <table
            style={{
              borderCollapse: "collapse",
              width: "100%",
              fontSize: "0.9rem",
            }}
          >
            <thead>
              <tr>
                <Th>Date</Th>
                <Th>Total</Th>
                <Th>Turned in</Th>
                <Th>Returned</Th>
                <Th>Late</Th>
                <Th>Avg grade</Th>
                <Th>Max grade</Th>
              </tr>
            </thead>
            <tbody>
              {timeseries.map((row) => (
                <tr key={row.metric_date}>
                  <Td>{row.metric_date}</Td>
                  <Td>{row.total_submissions}</Td>
                  <Td>{row.turned_in_submissions}</Td>
                  <Td>{row.returned_submissions}</Td>
                  <Td>{row.late_submissions}</Td>
                  <Td>
                    {row.avg_grade != null
                      ? Number(row.avg_grade).toFixed(2)
                      : "–"}
                  </Td>
                  <Td>{row.max_grade ?? "–"}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}

// small presentational helpers
function StatCard({ label, value }) {
  return (
    <div
      style={{
        minWidth: "160px",
        padding: "10px 12px",
        borderRadius: "6px",
        border: "1px solid #ddd",
        backgroundColor: "#fafafa",
      }}
    >
      <div style={{ fontSize: "0.75rem", color: "#777" }}>{label}</div>
      <div style={{ fontSize: "1.2rem", fontWeight: 600, marginTop: "4px" }}>
        {value}
      </div>
    </div>
  );
}

function Th({ children }) {
  return (
    <th
      style={{
        borderBottom: "1px solid #ddd",
        textAlign: "left",
        padding: "6px 8px",
        backgroundColor: "#f3f3f3",
        position: "sticky",
        top: 0,
        zIndex: 1,
      }}
    >
      {children}
    </th>
  );
}

function Td({ children }) {
  return (
    <td
      style={{
        borderBottom: "1px solid #eee",
        padding: "6px 8px",
      }}
    >
      {children}
    </td>
  );
}
