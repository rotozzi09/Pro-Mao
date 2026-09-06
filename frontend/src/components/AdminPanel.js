import { useEffect, useState } from "react";
import axios from "axios";
import { ChevronLeft, Users, FileText, Star, Ban, CheckCircle, Trash2, Calendar } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AdminPanel({ user, onBack, onMessage }) {
  const [stats, setStats] = useState({});
  const [users, setUsers] = useState([]);
  const [requests, setRequests] = useState([]);
  const [reviews, setReviews] = useState([]);
  const [tab, setTab] = useState("users");

  const load = () => {
    axios.get(`${API}/admin/stats`, { withCredentials: true }).then(r => setStats(r.data)).catch(() => {});
    axios.get(`${API}/admin/users`, { withCredentials: true }).then(r => setUsers(r.data)).catch(() => {});
    axios.get(`${API}/admin/requests`, { withCredentials: true }).then(r => setRequests(r.data)).catch(() => {});
    axios.get(`${API}/admin/reviews`, { withCredentials: true }).then(r => setReviews(r.data)).catch(() => {});
  };
  useEffect(load, []);

  const toggleBan = async (u) => {
    try {
      await axios.patch(`${API}/admin/users/${u.id}`, { banned: !u.banned }, { withCredentials: true });
      onMessage(u.banned ? "Conta reativada." : "Conta suspensa.");
      load();
    } catch (err) {
      onMessage("Não foi possível atualizar.");
    }
  };

  const deleteRequest = async (id) => {
    if (!confirm("Excluir este pedido?")) return;
    await axios.delete(`${API}/admin/requests/${id}`, { withCredentials: true });
    onMessage("Pedido excluído.");
    load();
  };

  const deleteReview = async (id) => {
    if (!confirm("Excluir esta avaliação?")) return;
    await axios.delete(`${API}/admin/reviews/${id}`, { withCredentials: true });
    onMessage("Avaliação excluída.");
    load();
  };

  const statCards = [
    { label: "Usuários", value: stats.users, icon: Users },
    { label: "Prestadores", value: stats.providers, icon: CheckCircle },
    { label: "Pedidos", value: stats.requests, icon: FileText },
    { label: "Concluídos", value: stats.completed, icon: Star },
    { label: "Avaliações", value: stats.reviews, icon: Star },
    { label: "Agendamentos", value: stats.appointments, icon: Calendar },
  ];

  return (
    <main className="admin-page">
      <button className="back-btn" data-testid="admin-back-button" onClick={onBack}><ChevronLeft size={18} /> voltar</button>
      <span className="section-kicker">PAINEL ADMINISTRATIVO</span>
      <h1>Visão geral<br /><em>da plataforma.</em></h1>
      <div className="admin-stats-grid">
        {statCards.map((s, i) => (
          <div className="admin-stat-card" key={i} data-testid={`admin-stat-${i}`}>
            <s.icon size={20} />
            <div><b>{s.value ?? 0}</b><small>{s.label}</small></div>
          </div>
        ))}
      </div>
      <div className="admin-tabs">
        <button className={tab === "users" ? "active" : ""} data-testid="admin-tab-users" onClick={() => setTab("users")}>Usuários</button>
        <button className={tab === "requests" ? "active" : ""} data-testid="admin-tab-requests" onClick={() => setTab("requests")}>Pedidos</button>
        <button className={tab === "reviews" ? "active" : ""} data-testid="admin-tab-reviews" onClick={() => setTab("reviews")}>Avaliações</button>
      </div>
      {tab === "users" && (
        <div className="admin-table" data-testid="admin-users-table">
          {users.map((u, i) => (
            <div className={`admin-row ${u.banned ? "banned" : ""}`} key={u.id} data-testid={`admin-user-${i}`}>
              <span className="admin-row-avatar">{u.name?.[0]}</span>
              <div className="admin-row-info">
                <b>{u.name}</b>
                <small>{u.email} · {(u.roles || []).join(", ")}</small>
              </div>
              <button className={u.banned ? "outline-btn small" : "ban-btn small"} data-testid={`admin-ban-${i}`} onClick={() => toggleBan(u)}>
                {u.banned ? <><CheckCircle size={14} /> Reativar</> : <><Ban size={14} /> Suspender</>}
              </button>
            </div>
          ))}
        </div>
      )}
      {tab === "requests" && (
        <div className="admin-table" data-testid="admin-requests-table">
          {requests.length === 0 && <div className="empty-state">Nenhum pedido.</div>}
          {requests.map((r, i) => (
            <div className="admin-row" key={r.id} data-testid={`admin-request-${i}`}>
              <div className="admin-row-info">
                <b>{r.service}</b>
                <small>{r.category} · {r.status}</small>
              </div>
              <button className="ban-btn small" data-testid={`admin-delete-request-${i}`} onClick={() => deleteRequest(r.id)}><Trash2 size={14} /></button>
            </div>
          ))}
        </div>
      )}
      {tab === "reviews" && (
        <div className="admin-table" data-testid="admin-reviews-table">
          {reviews.length === 0 && <div className="empty-state">Nenhuma avaliação.</div>}
          {reviews.map((r, i) => (
            <div className="admin-row" key={r.id} data-testid={`admin-review-${i}`}>
              <div className="admin-row-info">
                <b>{r.client_name} · ★ {r.rating}</b>
                <small>{r.testimonial?.substring(0, 80)}</small>
              </div>
              <button className="ban-btn small" data-testid={`admin-delete-review-${i}`} onClick={() => deleteReview(r.id)}><Trash2 size={14} /></button>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
