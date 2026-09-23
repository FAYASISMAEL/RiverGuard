import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, categories } from "../services/api";
import { ErrorBox } from "../components/Shared";
import ReportCards from "../components/ReportCards";
export default function History() {
  const [reports, setReports] = useState([]),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [search, setSearch] = useState(""),
    [status, setStatus] = useState("");
  async function load() {
    setLoading(true);
    setError("");
    try {
      setReports(await api("/reports"));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    load();
    const refresh = () => load();
    window.addEventListener("focus", refresh);
    return () => window.removeEventListener("focus", refresh);
  }, []);
  const filtered = reports.filter(
    (r) =>
      (!status || r.status === status) &&
      `${r.id} ${r.case?.id || ""} ${r.location_name} ${r.segment_id} ${r.contamination_type}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  return (
    <main className="page">
      <div className="page-heading">
        <div className="eyebrow">OBSERVE. REPORT. STAY INFORMED.</div>
        <h1>Every observation has a story.</h1>
        <p>
          Track submitted reports, review their potential impact, and follow the
          latest verification status.
        </p>
      </div>
      <div className="filterbar">
        <input
          aria-label="Search history"
          placeholder="Search report, case or location"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          aria-label="History status"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="">All statuses</option>
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
        <button className="button secondary" onClick={load} disabled={loading}>
          Refresh history
        </button>
      </div>
      <ErrorBox error={error} />
      {loading ? (
        <p>Loading report history…</p>
      ) : filtered.length ? (
        <ReportCards reports={filtered} />
      ) : (
        <div className="empty">
          <h2>No matching observations yet.</h2>
          <Link className="button" to="/map">
            Explore the river map
          </Link>
        </div>
      )}
    </main>
  );
}
