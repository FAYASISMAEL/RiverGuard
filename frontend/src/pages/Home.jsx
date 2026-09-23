import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowUpRight,
  ArrowRight,
  MapPin,
  GitBranch,
  Bell,
  Play,
  ShieldCheck,
} from "lucide-react";
import RiverMap from "../map/RiverMap";
import { post } from "../services/api";
import { ErrorBox } from "../components/Shared";
export default function Home() {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function demo() {
    setBusy(true);
    try {
      const r = await post("/demo");
      navigate("/map?report=" + r.id);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="page home">
      <section className="hero">
        <div className="hero-copy">
          <div className="eyebrow">
            <span className="live-dot" /> CONNECTED BY THE PERIYAR
          </div>
          <h1>
            A healthier river
            <br />
            starts with <em>us.</em>
          </h1>
          <p>
            Report what you see. Understand what lies downstream. Help the right
            people respond faster.
          </p>
          <div className="hero-actions">
            <Link className="button" to="/report">
              Report contamination <ArrowUpRight size={18} />
            </Link>
            <Link className="button secondary" to="/map">
              View live map <ArrowRight size={18} />
            </Link>
          </div>
          <a className="text-link" href="#how-it-works">
            How it works ↓
          </a>
          <div className="trust-note">
            <ShieldCheck size={18} />
            <span>
              Every observation matters.
              <br />
              <b>Every report is verified by people.</b>
            </span>
          </div>
        </div>
        <div className="hero-map">
          <RiverMap compact />
          <div className="floating-note">
            <span className="icon-tile">
              <GitBranch size={22} />
            </span>
            <div>
              <b>See beyond a single point.</b>
              <p>Follow the river. Understand the impact.</p>
            </div>
          </div>
        </div>
      </section>
      <section className="overview-band">
        <div>
          <span className="eyebrow">A RIVER IS A CONNECTED SYSTEM</span>
          <h2>
            What happens upstream
            <br />
            matters downstream.
          </h2>
        </div>
        <p>
          RiverGuard connects citizen observations with the river’s flow
          direction to identify communities, water intakes, and monitoring
          points that may be affected.
        </p>
        <Link to="/map" className="circle-link" aria-label="Explore the map">
          <ArrowUpRight />
        </Link>
      </section>
      <section id="how-it-works">
        <div className="section-title">
          <div>
            <div className="eyebrow">FROM OBSERVATION TO ACTION</div>
            <h2>Small actions. A clearer picture.</h2>
          </div>
          <span className="muted">Three steps towards a safer river</span>
        </div>
        <div className="steps-grid">
          {[
            [
              MapPin,
              "01",
              "Share what you observe",
              "Add a description, a photo, and a location. No technical knowledge needed.",
            ],
            [
              GitBranch,
              "02",
              "Follow the downstream path",
              "We connect your observation to the river and identify potential downstream exposure.",
            ],
            [
              Bell,
              "03",
              "Help the right people respond",
              "Targeted simulated alerts reach the relevant teams. Authorities review every observation.",
            ],
          ].map(([Icon, n, title, copy]) => (
            <article className="step-card" key={n}>
              <div>
                <Icon size={23} />
                <span>{n}</span>
              </div>
              <h3>{title}</h3>
              <p>{copy}</p>
            </article>
          ))}
        </div>
      </section>
      <section className="demo-card">
        <div>
          <div className="eyebrow">TAKE A GUIDED FIRST LOOK</div>
          <h2>One observation. The whole downstream story.</h2>
          <p>
            Load an example upstream discharge report and explore its connected
            impact.
          </p>
          <ErrorBox error={error} />
        </div>
        <button className="button secondary" disabled={busy} onClick={demo}>
          <Play size={16} />
          {busy ? "Analyzing…" : "Load Demo Scenario"}
        </button>
      </section>
    </main>
  );
}
