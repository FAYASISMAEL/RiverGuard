import { useState } from "react";
import {
  Routes,
  Route,
  NavLink,
  Link,
  useLocation,
  Navigate,
} from "react-router-dom";
import {
  Waves,
  ArrowUpRight,
  LogOut,
  LayoutDashboard,
  Files,
  FolderCheck,
} from "lucide-react";
import Home from "./pages/Home";
import LiveMap from "./pages/LiveMap";
import ReportForm from "./pages/ReportForm";
import ReportDetail from "./pages/ReportDetail";
import Insights from "./pages/Insights";
import History from "./pages/History";
import About from "./pages/About";
import AdminLogin from "./pages/AdminLogin";
import AdminDashboard from "./pages/AdminDashboard";
import { AdminProvider, RequireAdmin, useAdmin } from "./services/adminAuth";
function Layout() {
  const { pathname } = useLocation(),
    admin = pathname.startsWith("/admin"),
    { user, logout } = useAdmin(),
    [error, setError] = useState("");
  return (
    <>
      <header className="topbar">
        <Link to={admin ? "/admin/dashboard" : "/"} className="brand">
          <span className="brand-icon">
            <Waves size={25} />
          </span>
          <span>
            RiverGuard
            <small>{admin ? "ADMIN PORTAL" : "PERIYAR RIVER WATCH"}</small>
          </span>
        </Link>
        {admin ? (
          user && (
            <>
              <span className="muted small">Signed in as {user.username}</span>
              <button
                className="button secondary"
                onClick={() => logout().catch((e) => setError(e.message))}
              >
                <LogOut size={16} />
                Sign out
              </button>
            </>
          )
        ) : (
          <>
            <nav>
              <NavLink to="/" end>
                Home
              </NavLink>
              <NavLink to="/map">Live river map</NavLink>
              <NavLink to="/history">History</NavLink>
              <NavLink to="/hotspots">Hotspots</NavLink>
              <NavLink to="/about">About</NavLink>
            </nav>
            <Link className="button" to="/report">
              Report observation <ArrowUpRight size={16} />
            </Link>
          </>
        )}
      </header>
      <div className="demo-strip">
        <span className="live-dot" /> PERIYAR RIVER WATCH{" "}
        <span>
          OpenStreetMap river geometry · Demo assets · Simulated alerts
        </span>
      </div>
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      <div className={admin && user ? "admin-workspace" : ""}>
        {admin && user && (
          <aside className="admin-sidebar">
            <div className="eyebrow">RESPONSE WORKSPACE</div>
            <NavLink to="/admin/dashboard">
              <LayoutDashboard size={18} />
              Dashboard
            </NavLink>
            <NavLink to="/admin/reports">
              <Files size={18} />
              Reports
            </NavLink>
            <NavLink to="/admin/cases">
              <FolderCheck size={18} />
              Case files
            </NavLink>
            <Link to="/map" className="citizen-link">
              View citizen map ↗
            </Link>
            <p>
              Review the evidence.
              <br />
              Record the response.
            </p>
          </aside>
        )}
        <div className="route-content">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/map" element={<LiveMap />} />
            <Route path="/report" element={<ReportForm />} />
            <Route path="/reports" element={<History />} />
            <Route path="/history" element={<History />} />
            <Route path="/reports/:id" element={<ReportDetail />} />
            <Route path="/insights" element={<Insights />} />
            <Route path="/hotspots" element={<Insights />} />
            <Route path="/about" element={<About />} />
            <Route
              path="/authority"
              element={<Navigate to="/admin" replace />}
            />
            <Route path="/admin" element={<AdminLogin />} />
            <Route element={<RequireAdmin />}>
              <Route path="/admin/dashboard" element={<AdminDashboard />} />
              <Route path="/admin/reports" element={<AdminDashboard />} />
              <Route path="/admin/cases" element={<AdminDashboard />} />
              <Route
                path="/admin/reports/:id"
                element={<ReportDetail adminMode />}
              />
              <Route
                path="/admin/*"
                element={<Navigate to="/admin/dashboard" replace />}
              />
            </Route>
            <Route
              path="*"
              element={
                <main className="page">
                  <h1>Page not found</h1>
                  <Link to="/">Return to home</Link>
                </main>
              }
            />
          </Routes>
        </div>
      </div>
      <footer>
        <span>
          <Waves size={17} />
          One river. Shared responsibility.
        </span>
        <span>RiverGuard / Periyar, Kerala</span>
      </footer>
    </>
  );
}
export default function App() {
  return (
    <AdminProvider>
      <Layout />
    </AdminProvider>
  );
}
