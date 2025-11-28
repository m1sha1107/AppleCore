import { useState } from "react";

export default function SyncClassroom() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  async function runSync() {
    setLoading(true);
    setResult(null);

    try {
      const res = await fetch("http://127.0.0.1:8000/sync/app", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ app: "classroom" }),
      });

      const data = await res.json();
      setResult(data);
    } catch (err) {
      setResult({ status: "error", message: err.message });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h2>Sync Classroom</h2>
      <button onClick={runSync} disabled={loading}>
        {loading ? "Running..." : "Run Sync"}
      </button>

      {result && (
        <pre style={{ background: "#eee", padding: "10px" }}>
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}
