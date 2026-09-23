import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  LocateFixed,
  Upload,
} from "lucide-react";
import RiverMap from "../map/RiverMap";
import EvidenceGallery from "../components/EvidenceGallery";
import { api, post, categories } from "../services/api";
import { ErrorBox, ImpactPanel } from "../components/Shared";
const localNow = () => {
  const d = new Date();
  return new Date(d - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
};
export default function ReportForm() {
  const nav = useNavigate(),
    [params] = useSearchParams(),
    seq = useRef(0),
    urls = useRef(new Set()),
    uploaded = useRef(new Map());
  const [step, setStep] = useState(1),
    [form, setForm] = useState({
      contamination_type: categories.includes(params.get("type"))
        ? params.get("type")
        : "Dead Fish",
      description: "",
      observed_at: params.get("time") || localNow(),
      reporter_name: "",
      contact: "",
    }),
    [files, setFiles] = useState([]),
    [maximum, setMaximum] = useState(5),
    [point, setPoint] = useState(null),
    [impact, setImpact] = useState(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [progress, setProgress] = useState("");
  useEffect(() => {
    api("/config")
      .then((c) => setMaximum(c.max_images_per_report))
      .catch(() => {});
    if (params.has("lat") && params.has("lon")) {
      const latitude = Number(params.get("lat")),
        longitude = Number(params.get("lon"));
      if (Number.isFinite(latitude) && Number.isFinite(longitude))
        locate({ latitude, longitude });
    }
    return () => {
      urls.current.forEach(URL.revokeObjectURL);
    };
  }, []);
  function field(key) {
    return {
      value: form[key],
      onChange: (e) => setForm({ ...form, [key]: e.target.value }),
    };
  }
  async function locate(p) {
    const ticket = ++seq.current;
    setPoint(p);
    setImpact(null);
    setError("");
    setBusy(true);
    setProgress("Analyzing downstream river network…");
    try {
      const a = await post("/analyze", p);
      if (ticket === seq.current) setImpact(a);
    } catch (e) {
      if (ticket === seq.current) setError(e.message);
    } finally {
      if (ticket === seq.current) {
        setBusy(false);
        setProgress("");
      }
    }
  }
  function gps() {
    if (!navigator.geolocation) {
      setError("Location is unavailable. Please choose a point on the map.");
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
      { timeout: 10000 },
    );
  }
  function addFiles(event) {
    const incoming = Array.from(event.target.files);
    event.target.value = "";
    setError("");
    if (incoming.length + files.length > maximum) {
      setError(`Please attach no more than ${maximum} images.`);
      return;
    }
    if (
      incoming.some(
        (f) =>
          !["image/jpeg", "image/png", "image/webp"].includes(f.type) ||
          f.size > 5 * 1024 * 1024,
      )
    ) {
      setError("Choose JPEG, PNG or WebP images, each under 5 MB.");
      return;
    }
    const additions = incoming.map((file) => {
      const src = URL.createObjectURL(file);
      urls.current.add(src);
      return { id: crypto.randomUUID(), file, src, name: file.name };
    });
    setFiles([...files, ...additions]);
  }
  function remove(id) {
    const file = files.find((f) => f.id === id);
    if (file) {
      URL.revokeObjectURL(file.src);
      urls.current.delete(file.src);
    }
    setFiles(files.filter((f) => f.id !== id));
    setError("");
  }
  function next(e) {
    e.preventDefault();
    if (busy) return;
    setError("");
    if (step === 1) {
      if (form.description.trim().length < 10) {
        setError("Please describe your observation in at least 10 characters.");
        return;
      }
      if (!form.observed_at || new Date(form.observed_at) > new Date()) {
        setError(
          "Please choose a valid observation time that is not in the future.",
        );
        return;
      }
    }
    if (step === 3 && !impact) {
      setError("Select a point near the mapped river before continuing.");
      return;
    }
    if (step === 5) submit();
    else setStep(step + 1);
  }
  async function submit() {
    setBusy(true);
    setError("");
    try {
      const image_urls = [];
      for (let i = 0; i < files.length; i++) {
        const item = files[i];
        setProgress(`Uploading image ${i + 1} of ${files.length}…`);
        if (!uploaded.current.has(item.id)) {
          const body = new FormData();
          body.append("file", item.file);
          uploaded.current.set(
            item.id,
            (await api("/uploads", { method: "POST", body })).image_url,
          );
        }
        image_urls.push(uploaded.current.get(item.id));
      }
      setProgress("Analyzing downstream river network…");
      const report = await post("/reports", {
        ...form,
        ...point,
        image_urls,
        observed_at: new Date(form.observed_at).toISOString(),
      });
      nav("/reports/" + report.id + "?submitted=1");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
      setProgress("");
    }
  }
  return (
    <main className="page form-page">
      <div className="page-heading">
        <div className="eyebrow">SMALL OBSERVATIONS. MEANINGFUL ACTION.</div>
        <h1>Tell us what you noticed.</h1>
        <p>
          You don’t need to be certain. Share what you observed, and let the
          review team take it from there.
        </p>
      </div>
      <div className="stepper five-steps">
        {[
          "Describe",
          "Add evidence",
          "Select location",
          "Review",
          "Submit",
        ].map((name, i) => (
          <div
            key={name}
            className={step === i + 1 ? "active" : step > i + 1 ? "done" : ""}
          >
            <span>{step > i + 1 ? <Check size={15} /> : i + 1}</span>
            {name}
          </div>
        ))}
      </div>
      <ErrorBox error={error} />
      {progress && (
        <div className="notice" role="status">
          {progress}
        </div>
      )}
      {step === 1 && impact && (
        <div className="success">
          River location selected: {impact.snapped_location.name} ·{" "}
          {impact.snapped_location.segment_id} · snapped{" "}
          {impact.snapped_location.snap_distance_m} m.
        </div>
      )}
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
                placeholder="Describe the colour, smell, or anything unusual…"
                {...field("description")}
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
              Your contact information is not displayed in public reports.
            </p>
          </>
        ) : step === 2 ? (
          <>
            <h2>Evidence photos</h2>
            <p>
              Add up to {maximum} photos to help reviewers understand the
              observation. Photos are optional.
            </p>
            <EvidenceGallery images={files} removable onRemove={remove} />
            <label className="upload">
              <Upload size={25} />
              <b>{files.length ? "Add more photos" : "Add evidence photos"}</b>
              <span>JPEG, PNG or WebP · maximum 5 MB per image</span>
              <input
                aria-label="Evidence photos"
                type="file"
                multiple
                accept="image/jpeg,image/png,image/webp"
                onChange={addFiles}
                disabled={files.length >= maximum}
              />
            </label>
            <p className="small muted">
              {files.length} / {maximum} images selected
            </p>
          </>
        ) : step === 3 ? (
          <>
            <div className="section-title">
              <div>
                <h2>Where did you see it?</h2>
                <p>
                  Tap the river or a nearby point. We’ll show where it snaps.
                </p>
              </div>
              <button type="button" className="button secondary" onClick={gps}>
                <LocateFixed size={16} />
                Use my location
              </button>
            </div>
            <RiverMap compact point={point} onSelect={locate} impact={impact} />
            <div className="location-summary">
              <b>Selected River Point</b>
              {point ? (
                <>
                  <span>
                    Latitude {point.latitude.toFixed(6)} · Longitude{" "}
                    {point.longitude.toFixed(6)}
                  </span>
                  {impact && (
                    <>
                      <span>
                        Nearest River Segment:{" "}
                        {impact.snapped_location.segment_id}
                      </span>
                      <span>{impact.snapped_location.name}</span>
                      <span>
                        Location snapped to the nearest Periyar River segment.
                        Snap distance: {impact.snapped_location.snap_distance_m}{" "}
                        m.
                      </span>
                    </>
                  )}
                </>
              ) : (
                <span>No location selected yet.</span>
              )}
            </div>
          </>
        ) : step === 4 ? (
          <>
            <h2>Review your observation</h2>
            <p>
              <b>{form.contamination_type}</b> ·{" "}
              {new Date(form.observed_at).toLocaleString()}
            </p>
            <p>{form.description}</p>
            <EvidenceGallery images={files} />
            <ImpactPanel impact={impact} />
          </>
        ) : (
          <>
            <div className="eyebrow">READY WHEN YOU ARE</div>
            <h2>Share your observation.</h2>
            <p>
              {form.contamination_type} · {files.length} evidence image
              {files.length === 1 ? "" : "s"}
            </p>
            <p>
              {impact?.snapped_location.name}
              <br />
              {impact?.snapped_location.segment_id}
            </p>
            <div className="notice">
              Your report will start as <b>UNVERIFIED</b>. Potential impact does
              not confirm pollution. Alerts in this hackathon application are
              simulated.
            </div>
          </>
        )}
        <div className="form-actions">
          {step > 1 ? (
            <button
              type="button"
              className="button secondary"
              disabled={busy}
              onClick={() => setStep(step - 1)}
            >
              <ArrowLeft size={16} />
              Back
            </button>
          ) : (
            <span />
          )}
          <button
            type="submit"
            className="button"
            disabled={busy || (step === 3 && !impact)}
          >
            {busy
              ? "Please wait…"
              : step === 5
                ? "Submit observation"
                : "Continue"}
            {step === 5 ? <Check size={16} /> : <ArrowRight size={16} />}
          </button>
        </div>
      </form>
    </main>
  );
}
