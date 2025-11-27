import { useState } from "react";

export default function DashboardPreview() {
  const [data, setData] = useState(null);

  async function load() {
    const res = await fetch("http://127.0.0.1:8000/query/checkpoint", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        app: "classroom",
        limit: 20,
      }),
    });

    const rows = await res.json();
    setData(rows);
  }

  return (
    <div>
      <h2>Dashboard Preview</h2>
      <button onClick={load}>Load Preview</button>

      {data && (
        <pre>{JSON.stringify(data, null, 2)}</pre>
      )}
    </div>
  );
}
