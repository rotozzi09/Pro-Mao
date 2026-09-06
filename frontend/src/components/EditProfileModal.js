import { useState } from "react";
import axios from "axios";
import { X, ArrowRight, Camera } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function EditProfileModal({ user, close, onSuccess, onMessage }) {
  const [name, setName] = useState(user?.name || "");
  const [email, setEmail] = useState(user?.email || "");
  const [avatar, setAvatar] = useState(user?.avatar_data || "");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const onFile = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 500_000) { setError("A imagem deve ter no máximo 500KB."); return; }
    const reader = new FileReader();
    reader.onload = () => setAvatar(reader.result);
    reader.readAsDataURL(file);
  };

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const r = await axios.put(`${API}/users/me`, { name, email, avatar_data: avatar || null }, { withCredentials: true });
      onSuccess(r.data);
      onMessage("Perfil atualizado com sucesso.");
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Não foi possível salvar.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={close}>
      <div className="auth-modal" onClick={e => e.stopPropagation()}>
        <button className="modal-close" data-testid="edit-profile-close" onClick={close}><X size={20} /></button>
        <span className="section-kicker">EDITAR PERFIL</span>
        <h2>Seus dados</h2>
        <form onSubmit={submit} data-testid="edit-profile-form" className="edit-profile-form">
          <div className="avatar-preview">
            {avatar ? <img src={avatar} alt="Avatar" /> : <span>{(name || "U")[0]}</span>}
            <label className="avatar-upload" data-testid="avatar-upload-label">
              <Camera size={16} />
              <input type="file" accept="image/*" onChange={onFile} data-testid="avatar-file-input" />
            </label>
          </div>
          <label>Seu nome
            <input data-testid="edit-name-input" value={name} onChange={e => setName(e.target.value)} required placeholder="Como podemos te chamar?" />
          </label>
          <label>Seu e-mail
            <input data-testid="edit-email-input" type="email" value={email} onChange={e => setEmail(e.target.value)} required placeholder="voce@email.com" />
          </label>
          {error && <div className="form-error" data-testid="edit-profile-error">{error}</div>}
          <button className="primary-btn wide" data-testid="edit-profile-save" disabled={saving}>{saving ? "Salvando..." : "Salvar alterações"} <ArrowRight size={17} /></button>
        </form>
      </div>
    </div>
  );
}
