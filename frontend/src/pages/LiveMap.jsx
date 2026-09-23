import { useEffect, useState, useRef } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { Plus, RefreshCw } from "lucide-react";
import RiverMap from "../map/RiverMap";
import { api, post, categories } from "../services/api";
import { ImpactPanel, ErrorBox } from "../components/Shared";
export default function LiveMap() {
  const [params, setParams] = useSearchParams();
  const sequence = useRef(0);
  const [point, setPoint] = useState(null),
    [preview, setPreview] = useState(null),
    [snapping, setSnapping] = useState(false),
    [observationType, setObservationType] = useState("Dead Fish"),
    [observedAt, setObservedAt] = useState(() => {
      const d = new Date();
      return new Date(d - d.getTimezoneOffset() * 60000)
        .toISOString()
        .slice(0, 16);
    });
  async function selectLocation(location) {
    const ticket = ++sequence.current;
    setParams({});
    setPoint(location);
    setPreview(null);
    setError("");
    setSnapping(true);
    try {
      const analysis = await post("/analyze", location);
      if (ticket === sequence.current) setPreview(analysis);
    } catch (e) {
      if (ticket === sequence.current) setError(e.message);
    } finally {
      if (ticket === sequence.current) setSnapping(false);
    }
  }
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
    if (params.has("lat") && params.has("lon")) {
      const latitude = Number(params.get("lat")),
        longitude = Number(params.get("lon"));
      if (Number.isFinite(latitude) && Number.isFinite(longitude))
        selectLocation({ latitude, longitude });
    }
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
            onReport={(r) => {
              sequence.current++;
              setPoint(null);
              setPreview(null);
              setParams({ report: r.id });
            }}
            onSelect={selectLocation}
            point={point}
            impact={preview}
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
                onClick={() => {
                  sequence.current++;
                  setPoint(null);
                  setPreview(null);
                  setParams({ report: r.id });
                }}
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
          {point ? (
            <div className="impact-content">
              <div className="eyebrow">A PLACE TO START</div>
              <h2>Report an Observation Here</h2>
              {snapping ? (
                <p>Finding the nearest river segment…</p>
              ) : preview ? (
                <>
                  <p className="notice">
                    Location snapped to the nearest Periyar River segment.
                  </p>
                  <p>
                    <b>{preview.snapped_location.name}</b>
                    <br />
                    Segment {preview.snapped_location.segment_id}
                  </p>
                  <p className="small">
                    Selected: {point.latitude.toFixed(6)},{" "}
                    {point.longitude.toFixed(6)}
                    <br />
                    Snapped: {preview.snapped_location.latitude.toFixed(
                      6,
                    )}, {preview.snapped_location.longitude.toFixed(6)}
                    <br />
                    Snap distance: {preview.snapped_location.snap_distance_m} m
                  </p>
                  <label>
                    Date and time
                    <input
                      type="datetime-local"
                      value={observedAt}
                      onChange={(e) => setObservedAt(e.target.value)}
                    />
                  </label>
                  <label>
                    Contamination type
                    <select
                      value={observationType}
                      onChange={(e) => setObservationType(e.target.value)}
                    >
                      {categories.map((c) => (
                        <option key={c}>{c}</option>
                      ))}
                    </select>
                  </label>
                  <Link
                    className="button full"
                    to={
                      "/report?" +
                      new URLSearchParams({
                        lat: point.latitude,
                        lon: point.longitude,
                        type: observationType,
                        time: observedAt,
                      })
                    }
                  >
                    Report Observation →
                  </Link>
                </>
              ) : (
                <p>Please choose a location closer to the mapped river.</p>
              )}
            </div>
          ) : (
            <ImpactPanel report={selected} />
          )}
        </aside>
      </div>
    </main>
  );
}
