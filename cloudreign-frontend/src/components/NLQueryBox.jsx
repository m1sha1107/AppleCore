// src/components/NLQueryBox.jsx
import { useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

export default function NLQueryBox() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null); // { sql, row_count, data }

  async function handleAsk(e) {
    e.preventDefault();
    setError("");
    setResult(null);

    const trimmed = question.trim();
    if (!trimmed) {
      setError("Please type a question first.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/query/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          app: "classroom",
          question: trimmed,
          max_rows: 100,
        }),
      });

      const json = await res.json();

      if (!res.ok || json.status !== "ok") {
        throw new Error(json.error || json.message || "Query failed");
      }

      setResult({
        sql: json.sql,
        row_count: json.row_count,
        data: json.data,
      });
    } catch (err) {
      console.error(err);
      setError(err.message || "Failed to run NL query");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section style={{ marginTop: "20px" }}>
      <h2>Ask a Question (NL → SQL → BigQuery)</h2>

      <form onSubmit={handleAsk} style={{ display: "flex", gap: "8px" }}>
        <input
          type="text"
          style={{ flex: 1 }}
          placeholder="e.g. Which course had the most late submissions last week?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <button type="submit" disabled={loading}>
          {loading ? "Asking..." : "Ask"}
        </button>
      </form>

      {error && (
        <div
          style={{
            marginTop: "8px",
            padding: "6px 8px",
            border: "1px solid red",
            color: "red",
            fontSize: "0.9rem",
          }}
        >
          {error}
        </div>
      )}

      {result && (
        <div style={{ marginTop: "12px", fontSize: "0.9rem" }}>
          <div style={{ marginBottom: "6px" }}>
            <strong>Generated SQL:</strong>
            <pre
              style={{
                background: "#f5f5f5",
                padding: "8px",
                overflowX: "auto",
              }}
            >
{result.sql}
            </pre>
          </div>

          <div style={{ marginBottom: "4px" }}>
            <strong>Rows returned:</strong> {result.row_count}
          </div>

          {result.row_count > 0 && (
            <table
              style={{
                marginTop: "6px",
                borderCollapse: "collapse",
                width: "100%",
                fontSize: "0.85rem",
              }}
            >
              <thead>
                <tr>
                  {Object.keys(result.data[0]).map((col) => (
                    <th
                      key={col}
                      style={{
                        border: "1px solid #ddd",
                        padding: "4px 6px",
                        textAlign: "left",
                        background: "#fafafa",
                      }}
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.data.map((row, idx) => (
                  <tr key={idx}>
                    {Object.keys(result.data[0]).map((col) => (
                      <td
                        key={col}
                        style={{ border: "1px solid #eee", padding: "4px 6px" }}
                      >
                        {row[col] === null ? "" : String(row[col])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </section>
  );
}
