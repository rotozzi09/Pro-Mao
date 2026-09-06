import { useEffect, useState } from "react";
import axios from "axios";
import { ChevronLeft, Calendar, Check, X, Clock } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STATUS = {
  pending: { label: "Aguardando", cls: "apt-pending" },
  confirmed: { label: "Confirmado", cls: "apt-confirmed" },
  completed: { label: "Concluído", cls: "apt-completed" },
  cancelled: { label: "Cancelado", cls: "apt-cancelled" },
};

export default function AppointmentsView({ user, onBack, onMessage }) {
  const [items, setItems] = useState([]);
  const isProvider = (user?.roles || []).includes("provider");

  const load = () => {
    axios.get(`${API}/appointments`, { withCredentials: true })
      .then(r => setItems(r.data))
      .catch(() => {});
  };
  useEffect(load, []);

  const updateStatus = async (id, status) => {
    try {
      await axios.post(`${API}/appointments/${id}/status`, { status }, { withCredentials: true });
      onMessage(STATUS[status]?.label ? `Agendamento ${STATUS[status].label.toLowerCase()}.` : "Atualizado.");
      load();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      onMessage(typeof detail === "string" ? detail : "Não foi possível atualizar.");
    }
  };

  return (
    <main className="appointments-page">
      <button className="back-btn" data-testid="apt-back-button" onClick={onBack}><ChevronLeft size={18} /> voltar</button>
      <span className="section-kicker">AGENDAMENTOS</span>
      <h1>Horários<br /><em>marcados.</em></h1>
      {items.length === 0 ? (
        <div className="empty-state" data-testid="empty-appointments">Nenhum agendamento ainda. Visite o perfil de um prestador para marcar um serviço.</div>
      ) : (
        <div className="apt-list">
          {items.map((a, i) => {
            const st = STATUS[a.status] || STATUS.pending;
            const isMyApt = a.provider_id === user?.id;
            return (
              <div className={`apt-card ${st.cls}`} key={a.id} data-testid={`apt-card-${i}`}>
                <div className="apt-card-head">
                  <b data-testid={`apt-service-${i}`}>{a.service}</b>
                  <span className={`chip ${st.cls}`} data-testid={`apt-status-${i}`}>{st.label}</span>
                </div>
                <div className="apt-card-meta">
                  <span><Calendar size={14} /> {a.date}</span>
                  <span><Clock size={14} /> {a.time}</span>
                </div>
                <p className="apt-parties">{isProvider && a.client_id !== user?.id ? `Cliente: ${a.client_name}` : `Prestador: ${a.provider_name}`}</p>
                {a.notes && <p className="apt-notes">{a.notes}</p>}
                {isProvider && a.status === "pending" && (
                  <div className="apt-actions">
                    <button className="primary-btn small" data-testid={`apt-confirm-${i}`} onClick={() => updateStatus(a.id, "confirmed")}><Check size={14} /> Confirmar</button>
                    <button className="outline-btn small" data-testid={`apt-cancel-${i}`} onClick={() => updateStatus(a.id, "cancelled")}><X size={14} /> Cancelar</button>
                  </div>
                )}
                {a.status === "confirmed" && (
                  <div className="apt-actions">
                    <button className="primary-btn small" data-testid={`apt-complete-${i}`} onClick={() => updateStatus(a.id, "completed")}><Check size={14} /> Concluir</button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </main>
  );
}
