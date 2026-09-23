import { useEffect, useState } from "react";
import { useParams, useSearchParams, Link } from "react-router-dom";
import { api, patch, post, dateLabel, assetUrl } from "../services/api";
import { ImpactPanel, Badge, ErrorBox } from "../components/Shared";
import RiverMap from "../map/RiverMap";
export default function ReportDetail() {
  const { id } = useParams(),
    [params] = useSearchParams();
  const [r, setReport] = useState(null),
    [alerts, setAlerts] = useState([]),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [note, setNote] = useState("");
  const authority = params.get("authority") === "1";
  async function load() {
    try {
      const [a, b] = await Promise.all([
        api("/reports/" + id),
        api("/reports/" + id + "/alerts"),
      ]);
      setReport(a);
      setAlerts(b);
    } catch (e) {
      setError(e.message);
    }
  }
  useEffect(() => {
    load();
  }, [id]);
  async function action(fn) {
    setBusy(true);
    setError("");
    try {
      await fn();
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  const allowed = {
    UNVERIFIED: ["UNDER REVIEW", "VERIFIED", "REJECTED"],
    "UNDER REVIEW": ["VERIFIED", "REJECTED"],
    VERIFIED: ["RESOLVED"],
    REJECTED: [],
    RESOLVED: [],
  };
  return (
    <main className="page">
      <Link className="text-link" to={authority ? "/authority" : "/map"}>
        ← {authority ? "Authority dashboard" : "Back to map"}
      </Link>
      <ErrorBox error={error} />
      {!r ? (
        <p>{error ? "Report could not be loaded." : "Loading report…"}</p>
      ) : (
        <>
          {params.has("submitted") && (
            <div className="success">
              Your observation has been submitted. Its status is unverified;
              downstream analysis and simulated alerts are ready.
            </div>
          )}
          <div className="page-heading">
            <div className="eyebrow">OBSERVATION / {r.id}</div>
            <h1>{r.contamination_type}</h1>
            <p>
              Observed {dateLabel(r.observed_at)} · Submitted{" "}
              {dateLabel(r.created_at)}
            </p>
          </div>
          <div className="detail-grid">
            <div>
              <section className="card">
                <div className="status-row">
                  <h2>What was observed</h2>
                  <Badge value={r.status} />
                </div>
                <p>{r.description}</p>
                {r.image_url && (
                  <img
                    className="evidence"
                    src={assetUrl(r.image_url)}
                    alt="Citizen-submitted observation evidence"
                  />
                )}
                <p className="muted small">
                  Submitted location: {r.latitude.toFixed(6)},{" "}
                  {r.longitude.toFixed(6)}
                  <br />
                  Snapped location:{" "}
                  {r.impact.snapped_location.latitude.toFixed(6)},{" "}
                  {r.impact.snapped_location.longitude.toFixed(6)}
                </p>
              </section>
              <RiverMap reports={[r]} selected={r} compact />
              {authority && (
                <section className="card">
                  <div className="eyebrow">AUTHORITY WORKSPACE</div>
                  <h2>Review this observation</h2>
                  <label>
                    Review note
                    <textarea
                      value={note}
                      maxLength={1000}
                      onChange={(e) => setNote(e.target.value)}
                      placeholder="Record the reason for your decision"
                    />
                  </label>
                  <div className="button-row">
                    {allowed[r.status].map((status) => (
                      <button
                        className={
                          "button " +
                          (status === "REJECTED" ? "danger" : "secondary")
                        }
                        key={status}
                        disabled={busy}
                        onClick={() =>
                          action(() =>
                            patch("/reports/" + id + "/status", {
                              status,
                              note,
                            }),
                          )
                        }
                      >
                        {status === "UNDER REVIEW"
                          ? "Mark under review"
                          : status === "VERIFIED"
                            ? "Verify"
                            : status === "REJECTED"
                              ? "Reject"
                              : "Resolve"}
                      </button>
                    ))}
                  </div>
                  {!allowed[r.status].length && (
                    <p>This report has reached its final status.</p>
                  )}
                </section>
              )}
              <section className="card">
                <div className="section-title">
                  <h2>
                    Targeted alerts{" "}
                    <span className="count">{alerts.length}</span>
                  </h2>
                  {authority && (
                    <button
                      disabled={busy}
                      className="button secondary"
                      onClick={() =>
                        action(() => post("/reports/" + id + "/alerts"))
                      }
                    >
                      Generate alerts
                    </button>
                  )}
                </div>
                <p className="muted small">
                  Simulation only. No SMS, email, or public warning has been
                  sent.
                </p>
                {!alerts.length && (
                  <p>No mapped recipients are affected by this route.</p>
                )}
                {alerts.map((a) => (
                  <div className="alert-item" key={a.id}>
                    <div className="status-row">
                      <b>{a.target}</b>
                      <Badge value={a.state} />
                    </div>
                    <small>
                      {a.target_type.replaceAll("_", " ")} ·{" "}
                      {dateLabel(a.created_at)}
                    </small>
                    <details>
                      <summary>View alert message</summary>
                      <p>{a.message}</p>
                    </details>
                    {authority && a.state !== "Acknowledged" && (
                      <button
                        className="text-button"
                        disabled={busy}
                        onClick={() =>
                          action(() =>
                            patch("/alerts/" + a.id, {
                              state:
                                a.state === "Generated"
                                  ? "Sent - Simulated"
                                  : "Acknowledged",
                            }),
                          )
                        }
                      >
                        {a.state === "Generated"
                          ? "Send simulated alert"
                          : "Acknowledge alert"}{" "}
                        →
                      </button>
                    )}
                  </div>
                ))}
              </section>
              <section className="card">
                <h2>Observation timeline</h2>
                <ol className="timeline">
                  {r.timeline.map((e, i) => (
                    <li key={i}>
                      <b>{e.label}</b>
                      <time>{dateLabel(e.timestamp)}</time>
                      {e.note && <p>{e.note}</p>}
                    </li>
                  ))}
                </ol>
              </section>
            </div>
            <aside className="panel">
              <ImpactPanel report={r} details={false} />
            </aside>
          </div>
        </>
      )}
    </main>
  );
}
