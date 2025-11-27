import { useState } from "react";

export default function NLQueryBox() {
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState(null);

  async function ask() {
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
    setResponse(data);
  }

  return (
    <div>
      <h2>Ask a Question</h2>
      <input
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="e.g., Show average grades per course"
        style={{ width: "300px" }}
      />
      <button onClick={ask}>Ask</button>

      {response && (
        <pre>{JSON.stringify(response, null, 2)}</pre>
      )}
    </div>
  );
}
