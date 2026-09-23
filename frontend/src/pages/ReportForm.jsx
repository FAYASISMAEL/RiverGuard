import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  LocateFixed,
  Check,
  Upload,
} from "lucide-react";
import RiverMap from "../map/RiverMap";
import { api, post, categories } from "../services/api";
import { ErrorBox, ImpactPanel } from "../components/Shared";
const localNow = () => {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
};
export default function ReportForm() {
  const nav = useNavigate(),
    seq = useRef(0);
  const [step, setStep] = useState(1),
    [form, setForm] = useState({
      contamination_type: "Industrial Discharge",
      description: "",
      observed_at: localNow(),
      reporter_name: "",
      contact: "",
    }),
    [point, setPoint] = useState(null),
    [impact, setImpact] = useState(null),
    [file, setFile] = useState(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  function field(key) {
    return {
      value: form[key],
      onChange: (e) => setForm({ ...form, [key]: e.target.value }),
    };
  }
  async function locate(p) {
    const current = ++seq.current;
    setPoint(p);
    setImpact(null);
    setError("");
    setBusy(true);
    try {
      const result = await post("/analyze", p);
      if (current === seq.current) setImpact(result);
    } catch (e) {
      if (current === seq.current) setError(e.message);
    } finally {
      if (current === seq.current) setBusy(false);
    }
  }
  function gps() {
    if (!navigator.geolocation) {
      setError(
        "Location is unavailable in this browser. Select a point on the map.",
      );
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) =>
        locate({
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
        }),
      () =>
        setError(
          "Could not access your location. Allow location access or choose a point on the map.",
        ),
    );
  }
  function next(e) {
    e.preventDefault();
    if (busy || (step === 2 && !impact)) return;
    if (step === 3) {
      submit();
      return;
    }
    setError("");
    if (step === 1) {
      if (form.description.trim().length < 10) {
        setError("Please describe your observation in at least 10 characters.");
        return;
      }
      if (new Date(form.observed_at) > new Date()) {
        setError("Observation time cannot be in the future.");
        return;
      }
    }
    setStep(step + 1);
  }
  async function submit() {
    setBusy(true);
    setError("");
    try {
      let image_url = null;
      if (file) {
        const body = new FormData();
        body.append("file", file);
        image_url = (await api("/uploads", { method: "POST", body })).image_url;
      }
      const result = await post("/reports", {
        ...form,
        ...point,
        image_url,
        observed_at: new Date(form.observed_at).toISOString(),
      });
      nav("/reports/" + result.id + "?submitted=1");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="page form-page">
      <div className="page-heading">
        <div className="eyebrow">YOUR OBSERVATION CAN MAKE A DIFFERENCE</div>
        <h1>Tell us what you noticed.</h1>
        <p>
          You don’t need to be certain. Share what you observed, and let the
          review team take it from there.
        </p>
      </div>
      <div className="stepper">
        {["Describe", "Locate", "Review & submit"].map((s, i) => (
          <div
            className={step === i + 1 ? "active" : step > i + 1 ? "done" : ""}
            key={s}
          >
            <span>{step > i + 1 ? <Check size={16} /> : i + 1}</span>
            {s}
          </div>
        ))}
      </div>
      <ErrorBox error={error} />
      <form className="form-card" onSubmit={next}>
        {step === 1 ? (
          <>
            <h2>What did you observe?</h2>
            <label>
              Contamination type
              <select {...field("contamination_type")}>
                {categories.map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </label>
            <label>
              Date and time
              <input type="datetime-local" required {...field("observed_at")} />
            </label>
            <label>
              Description
              <textarea
                required
                minLength={10}
                maxLength={3000}
                rows={4}
                placeholder="Describe the colour, smell, or anything unusual you noticed…"
                {...field("description")}
              />
            </label>
            <label className="upload">
              <Upload size={23} />
              <b>{file ? file.name : "Add a photo (optional)"}</b>
              <span>JPEG, PNG or WebP · up to 5 MB</span>
              <input
                aria-label="Observation photo"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={(e) => {
                  const f = e.target.files[0];
                  setFile(null);
                  setError("");
                  if (
                    f &&
                    (!["image/jpeg", "image/png", "image/webp"].includes(
                      f.type,
                    ) ||
                      f.size > 5 * 1024 * 1024)
                  ) {
                    setError("Choose a JPEG, PNG or WebP image under 5 MB.");
                    e.target.value = "";
                  } else setFile(f);
                }}
              />
            </label>
            <div className="two-col">
              <label>
                Your name (optional)
                <input maxLength={100} {...field("reporter_name")} />
              </label>
              <label>
                Phone or email (optional)
                <input maxLength={200} {...field("contact")} />
              </label>
            </div>
            <p className="muted small">
              Contact information is not displayed in public reports.
            </p>
          </>
        ) : step === 2 ? (
          <>
            <div className="section-title">
              <div>
                <h2>Where did you see it?</h2>
                <p>Click the map to select the observation location.</p>
              </div>
              <button type="button" className="button secondary" onClick={gps}>
                <LocateFixed size={16} />
                Use my location
              </button>
            </div>
            <RiverMap point={point} onSelect={locate} impact={impact} compact />
            <div className="location-summary">
              <b>Selected location</b>
              {point ? (
                <>
                  <span>
                    Latitude {point.latitude.toFixed(6)} · Longitude{" "}
                    {point.longitude.toFixed(6)}
                  </span>
                  <span>
                    {busy
                      ? "Finding nearest river segment…"
                      : impact
                        ? `Nearest river segment: ${impact.snapped_location.segment_id} · Distance to river: ${impact.snapped_location.snap_distance_m} m`
                        : "Select a location closer to the river."}
                  </span>
                </>
              ) : (
                <span>No location selected yet</span>
              )}
            </div>
          </>
        ) : (
          <>
            <h2>Ready to share your observation?</h2>
            <p>
              <b>{form.contamination_type}</b> ·{" "}
              {new Date(form.observed_at).toLocaleString()}
            </p>
            <p>{form.description}</p>
            {file && <p>Photo attached: {file.name}</p>}
            <div className="notice">
              Your report will be saved as <b>UNVERIFIED</b>. Potential impact
              does not confirm pollution. Alerts in this prototype are
              simulated.
            </div>
            <ImpactPanel impact={impact} />
          </>
        )}
        <div className="form-actions">
          {step > 1 ? (
            <button
              className="button secondary"
              type="button"
              disabled={busy}
              onClick={() => setStep(step - 1)}
            >
              <ArrowLeft size={16} />
              Back
            </button>
          ) : (
            <span />
          )}
          {step < 3 ? (
            <button
              className="button"
              disabled={busy || (step === 2 && !impact)}
              type="submit"
            >
              Continue <ArrowRight size={17} />
            </button>
          ) : (
            <button
              className="button"
              type="button"
              disabled={busy}
              onClick={submit}
            >
              {busy ? "Submitting observation…" : "Submit observation"}
              <Check size={17} />
            </button>
          )}
        </div>
      </form>
    </main>
  );
}
