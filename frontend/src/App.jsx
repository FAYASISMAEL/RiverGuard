import { Routes, Route, NavLink, Link } from "react-router-dom";
import { Waves, ArrowUpRight, Map, ShieldCheck } from "lucide-react";
import Home from "./pages/Home";
import LiveMap from "./pages/LiveMap";
import ReportForm from "./pages/ReportForm";
import ReportDetail from "./pages/ReportDetail";
import Insights from "./pages/Insights";
import Authority from "./pages/Authority";
export default function App() {
  return (
    <>
      <header className="topbar">
        <Link to="/" className="brand">
          <span className="brand-icon">
            <Waves size={25} />
          </span>
          <span>
            RiverGuard<small>PERIYAR RIVER WATCH</small>
          </span>
        </Link>
        <nav>
          <NavLink to="/" end>
            Overview
          </NavLink>
          <NavLink to="/map">
            <Map size={16} />
            Live map
          </NavLink>
          <NavLink to="/insights">Insights</NavLink>
          <NavLink to="/authority">
            <ShieldCheck size={16} />
            Authority
          </NavLink>
        </nav>
        <Link className="button" to="/report">
          Report an observation <ArrowUpRight size={16} />
        </Link>
      </header>
      <div className="demo-strip">
        <span className="live-dot" /> HACKATHON PROTOTYPE{" "}
        <span>Illustrative river & asset data. Alerts are simulated.</span>
      </div>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/map" element={<LiveMap />} />
        <Route path="/report" element={<ReportForm />} />
        <Route path="/reports/:id" element={<ReportDetail />} />
        <Route path="/insights" element={<Insights />} />
        <Route path="/authority" element={<Authority />} />
        <Route
          path="*"
          element={
            <main className="page">
              <h1>Page not found</h1>
              <Link to="/">Return to overview</Link>
            </main>
          }
        />
      </Routes>
      <footer>
        <span>
          <Waves size={17} /> One river. Shared responsibility.
        </span>
        <span>RiverGuard / Periyar, Kerala</span>
      </footer>
    </>
  );
}
