import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { X, Send } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ChatModal({ offerId, title, user, close }) {
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    let active = true;
    const poll = () => axios.get(`${API}/offers/${offerId}/messages`, { withCredentials: true })
      .then(r => { if (active) setMessages(r.data); })
      .catch(() => {});
    poll();
    const interval = setInterval(poll, 3000);
    return () => { active = false; clearInterval(interval); };
  }, [offerId]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const send = async (e) => {
    e.preventDefault();
    if (!text.trim() || sending) return;
    setSending(true);
    setError("");
    try {
      const r = await axios.post(`${API}/offers/${offerId}/messages`, { text }, { withCredentials: true });
      setMessages(prev => [...prev, r.data]);
      setText("");
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Não foi possível enviar a mensagem.");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={close}>
      <div className="chat-modal" onClick={e => e.stopPropagation()}>
        <div className="chat-header">
          <div>
            <span className="section-kicker">CONVERSA</span>
            <h2>{title}</h2>
          </div>
          <button className="modal-close" onClick={close}><X size={20} /></button>
        </div>
        <div className="chat-body" ref={scrollRef}>
          {messages.length === 0 && <div className="chat-empty">As mensagens trocadas aparecem aqui. Comece a conversa!</div>}
          {messages.map(m => (
            <div key={m.id} className={`chat-bubble ${m.sender_id === user?.id ? "mine" : "theirs"}`}>
              {m.sender_id !== user?.id && <span className="chat-sender">{m.sender_name}</span>}
              <p>{m.text}</p>
              <small>{new Date(m.created_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</small>
            </div>
          ))}
        </div>
        {error && <div className="form-error chat-error">{error}</div>}
        <form className="chat-input-row" onSubmit={send}>
          <input data-testid="chat-message-input" value={text} onChange={e => setText(e.target.value)} placeholder="Escreva uma mensagem..." />
          <button type="submit" data-testid="chat-send-button" disabled={sending || !text.trim()}><Send size={17} /></button>
        </form>
      </div>
    </div>
  );
}
