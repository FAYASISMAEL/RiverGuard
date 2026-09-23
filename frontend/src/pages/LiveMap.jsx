import { useEffect, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { Plus, RefreshCw } from "lucide-react";
import RiverMap from "../map/RiverMap";
import { api, categories } from "../services/api";
import { ImpactPanel, ErrorBox } from "../components/Shared";
export default function LiveMap() {
  const [params, setParams] = useSearchParams();
  const [reports, setReports] = useState([]),
    [status, setStatus] = useState(""),
    [category, setCategory] = useState(""),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true);
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
  }, []);
  const filtered = reports.filter(
    (r) =>
      (!status || r.status === status) &&
      (!category || r.contamination_type === category),
  );
  const selected = filtered.find((r) => r.id === params.get("report"));
  return (
    <main className="page map-page">
      <div className="page-heading">
        <div className="eyebrow">PERIYAR / COMMUNITY OBSERVATIONS</div>
        <h1>The river, in view.</h1>
        <p>
          Explore observations and follow their potential downstream impact.
        </p>
      </div>
      <div className="filterbar">
        <select
          aria-label="Filter status"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="">All observation statuses</option>
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
        <select
          aria-label="Filter contamination"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        >
          <option value="">All contamination types</option>
          {categories.map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
        <span className="muted">
          {loading ? "Loading…" : filtered.length + " observations"}
        </span>
        <button
          className="icon-button"
          aria-label="Refresh reports"
          onClick={load}
        >
          <RefreshCw size={17} />
        </button>
        <Link className="button" to="/report">
          <Plus size={16} />
          New report
        </Link>
      </div>
      <ErrorBox error={error} />
      <div className="map-layout">
        <div>
          <RiverMap
            reports={filtered}
            selected={selected}
            onReport={(r) => setParams({ report: r.id })}
          />
          <div className="report-strip">
            {!filtered.length && !loading && (
              <p>
                No observations match. Submit a report or load the demo from
                Overview.
              </p>
            )}
            {filtered.map((r) => (
              <button
                key={r.id}
                className={selected?.id === r.id ? "selected" : ""}
                onClick={() => setParams({ report: r.id })}
              >
                <span className="tiny-dot" />
                {r.contamination_type}
                <small>
                  {r.segment_id} · {r.status}
                </small>
              </button>
            ))}
          </div>
        </div>
        <aside className="panel">
          <ImpactPanel report={selected} />
        </aside>
      </div>
    </main>
  );
}
