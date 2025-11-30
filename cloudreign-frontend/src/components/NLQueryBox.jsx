import { useState, useMemo } from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const BASE_URL =
  import.meta.env.VITE_BACKEND_URL || "http://127.0.0.1:8000";

export default function NLQueryBox() {
  const [question, setQuestion] = useState(
    "Which courses had the most late submissions in the last 7 days?"
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [sql, setSql] = useState("");
  const [rows, setRows] = useState([]);
  const [activeTab, setActiveTab] = useState("chart"); // chart | table | sql

  async function runQuery(e) {
    e.preventDefault();
    if (!question.trim()) return;

    try {
      setLoading(true);
      setError("");
      setSql("");
      setRows([]);

      const res = await fetch(`${BASE_URL}/query/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          app: "classroom",
          question,
          max_rows: 200,
        }),
      });

      const json = await res.json();

      if (!res.ok || json.status !== "ok") {
        throw new Error(
          json.error ||
            json.message ||
            `HTTP ${res.status}: ${JSON.stringify(json)}`
        );
      }

      setSql(json.sql || "");
      setRows(json.data || []);
      setActiveTab("chart");
    } catch (err) {
      console.error("NL query error:", err);
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  // ---- derive metadata from rows for chart + table ----
  const { columns, dateKey, numericKeys, chartData } = useMemo(() => {
    if (!rows || rows.length === 0) {
      return { columns: [], dateKey: null, numericKeys: [], chartData: [] };
    }

    const cols = Object.keys(rows[0] || {});

    // pick a date/time-like column for X axis if present
    const dKey =
      cols.find((k) =>
        k.toLowerCase().includes("date")
      ) ||
      cols.find((k) => k.toLowerCase().includes("time")) ||
      null;

    // numeric-ish columns (anything that parses to a number at least once)
    const numKeys = cols.filter((k) =>
      rows.some((r) => {
        const val = r[k];
        if (val === null || val === undefined || val === "") return false;
        return !isNaN(Number(val));
      })
    );

    const normalized = rows.map((r, idx) => {
      const obj = { ...r };
      if (dKey && r[dKey] != null) {
        obj[dKey] = String(r[dKey]).slice(0, 10);
      } else {
        obj._index = idx + 1;
      }
      numKeys.forEach((k) => {
        obj[k] = Number(r[k]) || 0;
      });
      return obj;
    });

    return {
      columns: cols,
      dateKey: dKey,
      numericKeys: numKeys,
      chartData: normalized,
    };
  }, [rows]);

  const hasChart = chartData.length > 0 && numericKeys.length > 0;

  // pick up to 3 numeric series to avoid clutter
  const seriesKeys = numericKeys.slice(0, 3);

  return (
    <section style={{ marginTop: "24px" }}>
      <h2 style={{ marginBottom: "4px" }}>Ask a Question (NL → SQL → BigQuery)</h2>

      <form
        onSubmit={runQuery}
        style={{
          display: "flex",
          gap: "8px",
          alignItems: "center",
          marginBottom: "12px",
        }}
      >
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask something like: show top 5 courses by late submissions"
          style={{
            flex: 1,
            padding: "6px 8px",
            fontSize: "14px",
            borderRadius: "4px",
            border: "1px solid #ccc",
          }}
        />
        <button
          type="submit"
          disabled={loading}
          style={{
            padding: "6px 14px",
            fontSize: "14px",
            borderRadius: "4px",
            border: "1px solid #2563eb",
            background: "#2563eb",
            color: "#fff",
            cursor: "pointer",
          }}
        >
          {loading ? "Running..." : "Ask"}
        </button>
      </form>

      {error && (
        <div
          style={{
            border: "1px solid #e11",
            background: "#fee2e2",
            padding: "6px 8px",
            marginBottom: "8px",
            fontSize: "13px",
            color: "#991b1b",
          }}
        >
          {error}
        </div>
      )}

      {/* Tabs */}
      <div
        style={{
          display: "flex",
          borderBottom: "1px solid #ddd",
          marginBottom: "8px",
          gap: "4px",
        }}
      >
        <TabButton
          label="Chart"
          active={activeTab === "chart"}
          onClick={() => setActiveTab("chart")}
        />
        <TabButton
          label="Table"
          active={activeTab === "table"}
          onClick={() => setActiveTab("table")}
        />
        <TabButton
          label="SQL"
          active={activeTab === "sql"}
          onClick={() => setActiveTab("sql")}
        />
        <div style={{ flex: 1 }} />
        {rows.length > 0 && (
          <span style={{ fontSize: "12px", color: "#555", padding: "4px 0" }}>
            {rows.length} rows
          </span>
        )}
      </div>

      {/* Content area */}
      <div
        style={{
          border: "1px solid #ddd",
          borderRadius: "6px",
          padding: "10px",
          background: "#fafafa",
          minHeight: "140px",
        }}
      >
        {/* Chart tab */}
        {activeTab === "chart" && (
          <>
            {!hasChart && (
              <p style={{ fontSize: "13px", color: "#555" }}>
                No obvious chart shape detected. Try asking for something with
                a date and numeric metrics, or switch to the Table / SQL tab.
              </p>
            )}

            {hasChart && (
              <div style={{ height: 320 }}>
                <ResponsiveContainer width="100%" height="100%">
                  {dateKey ? (
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey={dateKey} />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      {seriesKeys.map((k, idx) => (
                        <Line
                          key={k}
                          type="monotone"
                          dataKey={k}
                          name={k}
                          dot={false}
                          stroke={
                            ["#2563eb", "#16a34a", "#dc2626"][idx % 3]
                          }
                        />
                      ))}
                    </LineChart>
                  ) : (
                    <BarChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="_index" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      {seriesKeys.map((k, idx) => (
                        <Bar
                          key={k}
                          dataKey={k}
                          name={k}
                          fill={
                            ["#2563eb", "#16a34a", "#dc2626"][idx % 3]
                          }
                        />
                      ))}
                    </BarChart>
                  )}
                </ResponsiveContainer>
              </div>
            )}
          </>
        )}

        {/* Table tab */}
        {activeTab === "table" && (
          <>
            {rows.length === 0 ? (
              <p style={{ fontSize: "13px", color: "#555" }}>
                No rows. Ask a question first.
              </p>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table
                  style={{
                    borderCollapse: "collapse",
                    width: "100%",
                    fontSize: "12px",
                    background: "#fff",
                  }}
                >
                  <thead>
                    <tr style={{ background: "#f3f4f6" }}>
                      {columns.map((c) => (
                        <th
                          key={c}
                          style={{
                            border: "1px solid #e5e7eb",
                            padding: "4px 6px",
                            textAlign: "left",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {c}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r, idx) => (
                      <tr key={idx}>
                        {columns.map((c) => (
                          <td
                            key={c}
                            style={{
                              border: "1px solid #f3f4f6",
                              padding: "4px 6px",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {String(r[c] ?? "")}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}

        {/* SQL tab */}
        {activeTab === "sql" && (
          <>
            {!sql ? (
              <p style={{ fontSize: "13px", color: "#555" }}>
                No SQL yet. Ask a question to see what Gemini generates.
              </p>
            ) : (
              <pre
                style={{
                  fontFamily: "Menlo, Consolas, monospace",
                  fontSize: "12px",
                  margin: 0,
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                }}
              >
                {sql}
              </pre>
            )}
          </>
        )}
      </div>
    </section>
  );
}

function TabButton({ label, active, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        padding: "4px 10px",
        fontSize: "12px",
        borderRadius: "4px 4px 0 0",
        border: active ? "1px solid #2563eb" : "1px solid transparent",
        borderBottom: active ? "1px solid #fafafa" : "1px solid #ddd",
        background: active ? "#eff6ff" : "transparent",
        cursor: "pointer",
      }}
    >
      {label}
    </button>
  );
}
