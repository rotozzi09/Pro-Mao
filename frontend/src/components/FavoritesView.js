import { useEffect, useState } from "react";
import axios from "axios";
import { ChevronLeft, HeartHandshake, ArrowRight, X } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function FavoritesView({ user, onBack, onProviderProfile, onMessage }) {
  const [items, setItems] = useState([]);

  const load = () => {
    axios.get(`${API}/favorites`, { withCredentials: true })
      .then(r => setItems(r.data))
      .catch(() => {});
  };
  useEffect(load, []);

  const remove = async (providerId) => {
    await axios.post(`${API}/favorites/${providerId}`, {}, { withCredentials: true });
    setItems(items.filter(i => i.provider_id !== providerId));
    onMessage("Removido dos favoritos.");
  };

  return (
    <main className="favorites-page">
      <button className="back-btn" data-testid="fav-back-button" onClick={onBack}><ChevronLeft size={18} /> voltar</button>
      <span className="section-kicker">FAVORITOS</span>
      <h1>Seus prestadores<br /><em>de confiança.</em></h1>
      {items.length === 0 ? (
        <div className="empty-state" data-testid="empty-favorites">Você ainda não salvou nenhum prestador. Toque no coração nos cards para guardar seus preferidos.</div>
      ) : (
        <div className="fav-list">
          {items.map((f, i) => (
            <div className="fav-card" key={f.id} data-testid={`fav-card-${i}`}>
              <span className="fav-avatar">{f.initials}</span>
              <div className="fav-info">
                <b data-testid={`fav-name-${i}`}>{f.name}</b>
                <small>{f.category}</small>
              </div>
              <div className="fav-actions">
                <button className="outline-btn small" data-testid={`fav-view-${i}`} onClick={() => onProviderProfile(f.provider_id)}>Ver perfil <ArrowRight size={14} /></button>
                <button className="icon-btn" data-testid={`fav-remove-${i}`} onClick={() => remove(f.provider_id)}><X size={16} /></button>
              </div>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
