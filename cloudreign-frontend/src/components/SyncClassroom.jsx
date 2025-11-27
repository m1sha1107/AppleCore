import { useState } from "react";

export default function SyncClassroom() {
  const [result, setResult] = useState(null);

  async function runSync() {
    const res = await fetch("http://127.0.0.1:8000/sync/app", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ app: "classroom" }),
    });

    const data = await res.json();
    setResult(data);
  }

  return (
    <div>
      <h2>Sync Google Classroom</h2>
      <button onClick={runSync}>Run Sync</button>

      {result && (
        <pre>{JSON.stringify(result, null, 2)}</pre>
      )}
    </div>
  );
}
