// src/components/LookerDashboard.jsx
import { useState } from "react";

const LOOKER_EMBED_URL ="https://lookerstudio.google.com/embed/reporting/7b75f2e5-3f70-4a1a-92e0-88ff693d4ef5/page/4ZFhF"
export default function LookerDashboard({ height = 600 }) {
  // key trick forces iframe reload when we change key
  const [reloadKey, setReloadKey] = useState(0);

  const handleReload = () => {
    setReloadKey((k) => k + 1);
  };

  return (
    <section style={{ marginTop: "24px" }}>
      <h2>Looker Studio dashboard</h2>
      <p style={{ fontSize: "12px", color: "#555" }}>
        This is the production dashboard backed by <code>dashboard_temp</code>.
      </p>

      <button
        onClick={handleReload}
        style={{
          margin: "8px 0",
          padding: "4px 10px",
          cursor: "pointer",
        }}
      >
        Reload dashboard
      </button>

      <div
        style={{
          marginTop: "8px",
          border: "1px solid #ccc",
          borderRadius: "4px",
          overflow: "hidden",
        }}
      >
        <iframe
          key={reloadKey}
          title="CloudReign Classroom Dashboard"
          src={LOOKER_EMBED_URL}
          style={{
            width: "100%",
            height: `${height}px`,
            border: "0",
          }}
          allowFullScreen
        />
      </div>
    </section>
  );
}
