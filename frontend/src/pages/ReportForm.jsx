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
import {
  aggregateImages,
  taskQueue,
  AI_UNAVAILABLE,
} from "../services/imageAnalysis";
const localNow = () => {
  const d = new Date();
  return new Date(d - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
};
export default function ReportForm() {
  const nav = useNavigate(),
    [params] = useSearchParams(),
    seq = useRef(0),
    urls = useRef(new Set()),
    uploaded = useRef(new Map()),
    uploadQueue = useRef(taskQueue()),
    aiQueue = useRef(taskQueue()),
    manualChoice = useRef(categories.includes(params.get("type")));
  const [step, setStep] = useState(1),
    [form, setForm] = useState({
      contamination_type: categories.includes(params.get("type"))
        ? params.get("type")
        : "Other / Unclear",
      description: "",
      observed_at: params.get("time") || localNow(),
      reporter_name: "",
      contact: "",
    }),
    [files, setFiles] = useState([]),
    [maximum, setMaximum] = useState(5),
    [threshold, setThreshold] = useState(0.75),
    [maxImageBytes, setMaxImageBytes] = useState(4 * 1024 * 1024),
    [point, setPoint] = useState(null),
    [impact, setImpact] = useState(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [progress, setProgress] = useState("");
  useEffect(() => {
    api("/config")
      .then((c) => {
        setMaximum(c.max_images_per_report);
        setMaxImageBytes(c.max_image_bytes);
        setThreshold(c.ai_confidence_threshold ?? 0.75);
      })
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
  const suggestion = aggregateImages(files);
  const analysing = files.some((f) => f.aiPending);
  const uploading = files.some((f) => f.uploadPending);
  const aiFailed = files.some((f) => f.aiFailed);
  const canSuggest =
    suggestion &&
    suggestion.category !== "Other / Unclear" &&
    suggestion.confidence >= threshold;
  useEffect(() => {
    if (!manualChoice.current) {
      setForm((previous) => ({
        ...previous,
        contamination_type: canSuggest
          ? suggestion.category
          : "Other / Unclear",
      }));
    }
  }, [suggestion?.category, suggestion?.confidence, canSuggest]);
  function updateFile(id, changes) {
    setFiles((current) =>
      current.map((file) => (file.id === id ? { ...file, ...changes } : file)),
    );
  }
  async function uploadFile(item) {
    updateFile(item.id, { uploadPending: true, uploadError: "" });
    try {
      const body = new FormData();
      body.append("file", item.file);
      const result = await uploadQueue.current(() =>
        api("/uploads", { method: "POST", body }),
      );
      uploaded.current.set(item.id, result.image_url);
      updateFile(item.id, {
        uploadPending: false,
        image_url: result.image_url,
      });
    } catch (error) {
      updateFile(item.id, { uploadPending: false, uploadError: error.message });
    }
  }
  async function classifyFile(item) {
    updateFile(item.id, { aiPending: true, aiFailed: false });
    try {
      const body = new FormData();
      body.append("images[]", item.file);
      const result = await aiQueue.current(() =>
        api("/ai/classify-contamination", {
          method: "POST",
          body,
          signal: AbortSignal.timeout(50000),
        }),
      );
      if (!result.success || !result.image_results?.[0])
        throw new Error(AI_UNAVAILABLE);
      updateFile(item.id, {
        aiPending: false,
        prediction: result.image_results[0],
      });
    } catch {
      updateFile(item.id, { aiPending: false, aiFailed: true });
    }
  }
  function addFiles(incoming) {
    setError("");
    if (incoming.length + files.length > maximum) {
      setError(`Please attach no more than ${maximum} images.`);
      return;
    }
    if (
      incoming.some(
        (f) =>
          !["image/jpeg", "image/png", "image/webp"].includes(f.type) ||
          f.size > maxImageBytes,
      )
    ) {
      setError(
        `Choose JPEG, PNG or WebP images, each under ${maxImageBytes / (1024 * 1024)} MB.`,
      );
      return;
    }
    const additions = incoming.map((file) => {
      const src = URL.createObjectURL(file);
      urls.current.add(src);
      return {
        id: crypto.randomUUID(),
        file,
        src,
        name: file.name,
        uploadPending: true,
        aiPending: true,
      };
    });
    setFiles((current) => [...current, ...additions]);
    additions.forEach((item) => {
      uploadFile(item);
      classifyFile(item);
    });
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
      if (uploading || files.some((file) => file.uploadError)) {
        setError(
          "Please finish uploading, retry failed photos, or remove them before continuing.",
        );
        return;
      }
      manualChoice.current = true;
    }
    if (step === 2) {
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
    if (step === 4) submit();
    else setStep(step + 1);
  }
  async function submit() {
    setBusy(true);
    setError("");
    try {
      const image_urls = files.map((file) => uploaded.current.get(file.id));
      if (image_urls.some((url) => !url))
        throw new Error(
          "Please return to Upload Evidence and retry the failed photo.",
        );
      setProgress("Analyzing downstream river network…");
      const report = await post("/reports", {
        ...form,
        ...point,
        image_urls,
        ai_image_results: suggestion
          ? files.map((file) => file.prediction)
          : [],
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
          Upload photos of the river condition. RiverGuard will help identify
          the type of observation.
        </p>
      </div>
      <div className="stepper four-steps">
        {[
          "Upload Evidence",
          "Describe Observation",
          "Select River Location",
          "Review & Submit",
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
            <h2>Upload Evidence</h2>
            <p>
              Add up to {maximum} photos. Photos are optional if you cannot
              safely take one.
            </p>
            <EvidenceGallery images={files} removable onRemove={remove} />
            <label
              className="upload"
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault();
                addFiles(Array.from(event.dataTransfer.files));
              }}
            >
              <Upload size={25} />
              <b>{files.length ? "Add more photos" : "Upload Evidence"}</b>
              <span>or drag &amp; drop photos here</span>
              <span>
                JPG, JPEG, PNG or WEBP · maximum {maxImageBytes / (1024 * 1024)}{" "}
                MB per image
              </span>
              <input
                aria-label="Evidence photos"
                type="file"
                multiple
                accept="image/jpeg,image/png,image/webp"
                onChange={(event) => {
                  addFiles(Array.from(event.target.files));
                  event.target.value = "";
                }}
                disabled={files.length >= maximum}
              />
            </label>
            <p className="small muted">
              {files.length} / {maximum} images selected
            </p>
            {uploading && <p role="status">Uploading evidence…</p>}
            {files
              .filter((file) => file.uploadError)
              .map((file) => (
                <div className="error" key={file.id} role="alert">
                  {file.name}: {file.uploadError}{" "}
                  <button
                    type="button"
                    className="button secondary"
                    onClick={() => uploadFile(file)}
                  >
                    Retry upload
                  </button>
                </div>
              ))}
            <section className="ai-suggestion" aria-live="polite">
              <div className="eyebrow">AI SUGGESTED OBSERVATION</div>
              {analysing ? (
                <p role="status">
                  Analysing evidence… You can choose a category and continue
                  while we work.
                </p>
              ) : aiFailed ? (
                <>
                  <p>{AI_UNAVAILABLE}</p>
                  <button
                    type="button"
                    className="button secondary"
                    onClick={() =>
                      files
                        .filter((file) => file.aiFailed)
                        .forEach(classifyFile)
                    }
                  >
                    Retry analysis
                  </button>
                </>
              ) : suggestion ? (
                <>
                  <h3>{suggestion.category}</h3>
                  <p>
                    AI confidence: {Math.round(suggestion.confidence * 100)}%
                  </p>
                  {!canSuggest && (
                    <p>
                      We couldn't confidently identify the observation. Please
                      select the most suitable category.
                    </p>
                  )}
                  <button
                    type="button"
                    className="button secondary"
                    onClick={() => {
                      manualChoice.current = true;
                      setForm((previous) => ({
                        ...previous,
                        contamination_type: suggestion.category,
                      }));
                    }}
                  >
                    Use this category
                  </button>
                </>
              ) : (
                <p>
                  Add a photo for an optional suggestion, or choose a category
                  yourself.
                </p>
              )}
              <p className="small muted">
                A visual suggestion, not a confirmed pollution finding. You can
                always change it.
              </p>
            </section>
            <label>
              Contamination type
              <select
                value={form.contamination_type}
                onChange={(event) => {
                  manualChoice.current = true;
                  setForm((previous) => ({
                    ...previous,
                    contamination_type: event.target.value,
                  }));
                }}
              >
                {categories.map((category) => (
                  <option key={category}>{category}</option>
                ))}
              </select>
            </label>
            <p className="small muted">
              Continue with your selected category. Photos stay with your
              report.
            </p>
          </>
        ) : step === 2 ? (
          <>
            <h2>What did you observe?</h2>
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
        ) : (
          <>
            <h2>Review your observation</h2>
            <p>
              <b>{form.contamination_type}</b> ·{" "}
              {new Date(form.observed_at).toLocaleString()}
            </p>
            <p>{form.description}</p>
            <EvidenceGallery images={files} />
            {suggestion && (
              <p className="small muted">
                AI suggestion: {suggestion.category} —{" "}
                {Math.round(suggestion.confidence * 100)}%. Your selected
                category: {form.contamination_type}.
              </p>
            )}
            <ImpactPanel impact={impact} />
            <div className="notice">
              Your report will start as <b>UNVERIFIED</b>. AI suggestions and
              potential impact do not confirm pollution. Authority review
              remains separate.
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
            disabled={
              busy || (step === 1 && uploading) || (step === 3 && !impact)
            }
          >
            {busy
              ? "Please wait…"
              : step === 4
                ? "Submit observation"
                : "Continue"}
            {step === 4 ? <Check size={16} /> : <ArrowRight size={16} />}
          </button>
        </div>
      </form>
    </main>
  );
}
