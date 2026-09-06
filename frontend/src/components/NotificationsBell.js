import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { Bell, CheckCheck, X } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function NotificationsBell({ user }) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState({ notifications: [], unread: 0 });
  const ref = useRef(null);

  const load = () => {
    if (!user) return;
    axios.get(`${API}/notifications`, { withCredentials: true })
      .then(r => setData(r.data))
      .catch(() => {});
  };

  useEffect(() => {
    let active = true;
    const poll = () => { if (!user) return; axios.get(`${API}/notifications`, { withCredentials: true }).then(r => { if (active) setData(r.data); }).catch(() => {}); };
    poll();
    const interval = setInterval(poll, 15000);
    return () => { active = false; clearInterval(interval); };
  }, [user]);

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const markRead = async (id) => {
    await axios.post(`${API}/notifications/${id}/read`, {}, { withCredentials: true });
    load();
  };

  const markAllRead = async () => {
    await axios.post(`${API}/notifications/read-all`, {}, { withCredentials: true });
    load();
  };

  if (!user) return null;

  return (
    <div className="notif-bell" ref={ref}>
      <button className="bell-btn" data-testid="notifications-bell" onClick={() => setOpen(!open)}>
        <Bell size={19} />
        {data.unread > 0 && <span className="notif-badge" data-testid="notif-unread-badge">{data.unread}</span>}
      </button>
      {open && (
        <div className="notif-dropdown" data-testid="notif-dropdown">
          <div className="notif-header">
            <span>Notificações</span>
            {data.unread > 0 && <button data-testid="notif-read-all" onClick={markAllRead}><CheckCheck size={15} /> Marcar todas</button>}
          </div>
          <div className="notif-list">
            {data.notifications.length === 0 && <div className="notif-empty">Sem notificações por enquanto.</div>}
            {data.notifications.map((n, i) => (
              <div key={n.id} className={`notif-item ${n.read ? "" : "unread"}`} data-testid={`notif-item-${i}`} onClick={() => !n.read && markRead(n.id)}>
                <div className="notif-dot-wrap">{!n.read && <span className="notif-dot" />}
                  <div>
                    <b>{n.title}</b>
                    <p>{n.body}</p>
                    <small>{new Date(n.created_at).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}</small>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
