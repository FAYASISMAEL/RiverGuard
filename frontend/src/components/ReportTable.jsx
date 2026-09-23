import { Link } from "react-router-dom";
import { Badge } from "./Shared";
import { dateLabel } from "../services/api";
export default function ReportTable({ reports }) {
  return (
    <div className="table-scroll">
      <table className="reports-table">
        <thead>
          <tr>
            <th>Report / case</th>
            <th>Observation</th>
            <th>Submitted</th>
            <th>River location</th>
            <th>Status</th>
            <th>Potential impact</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {reports.map((r) => (
            <tr key={r.id}>
              <td>
                <b>{r.id}</b>
                <small>{r.case?.id || "No case yet"}</small>
                {r.is_demo && <span className="badge">SAMPLE</span>}
              </td>
              <td>
                {r.contamination_type}
                <small>{r.image_urls?.length || 0} images</small>
              </td>
              <td>{dateLabel(r.created_at)}</td>
              <td>
                {r.location_name}
                <small>{r.segment_id}</small>
              </td>
              <td>
                <Badge value={r.status} />
              </td>
              <td>
                <Badge value={r.priority_level} />
              </td>
              <td>
                <Link className="text-link" to={"/admin/reports/" + r.id}>
                  View Case →
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
