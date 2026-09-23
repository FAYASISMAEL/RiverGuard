import { createContext, useContext, useEffect, useState } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { api, post, setCsrfToken } from "./api";

const AdminContext = createContext(null);
export function AdminProvider({ children }) {
  const [user, setUser] = useState(null),
    [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    api("/admin/session")
      .then((session) => {
        if (active) {
          setUser(session);
          setCsrfToken(session.csrf_token);
        }
      })
      .catch(() => {})
      .finally(() => {
        if (active) setLoading(false);
      });
    const expired = () => {
      setUser(null);
      setCsrfToken("");
    };
    window.addEventListener("admin-session-expired", expired);
    return () => {
      active = false;
      window.removeEventListener("admin-session-expired", expired);
    };
  }, []);
  async function login(username, password) {
    const session = await post("/admin/login", { username, password });
    setCsrfToken(session.csrf_token);
    setUser(session);
  }
  async function logout() {
    await post("/admin/logout");
    setCsrfToken("");
    setUser(null);
  }
  return (
    <AdminContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AdminContext.Provider>
  );
}
export const useAdmin = () => useContext(AdminContext);
export function RequireAdmin() {
  const { user, loading } = useAdmin(),
    location = useLocation();
  if (loading)
    return (
      <main className="page">
        <p>Checking admin session…</p>
      </main>
    );
  return user ? (
    <Outlet />
  ) : (
    <Navigate to="/admin" replace state={{ from: location.pathname }} />
  );
}
