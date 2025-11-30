// src/components/DashboardPreview.jsx
import { useEffect, useMemo, useState } from "react";

const API_BASE =
  import.meta.env.VITE_BACKEND_URL || "http://127.0.0.1:8000";

export default function DashboardPreview() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [limit, setLimit] = useState(50);
  const [selectedCourseId, setSelectedCourseId] = useState("ALL");
  const [backendRowCount, setBackendRowCount] = useState(null);

  // --- derived: unique course options ---
  const courseOptions = useMemo(() => {
    const map = new Map(); // course_id -> label
    rows.forEach((r) => {
      if (!r.course_id) return;
      const label = `${r.course_name || "(no name)"}${
        r.section ? ` – ${r.section}` : ""
      }`;
      if (!map.has(r.course_id)) {
        map.set(r.course_id, label);
      }
    });
    return Array.from(map.entries()).map(([id, label]) => ({ id, label }));
  }, [rows]);

  const filteredRows = useMemo(() => {
    if (selectedCourseId === "ALL") return rows;
    return rows.filter((r) => String(r.course_id) === String(selectedCourseId));
  }, [rows, selectedCourseId]);

  async function fetchDashboard() {
    try {
      setLoading(true);
      setError("");
      setBackendRowCount(null);

      const res = await fetch(`${API_BASE}/query/checkpoint`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          app: "classroom",
          limit: Number(limit) || 50,
        }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(
          `Backend HTTP ${res.status}: ${text || res.statusText}`
        );
      }

      const json = await res.json();
      console.log("checkpoint response:", json);

      if (json.status && json.status !== "ok") {
        throw new Error(json.message || `Backend status: ${json.status}`);
      }

      const data = Array.isArray(json.data) ? json.data : [];
      setRows(data);
      setBackendRowCount(
        typeof json.row_count === "number" ? json.row_count : data.length
      );
    } catch (err) {
      console.error("Failed to fetch dashboard_temp:", err);
      setError(err instanceof Error ? err.message : "Failed to fetch data.");
      setRows([]);
    } finally {
      setLoading(false);
    }
  }

  // initial load
  useEffect(() => {
    fetchDashboard();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <section style={{ marginTop: "24px" }}>
      <h2 style={{ marginBottom: "4px" }}>Classroom dashboard data</h2>
      <p style={{ marginTop: 0, fontSize: "12px", color: "#555" }}>
        Live view of aggregated metrics from <code>dashboard_temp</code>.
      </p>

      {/* controls row */}
      <div
        style={{
          display: "flex",
          gap: "12px",
          alignItems: "center",
          marginBottom: "8px",
        }}
      >
        <label style={{ fontSize: "12px" }}>
          Course:&nbsp;
          <select
            value={selectedCourseId}
            onChange={(e) => setSelectedCourseId(e.target.value)}
          >
            <option value="ALL">All courses</option>
            {courseOptions.map((c) => (
              <option key={c.id} value={c.id}>
                {c.label}
              </option>
            ))}
          </select>
        </label>

        <label style={{ fontSize: "12px" }}>
          Rows:&nbsp;
          <input
            type="number"
            min={1}
            max={500}
            value={limit}
            onChange={(e) => setLimit(e.target.value)}
            style={{ width: "64px" }}
          />
        </label>

        <button onClick={fetchDashboard} disabled={loading}>
          {loading ? "Loading..." : "Refresh"}
        </button>

        <span style={{ fontSize: "12px", color: "#555" }}>
          Showing {filteredRows.length} rows
          {backendRowCount !== null ? ` (backend row_count=${backendRowCount})` : ""}
        </span>
      </div>

      {/* error banner */}
      {error && (
        <div
          style={{
            border: "1px solid #e00",
            background: "#ffecec",
            color: "#a00",
            padding: "4px 8px",
            marginBottom: "8px",
            fontSize: "12px",
          }}
        >
          Failed to fetch: {error}
        </div>
      )}

      {/* data table */}
      <div style={{ overflowX: "auto" }}>
        <table
          style={{
            borderCollapse: "collapse",
            width: "100%",
            fontSize: "12px",
          }}
        >
          <thead>
            <tr style={{ background: "#f5f5f5" }}>
              <th style={th}>Metric date</th>
              <th style={th}>Course</th>
              <th style={th}>Section</th>
              <th style={th}>Primary teacher</th>
              <th style={th}>Students</th>
              <th style={th}>Total submissions</th>
              <th style={th}>Turned in</th>
              <th style={th}>Returned</th>
              <th style={th}>Late</th>
              <th style={th}>Avg grade</th>
              <th style={th}>Max grade</th>
              <th style={th}>Ingested at</th>
            </tr>
          </thead>
          <tbody>
            {filteredRows.length === 0 && !loading && !error && (
              <tr>
                <td style={td} colSpan={12}>
                  No data available. Try running sync and then Refresh.
                </td>
              </tr>
            )}
            {filteredRows.map((row, idx) => (
              <tr key={idx}>
                <td style={td}>
                  {row.metric_date
                    ? String(row.metric_date).slice(0, 10)
                    : ""}
                </td>
                <td style={td}>{row.course_name}</td>
                <td style={td}>{row.section}</td>
                <td style={td}>{row.primary_teacher_email}</td>
                <td style={td}>{row.total_students}</td>
                <td style={td}>{row.total_submissions}</td>
                <td style={td}>{row.turned_in_submissions}</td>
                <td style={td}>{row.returned_submissions}</td>
                <td style={td}>{row.late_submissions}</td>
                <td style={td}>
                  {row.avg_grade != null
                    ? Number(row.avg_grade).toFixed(2)
                    : ""}
                </td>
                <td style={td}>{row.max_grade}</td>
                <td style={td}>
                  {row.ingestion_time
                    ? String(row.ingestion_time).replace("T", " ")
                    : ""}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

const th = {
  border: "1px solid #ddd",
  padding: "4px 6px",
  textAlign: "left",
  whiteSpace: "nowrap",
};

const td = {
  border: "1px solid #eee",
  padding: "4px 6px",
  whiteSpace: "nowrap",
};
