// src/App.jsx
import SyncClassroom from "./components/SyncClassroom";
import NLQueryBox from "./components/NLQueryBox";
import DashboardPreview from "./components/DashboardPreview";
import LookerDashboard from "./components/LookerDashboard";

export default function App() {
  return (
    <div style={{ padding: "20px", fontFamily: "Arial" }}>
      <h1>CloudReign</h1>

      <SyncClassroom />
      <hr />

      <NLQueryBox />
      <hr />

      <DashboardPreview />
      <hr />

      <LookerDashboard />
    </div>
  );
}
