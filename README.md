# **AppleCore — Google Classroom Analytics Platform**

*A full-stack analytics system for schools, powered by Google Classroom, FastAPI, BigQuery, Gemini, and React.*

---

## **Overview**

AppleCore turns raw Google Classroom data into insightful dashboards, time-series visualizations, and natural-language analytics powered by Gemini.

It includes:

-   **Data ingestion** from Google Classroom → BigQuery
-   **Daily metrics** per course
-   **Interactive dashboards** (React + Recharts)
-   **Natural language → SQL → Charts** querying
-   **Course analytics** (submissions, grades, timelines)
-   **Looker Studio integration**
-   Clean modular backend (FastAPI) and frontend (React/Vite)

---

## **Project Structure**

```
/CloudReign│├── backend/               # FastAPI backend│   ├── main.py            # All API routes + Classroom ingestion│   ├── requirements.txt  │   └── ...               │├── cloudreign-frontend/   # React + Vite frontend│   ├── src/│   │   ├── App.jsx│   │   ├── components/│   │   │    ├── SyncClassroom.jsx│   │   │    ├── NLQueryBox.jsx│   │   │    ├── DashboardPreview.jsx│   │   │    ├── CourseAnalytics.jsx│   │   │    └── CourseDetail.jsx│   │   └── main.jsx│   └── package.json│└── README.md
```

---

## **Features**

### **1. Google Classroom Sync**

-   Courses
-   Students & teachers
-   Assignments
-   Submissions
-   Aggregated daily metrics

Accessible via:

```
POST /sync/app
```

---

### **2. Dashboard Preview**

Displays the **dashboard_temp** BigQuery table live:

-   Metrics per course
-   Teacher email
-   Total submissions
-   Late/returned/turned-in counts
-   Grade metrics
-   Filter by course
-   Adjustable row limit

---

### **3. Course Analytics Dashboard**

For every course:

-   Student count
-   Submission activity over time
-   Grades over time
-   Late work tracking
-   Daily time-series charts

Uses:

```
GET  /analytics/coursesPOST /analytics/course_timeseries
```

---

### **4. Course Detail View**

Per-course breakdown:

-   Course metadata
-   Enrolled students
-   Assignments & submissions

Uses:

```
POST /analytics/course_detail
```

---

### **5. Natural Language Queries (Gemini)**

Ask questions like:

> “Show me the top 5 courses by late submissions last month.”

Pipeline:

1.  User writes NL question
    
2.  `/query/run` sends prompt to Gemini
    
3.  Gemini returns executable BigQuery SQL
    
4.  Backend executes SQL
    
5.  Frontend:
    
    -   Shows SQL
    -   Shows table
    -   Builds charts automatically (line or bar)

---

### **6. Looker Studio Embeds**

You can embed any Looker dashboard via iframe.

---

## ** Technology Stack**

### **Backend**

-   Python
-   FastAPI
-   Google API Client (Classroom)
-   BigQuery
-   Gemini (Generative AI)
-   Uvicorn

### **Frontend**

-   React + Vite
-   Recharts (graphs)
-   Fetch API
-   Modern grid-based UI

---

## ** BigQuery Tables**

During sync, the following tables are populated:

Table

Description

`classroom_courses`

Course metadata

`classroom_enrollments`

Students + teachers in each course

`classroom_submissions`

Assignment submissions per student

`dashboard_temp`

Aggregated daily metrics (used for dashboard)

---

## ** API Endpoints**

### **Sync**

```
POST /sync/app
```

---

### **Dashboard Query**

```
POST /query/checkpoint
```

---

### **Natural Language Query**

```
POST /query/run
```

Returns:

-   `sql` (generated)
-   `data`
-   `status`
-   `error` (if any)

---

### **Analytics**

```
GET  /analytics/coursesPOST /analytics/course_timeseriesPOST /analytics/course_detail
```

---

## ** Backend Setup**

### **1. Install dependencies**

```
cd backendpip install -r requirements.txt
```

### **2. Set environment variables**

You need:

```
GOOGLE_APPLICATION_CREDENTIALS=service-account.jsonPROJECT_ID=your-gcp-projectBQ_DATASET=workspace_analyticsGEMINI_API_KEY=your_key
```

### **3. Run FastAPI**

```
uvicorn backend.main:app --reload --port 8000
```

Backend will start on:

```
http://127.0.0.1:8000
```

---

## ** Frontend Setup**

### **1. Install**

```
cd cloudreign-frontendnpm install
```

### **2. Configure .env**

```
VITE_BACKEND_URL=http://127.0.0.1:8000VITE_GEMINI_API_KEY=your_key
```

### **3. Run**

```
npm run dev
```

---

## ** How Everything Works (End-to-End)**

1.  User clicks **Sync Classroom**
2.  Backend fetches Classroom data
3.  Stores processed data into BigQuery
4.  DashboardPreview loads aggregated data from BigQuery
5.  CourseAnalytics shows charts using `/analytics/course_timeseries`
6.  NLQueryBox → Gemini → SQL → BigQuery → charts
7.  Everything updates in real time

---

## ** Component Overview**

### **SyncClassroom.jsx**

Runs the backend sync.

### **DashboardPreview.jsx**

Live table of aggregated metrics.

### **CourseAnalytics.jsx**

Charts per-course activity.

### **NLQueryBox.jsx**

Natural language → SQL → table → chart.

### **CourseDetail.jsx**

Detailed course view (metadata + students).

---

## ** Roadmap**

-   Tailwind styling pass
-   Saved queries
-   CSV export
-   Google OAuth login
-   Better error messages
-   More chart types (scatter, stacked bar)

---

## ** Contributing**

## PRs and issues welcome.

## **License**

MIT License.