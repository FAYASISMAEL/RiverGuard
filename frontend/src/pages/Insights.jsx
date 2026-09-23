import { useEffect, useState } from "react";
import { api, categories } from "../services/api";
import { ErrorBox, Badge } from "../components/Shared";
export default function Insights() {
  const [reports, setReports] = useState([]),
    [hotspots, setHotspots] = useState([]),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true);
  useEffect(() => {
    Promise.all([api("/reports"), api("/hotspots")])
      .then(([r, h]) => {
        setReports(r);
        setHotspots(h);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);
  const days = Array.from({ length: 7 }, (_, i) => {
    let d = new Date();
    d.setDate(d.getDate() - 6 + i);
    return d.toISOString().slice(0, 10);
  });
  const countByDate = (day) =>
    reports.filter((r) => r.created_at.startsWith(day)).length;
  const max = Math.max(1, ...days.map(countByDate));
  const segments = {};
  reports.forEach((r) =>
    r.impact.downstream_segments.forEach((s) => {
      segments[s] = (segments[s] || 0) + 1;
    }),
  );
  return (
    <main className="page">
      <div className="page-heading">
        <div className="eyebrow">PATTERNS, NOT ASSUMPTIONS</div>
        <h1>A clearer picture over time.</h1>
        <p>
          Understand where observations repeat and which stretches are
          frequently in the downstream path.
        </p>
      </div>
      <ErrorBox error={error} />
      <div className="notice">
        Frequency measures citizen reporting activity. It does not confirm
        pollution or measure water quality. Rejected reports remain in these
        activity counts.
      </div>
      {loading ? (
        <p>Loading insights…</p>
      ) : (
        <>
          <div className="stat-grid">
            <div className="stat">
              <span>Total observations</span>
              <strong>{reports.length}</strong>
            </div>
            <div className="stat">
              <span>Reported segments</span>
              <strong>{hotspots.length}</strong>
            </div>
            <div className="stat">
              <span>Repeated locations</span>
              <strong>{hotspots.filter((h) => h.total > 1).length}</strong>
            </div>
            <div className="stat">
              <span>Verified observations</span>
              <strong>
                {reports.filter((r) => r.status === "VERIFIED").length}
              </strong>
            </div>
          </div>
          <div className="two-col">
            <section className="card">
              <h2>Reports over the last 7 days</h2>
              <p className="muted small">Submission dates · UTC</p>
              <div className="bar-chart">
                {days.map((day) => (
                  <div key={day}>
                    <b>{countByDate(day)}</b>
                    <div
                      className="bar"
                      style={{
                        height: Math.max(3, (countByDate(day) / max) * 130),
                      }}
                    />
                    <small>{day.slice(5)}</small>
                  </div>
                ))}
              </div>
            </section>
            <section className="card">
              <h2>What people are observing</h2>
              {categories
                .filter((c) => reports.some((r) => r.contamination_type === c))
                .map((c) => (
                  <div className="category-row" key={c}>
                    <span>{c}</span>
                    <meter
                      value={
                        reports.filter((r) => r.contamination_type === c).length
                      }
                      min="0"
                      max={reports.length}
                    />
                    <b>
                      {reports.filter((r) => r.contamination_type === c).length}
                    </b>
                  </div>
                ))}
              {!reports.length && (
                <p>Categories will appear after the first observation.</p>
              )}
            </section>
            <section className="card">
              <h2>Repeated report locations</h2>
              {hotspots
                .sort((a, b) => b.total - a.total)
                .map((h) => (
                  <div className="hotspot" key={h.segment_id}>
                    <div>
                      <b>{h.segment_id}</b>
                      <p>
                        Reports in this area: {h.total}
                        <br />
                        Reports in last 30 days: {h.last_30_days}
                      </p>
                    </div>
                    <Badge value={h.frequency} />
                  </div>
                ))}
              {!hotspots.length && <p>No reported locations yet.</p>}
            </section>
            <section className="card">
              <h2>Frequently affected river segments</h2>
              <p className="muted small">
                Number of analyses whose downstream route includes this segment.
              </p>
              {Object.entries(segments)
                .sort((a, b) => b[1] - a[1])
                .map(([s, n]) => (
                  <div className="category-row" key={s}>
                    <b>{s}</b>
                    <meter
                      value={n}
                      min="0"
                      max={Math.max(1, reports.length)}
                    />
                    <span>{n}</span>
                  </div>
                ))}
              {!reports.length && <p>Downstream patterns will appear here.</p>}
            </section>
          </div>
        </>
      )}
    </main>
  );
}
