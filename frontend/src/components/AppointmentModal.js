import { useState } from "react";
import axios from "axios";
import { X, ArrowRight, Calendar } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AppointmentModal({ providerId, providerName, user, close, onDone }) {
  const [form, setForm] = useState({ service: "", date: "", time: "", notes: "" });
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await axios.post(`${API}/appointments`, { ...form, provider_id: providerId }, { withCredentials: true });
      onDone(`Agendamento enviado para ${providerName}! Aguarde a confirmação.`);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Não foi possível agendar.");
    }
  };

  return (
    <div className="modal-backdrop" onClick={close}>
      <div className="auth-modal" onClick={e => e.stopPropagation()}>
        <button className="modal-close" data-testid="appointment-close" onClick={close}><X size={20} /></button>
        <span className="section-kicker">AGENDAR SERVIÇO</span>
        <h2>Marcar com<br /><em>{providerName}</em></h2>
        <form onSubmit={submit} data-testid="appointment-form">
          <label>Qual serviço?
            <input data-testid="apt-service-input" required value={form.service} onChange={e => setForm({ ...form, service: e.target.value })} placeholder="Ex.: revisão elétrica" />
          </label>
          <div className="apt-datetime">
            <label>Data
              <input data-testid="apt-date-input" type="date" required value={form.date} onChange={e => setForm({ ...form, date: e.target.value })} />
            </label>
            <label>Hora
              <input data-testid="apt-time-input" type="time" required value={form.time} onChange={e => setForm({ ...form, time: e.target.value })} />
            </label>
          </div>
          <label>Observações <span className="optional">opcional</span>
            <textarea data-testid="apt-notes-input" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} placeholder="Detalhes para o prestador" />
          </label>
          {error && <div className="form-error" data-testid="appointment-error">{error}</div>}
          <button className="primary-btn wide" data-testid="appointment-submit"><Calendar size={16} /> Confirmar agendamento <ArrowRight size={17} /></button>
        </form>
      </div>
    </div>
  );
}
