import { useEffect, useState } from "react";
import {
  MapContainer,
  TileLayer,
  GeoJSON,
  CircleMarker,
  Popup,
  LayersControl,
  useMapEvents,
  useMap,
} from "react-leaflet";
import { api } from "../services/api";
import { geoJSON } from "leaflet";
const colors = {
  settlements: "#967047",
  intakes: "#3674b5",
  "monitoring-points": "#805aad",
};
function SelectPoint({ onSelect }) {
  useMapEvents({
    click: (e) =>
      onSelect?.({ latitude: e.latlng.lat, longitude: e.latlng.lng }),
  });
  return null;
}
function Move({ point }) {
  const map = useMap();
  useEffect(() => {
    if (point) map.panTo([point.latitude, point.longitude], { animate: false });
  }, [point?.latitude, point?.longitude, map]);
  return null;
}
function FitRoute({ report }) {
  const map = useMap();
  useEffect(() => {
    if (report) {
      const bounds = geoJSON(report.impact.downstream_path).getBounds();
      if (bounds.isValid())
        map.fitBounds(bounds, {
          padding: [45, 60],
          maxZoom: 14,
          animate: false,
        });
    }
  }, [report?.id, map]);
  return null;
}
function FitNetwork({ data, active }) {
  const map = useMap();
  useEffect(() => {
    if (data && active) {
      map.fitBounds(geoJSON(data).getBounds(), {
        padding: [35, 50],
        maxZoom: 12,
        animate: false,
      });
    }
  }, [data, active, map]);
  return null;
}
export default function RiverMap({
  reports = [],
  selected,
  onReport,
  onSelect,
  point,
  impact,
  compact = false,
}) {
  const [layers, setLayers] = useState(null),
    [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    Promise.all(
      [
        "river",
        "settlements",
        "intakes",
        "monitoring-points",
        "local-bodies",
      ].map(async (key) => [key, await api("/map/" + key)]),
    )
      .then((items) => {
        if (active) setLayers(Object.fromEntries(items));
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, []);
  const result = impact || selected?.impact;
  return (
    <div className={"map-shell " + (compact ? "compact" : "")}>
      {error && (
        <div className="map-error" role="alert">
          Map data unavailable: {error}
        </div>
      )}
      {!layers && !error && (
        <div className="map-error">Loading river layers…</div>
      )}
      <MapContainer
        center={[10.13, 76.335]}
        zoom={12}
        scrollWheelZoom
        className="river-map"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
          url={
            import.meta.env.VITE_TILE_URL ||
            "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          }
        />
        <SelectPoint onSelect={onSelect} />
        <Move point={point} />
        <FitRoute report={selected} />
        <FitNetwork data={layers?.river} active={!selected && !point} />
        <LayersControl position="topright">
          {layers && (
            <LayersControl.Overlay checked name="Periyar river (demo)">
              <GeoJSON
                data={layers.river}
                style={{ color: "#3493a9", weight: 5, opacity: 0.8 }}
              />
            </LayersControl.Overlay>
          )}
          {layers && (
            <LayersControl.Overlay name="Local boundaries">
              <GeoJSON
                data={layers["local-bodies"]}
                style={{
                  color: "#829b88",
                  weight: 1,
                  dashArray: "5 5",
                  fillOpacity: 0.07,
                }}
              />
            </LayersControl.Overlay>
          )}
          {layers &&
            Object.entries(colors).map(([kind, color]) => (
              <LayersControl.Overlay
                checked
                name={kind.replaceAll("-", " ")}
                key={kind}
              >
                <>
                  {layers[kind].features.map((f) => (
                    <CircleMarker
                      key={f.properties.id}
                      center={[
                        f.geometry.coordinates[1],
                        f.geometry.coordinates[0],
                      ]}
                      radius={kind === "intakes" ? 8 : 5}
                      pathOptions={{
                        color: "white",
                        weight: 2,
                        fillColor: color,
                        fillOpacity: 1,
                      }}
                    >
                      <Popup>
                        <b>{f.properties.name}</b>
                        <br />
                        {kind} · Demo asset
                      </Popup>
                    </CircleMarker>
                  ))}
                </>
              </LayersControl.Overlay>
            ))}
          <LayersControl.Overlay checked name="Citizen observations">
            <>
              {reports.map((r) => (
                <CircleMarker
                  key={r.id}
                  center={[r.latitude, r.longitude]}
                  radius={selected?.id === r.id ? 11 : 7}
                  pathOptions={{
                    color: "white",
                    weight: 3,
                    fillColor:
                      r.status === "VERIFIED"
                        ? "#187c66"
                        : r.status === "REJECTED"
                          ? "#8d9595"
                          : "#e69a3b",
                    fillOpacity: 1,
                  }}
                  eventHandlers={{ click: () => onReport?.(r) }}
                >
                  <Popup>
                    <b>{r.contamination_type}</b>
                    <br />
                    {r.status}
                    <br />
                    Potential impact: {r.priority_level}
                    <br />
                    {onReport && (
                      <button type="button" onClick={() => onReport(r)}>
                        View impact
                      </button>
                    )}
                  </Popup>
                </CircleMarker>
              ))}
            </>
          </LayersControl.Overlay>
          {result && (
            <LayersControl.Overlay checked name="Potential downstream path">
              <GeoJSON
                key={JSON.stringify(result.snapped_location)}
                data={result.downstream_path}
                style={{ color: "#ed754b", weight: 7, opacity: 0.9 }}
              />
            </LayersControl.Overlay>
          )}
        </LayersControl>
        {point && (
          <CircleMarker
            center={[point.latitude, point.longitude]}
            radius={10}
            pathOptions={{ color: "#126c60", weight: 3, fillOpacity: 0.4 }}
          />
        )}
      </MapContainer>
      <div className="map-caption">
        <span className="live-dot" /> Illustrative Periyar network{" "}
        <span>DEMO DATA</span>
      </div>
      <div className="map-legend">
        <span>
          <i style={{ background: "#3493a9" }} />
          River
        </span>
        <span>
          <i style={{ background: "#ed754b" }} />
          Downstream path
        </span>
        <span>
          <i style={{ background: "#e69a3b" }} />
          Unverified
        </span>
        <span>
          <i style={{ background: "#187c66" }} />
          Verified
        </span>
        <span>
          <i style={{ background: "#3674b5" }} />
          Intake
        </span>
        <span>
          <i style={{ background: "#805aad" }} />
          Monitor
        </span>
        <span>
          <i style={{ background: "#967047" }} />
          Settlement
        </span>
      </div>
    </div>
  );
}
