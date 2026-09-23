import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { api, categories, localDay } from "../services/api";
import { ErrorBox } from "../components/Shared";
import ReportCards from "../components/ReportCards";
import ReportTable from "../components/ReportTable";
export default function AdminDashboard() {
  const { pathname } = useLocation();
  const mode = pathname.endsWith("/cases")
    ? "cases"
    : pathname.endsWith("/reports")
      ? "reports"
      : "dashboard";
  const [reports, setReports] = useState([]),
    [summary, setSummary] = useState(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({
    status: "",
    category: "",
    priority: "",
    date: "",
    segment: "",
    search: "",
  });
  function control(key) {
    return {
      value: filter[key],
      onChange: (e) => setFilter({ ...filter, [key]: e.target.value }),
    };
  }
  async function load() {
    setLoading(true);
    setError("");
    try {
      if (mode === "dashboard") {
        const d = await api("/admin/dashboard");
        setSummary(d);
        setReports(d.recent);
      } else {
        setReports(await api("/admin/" + mode));
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    load();
  }, [mode]);
  const today = localDay(new Date().toISOString());
  const filtered = reports.filter((r) => {
    const day = localDay(r.created_at);
    return (
      (!filter.status ||
        (filter.status === "TODAY"
          ? day === today
          : r.status === filter.status)) &&
      (!filter.category || r.contamination_type === filter.category) &&
      (!filter.priority || r.priority_level === filter.priority) &&
      (!filter.date || day === filter.date) &&
      (!filter.segment || r.segment_id === filter.segment) &&
      `${r.id} ${r.case?.id || ""} ${r.location_name} ${r.segment_id}`
        .toLowerCase()
        .includes(filter.search.toLowerCase())
    );
  });
  return (
    <main className="page">
      <div className="page-heading">
        <div className="eyebrow">ADMIN / {mode.toUpperCase()}</div>
        <h1>
          {mode === "dashboard"
            ? "From observation to action."
            : mode === "cases"
              ? "Case files. Connected history."
              : "Review citizen observations."}
        </h1>
        <p>
          {mode === "cases"
            ? "Every case stays linked to its original report and append-only timeline."
            : "Inspect the evidence, follow the river, and record your decision."}
        </p>
      </div>
      <ErrorBox error={error} />
      {mode === "dashboard" && summary && (
        <div className="stat-grid admin-stats">
          {[
            ["Total Reports", summary.total],
            ["Unverified Reports", summary.statuses.UNVERIFIED],
            ["Under Review", summary.statuses["UNDER REVIEW"]],
            ["Verified Cases", summary.statuses.VERIFIED],
            ["Rejected Cases", summary.statuses.REJECTED],
            ["Resolved Cases", summary.statuses.RESOLVED],
            ["High Risk", summary.high],
            ["Critical Risk", summary.critical],
          ].map(([label, n]) => (
            <div className="stat" key={label}>
              <span>{label}</span>
              <strong>{n}</strong>
            </div>
          ))}
        </div>
      )}
      {mode === "dashboard" ? (
        <h2>Recent reports</h2>
      ) : (
        <div className="admin-filters">
          <input
            aria-label="Search reports"
            placeholder="Report ID, Case ID or location"
            {...control("search")}
          />
          <select aria-label="Report status filter" {...control("status")}>
            <option value="">All</option>
            <option value="TODAY">Today</option>
            {[
              "UNVERIFIED",
              "UNDER REVIEW",
              "VERIFIED",
              "REJECTED",
              "RESOLVED",
            ].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
          <select aria-label="Contamination filter" {...control("category")}>
            <option value="">All contamination types</option>
            {categories.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
          <select aria-label="Priority filter" {...control("priority")}>
            <option value="">All priorities</option>
            {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
          <input aria-label="Submitted date" type="date" {...control("date")} />
          <select aria-label="River segment filter" {...control("segment")}>
            <option value="">All river segments</option>
            {[...new Set(reports.map((r) => r.segment_id))].sort().map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
          <button
            className="button secondary"
            onClick={() =>
              setFilter({
                status: "",
                category: "",
                priority: "",
                date: "",
                segment: "",
                search: "",
              })
            }
          >
            Clear filters
          </button>
        </div>
      )}
      <div className="section-title">
        <p className="muted">
          {loading ? "Loading…" : filtered.length + " reports"}
        </p>
        <button className="button secondary" onClick={load} disabled={loading}>
          Refresh
        </button>
      </div>
      {!loading &&
        (filtered.length ? (
          <ReportTable reports={filtered} />
        ) : (
          <div className="empty">
            <h2>No matching {mode === "cases" ? "case files" : "reports"}.</h2>
            <p>
              Case files are created when an admin starts a review or verifies a
              report.
            </p>
          </div>
        ))}
    </main>
  );
}
