import { useState } from "react";

export default function NLQueryBox() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  async function ask() {
    if (!question.trim()) return;

    setLoading(true);
    setResult(null);

    try {
      const res = await fetch("http://127.0.0.1:8000/query/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          app: "classroom",
          question,
          max_rows: 50,
        }),
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
      <h2>Ask a Question (NL → SQL → BigQuery)</h2>

      <input
        type="text"
        placeholder="Ask something like: show top 5 courses"
        style={{ width: "70%", padding: "5px" }}
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
      />

      <button onClick={ask} disabled={loading} style={{ marginLeft: "10px" }}>
        {loading ? "Thinking..." : "Ask"}
      </button>

      {result && (
        <pre style={{ background: "#eee", padding: "10px", marginTop: "10px" }}>
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}
