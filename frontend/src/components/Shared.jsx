import { ArrowUpRight, Droplets, MapPin, Radio, Building2 } from "lucide-react";
import { Link } from "react-router-dom";
export function Badge({ value }) {
  return (
    <span className={"badge " + value.toLowerCase().replaceAll(" ", "-")}>
      {value}
    </span>
  );
}
export function ErrorBox({ error }) {
  return error ? (
    <div className="error" role="alert">
      {error}
    </div>
  ) : null;
}
export function ImpactPanel({ report, impact, details = true }) {
  const data = impact || report?.impact;
  if (!data)
    return (
      <div className="empty">
        <MapPin size={32} />
        <h3>Follow the river.</h3>
        <p>Select an observation to see its potential downstream impact.</p>
        <p>Orange markers are citizen observations awaiting verification.</p>
      </div>
    );
  const icons = {
    settlements: Building2,
    water_intakes: Droplets,
    monitoring_points: Radio,
    local_bodies: MapPin,
  };
  return (
    <div className="impact-content">
      <div className="eyebrow">DOWNSTREAM IMPACT</div>
      <h2>{report?.contamination_type || "Location analysis"}</h2>
      {report && (
        <>
          <div className="muted mono">{report.id}</div>
          <div className="status-row">
            <span>Observation status</span>
            <Badge value={report.status} />
          </div>
          {report.status === "UNVERIFIED" && (
            <p className="notice">Citizen Observation – Unverified</p>
          )}
        </>
      )}
      <div className="priority-card">
        <div className="status-row">
          <span>Potential impact priority</span>
          <Badge value={data.priority.level} />
        </div>
        <strong>
          {data.priority.score}
          <small> / 10 points</small>
        </strong>
        <ul>
          {data.priority.reasons.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      </div>
      <div className="route-line">
        <span className="route-dot" />
        <div>
          <b>{data.snapped_location.segment_id}</b>
          <p>
            Snapped {data.snapped_location.snap_distance_m} m from observation
          </p>
        </div>
      </div>
      <p className="muted small">
        {data.downstream_segments.length} connected segments ·{" "}
        {data.downstream_segments.join(" → ")}
      </p>
      <h3>Potentially affected downstream</h3>
      {Object.entries(data.affected).map(([kind, assets]) => {
        const Icon = icons[kind];
        return (
          <div className="asset-group" key={kind}>
            <div className="asset-title">
              <Icon size={16} />
              {kind.replaceAll("_", " ")}
              <b>{assets.length}</b>
            </div>
            {assets.map((a) => (
              <div className="asset" key={a.id}>
                <span>
                  {a.name}
                  <small>{a.local_body}</small>
                </span>
                <b>{(a.distance_downstream / 1000).toFixed(1)} km</b>
              </div>
            ))}
          </div>
        );
      })}
      <p className="notice">
        Potential exposure from network connectivity. Not confirmed pollution, a
        concentration model, or a travel-time prediction.
      </p>
      {report && details && (
        <Link className="button secondary full" to={"/reports/" + report.id}>
          Full report & timeline <ArrowUpRight size={16} />
        </Link>
      )}
    </div>
  );
}
