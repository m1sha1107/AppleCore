// src/components/CourseAnalytics.jsx
import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
} from "recharts";

const BASE_URL =
  import.meta.env.VITE_BACKEND_URL || "http://127.0.0.1:8000";

export default function CourseAnalytics() {
  const [courses, setCourses] = useState([]);
  const [coursesLoading, setCoursesLoading] = useState(false);
  const [coursesError, setCoursesError] = useState("");

  const [selectedCourseId, setSelectedCourseId] = useState(null);
  const [selectedCourseMeta, setSelectedCourseMeta] = useState(null);

  const [timeseries, setTimeseries] = useState([]);
  const [tsLoading, setTsLoading] = useState(false);
  const [tsError, setTsError] = useState("");

  const [days, setDays] = useState(30); // time window

  // ---------- LOAD COURSE LIST ON MOUNT ----------
  useEffect(() => {
    async function fetchCourses() {
      try {
        setCoursesLoading(true);
        setCoursesError("");

        const res = await fetch(`${BASE_URL}/analytics/courses`);
        if (!res.ok) {
          const text = await res.text();
          throw new Error(`HTTP ${res.status}: ${text}`);
        }

        const json = await res.json();
        setCourses(json.courses || []);
      } catch (err) {
        console.error("Error fetching courses:", err);
        setCoursesError(
          err instanceof Error ? err.message : "Unknown error"
        );
      } finally {
        setCoursesLoading(false);
      }
    }

    fetchCourses();
  }, []);

  // ---------- LOAD TIMESERIES FOR A COURSE ----------
  async function loadTimeseries(course) {
    if (!course?.course_id) return;

    try {
      setTsLoading(true);
      setTsError("");
      setTimeseries([]);

      setSelectedCourseId(course.course_id);
      setSelectedCourseMeta(course);

      const res = await fetch(`${BASE_URL}/analytics/course_timeseries`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          app: "classroom",
          course_id: String(course.course_id), // force string
          days: Number(days) || 30,
        }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`HTTP ${res.status}: ${text}`);
      }

      const json = await res.json();
      setTimeseries(json.data || []);
    } catch (err) {
      console.error("Error fetching timeseries:", err);
      setTsError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setTsLoading(false);
    }
  }

  // ---------- DERIVED: RECHARTS DATA ----------
  const chartData = timeseries.map((row) => ({
    date: (row.metric_date || "").slice(0, 10),
    total: row.total_submissions ?? 0,
    turnedIn: row.turned_in_submissions ?? 0,
    returned: row.returned_submissions ?? 0,
    late: row.late_submissions ?? 0,
    avgGrade: row.avg_grade ?? 0,
    maxGrade: row.max_grade ?? 0,
  }));

  const latest = chartData[chartData.length - 1] || null;

  // ---------- UI ----------
  return (
    <div style={{ padding: "16px" }}>
      <h2 style={{ marginBottom: "12px" }}>Course Analytics</h2>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "280px 1fr",
          gap: "16px",
          alignItems: "flex-start",
        }}
      >
        {/* LEFT: COURSE LIST */}
        <div
          style={{
            border: "1px solid #ddd",
            borderRadius: "8px",
            padding: "12px",
            maxHeight: "70vh",
            overflowY: "auto",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: "8px",
              alignItems: "center",
            }}
          >
            <strong>Courses</strong>
            <span style={{ fontSize: "12px", color: "#666" }}>
              {courses.length} found
            </span>
          </div>

          {coursesLoading && <p>Loading courses…</p>}
          {coursesError && (
            <p style={{ color: "red", fontSize: "12px" }}>{coursesError}</p>
          )}

          {!coursesLoading && !coursesError && courses.length === 0 && (
            <p style={{ fontSize: "12px", color: "#555" }}>
              No courses found. Run a sync first.
            </p>
          )}

          {courses.map((c) => (
            <button
              key={c.course_id}
              onClick={() => loadTimeseries(c)}
              style={{
                width: "100%",
                textAlign: "left",
                padding: "8px 10px",
                marginBottom: "6px",
                borderRadius: "6px",
                border:
                  c.course_id === selectedCourseId
                    ? "1px solid #2563eb"
                    : "1px solid #ddd",
                background:
                  c.course_id === selectedCourseId ? "#eff6ff" : "#fff",
                cursor: "pointer",
                fontSize: "13px",
              }}
            >
              <div style={{ fontWeight: 600 }}>
                {c.course_name || "(no name)"}
              </div>
              <div style={{ fontSize: "11px", color: "#555" }}>
                ID: {c.course_id}
                {c.section ? ` • Section ${c.section}` : ""}
              </div>
            </button>
          ))}
        </div>

        {/* RIGHT: DETAILS + CHARTS */}
        <div>
          {/* top controls */}
          <div
            style={{
              marginBottom: "12px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div>
              <h3 style={{ margin: 0 }}>
                {selectedCourseMeta?.course_name || "Select a course"}
              </h3>
              {selectedCourseMeta && (
                <div style={{ fontSize: "12px", color: "#555" }}>
                  Course ID: {selectedCourseMeta.course_id}
                  {selectedCourseMeta.section
                    ? ` • Section ${selectedCourseMeta.section}`
                    : ""}
                </div>
              )}
            </div>

            <div style={{ fontSize: "12px" }}>
              <label>
                Window (days):{" "}
                <input
                  type="number"
                  min={1}
                  max={365}
                  value={days}
                  onChange={(e) => setDays(e.target.value)}
                  style={{ width: "60px", marginLeft: "4px" }}
                />
              </label>
              {selectedCourseMeta && (
                <button
                  onClick={() => loadTimeseries(selectedCourseMeta)}
                  style={{
                    marginLeft: "8px",
                    padding: "4px 10px",
                    fontSize: "12px",
                    borderRadius: "4px",
                    border: "1px solid #2563eb",
                    background: "#2563eb",
                    color: "#fff",
                    cursor: "pointer",
                  }}
                >
                  Refresh
                </button>
              )}
            </div>
          </div>

          {tsLoading && <p>Loading time series…</p>}
          {tsError && (
            <p style={{ color: "red", fontSize: "12px" }}>{tsError}</p>
          )}

          {!tsLoading && !tsError && !selectedCourseId && (
            <p style={{ fontSize: "13px", color: "#555" }}>
              Pick a course on the left to see trends.
            </p>
          )}

          {!tsLoading &&
            !tsError &&
            selectedCourseId &&
            chartData.length === 0 && (
              <p style={{ fontSize: "13px", color: "#555" }}>
                No data in this window. Try expanding days or running a sync.
              </p>
            )}

          {/* SUMMARY CARDS */}
          {latest && (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
                gap: "10px",
                marginBottom: "12px",
              }}
            >
              <SummaryCard label="Total submissions" value={latest.total} />
              <SummaryCard label="Turned in" value={latest.turnedIn} />
              <SummaryCard label="Returned" value={latest.returned} />
              <SummaryCard label="Late" value={latest.late} />
            </div>
          )}

          {/* CHARTS */}
          {chartData.length > 0 && (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "2fr 1fr",
                gap: "16px",
              }}
            >
              {/* Submissions over time */}
              <div
                style={{
                  border: "1px solid #ddd",
                  borderRadius: "8px",
                  padding: "8px",
                  height: "300px",
                }}
              >
                <div
                  style={{
                    fontSize: "13px",
                    fontWeight: 600,
                    marginBottom: "4px",
                  }}
                >
                  Submissions over time
                </div>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="total"
                      name="Total"
                      stroke="#2563eb"
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="turnedIn"
                      name="Turned in"
                      stroke="#16a34a"
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="returned"
                      name="Returned"
                      stroke="#9333ea"
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="late"
                      name="Late"
                      stroke="#dc2626"
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Grade distribution */}
              <div
                style={{
                  border: "1px solid #ddd",
                  borderRadius: "8px",
                  padding: "8px",
                  height: "300px",
                }}
              >
                <div
                  style={{
                    fontSize: "13px",
                    fontWeight: 600,
                    marginBottom: "4px",
                  }}
                >
                  Average grade over time
                </div>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="avgGrade" name="Avg grade" fill="#2563eb" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SummaryCard({ label, value }) {
  return (
    <div
      style={{
        border: "1px solid #ddd",
        borderRadius: "8px",
        padding: "8px 10px",
        fontSize: "12px",
        background: "#fafafa",
      }}
    >
      <div style={{ color: "#555", marginBottom: "4px" }}>{label}</div>
      <div style={{ fontWeight: 700, fontSize: "16px" }}>{value}</div>
    </div>
  );
}
