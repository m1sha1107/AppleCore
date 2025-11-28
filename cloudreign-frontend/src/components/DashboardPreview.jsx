import { useState } from "react";

export default function DashboardPreview() {
  const [rows, setRows] = useState(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    setRows(null);

    try {
      const res = await fetch("http://127.0.0.1:8000/query/checkpoint", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          app: "classroom",
          limit: 10,
        }),
      });

      const data = await res.json();
      setRows(data);
    } catch (err) {
      setRows({ status: "error", message: err.message });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h2>Dashboard Preview (Last 10 Rows)</h2>
      <button onClick={load} disabled={loading}>
        {loading ? "Loading..." : "Load Data"}
      </button>

      {rows && (
        <pre style={{ background: "#eee", padding: "10px", marginTop: "10px" }}>
          {JSON.stringify(rows, null, 2)}
        </pre>
      )}
    </div>
  );
}
