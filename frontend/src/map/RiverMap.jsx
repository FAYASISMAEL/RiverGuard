import { useEffect, useState } from "react";
import {
  MapContainer,
  TileLayer,
  GeoJSON,
  CircleMarker,
  Popup,
  LayersControl,
  LayerGroup,
  useMapEvents,
  useMap,
} from "react-leaflet";
import { mapApi } from "../services/api";
import { geoJSON, DomEvent } from "leaflet";
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
    if (point)
      map.setView(
        [point.latitude, point.longitude],
        Math.max(14, map.getZoom()),
        { animate: false },
      );
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
      ].map(async (key) => [key, await mapApi("/map/" + key)]),
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
  const candidate = impact || selected?.impact;
  const result =
    candidate?.dataset_version &&
    candidate.dataset_version === layers?.river.version
      ? candidate
      : null;
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
        <FitRoute report={result && selected} />
        <FitNetwork data={layers?.river} active={!result && !point} />
        <LayersControl position="topright">
          {layers && (
            <LayersControl.Overlay checked name="Periyar river network">
              <GeoJSON
                data={layers.river}
                smoothFactor={0}
                style={(feature) => ({
                  color: "#3493a9",
                  weight: feature.properties.mainstem ? 4 : 2.5,
                  opacity: 0.9,
                })}
                onEachFeature={(feature, layer) => {
                  layer.on("add", () => {
                    const element = layer.getElement();
                    if (element) {
                      element.dataset.segmentId = feature.properties.id;
                      element.setAttribute(
                        "aria-label",
                        feature.properties.name + " " + feature.properties.id,
                      );
                    }
                  });
                  layer.options.bubblingMouseEvents = false;
                  layer.on("click", (event) => {
                    if (event.originalEvent)
                      DomEvent.stopPropagation(event.originalEvent);
                    onSelect?.(
                      {
                        latitude: event.latlng.lat,
                        longitude: event.latlng.lng,
                      },
                      feature.properties,
                    );
                  });
                  layer.bindTooltip(feature.properties.name || "Periyar River");
                }}
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
                <LayerGroup>
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
                </LayerGroup>
              </LayersControl.Overlay>
            ))}
          <LayersControl.Overlay checked name="Citizen observations">
            <LayerGroup>
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
                  bubblingMouseEvents={false}
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
            </LayerGroup>
          </LayersControl.Overlay>
          {result && (
            <LayersControl.Overlay checked name="Potential downstream path">
              <GeoJSON
                key={JSON.stringify(result.snapped_location)}
                data={result.downstream_path}
                interactive={false}
                smoothFactor={0}
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
        {result && (
          <CircleMarker
            center={[
              result.snapped_location.latitude,
              result.snapped_location.longitude,
            ]}
            radius={6}
            pathOptions={{
              color: "#ffffff",
              weight: 2,
              fillColor: "#126c60",
              fillOpacity: 1,
            }}
          >
            <Popup>
              Snapped river location
              <br />
              {result.snapped_location.segment_id}
              <br />
              {result.snapped_location.snap_distance_m} m from selected point
            </Popup>
          </CircleMarker>
        )}
      </MapContainer>
      <div className="map-caption">
        <span className="live-dot" /> Periyar river network{" "}
        <span>© OpenStreetMap</span>
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
