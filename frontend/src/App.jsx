import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import "./App.css";

const runtimeApiBaseUrl = window.__INSUMEAL_CONFIG__?.API_BASE_URL;
const envApiBaseUrl = import.meta.env.VITE_API_BASE_URL;
const API_BASE_URL = envApiBaseUrl || runtimeApiBaseUrl || "http://localhost:8000";
const PAGE_SIZE = 10;
const TOKEN_STORAGE_KEY = "insumeal_admin_token";
const LOGO_SRC = "/logo-insumeal.png";
const METRIC_WINDOWS = [1, 7, 30];
const DAY_PART_COLORS = ["#245be6", "#4d86ff", "#63b3ed", "#9f7aea"];

function App() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_STORAGE_KEY) || "");
  const [activeView, setActiveView] = useState("home");
  const [loginForm, setLoginForm] = useState({ email: "", password: "" });
  const [loginLoading, setLoginLoading] = useState(false);

  const [users, setUsers] = useState([]);
  const [pagination, setPagination] = useState({
    page: 1,
    page_size: PAGE_SIZE,
    total_items: 0,
    total_pages: 1,
    has_next: false,
    has_previous: false,
  });
  const [totalUsers, setTotalUsers] = useState(0);
  const [searchInput, setSearchInput] = useState("");
  const [activeSearch, setActiveSearch] = useState("");
  const [listLoading, setListLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const [usageModalUser, setUsageModalUser] = useState(null);
  const [usageLoading, setUsageLoading] = useState(false);
  const [usageData, setUsageData] = useState(null);

  const [editModalUser, setEditModalUser] = useState(null);
  const [editForm, setEditForm] = useState({ name: "", lastName: "", email: "", role: "user" });
  const [editLoading, setEditLoading] = useState(false);

  const [deleteModalUser, setDeleteModalUser] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [activeUsersMetrics, setActiveUsersMetrics] = useState([]);
  const [dayPartMetrics, setDayPartMetrics] = useState([]);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [selectedActiveWindow, setSelectedActiveWindow] = useState(1);

  const currentPage = pagination.page || 1;
  const activeUsersByWindow = useMemo(
    () =>
      activeUsersMetrics.reduce((acc, item) => {
        acc[item.window_days] = item.active_users;
        return acc;
      }, {}),
    [activeUsersMetrics]
  );
  const selectedActiveUsers = activeUsersByWindow[selectedActiveWindow] || 0;
  const activeUsersChartData = useMemo(
    () => [
      {
        name: `${selectedActiveWindow} día${selectedActiveWindow > 1 ? "s" : ""}`,
        usuarios: selectedActiveUsers,
      },
    ],
    [selectedActiveUsers, selectedActiveWindow]
  );
  const dayPartChartData = useMemo(
    () =>
      dayPartMetrics.map((segment) => ({
        name: segment.label,
        requests: segment.requests,
        percentage: segment.percentage,
      })),
    [dayPartMetrics]
  );

  const authHeaders = useMemo(
    () => ({
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    }),
    [token]
  );

  async function parseResponse(res) {
    const text = await res.text();
    let data = null;
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = { detail: text };
      }
    }
    if (!res.ok) {
      const detail = data?.detail;
      const msg =
        typeof detail === "string"
          ? detail
          : detail?.message || data?.message || `Error ${res.status}`;
      throw new Error(msg);
    }
    return data;
  }

  async function loadUsers(page = 1, search = activeSearch) {
    if (!token) return;
    setListLoading(true);
    setErrorMsg("");
    try {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(PAGE_SIZE),
      });
      if (search) params.set("search", search);
      const res = await fetch(`${API_BASE_URL}/admin/users?${params.toString()}`, {
        headers: authHeaders,
      });
      const data = await parseResponse(res);
      setUsers(data.items || []);
      setPagination(data.pagination || pagination);
    } catch (error) {
      setErrorMsg(error.message || "No se pudo cargar el listado de usuarios.");
    } finally {
      setListLoading(false);
    }
  }

  async function loadUsersCount() {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE_URL}/admin/users/count`, {
        headers: authHeaders,
      });
      const data = await parseResponse(res);
      setTotalUsers(data.total_users || 0);
    } catch {
      setTotalUsers(0);
    }
  }

  async function loadActiveUsersMetrics() {
    if (!token) return;
    const res = await fetch(`${API_BASE_URL}/admin/metrics/active-users`, {
      headers: authHeaders,
    });
    const data = await parseResponse(res);
    const rows = Array.isArray(data?.windows) ? data.windows : [];
    const fallback = METRIC_WINDOWS.map((days) => ({ window_days: days, active_users: 0 }));
    setActiveUsersMetrics(rows.length > 0 ? rows : fallback);
  }

  async function loadDayPartMetrics() {
    if (!token) return;
    const res = await fetch(`${API_BASE_URL}/admin/metrics/usage-by-daypart`, {
      headers: authHeaders,
    });
    const data = await parseResponse(res);
    setDayPartMetrics(Array.isArray(data?.segments) ? data.segments : []);
  }

  async function loadMetricsData() {
    if (!token) return;
    setMetricsLoading(true);
    setErrorMsg("");
    try {
      await Promise.all([loadActiveUsersMetrics(), loadDayPartMetrics()]);
    } catch (error) {
      setErrorMsg(error.message || "No se pudieron cargar las métricas.");
    } finally {
      setMetricsLoading(false);
    }
  }

  useEffect(() => {
    if (!token) return;
    loadUsers(1, activeSearch);
    loadUsersCount();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, activeSearch]);

  useEffect(() => {
    if (!token || activeView !== "metrics") return;
    loadMetricsData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, activeView]);

  async function handleLogin(e) {
    e.preventDefault();
    setLoginLoading(true);
    setErrorMsg("");
    try {
      const res = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(loginForm),
      });
      const data = await parseResponse(res);
      localStorage.setItem(TOKEN_STORAGE_KEY, data.access_token);
      setToken(data.access_token);
      setLoginForm({ email: "", password: "" });
    } catch (error) {
      setErrorMsg(error.message || "No se pudo iniciar sesión.");
    } finally {
      setLoginLoading(false);
    }
  }

  function handleLogout() {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken("");
    setActiveView("home");
    setUsers([]);
    setTotalUsers(0);
    setSearchInput("");
    setActiveSearch("");
    setActiveUsersMetrics([]);
    setDayPartMetrics([]);
    setSelectedActiveWindow(1);
    setErrorMsg("");
  }

  function handleSearchSubmit(e) {
    e.preventDefault();
    setActiveSearch(searchInput.trim());
  }

  async function openUsageModal(user) {
    setUsageModalUser(user);
    setUsageData(null);
    setUsageLoading(true);
    setErrorMsg("");
    try {
      const res = await fetch(`${API_BASE_URL}/admin/users/${user.id}/usage`, {
        headers: authHeaders,
      });
      const data = await parseResponse(res);
      setUsageData(data);
    } catch (error) {
      setErrorMsg(error.message || "No se pudo cargar el consumo.");
      setUsageModalUser(null);
    } finally {
      setUsageLoading(false);
    }
  }

  function openEditModal(user) {
    setEditModalUser(user);
    setEditForm({
      name: user.name || "",
      lastName: user.lastName || "",
      email: user.email || "",
      role: user.role || "user",
    });
  }

  async function submitEdit(e) {
    e.preventDefault();
    if (!editModalUser) return;
    setEditLoading(true);
    setErrorMsg("");
    try {
      const res = await fetch(`${API_BASE_URL}/admin/users/${editModalUser.id}`, {
        method: "PUT",
        headers: authHeaders,
        body: JSON.stringify(editForm),
      });
      await parseResponse(res);
      setEditModalUser(null);
      await loadUsers(currentPage, activeSearch);
      await loadUsersCount();
    } catch (error) {
      setErrorMsg(error.message || "No se pudo actualizar el usuario.");
    } finally {
      setEditLoading(false);
    }
  }

  async function confirmDelete() {
    if (!deleteModalUser) return;
    setDeleteLoading(true);
    setErrorMsg("");
    try {
      const res = await fetch(`${API_BASE_URL}/admin/users/${deleteModalUser.id}`, {
        method: "DELETE",
        headers: authHeaders,
      });
      await parseResponse(res);
      setDeleteModalUser(null);
      const nextPage =
        users.length === 1 && currentPage > 1 ? currentPage - 1 : currentPage;
      await loadUsers(nextPage, activeSearch);
      await loadUsersCount();
    } catch (error) {
      setErrorMsg(error.message || "No se pudo eliminar el usuario.");
    } finally {
      setDeleteLoading(false);
    }
  }

  if (!token) {
    return (
      <main className="app-shell centered">
        <section className="card login-card">
          <Brand title="InsuMeal Admin Login" subtitle="Ingresá con un usuario administrador." />
          <form onSubmit={handleLogin} className="form-grid">
            <label>
              Email
              <input
                type="email"
                value={loginForm.email}
                onChange={(e) =>
                  setLoginForm((prev) => ({ ...prev, email: e.target.value }))
                }
                required
                autoComplete="email"
              />
            </label>
            <label>
              Password
              <input
                type="password"
                value={loginForm.password}
                onChange={(e) =>
                  setLoginForm((prev) => ({ ...prev, password: e.target.value }))
                }
                required
                autoComplete="current-password"
              />
            </label>
            <button type="submit" className="btn primary" disabled={loginLoading}>
              {loginLoading ? "Ingresando..." : "Ingresar"}
            </button>
          </form>
          {errorMsg ? <p className="error">{errorMsg}</p> : null}
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <Brand
          title={activeView === "home" ? "InsuMeal Admin Home" : "InsuMeal Admin Métricas"}
          subtitle={
            activeView === "home"
              ? "Panel de administración de usuarios"
              : "Uso agregado y actividad de usuarios"
          }
        />
        <div className="topbar-actions">
          <div className="view-switch" role="tablist" aria-label="Vistas del panel">
            <button
              className={`btn small ${activeView === "home" ? "primary" : ""}`}
              onClick={() => setActiveView("home")}
              type="button"
            >
              Home
            </button>
            <button
              className={`btn small ${activeView === "metrics" ? "primary" : ""}`}
              onClick={() => setActiveView("metrics")}
              type="button"
            >
              Métricas
            </button>
          </div>
          <button className="btn" onClick={handleLogout}>
            Cerrar sesión
          </button>
        </div>
      </header>

      {activeView === "home" ? (
        <section className="card">
          <form className="search-row" onSubmit={handleSearchSubmit}>
            <input
              type="text"
              placeholder="Buscar por nombre, apellido o email"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
            />
            <button className="btn primary" type="submit">
              Buscar
            </button>
            <button
              className="btn"
              type="button"
              onClick={() => {
                setSearchInput("");
                setActiveSearch("");
              }}
            >
              Limpiar
            </button>
          </form>

          {errorMsg ? <p className="error">{errorMsg}</p> : null}

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Nombre</th>
                  <th>Apellido</th>
                  <th>Email</th>
                  <th>Rol</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {listLoading ? (
                  <tr>
                    <td colSpan={6} className="empty">
                      Cargando usuarios...
                    </td>
                  </tr>
                ) : users.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="empty">
                      No hay usuarios para mostrar.
                    </td>
                  </tr>
                ) : (
                  users.map((user) => (
                    <tr key={user.id}>
                      <td>{user.id}</td>
                      <td>{user.name}</td>
                      <td>{user.lastName}</td>
                      <td>{user.email}</td>
                      <td>
                        <span className={`role-badge ${user.role}`}>{user.role}</span>
                      </td>
                      <td>
                        <div className="actions">
                          <button className="btn small" onClick={() => openUsageModal(user)}>
                            Ver
                          </button>
                          <button className="btn small" onClick={() => openEditModal(user)}>
                            Editar
                          </button>
                          <button
                            className="btn small danger"
                            onClick={() => setDeleteModalUser(user)}
                          >
                            Eliminar
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="pager">
            <button
              className="btn"
              disabled={!pagination.has_previous || listLoading}
              onClick={() => loadUsers(currentPage - 1, activeSearch)}
            >
              Anterior
            </button>
            <span>
              Página {pagination.page} de {pagination.total_pages}
            </span>
            <button
              className="btn"
              disabled={!pagination.has_next || listLoading}
              onClick={() => loadUsers(currentPage + 1, activeSearch)}
            >
              Siguiente
            </button>
          </div>
        </section>
      ) : (
        <>
          <section className="metrics-grid">
            <article className="card metric-card">
              <h2 className="metric-section-title">Usuarios Totales</h2>
              <div className="metric-total-inline">
                <strong className="total-users-value">{totalUsers}</strong>
              </div>
              <h2 className="metric-section-title">Usuarios activos por ventana de tiempo</h2>
              <p className="muted">Cantidad de usuarios con al menos 1 request en 1, 7 y 30 días.</p>
              {metricsLoading ? (
                <p className="empty">Cargando métricas...</p>
              ) : (
                <div className="metric-chart-wrap">
                  <div className="metric-highlight">
                    <span className="metric-highlight-label">Usuarios activos</span>
                    <strong className="metric-highlight-value">{selectedActiveUsers}</strong>
                  </div>
                  <div className="metric-filter">
                    {METRIC_WINDOWS.map((days) => (
                      <button
                        key={days}
                        type="button"
                        className={`btn small ${selectedActiveWindow === days ? "primary" : ""}`}
                        onClick={() => setSelectedActiveWindow(days)}
                      >
                        {days} día{days > 1 ? "s" : ""}
                      </button>
                    ))}
                  </div>
                  <div className="chart-container">
                    <ResponsiveContainer width="100%" height={260}>
                      <BarChart data={activeUsersChartData} margin={{ top: 12, right: 12, left: 4, bottom: 8 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="name" />
                        <YAxis allowDecimals={false} />
                        <Tooltip formatter={(value) => [value, "Usuarios"]} />
                        <Bar dataKey="usuarios" fill="#245be6" radius={[8, 8, 0, 0]} maxBarSize={84} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
            </article>

            <article className="card metric-card">
              <h2>Uso por momento del día</h2>
              <p className="muted">
                Uso total agregado: mañana (00-12), mediodía (12-15), tarde (15-20), noche (20-00).
              </p>
              {metricsLoading ? (
                <p className="empty">Cargando métricas...</p>
              ) : (
                <div className="metric-chart-wrap">
                  <div className="chart-container">
                    <ResponsiveContainer width="100%" height={300}>
                      <PieChart>
                        <Pie
                          data={dayPartChartData}
                          dataKey="requests"
                          nameKey="name"
                          cx="50%"
                          cy="50%"
                          outerRadius={104}
                          innerRadius={58}
                          paddingAngle={2}
                        >
                          {dayPartChartData.map((entry, index) => (
                            <Cell key={`${entry.name}-${index}`} fill={DAY_PART_COLORS[index % DAY_PART_COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip
                          formatter={(value, _name, payload) => [
                            `${value} requests (${payload?.payload?.percentage || 0}%)`,
                            payload?.payload?.name || "Segmento",
                          ]}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="metric-legend">
                    {dayPartChartData.map((entry, index) => (
                      <div key={entry.name} className="metric-legend-item">
                        <span
                          className="metric-legend-dot"
                          style={{ backgroundColor: DAY_PART_COLORS[index % DAY_PART_COLORS.length] }}
                        />
                        <span>{entry.name}</span>
                        <strong>{entry.requests}</strong>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </article>
          </section>
        </>
      )}

      {usageModalUser ? (
        <Modal title={`Uso de tokens - ${usageModalUser.email}`} onClose={() => setUsageModalUser(null)}>
          {usageLoading ? (
            <p>Cargando consumo...</p>
          ) : usageData ? (
            <>
              <div className="usage-summary">
                <p>
                  <span className="usage-summary-label">Cantidad de requests:</span>
                  <strong className="usage-summary-value">{usageData.total_requests}</strong>
                </p>
                <p>
                  <span className="usage-summary-label">Input tokens:</span>
                  <strong className="usage-summary-value">{usageData.prompt_tokens}</strong>
                </p>
                <p>
                  <span className="usage-summary-label">Output tokens:</span>
                  <strong className="usage-summary-value">{usageData.completion_tokens}</strong>
                </p>
                <p>
                  <span className="usage-summary-label">Total tokens:</span>
                  <strong className="usage-summary-value">{usageData.total_tokens}</strong>
                </p>
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Provider</th>
                      <th>Modelo</th>
                      <th>Requests</th>
                      <th>Input</th>
                      <th>Output</th>
                      <th>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {usageData.breakdown.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="empty">
                          No hay consumo para este usuario.
                        </td>
                      </tr>
                    ) : (
                      usageData.breakdown.map((row) => (
                        <tr key={`${row.provider}-${row.model_name}`}>
                          <td>{row.provider}</td>
                          <td>{row.model_name}</td>
                          <td>{row.requests}</td>
                          <td>{row.prompt_tokens}</td>
                          <td>{row.completion_tokens}</td>
                          <td>{row.total_tokens}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </>
          ) : null}
        </Modal>
      ) : null}

      {editModalUser ? (
        <Modal title={`Editar usuario #${editModalUser.id}`} onClose={() => setEditModalUser(null)}>
          <form onSubmit={submitEdit} className="form-grid">
            <label>
              Nombre
              <input
                value={editForm.name}
                onChange={(e) => setEditForm((prev) => ({ ...prev, name: e.target.value }))}
                required
              />
            </label>
            <label>
              Apellido
              <input
                value={editForm.lastName}
                onChange={(e) => setEditForm((prev) => ({ ...prev, lastName: e.target.value }))}
                required
              />
            </label>
            <label>
              Email
              <input
                type="email"
                value={editForm.email}
                onChange={(e) => setEditForm((prev) => ({ ...prev, email: e.target.value }))}
                required
              />
            </label>
            <label>
              Rol
              <select
                value={editForm.role}
                onChange={(e) => setEditForm((prev) => ({ ...prev, role: e.target.value }))}
              >
                <option value="user">user</option>
                <option value="admin">admin</option>
              </select>
            </label>
            <div className="modal-actions">
              <button type="button" className="btn" onClick={() => setEditModalUser(null)}>
                Cancelar
              </button>
              <button type="submit" className="btn primary" disabled={editLoading}>
                {editLoading ? "Guardando..." : "Guardar"}
              </button>
            </div>
          </form>
        </Modal>
      ) : null}

      {deleteModalUser ? (
        <Modal title="Confirmar eliminación" onClose={() => setDeleteModalUser(null)}>
          <p>
            Vas a eliminar al usuario <strong>{deleteModalUser.email}</strong>. Esta acción no se
            puede deshacer.
          </p>
          <div className="modal-actions">
            <button className="btn" onClick={() => setDeleteModalUser(null)} disabled={deleteLoading}>
              Cancelar
            </button>
            <button className="btn danger" onClick={confirmDelete} disabled={deleteLoading}>
              {deleteLoading ? "Eliminando..." : "Eliminar"}
            </button>
          </div>
        </Modal>
      ) : null}
    </main>
  );
}

function Modal({ title, onClose, children }) {
  return (
    <div className="modal-overlay" role="presentation" onClick={onClose}>
      <section className="modal-card" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <header className="modal-header">
          <h2>{title}</h2>
          <button className="btn small" onClick={onClose}>
            Cerrar
          </button>
        </header>
        <div className="modal-body">{children}</div>
      </section>
    </div>
  );
}

function Brand({ title, subtitle }) {
  return (
    <div className="brand">
      <img src={LOGO_SRC} alt="InsuMeal logo" className="brand-logo" />
      <div>
        <h1>{title}</h1>
        {subtitle ? <p className="muted">{subtitle}</p> : null}
      </div>
    </div>
  );
}

export default App;
