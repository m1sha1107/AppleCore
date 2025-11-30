// src/App.jsx
import SyncClassroom from "./components/SyncClassroom";
import NLQueryBox from "./components/NLQueryBox";
import DashboardPreview from "./components/DashboardPreview";
import CourseAnalytics from "./components/CourseAnalytics";
// If you have a course detail component, you can import it here later.
// import CourseDetail from "./components/CourseDetail";

const appShell = {
  minHeight: "100vh",
  background: "#f3f4f6",
  color: "#0f172a",
  fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
};

const container = {
  maxWidth: "1200px",
  margin: "0 auto",
  padding: "24px 16px 40px",
};

const header = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  marginBottom: "24px",
};

const brand = {
  display: "flex",
  flexDirection: "column",
};

const appTitle = {
  fontSize: "24px",
  fontWeight: 700,
  letterSpacing: "-0.03em",
};

const appSubtitle = {
  fontSize: "13px",
  color: "#6b7280",
  marginTop: "4px",
};

const pill = {
  fontSize: "11px",
  padding: "4px 8px",
  borderRadius: "999px",
  border: "1px solid #cbd5f5",
  background: "#e0ecff",
  color: "#1d4ed8",
};

const card = {
  background: "#ffffff",
  borderRadius: "12px",
  padding: "16px 20px",
  marginBottom: "16px",
  boxShadow: "0 1px 3px rgba(15,23,42,0.08)",
  border: "1px solid #e5e7eb",
};

const sectionHeader = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "baseline",
  marginBottom: "10px",
};

const sectionTitle = {
  fontSize: "16px",
  fontWeight: 600,
};

const sectionCaption = {
  fontSize: "12px",
  color: "#6b7280",
};

export default function App() {
  return (
    <div style={appShell}>
      <div style={container}>
        {/* Top app header */}
        <header style={header}>
          <div style={brand}>
            <span style={appTitle}>CloudReign</span>
            <span style={appSubtitle}>
              Classroom analytics on top of BigQuery + Gemini.
            </span>
          </div>
          <span style={pill}>Internal prototype</span>
        </header>

        {/* Sync pipeline card */}
        <section style={card}>
          <div style={sectionHeader}>
            <h2 style={sectionTitle}>Sync Classroom</h2>
            <span style={sectionCaption}>
              Pull latest courses, enrollments, submissions and rebuild the
              dashboard table.
            </span>
          </div>
          <SyncClassroom />
        </section>

        {/* NL → SQL assistant card */}
        <section style={card}>
          <div style={sectionHeader}>
            <h2 style={sectionTitle}>Ask a question</h2>
            <span style={sectionCaption}>
              Natural language → Gemini → BigQuery SQL → results.
            </span>
          </div>
          <NLQueryBox />
        </section>

        {/* Dashboard preview card */}
        <section style={card}>
          <div style={sectionHeader}>
            <h2 style={sectionTitle}>Classroom dashboard table</h2>
            <span style={sectionCaption}>
              Live view of the aggregated rows from <code>dashboard_temp</code>.
            </span>
          </div>
          <DashboardPreview />
        </section>

        {/* Course analytics card */}
        <section style={card}>
          <div style={sectionHeader}>
            <h2 style={sectionTitle}>Course analytics</h2>
            <span style={sectionCaption}>
              Explore trends for individual courses over time.
            </span>
          </div>
          <CourseAnalytics />
        </section>

        {/* If/when you’re ready to wire the detail page, uncomment this block */}
        {/*
        <section style={card}>
          <div style={sectionHeader}>
            <h2 style={sectionTitle}>Course detail</h2>
            <span style={sectionCaption}>
              Drill into a single course: students, submissions, grades.
            </span>
          </div>
          <CourseDetail />
        </section>
        */}
      </div>
    </div>
  );
}
