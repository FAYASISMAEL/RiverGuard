import { useState } from "react";
import { Navigate, useLocation, useNavigate, Link } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import { useAdmin } from "../services/adminAuth";
import { ErrorBox } from "../components/Shared";
export default function AdminLogin() {
  const { user, loading, login } = useAdmin(),
    nav = useNavigate(),
    location = useLocation();
  const [username, setUsername] = useState(""),
    [password, setPassword] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  if (loading)
    return (
      <main className="page">
        <p>Checking admin session…</p>
      </main>
    );
  if (user) return <Navigate to="/admin/dashboard" replace />;
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(username, password);
      nav(location.state?.from || "/admin/dashboard", { replace: true });
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="page login-page">
      <form className="card login-card" onSubmit={submit}>
        <span className="icon-tile">
          <ShieldCheck size={28} />
        </span>
        <div className="eyebrow">RIVERGUARD / ADMIN PORTAL</div>
        <h1>Welcome back.</h1>
        <p>Sign in to review observations and manage case files.</p>
        <ErrorBox error={error} />
        <label>
          Username
          <input
            autoComplete="username"
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </label>
        <label>
          Password
          <input
            autoComplete="current-password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <button className="button full" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
        <Link className="text-link" to="/">
          ← Return to citizen site
        </Link>
      </form>
    </main>
  );
}
