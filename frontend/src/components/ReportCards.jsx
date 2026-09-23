import { Link } from "react-router-dom";
import { CameraOff } from "lucide-react";
import { Badge } from "./Shared";
import { dateLabel, assetUrl } from "../services/api";
export default function ReportCards({ reports, admin = false }) {
  return (
    <div className="history-grid">
      {reports.map((r) => (
        <Link
          key={r.id}
          className="history-card"
          to={(admin ? "/admin/reports/" : "/reports/") + r.id}
        >
          <div className="history-image">
            {r.image_url ? (
              <img
                src={assetUrl(r.image_url)}
                alt={r.contamination_type + " observation"}
              />
            ) : (
              <>
                <CameraOff size={24} />
                <span>No photo attached</span>
              </>
            )}
            {r.is_demo && <span className="sample-label">SAMPLE RECORD</span>}
          </div>
          <div className="history-copy">
            <div className="eyebrow">{r.id}</div>
            <h3>{r.contamination_type}</h3>
            <p>{(r.image_urls || []).length} Evidence Images</p>
            <p>{dateLabel(r.created_at)}</p>
            <p>
              {r.location_name}
              <br />
              <span className="mono">Segment {r.segment_id}</span>
            </p>
            {r.case && <p className="case-reference">{r.case.id}</p>}
            <div className="status-row">
              <span>Observation status</span>
              <Badge value={r.status} />
            </div>
            <div className="status-row">
              <span>Potential impact</span>
              <Badge value={r.priority_level} />
            </div>
            <span className="text-link">
              {admin ? "Open report" : "View details & history"} →
            </span>
          </div>
        </Link>
      ))}
    </div>
  );
}
