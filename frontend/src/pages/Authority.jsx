import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, dateLabel } from "../services/api";
import { Badge, ErrorBox } from "../components/Shared";
export default function Authority() {
  const [reports, setReports] = useState([]),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true),
    [key, setKey] = useState(sessionStorage.getItem("authorityKey") || ""),
    [saved, setSaved] = useState(false),
    [filter, setFilter] = useState(""),
    [mode, setMode] = useState("");
  useEffect(() => {
    Promise.all([api("/reports"), api("/health")])
      .then(([r, h]) => {
        setReports(r);
        setMode(h.authority_mode);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);
  return (
    <main className="page">
      <div className="page-heading">
        <div className="eyebrow">AUTHORITY WORKSPACE</div>
        <h1>From observation to action.</h1>
        <p>
          Review incoming observations, inspect downstream exposure, and record
          your decision.
        </p>
      </div>
      <div className="notice">
        {mode === "demo"
          ? "Demo authority mode is enabled. Status changes are available to all prototype users."
          : "Authority actions require the configured key."}{" "}
        Verification is separate from potential impact priority.
      </div>
      <details className="card">
        <summary>Authority access settings</summary>
        <label>
          Authority key
          <input
            type="password"
            value={key}
            onChange={(e) => {
              setKey(e.target.value);
              setSaved(false);
            }}
            autoComplete="off"
          />
        </label>
        <button
          className="button secondary"
          onClick={() => {
            sessionStorage.setItem("authorityKey", key);
            setSaved(true);
          }}
        >
          Save for this session
        </button>
        {saved && <span role="status"> Key saved.</span>}
      </details>
      <ErrorBox error={error} />
      <div className="stat-grid">
        {[
          [
            "Awaiting review",
            reports.filter((r) => r.status === "UNVERIFIED").length,
          ],
          [
            "Under review",
            reports.filter((r) => r.status === "UNDER REVIEW").length,
          ],
          ["Verified", reports.filter((r) => r.status === "VERIFIED").length],
          ["Resolved", reports.filter((r) => r.status === "RESOLVED").length],
        ].map(([name, count]) => (
          <div className="stat" key={name}>
            <span>{name}</span>
            <strong>{count}</strong>
          </div>
        ))}
      </div>
      <section className="card">
        <div className="section-title">
          <h2>Incoming observations</h2>
          <select
            aria-label="Authority status filter"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
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
        </div>
        {loading ? (
          <p>Loading observations…</p>
        ) : !reports.filter((r) => !filter || r.status === filter).length ? (
          <p>No observations match this status.</p>
        ) : (
          reports
            .filter((r) => !filter || r.status === filter)
            .map((r) => (
              <Link
                className="report-row"
                key={r.id}
                to={"/reports/" + r.id + "?authority=1"}
              >
                <div>
                  <b>{r.contamination_type}</b>
                  <small>
                    {r.id} · {r.segment_id} · {dateLabel(r.created_at)}
                  </small>
                </div>
                <div>
                  <small>Observation</small>
                  <Badge value={r.status} />
                </div>
                <div>
                  <small>Potential impact</small>
                  <Badge value={r.priority_level} />
                </div>
                <span>Review →</span>
              </Link>
            ))
        )}
      </section>
    </main>
  );
}
