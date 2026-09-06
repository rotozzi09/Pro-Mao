import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { BrowserRouter, useLocation, useNavigate } from "react-router-dom";
import { Search, ArrowRight, Star, ShieldCheck, MapPin, LogOut, ChevronLeft, HeartHandshake, Plus, X, Share2, Copy, Mail, ExternalLink, MessageCircle, Calendar, UserCog, Compass, User } from "lucide-react";
import "@/App.css";
import ChatModal from "@/components/ChatModal";
import NotificationsBell from "@/components/NotificationsBell";
import EditProfileModal from "@/components/EditProfileModal";
import AppointmentModal from "@/components/AppointmentModal";
import AppointmentsView from "@/components/AppointmentsView";
import AdminPanel from "@/components/AdminPanel";
import FavoritesView from "@/components/FavoritesView";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const heroImage = "https://media.base44.com/images/public/6a9a2df2d94daa975c6ae948/04dab8fe3_generated_b4c36483.png";
const demoProviders = [
  {id:"demo-1",name:"Marina Alves",category:"Limpeza e organização",rating:4.9,reviews:32,price:"a partir de R$ 120",initials:"MA"},
  {id:"demo-2",name:"Rafael Costa",category:"Elétrica residencial",rating:4.8,reviews:18,price:"a partir de R$ 90",initials:"RC"},
  {id:"demo-3",name:"Júlia Martins",category:"Pintura e reparos",rating:5.0,reviews:27,price:"a partir de R$ 150",initials:"JM"}
];

function formatError(error) {
  const detail = error?.response?.data?.detail;
  return typeof detail === "string" ? detail : "Não foi possível concluir. Tente novamente.";
}

function userRoles(user) { return user?.roles?.length ? user.roles : (user?.role ? [user.role] : []); }
function canUse(user, role) { return userRoles(user).includes(role); }

function AppRouter() {
  const location = useLocation();
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [view, setView] = useState("welcome");
  const [auth, setAuth] = useState(null);
  const [authRole, setAuthRole] = useState("client");
  const [services, setServices] = useState([]);
  const [category, setCategory] = useState("");
  const [providers, setProviders] = useState(demoProviders);
  const [message, setMessage] = useState("");
  const [editProfile, setEditProfile] = useState(false);
  const [appointmentFor, setAppointmentFor] = useState(null);
  const oauthHandled = useRef(false);
  const publicProviderId = location.pathname.match(/^\/prestador\/([^/]+)/)?.[1];

  useEffect(() => {
    axios.get(`${API}/services`).then(r => setServices(r.data)).catch(() => setServices([
      {id:"cleaning",name:"Limpeza",icon:"✦",tone:"mint",description:"Casa leve, rotina tranquila"},
      {id:"electric",name:"Elétrica",icon:"ϟ",tone:"gold",description:"Energia funcionando bem"},
      {id:"plumbing",name:"Hidráulica",icon:"◒",tone:"blue",description:"Cuidado para cada detalhe"},
      {id:"painting",name:"Pintura",icon:"◉",tone:"rose",description:"Novas cores para viver"},
      {id:"gardening",name:"Jardinagem",icon:"⌁",tone:"green",description:"Mais vida nos seus espaços"},
      {id:"assembly",name:"Montagem",icon:"⊞",tone:"violet",description:"Tudo no lugar certo"}
    ]));
    const sessionId = new URLSearchParams(location.hash.replace(/^#/, "")).get("session_id");
    if (sessionId && !oauthHandled.current) {
      oauthHandled.current = true;
      axios.post(`${API}/auth/google/session`, {session_id: sessionId}, {withCredentials: true}).then(r => {
        setUser(r.data);
        setMessage("");
        setView("home");
        window.history.replaceState({}, document.title, window.location.pathname);
      }).catch(() => setMessage("Não foi possível concluir o acesso Google."));
    } else if (!sessionId) {
      axios.get(`${API}/auth/me`, {withCredentials: true}).then(r => { setUser(r.data); setView("home"); }).catch(() => {});
    }
  }, [location.hash]);

  useEffect(() => {
    if (!message) return;
    const t = setTimeout(() => setMessage(""), 4500);
    return () => clearTimeout(t);
  }, [message]);

  useEffect(() => { setMessage(""); }, [location.pathname]);
  useEffect(() => { window.scrollTo(0, 0); }, [view, publicProviderId]);

  const openHome = () => { setMessage(""); navigate("/"); setView(user ? "home" : "welcome"); };
  const search = (cat = "", q = "") => {
    setMessage("");
    setCategory(cat);
    setView("home");
    navigate("/");
    axios.get(`${API}/providers`, {params: {category: cat, q}, withCredentials: true}).then(r => setProviders(r.data)).catch(() => setProviders(demoProviders));
  };
  const logout = async () => { await axios.post(`${API}/auth/logout`, {}, {withCredentials: true}).catch(() => {}); setMessage(""); setUser(null); setView("welcome"); navigate("/"); };
  const openRegister = (role = "client") => { setMessage(""); setAuthRole(role); setAuth("register"); };
  const openProfile = (providerId) => { setMessage(""); if (!providerId || String(providerId).startsWith("demo")) { user ? setView("request") : setAuth("login"); return; } navigate(`/prestador/${providerId}`); };

  if (auth) return <AuthModal mode={auth} initialRole={authRole} close={() => setAuth(null)} onSwitch={() => setAuth(auth === "login" ? "register" : "login")} onSuccess={(u) => { setMessage(""); setUser(u); setAuth(null); setView("home"); }} />;

  return <div className="app-shell">
    <nav className="topbar">
      <button className="brand" data-testid="brand-home-button" onClick={openHome}><span className="brand-mark">P</span><span>Pro<span>Mão</span></span></button>
      <div className="nav-links"><button data-testid="nav-services-button" className={view === "home" ? "active" : ""} onClick={() => search(category)}>Encontrar serviço</button>{user && <button data-testid="nav-favorites-button" className={view === "favorites" ? "active" : ""} onClick={() => { setMessage(""); navigate("/"); setView("favorites"); }}>Favoritos</button>}{user && <button data-testid="nav-appointments-button" className={view === "appointments" ? "active" : ""} onClick={() => { setMessage(""); navigate("/"); setView("appointments"); }}>Agendamentos</button>}<button data-testid="nav-how-button" className={view === "about" ? "active" : ""} onClick={() => { setMessage(""); navigate("/"); setView("about"); }}>Como funciona</button></div>
      <div className="nav-actions">{user ? <><NotificationsBell user={user} />{canUse(user, "admin") && <button className="icon-btn" data-testid="nav-admin-button" onClick={() => { setMessage(""); navigate("/"); setView("admin"); }} title="Painel admin"><UserCog size={18}/></button>}<button className="profile-chip" data-testid="profile-menu-button" onClick={() => { setMessage(""); navigate("/"); setView("profile"); }}>{user.avatar_data ? <img src={user.avatar_data} alt="" className="avatar-small-img"/> : <span className="avatar-small">{user.name?.[0]}</span>}{user.name?.split(" ")[0]}</button><button className="icon-btn" data-testid="logout-button" onClick={logout} title="Sair"><LogOut size={18}/></button></> : <><button className="login-link" data-testid="login-open-button" onClick={() => { setMessage(""); setAuth("login"); }}>Entrar</button><button className="dark-btn" data-testid="signup-open-button" onClick={() => openRegister("client")}>Criar conta <ArrowRight size={16}/></button></>}</div>
    </nav>
    {message && <div className="toast" data-testid="success-message">{message}<button data-testid="close-message-button" onClick={() => setMessage("")}><X size={15}/></button></div>}
    {editProfile && <EditProfileModal user={user} close={() => setEditProfile(false)} onSuccess={(u) => { setUser(u); setEditProfile(false); }} onMessage={setMessage} />}
    {appointmentFor && <AppointmentModal providerId={appointmentFor.id} providerName={appointmentFor.name} user={user} close={() => setAppointmentFor(null)} onDone={(m) => { setMessage(m); setAppointmentFor(null); }} />}
    {publicProviderId && <PublicProviderProfile providerId={publicProviderId} user={user} onBack={openHome} onLogin={() => setAuth("login")} onMessage={setMessage} onSchedule={(provider) => setAppointmentFor(provider)}/>}    
    {!publicProviderId && view === "welcome" && <Welcome onChoose={openRegister} onLogin={() => setAuth("login")} onExplore={() => setView("home")} />}
    {!publicProviderId && view === "home" && <Home services={services} category={category} search={search} providers={providers} user={user} onRequest={() => user ? setView("request") : setAuth("login")} onProviderProfile={openProfile} />}
    {!publicProviderId && view === "profile" && <Profile user={user} logout={logout} onBack={() => { setMessage(""); setView("home"); }} onMessage={setMessage} onUserUpdate={setUser} onEditProfile={() => setEditProfile(true)} onAdmin={() => { setMessage(""); navigate("/"); setView("admin"); }} />}
    {!publicProviderId && view === "request" && <RequestForm onBack={() => { setMessage(""); setView("home"); }} onDone={(m) => { setMessage(m); setView("home"); }} />}
    {!publicProviderId && view === "about" && <About onBack={() => { setMessage(""); setView("home"); }} />}
    {!publicProviderId && view === "favorites" && <FavoritesView user={user} onBack={() => { setMessage(""); setView("home"); }} onProviderProfile={openProfile} onMessage={setMessage} />}
    {!publicProviderId && view === "appointments" && <AppointmentsView user={user} onBack={() => { setMessage(""); setView("home"); }} onMessage={setMessage} />}
    {!publicProviderId && view === "admin" && <AdminPanel user={user} onBack={() => { setMessage(""); setView("home"); }} onMessage={setMessage} />}
    {user && !publicProviderId && view !== "welcome" && <nav className="mobile-nav" data-testid="mobile-nav"><button data-testid="mobile-nav-home" className={view === "home" ? "active" : ""} onClick={() => { setMessage(""); setView("home"); }}><Compass size={20}/><span>Início</span></button><button data-testid="mobile-nav-favorites" className={view === "favorites" ? "active" : ""} onClick={() => { setMessage(""); setView("favorites"); }}><HeartHandshake size={20}/><span>Favoritos</span></button><button data-testid="mobile-nav-appointments" className={view === "appointments" ? "active" : ""} onClick={() => { setMessage(""); setView("appointments"); }}><Calendar size={20}/><span>Agenda</span></button><button data-testid="mobile-nav-profile" className={view === "profile" ? "active" : ""} onClick={() => { setMessage(""); setView("profile"); }}><User size={20}/><span>Perfil</span></button></nav>}
    <footer><span>ProMão</span><span>Serviços de confiança, perto de você.</span><span>© 2026</span></footer>
  </div>;
}

export default function App() { return <BrowserRouter><AppRouter /></BrowserRouter>; }

function Welcome({onChoose, onLogin, onExplore}) {
  return <main className="welcome"><section className="welcome-copy"><div className="eyebrow"><span className="live-dot"/><span className="eyebrow-copy">A rede que faz acontecer</span></div><h1>Seu tempo merece<br/><em>boas escolhas.</em></h1><p>Encontre profissionais de confiança para cuidar do que importa — ou faça seu trabalho chegar a quem precisa.</p><div className="welcome-actions"><button className="primary-btn" data-testid="choose-client-button" onClick={() => onChoose("client")}>Sou cliente <ArrowRight size={18}/></button><button className="outline-btn" data-testid="choose-provider-button" onClick={() => onChoose("provider")}>Sou prestador <Plus size={18}/></button></div><div className="trust-row"><span className="trust-pair"><ShieldCheck size={17}/><span>Perfis verificados</span></span><span className="divider"/><span className="trust-pair"><HeartHandshake size={17}/><span>Comunidade que recomenda</span></span></div></section><section className="welcome-visual"><img src={heroImage} alt="Equipe de prestadores de serviços, homens e mulheres, unidos" data-testid="welcome-hero-image"/><div className="image-note"><div className="avatar-stack"><span>MA</span><span>RC</span><span>JM</span></div><div><b>4.9 / 5</b><small>avaliação da comunidade</small></div><Star className="yellow-star" fill="currentColor"/></div></section><section className="welcome-stats" data-testid="welcome-stats"><div><b>500+</b><small>profissionais ativos</small></div><div><b>4.9</b><small>avaliação média</small></div><div><b>7</b><small>categorias de serviço</small></div></section><div className="scroll-hint" data-testid="welcome-explore" onClick={onExplore}>explore a rede <ArrowRight size={14}/></div></main>;
}

function Home({services, category, search, providers, user, onRequest, onProviderProfile}) {
  const [query, setQuery] = useState("");
  const [favIds, setFavIds] = useState([]);
  useEffect(() => { if (user) axios.get(`${API}/favorites/ids`, {withCredentials:true}).then(r => setFavIds(r.data)).catch(() => {}); }, [user]);
  const toggleFav = async (id) => { if (!user) return; try { const r = await axios.post(`${API}/favorites/${id}`, {}, {withCredentials:true}); setFavIds(r.data.favorited ? [...favIds, id] : favIds.filter(x => x !== id)); } catch {} };
  return <main className="home-page"><header className="page-intro"><div><div className="eyebrow">{user ? `Olá, ${user.name?.split(" ")[0]} 👋` : "A sua próxima solução está aqui"}</div><h1>O que você precisa<br/><em>resolver hoje?</em></h1></div><div className="location"><MapPin size={17}/><span>São Paulo, SP</span><ChevronLeft size={15} className="rotate"/></div></header><div className="search-line"><div className="search-box"><Search size={20}/><input data-testid="service-search-input" value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === "Enter" && search("", query)} placeholder="Busque por serviço ou profissional"/>{query && <button className="search-clear" data-testid="search-clear-button" onClick={() => { setQuery(""); search("", ""); }}><X size={16}/></button>}<button data-testid="service-search-button" onClick={() => search("", query)}><ArrowRight size={19}/></button></div><button className="need-btn" data-testid="post-need-button" onClick={onRequest}>Descrever uma necessidade <Plus size={17}/></button></div><section className="category-section"><div className="section-heading"><div><span className="section-kicker">EXPLORE POR CATEGORIA</span><h2>Feito para a sua rotina</h2></div><button data-testid="all-categories-button" onClick={() => search("")}>ver todas <ArrowRight size={15}/></button></div><div className="category-grid">{services.map(s => <button className={`category-tile ${category === s.name ? "selected" : ""}`} data-testid={`category-${s.id}-button`} key={s.id} onClick={() => search(s.name)}><span className={`tile-icon ${s.tone}`}>{s.icon}</span><span className="tile-text"><b>{s.name}</b><small>{s.description}</small></span><ArrowRight size={15}/></button>)}</div></section><section className="providers-section"><div className="section-heading"><div><span className="section-kicker">{category ? `PROFISSIONAIS EM ${category.toUpperCase()}` : "BONS PROFISSIONAIS, BOAS HISTÓRIAS"}</span><h2>Recomendados para você</h2></div><button data-testid="see-providers-button" onClick={() => search(category)}>ver todos <ArrowRight size={15}/></button></div><div className="provider-grid">{providers.map((p, i) => <article className="provider-card" key={p.id} data-testid={`provider-card-${i}`}><div className={`provider-photo photo-${i % 3}`}><span>{p.initials}</span><button data-testid={`favorite-provider-${i}`} className={`heart-btn ${favIds.includes(p.id) ? "favorited" : ""}`} onClick={() => toggleFav(p.id)}><HeartHandshake size={17} fill={favIds.includes(p.id) ? "currentColor" : "none"}/></button></div><div className="provider-info"><div className="provider-name"><h3 data-testid={`provider-name-${i}`}>{p.name}</h3><ShieldCheck size={16}/></div><p data-testid={`provider-category-${i}`}>{p.category}</p><div className="rating" data-testid={`provider-rating-${i}`}><Star size={15} fill="currentColor"/><b>{p.rating}</b><span>({p.reviews} avaliações)</span></div><div className="provider-bottom"><strong data-testid={`provider-price-${i}`}>{p.price}</strong><button data-testid={`request-provider-${i}`} onClick={() => onProviderProfile(p.id)}>Ver perfil <ArrowRight size={15}/></button></div></div></article>)}</div></section></main>;
}

function AuthModal({mode, initialRole, close, onSwitch, onSuccess}) {
  const [role, setRole] = useState(initialRole || "client");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const isLogin = mode === "login";
  const submit = async (e) => { e.preventDefault(); setError(""); try { const url = isLogin ? "/auth/login" : "/auth/register"; const payload = isLogin ? {email, password} : {name, email, password, role}; const r = await axios.post(API + url, payload, {withCredentials: true}); onSuccess(r.data); } catch (err) { setError(formatError(err)); } };
  const googleLogin = () => { window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(window.location.origin)}`; };
  return <div className="modal-backdrop"><div className="auth-modal"><button className="modal-close" data-testid="auth-close-button" onClick={close}><X size={20}/></button><div className="auth-brand"><span className="brand-mark">P</span><span>Pro<span>Mão</span></span></div><span className="section-kicker">{isLogin ? "BEM-VINDO DE VOLTA" : "COMECE POR AQUI"}</span><h2>{isLogin ? "Entre na sua conta" : "Qual é o seu papel nessa rede?"}</h2>{!isLogin && <div className="role-toggle"><button type="button" className={role === "client" ? "active" : ""} data-testid="role-client-option" onClick={() => setRole("client")}>Sou cliente<small>Encontro quem resolve</small></button><button type="button" className={role === "provider" ? "active" : ""} data-testid="role-provider-option" onClick={() => setRole("provider")}>Sou prestador<small>Ofereço meu trabalho</small></button></div>}<form onSubmit={submit} data-testid="auth-form">{!isLogin && <label>Seu nome<input data-testid="auth-name-input" value={name} onChange={e => setName(e.target.value)} required placeholder="Como podemos te chamar?"/></label>}<label>Seu e-mail<input data-testid="auth-email-input" type="email" value={email} onChange={e => setEmail(e.target.value)} required placeholder="voce@email.com"/></label><label>Senha<input data-testid="auth-password-input" type="password" value={password} onChange={e => setPassword(e.target.value)} required minLength="6" placeholder="mínimo de 6 caracteres"/></label>{error && <div className="form-error" data-testid="auth-error-message">{error}</div>}<button className="primary-btn wide" data-testid="auth-submit-button">{isLogin ? "Entrar na ProMão" : "Criar minha conta"}<ArrowRight size={17}/></button></form><div className="or"><span/> ou <span/></div><button className="google-btn" data-testid="google-link-button" onClick={googleLogin}>G <span>Continuar com Google</span></button><p className="auth-switch">{isLogin ? "Ainda não tem conta?" : "Já tem uma conta?"} <button data-testid="auth-switch-button" onClick={onSwitch}>{isLogin ? "Criar agora" : "Entrar"}</button></p></div></div>;
}

function RequestForm({onBack, onDone}) {
  const [form, setForm] = useState({service:"", category:"", description:"", budget:""});
  const [error, setError] = useState("");
  const submit = async (e) => { e.preventDefault(); try { await axios.post(`${API}/requests`, form, {withCredentials: true}); onDone("Pedido publicado! Em breve você receberá propostas de profissionais."); } catch (err) { setError(formatError(err)); } };
  return <main className="form-page"><button className="back-btn" data-testid="request-back-button" onClick={onBack}><ChevronLeft size={18}/> voltar</button><span className="section-kicker">NOVA SOLICITAÇÃO</span><h1>Conte o que você<br/><em>precisa resolver.</em></h1><form className="request-form" onSubmit={submit} data-testid="request-form"><label>Que serviço você procura?<input data-testid="request-service-input" required value={form.service} onChange={e => setForm({...form, service:e.target.value})} placeholder="Ex.: instalar uma luminária"/></label><label>Categoria<select data-testid="request-category-select" required value={form.category} onChange={e => setForm({...form, category:e.target.value})}><option value="">Selecione</option><option>Limpeza</option><option>Elétrica</option><option>Hidráulica</option><option>Pintura</option><option>Jardinagem</option><option>Montagem</option></select></label><label>Explique um pouco mais<textarea data-testid="request-description-input" required value={form.description} onChange={e => setForm({...form, description:e.target.value})} placeholder="Detalhes ajudam o profissional a preparar uma proposta melhor"/></label><label>Você tem um orçamento em mente? <span className="optional">opcional</span><input data-testid="request-budget-input" value={form.budget} onChange={e => setForm({...form, budget:e.target.value})} placeholder="Ex.: até R$ 250"/></label>{error && <div className="form-error" data-testid="request-error-message">{error}</div>}<button className="primary-btn" data-testid="request-submit-button">Publicar pedido <ArrowRight size={17}/></button></form></main>;
}

function Profile({user, logout, onBack, onMessage, onUserUpdate, onEditProfile, onAdmin}) {
  const initialMode = canUse(user, "client") ? "client" : "provider";
  const [mode, setMode] = useState(initialMode);
  const [activating, setActivating] = useState(false);
  useEffect(() => {
    if (mode === "provider" && !canUse(user, "provider")) setMode(canUse(user, "client") ? "client" : "provider");
    if (mode === "client" && !canUse(user, "client")) setMode("provider");
  }, [user, mode]);
  const activateProvider = async () => {
    setActivating(true);
    try {
      const r = await axios.post(`${API}/users/enable-provider`, {}, {withCredentials:true});
      onUserUpdate(r.data);
      setMode("provider");
      onMessage("Perfil de prestador ativado! Agora você pode criar catálogo e receber indicações.");
    } catch (err) {
      onMessage(formatError(err));
    } finally {
      setActivating(false);
    }
  };
  const activateAdmin = async () => {
    try {
      const r = await axios.post(`${API}/users/enable-admin`, {}, {withCredentials:true});
      onUserUpdate(r.data);
      onMessage("Acesso administrativo ativado.");
    } catch (err) {
      onMessage(formatError(err));
    }
  };
  const roles = userRoles(user);
  const switcher = <div className="role-mode-bar" data-testid="role-mode-switcher"><span>{roles.includes("provider") ? "Sua conta tem dois modos" : "Conta de cliente"}</span><div><button className={mode === "client" ? "active" : ""} data-testid="mode-client-button" onClick={() => setMode("client")} disabled={!canUse(user, "client")}>Cliente</button><button className={mode === "provider" ? "active" : ""} data-testid="mode-provider-button" onClick={() => canUse(user, "provider") ? setMode("provider") : activateProvider()} disabled={activating}>{canUse(user, "provider") ? "Prestador" : "Ativar prestador"}</button></div></div>;
  return <>{switcher}<div className="profile-action-bar"><button className="outline-btn small" data-testid="edit-profile-button" onClick={onEditProfile}>Editar perfil</button>{canUse(user, "admin") ? <button className="outline-btn small" data-testid="go-admin-button" onClick={onAdmin}>Painel admin</button> : <button className="outline-btn small" data-testid="activate-admin-button" onClick={activateAdmin}>Ativar admin</button>}</div>{mode === "provider" && canUse(user, "provider") ? <ProviderWorkspace user={user} onBack={onBack} onMessage={onMessage} logout={logout}/> : <ClientWorkspace user={user} onBack={onBack} onMessage={onMessage} logout={logout} canActivateProvider={!canUse(user, "provider")} onActivateProvider={activateProvider} activatingProvider={activating}/>}</>;
}

function ProviderWorkspace({user, onBack, onMessage, logout}) {
  const [catalog, setCatalog] = useState([]);
  const [requests, setRequests] = useState([]);
  const [myOffers, setMyOffers] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [form, setForm] = useState({name:"", category:"", price:"", includes_product:false, product_requirements:""});
  const [photo, setPhoto] = useState("");
  const [caption, setCaption] = useState("");
  const [clientEmail, setClientEmail] = useState("");
  const [chatFor, setChatFor] = useState(null);
  const profileLink = `${window.location.origin}/prestador/${user?.id}`;
  const load = () => { axios.get(`${API}/provider/catalog`, {withCredentials:true}).then(r => setCatalog(r.data)); axios.get(`${API}/requests`, {params:{mode:"provider"}, withCredentials:true}).then(r => setRequests(r.data)); axios.get(`${API}/offers/mine`, {withCredentials:true}).then(r => setMyOffers(r.data)).catch(() => {}); axios.get(`${API}/recommendations/mine`, {params:{mode:"provider"}, withCredentials:true}).then(r => setRecommendations(r.data)).catch(() => {}); };
  useEffect(load, []);
  const add = async (e) => { e.preventDefault(); const r = await axios.post(`${API}/provider/catalog`, {...form, price:Number(form.price)}, {withCredentials:true}); setCatalog([...catalog, r.data]); setForm({name:"", category:"", price:"", includes_product:false, product_requirements:""}); };
  const upload = async (e) => { const file = e.target.files?.[0]; if (!file) return; const reader = new FileReader(); reader.onload = async () => { const r = await axios.post(`${API}/portfolio`, {image_data:reader.result, caption, client_email:clientEmail || null}, {withCredentials:true}); setPhoto(r.data.image_data); onMessage("Foto salva e aguardando autorização do cliente."); }; reader.readAsDataURL(file); };
  const offer = async (id) => { const price = window.prompt("Preço da proposta (R$)"); if (!price) return; const eta = window.prompt("Prazo estimado (ex.: 2 dias)") || "A combinar"; try { await axios.post(`${API}/requests/${id}/offers`, {price:Number(price), eta, conditions:"Valor final confirmado após visita técnica."}, {withCredentials:true}); onMessage("Proposta enviada ao cliente."); load(); } catch (err) { onMessage(formatError(err)); } };
  const complete = async (offerId) => { try { const r = await axios.post(`${API}/offers/${offerId}/complete`, {}, {withCredentials:true}); onMessage(r.data.completed ? "Serviço concluído!" : "Sua confirmação foi registrada. Aguardando o cliente."); load(); } catch (err) { onMessage(formatError(err)); } };
  const copyProfile = async () => { await navigator.clipboard.writeText(profileLink).catch(() => {}); onMessage("Link do perfil copiado."); };
  return <main className="profile-page"><button className="back-btn" data-testid="provider-back-button" onClick={onBack}><ChevronLeft size={18}/> voltar</button><span className="section-kicker">PAINEL DO PRESTADOR</span><div className="profile-header"><span className="profile-avatar">{user?.name?.[0]}</span><div><h1>{user?.name}</h1><p>Seu trabalho, com clareza e confiança.</p></div></div><div className="provider-share-band" data-testid="provider-public-profile-card"><div><span className="section-kicker">PERFIL PÚBLICO</span><h2>Compartilhe seu cartão de confiança</h2><p data-testid="provider-public-profile-link">{profileLink}</p></div><button className="primary-btn" data-testid="copy-public-profile-button" onClick={copyProfile}><Copy size={16}/> Copiar link</button></div><div className="workspace-grid"><section><h2>Meu catálogo</h2><form className="catalog-form" onSubmit={add} data-testid="catalog-form"><input data-testid="catalog-service-input" required value={form.name} onChange={e => setForm({...form, name:e.target.value})} placeholder="Nome da tarefa"/><select data-testid="catalog-category-select" required value={form.category} onChange={e => setForm({...form, category:e.target.value})}><option value="">Categoria</option><option>Limpeza</option><option>Elétrica</option><option>Hidráulica</option><option>Pintura</option><option>Jardinagem</option><option>Montagem</option><option>Outras</option></select><input data-testid="catalog-price-input" required type="number" min="0" value={form.price} onChange={e => setForm({...form, price:e.target.value})} placeholder="Preço em R$"/><label className="check-row"><input data-testid="catalog-product-checkbox" type="checkbox" checked={form.includes_product} onChange={e => setForm({...form, includes_product:e.target.checked})}/> Incluo o produto</label>{form.includes_product && <input data-testid="catalog-requirements-input" value={form.product_requirements} onChange={e => setForm({...form, product_requirements:e.target.value})} placeholder="Exigências do cliente para o produto"/>}<button className="primary-btn" data-testid="catalog-submit-button">Adicionar serviço <Plus size={16}/></button></form><div className="catalog-list">{catalog.map((item, i) => <div className="catalog-item" key={item.id || i} data-testid={`catalog-item-${i}`}><span><b>{item.name}</b><small>{item.category} · {item.includes_product ? "com produto" : "mão de obra"}</small></span><strong>R$ {Number(item.price).toFixed(2).replace(".", ",")}</strong></div>)}</div><h2 className="portfolio-title">Minhas propostas</h2>{myOffers.length ? <div className="request-list">{myOffers.map((o, i) => <div className={`offer-card offer-${o.status}`} key={o.id} data-testid={`my-offer-${i}`}><div className="offer-head"><b>{o.request?.service || "Serviço"}</b><span className={`chip chip-${o.status}`} data-testid={`my-offer-status-${i}`}>{statusLabel(o.status)}</span></div><div className="offer-meta"><span>R$ {Number(o.price).toFixed(2).replace(".", ",")}</span><span>Prazo: {o.eta}</span></div><p className="offer-cond">{o.request?.description}</p>{(o.status === "accepted" || o.status === "client_completed") && !o.provider_completed && <button className="primary-btn small" data-testid={`provider-complete-${i}`} onClick={() => complete(o.id)}>Marcar como concluído <ArrowRight size={14}/></button>}{o.status === "provider_completed" && <div className="offer-note">Aguardando confirmação do cliente.</div>}{o.status === "completed" && <div className="offer-note">Atendimento finalizado.</div>}
{["accepted","client_completed","provider_completed","completed"].includes(o.status) && <button className="outline-btn small chat-trigger" data-testid={`provider-chat-${i}`} onClick={() => setChatFor(o)}><MessageCircle size={14}/> Conversar com o cliente</button>}</div>)}</div> : <div className="empty-state" data-testid="empty-my-offers">Você ainda não enviou propostas.</div>}</section><section><h2>Pedidos abertos</h2>{requests.length ? <div className="request-list">{requests.map((item, i) => <div className="request-item" key={item.id || i} data-testid={`open-request-${i}`}><b>{item.service}</b><p>{item.description}</p><button className="outline-btn" data-testid={`send-offer-${i}`} onClick={() => offer(item.id)}>Enviar proposta <ArrowRight size={15}/></button></div>)}</div> : <div className="empty-state" data-testid="empty-requests-message">Quando um cliente publicar uma necessidade, ela aparecerá aqui.</div>}<h2 className="portfolio-title">Indicações recebidas</h2>{recommendations.length ? <div className="recommendation-list">{recommendations.map((r, i) => <div className="recommendation-item" key={`${r.created_at}-${i}`} data-testid={`received-recommendation-${i}`}><b>{r.recommender_name}</b><p>indicou você para {r.recipient_name}</p>{r.message && <small>{r.message}</small>}</div>)}</div> : <div className="empty-state" data-testid="empty-recommendations-message">Suas indicações aparecerão aqui.</div>}<h2 className="portfolio-title">Portfólio autorizado</h2><label className="upload-box" data-testid="portfolio-upload-label">+ Adicionar foto<input data-testid="portfolio-file-input" type="file" accept="image/*" onChange={upload}/></label><input className="portfolio-caption" data-testid="portfolio-caption-input" value={caption} onChange={e => setCaption(e.target.value)} placeholder="Legenda do trabalho"/><input className="portfolio-caption" data-testid="portfolio-client-email-input" value={clientEmail} onChange={e => setClientEmail(e.target.value)} placeholder="E-mail do cliente para autorizar"/>{photo && <div className="pending-photo" data-testid="portfolio-pending-preview"><img src={photo} alt="Prévia do portfólio"/><span>Aguardando autorização</span></div>}</section></div><button className="list-action" data-testid="provider-google-link-button" onClick={() => onMessage("Sua conta já pode ser vinculada ao Google pelo botão de login.")}><span>G</span>Vincular conta Google <ArrowRight size={16}/></button><button className="list-action" data-testid="provider-logout-button" onClick={logout}><LogOut size={16}/> Sair da conta <ArrowRight size={16}/></button>
{chatFor && <ChatModal offerId={chatFor.id} title="Conversa com o cliente" user={user} close={() => setChatFor(null)} />}</main>;
}

function statusLabel(s) { return {open:"Aguardando propostas", in_progress:"Em andamento", completed:"Concluído", pending:"Aguardando sua escolha", accepted:"Aceita — em andamento", not_selected:"Não selecionada", client_completed:"Cliente concluiu", provider_completed:"Prestador concluiu"}[s] || s; }

function ClientWorkspace({user, onBack, onMessage, logout, canActivateProvider, onActivateProvider, activatingProvider}) {
  const [pending, setPending] = useState([]);
  const [requests, setRequests] = useState([]);
  const [offersMap, setOffersMap] = useState({});
  const [expanded, setExpanded] = useState(null);
  const [reviewFor, setReviewFor] = useState(null);
  const [chatFor, setChatFor] = useState(null);
  const load = () => { axios.get(`${API}/portfolio/pending`, {withCredentials:true}).then(r => setPending(r.data)).catch(() => {}); axios.get(`${API}/requests`, {params:{mode:"client"}, withCredentials:true}).then(r => setRequests(r.data)).catch(() => {}); };
  useEffect(load, []);
  const openRequest = async (req) => { if (expanded === req.id) { setExpanded(null); return; } setExpanded(req.id); const r = await axios.get(`${API}/requests/${req.id}/offers`, {withCredentials:true}); setOffersMap(prev => ({...prev, [req.id]: r.data})); };
  const refreshOffers = async (reqId) => { const r = await axios.get(`${API}/requests/${reqId}/offers`, {withCredentials:true}); setOffersMap(prev => ({...prev, [reqId]: r.data})); };
  const accept = async (offerId, reqId) => { try { await axios.post(`${API}/offers/${offerId}/accept`, {}, {withCredentials:true}); onMessage("Proposta aceita! O prestador foi notificado."); load(); refreshOffers(reqId); } catch (err) { onMessage(formatError(err)); } };
  const complete = async (offerId, reqId) => { try { const r = await axios.post(`${API}/offers/${offerId}/complete`, {}, {withCredentials:true}); onMessage(r.data.completed ? "Serviço concluído! Você já pode avaliar." : "Sua confirmação foi registrada. Aguardando o prestador."); load(); refreshOffers(reqId); } catch (err) { onMessage(formatError(err)); } };
  const authorize = async (id) => { await axios.post(`${API}/portfolio/${id}/authorize`, {}, {withCredentials:true}); setPending(pending.filter(p => p.id !== id)); onMessage("Autorização registrada."); };
  return <main className="profile-page"><button className="back-btn" data-testid="client-back-button" onClick={onBack}><ChevronLeft size={18}/> voltar</button><span className="section-kicker">MEU ESPAÇO</span><div className="profile-header"><span className="profile-avatar">{user?.name?.[0]}</span><div><h1>{user?.name}</h1><p>Cliente da comunidade · {user?.email}</p></div></div><div className="profile-columns"><section><h2>Meus pedidos</h2>{requests.length ? <div className="request-list">{requests.map((req, i) => <div className="request-item" key={req.id} data-testid={`client-request-${i}`}><div className="req-head"><b>{req.service}</b><span className={`chip chip-${req.status}`} data-testid={`client-request-status-${i}`}>{statusLabel(req.status)}</span></div><p>{req.description}</p><button className="outline-btn small" data-testid={`toggle-offers-${i}`} onClick={() => openRequest(req)}>{expanded === req.id ? "Ocultar propostas" : "Ver propostas"} <ArrowRight size={13}/></button>{expanded === req.id && <div className="offers-inline">{(offersMap[req.id] || []).length === 0 && <div className="empty-state" data-testid={`empty-offers-${i}`}>Ainda não há propostas para este pedido.</div>}{(offersMap[req.id] || []).map((o, j) => <div className={`offer-card offer-${o.status}`} key={o.id} data-testid={`offer-card-${i}-${j}`}><div className="offer-head"><b>{o.provider_name}</b><span className={`chip chip-${o.status}`} data-testid={`offer-status-${i}-${j}`}>{statusLabel(o.status)}</span></div><div className="offer-meta"><span>R$ {Number(o.price).toFixed(2).replace(".", ",")}</span><span>Prazo: {o.eta}</span></div><p className="offer-cond">{o.conditions}</p>{o.status === "pending" && req.status === "open" && <button className="primary-btn small" data-testid={`accept-offer-${i}-${j}`} onClick={() => accept(o.id, req.id)}>Aceitar proposta <ShieldCheck size={14}/></button>}{(o.status === "accepted" || o.status === "provider_completed") && !o.client_completed && <button className="primary-btn small" data-testid={`client-complete-${i}-${j}`} onClick={() => complete(o.id, req.id)}>Marcar como concluído <ArrowRight size={14}/></button>}{o.status === "client_completed" && <div className="offer-note">Aguardando confirmação do prestador.</div>}{o.status === "completed" && !o.reviewed && <button className="outline-btn small" data-testid={`review-offer-${i}-${j}`} onClick={() => setReviewFor(o)}>Avaliar atendimento <Star size={14}/></button>}{o.status === "completed" && o.reviewed && <div className="offer-note" data-testid={`reviewed-offer-${i}-${j}`}>Atendimento avaliado.</div>}
{["accepted","client_completed","provider_completed","completed"].includes(o.status) && <button className="outline-btn small chat-trigger" data-testid={`chat-offer-${i}-${j}`} onClick={() => setChatFor(o)}><MessageCircle size={14}/> Conversar</button>}</div>)}</div>}</div>)}</div> : <div className="empty-state" data-testid="empty-client-requests">Você ainda não publicou pedidos.</div>}</section><section><h2>Autorizações de fotos</h2>{pending.length ? pending.map((item, i) => <div className="pending-authorization" key={item.id} data-testid={`pending-photo-${i}`}><img src={item.image_data} alt="Trabalho para autorizar"/><div><b>{item.caption || "Foto de atendimento"}</b><p>Permitir que este trabalho apareça no portfólio?</p><button className="primary-btn" data-testid={`authorize-photo-${i}`} onClick={() => authorize(item.id)}>Autorizar divulgação <ShieldCheck size={15}/></button></div></div>) : <div className="empty-state" data-testid="empty-authorizations-message">Nenhuma foto aguarda sua autorização.</div>}{canActivateProvider && <div className="activate-provider-card" data-testid="activate-provider-card"><span className="section-kicker">TAMBÉM PRESTA SERVIÇOS?</span><h2>Ative seu perfil profissional</h2><p>Use a mesma conta para criar catálogo, receber propostas e compartilhar seu perfil público.</p><button className="primary-btn" data-testid="activate-provider-button" onClick={onActivateProvider} disabled={activatingProvider}>{activatingProvider ? "Ativando..." : "Ativar modo prestador"} <ArrowRight size={15}/></button></div>}<h2 className="portfolio-title">Conta</h2><button className="list-action" data-testid="profile-google-link-button" onClick={() => onMessage("Sua conta já pode ser vinculada ao Google pelo botão de login.")}><span>G</span>Vincular conta Google <ArrowRight size={16}/></button><button className="list-action" data-testid="profile-logout-button" onClick={logout}><LogOut size={16}/> Sair da conta <ArrowRight size={16}/></button></section></div>{reviewFor && <ReviewModal offer={reviewFor} close={() => setReviewFor(null)} onDone={() => { setReviewFor(null); onMessage("Obrigado! Seu depoimento foi publicado."); refreshOffers(reviewFor.request_id); }}/>}
{chatFor && <ChatModal offerId={chatFor.id} title={`Conversa com ${chatFor.provider_name}`} user={user} close={() => setChatFor(null)} />}</main>;
}

function ReviewModal({offer, close, onDone}) {
  const [rating, setRating] = useState(5);
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const submit = async (e) => { e.preventDefault(); setError(""); try { await axios.post(`${API}/reviews`, {offer_id:offer.id, rating, testimonial:text}, {withCredentials:true}); onDone(); } catch (err) { setError(formatError(err)); } };
  return <div className="modal-backdrop"><div className="auth-modal"><button className="modal-close" data-testid="review-close-button" onClick={close}><X size={20}/></button><span className="section-kicker">AVALIE O ATENDIMENTO</span><h2>Como foi o serviço<br/><em>de {offer.provider_name}?</em></h2><form onSubmit={submit} data-testid="review-form"><div className="stars-row" data-testid="review-stars">{[1,2,3,4,5].map(n => <button key={n} type="button" className={`star-btn ${n <= rating ? "on" : ""}`} data-testid={`star-${n}`} onClick={() => setRating(n)}><Star size={26} fill={n <= rating ? "currentColor" : "none"}/></button>)}</div><label>Seu depoimento<textarea data-testid="review-text-input" required minLength="10" value={text} onChange={e => setText(e.target.value)} placeholder="Compartilhe sua experiência com linguagem educada e respeitosa"/></label>{error && <div className="form-error" data-testid="review-error-message">{error}</div>}<button className="primary-btn wide" data-testid="review-submit-button">Publicar depoimento <ArrowRight size={17}/></button></form></div></div>;
}

function PublicProviderProfile({providerId, user, onBack, onLogin, onMessage, onSchedule}) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [form, setForm] = useState({recipient_name:"", recipient_email:"", message:""});
  useEffect(() => { setLoading(true); axios.get(`${API}/providers/public/${providerId}`).then(r => { setProfile(r.data); setError(""); }).catch(err => setError(formatError(err))).finally(() => setLoading(false)); }, [providerId]);
  const shareLink = profile?.provider?.share_url || window.location.href;
  const copyLink = async () => { await navigator.clipboard.writeText(shareLink).catch(() => {}); onMessage("Link do perfil copiado."); };
  const recommend = async (e) => { e.preventDefault(); try { await axios.post(`${API}/recommendations`, {...form, provider_id: providerId}, {withCredentials:true}); setForm({recipient_name:"", recipient_email:"", message:""}); onMessage("Indicação enviada! Se o e-mail estiver configurado, seu amigo receberá a mensagem."); const r = await axios.get(`${API}/providers/public/${providerId}`); setProfile(r.data); } catch (err) { onMessage(formatError(err)); } };
  if (loading) return <main className="public-profile" data-testid="public-profile-loading"><div className="empty-state">Carregando perfil público...</div></main>;
  if (error) return <main className="public-profile" data-testid="public-profile-error"><button className="back-btn" data-testid="public-profile-back-button" onClick={onBack}><ChevronLeft size={18}/> voltar</button><div className="empty-state">{error}</div></main>;
  const p = profile.provider;
  const isOwnProfile = user?.id === p.id;
  return <main className="public-profile" data-testid="public-profile-page"><button className="back-btn" data-testid="public-profile-back-button" onClick={onBack}><ChevronLeft size={18}/> voltar</button><section className="public-hero"><div className="public-avatar" data-testid="public-provider-initials">{p.initials}</div><div className="public-main"><span className="section-kicker">PERFIL PÚBLICO</span><h1 data-testid="public-provider-name">{p.name}</h1><p data-testid="public-provider-category">{p.category}</p><div className="public-stats"><span data-testid="public-rating-summary"><Star size={16} fill="currentColor"/> {profile.rating_average || "Novo"} · {profile.reviews_total} avaliações</span><span data-testid="public-recommendations-summary"><HeartHandshake size={16}/> {profile.recommendations_total} indicações</span><span data-testid="public-completed-summary"><ShieldCheck size={16}/> {profile.completed_services} concluídos</span></div></div><div className="public-actions"><button className="primary-btn" data-testid="public-profile-copy-button" onClick={copyLink}><Copy size={16}/> Copiar perfil</button><a className="outline-btn" data-testid="public-profile-share-whatsapp" href={`https://wa.me/?text=${encodeURIComponent(`Conheça ${p.name} na ProMão: ${shareLink}`)}`} target="_blank" rel="noreferrer"><Share2 size={16}/> Compartilhar</a>{user && !isOwnProfile && <button className="primary-btn" data-testid="public-profile-schedule-button" onClick={() => onSchedule({id: p.id, name: p.name})}><Calendar size={16}/> Agendar</button>}</div></section><div className="public-grid"><section><h2>Serviços e preços</h2>{profile.catalog.length ? <div className="catalog-list public-list">{profile.catalog.map((item, i) => <div className="catalog-item" key={`${item.name}-${i}`} data-testid={`public-catalog-item-${i}`}><span><b>{item.name}</b><small>{item.category} · {item.includes_product ? "com produto" : "mão de obra"}</small></span><strong>R$ {Number(item.price).toFixed(2).replace(".", ",")}</strong></div>)}</div> : <div className="empty-state" data-testid="public-empty-catalog">Este prestador ainda está montando o catálogo.</div>}<h2 className="portfolio-title">Portfólio autorizado</h2>{profile.portfolio.length ? <div className="public-portfolio-grid">{profile.portfolio.map((item, i) => <figure key={`${item.created_at}-${i}`} data-testid={`public-portfolio-item-${i}`}><img src={item.image_data} alt={item.caption || "Trabalho autorizado"}/><figcaption>{item.caption || "Trabalho autorizado"}</figcaption></figure>)}</div> : <div className="empty-state" data-testid="public-empty-portfolio">As fotos autorizadas aparecerão aqui.</div>}</section><section><h2>Indique para alguém</h2>{isOwnProfile && <div className="empty-state" data-testid="own-profile-note">Seu perfil está aberto para compartilhamento com clientes e outros profissionais.</div>}{!user && <div className="recommend-card" data-testid="recommend-login-card"><Mail size={22}/><p>Entre para indicar este profissional para amigos, clientes ou outros prestadores.</p><button className="primary-btn" data-testid="recommend-login-button" onClick={onLogin}>Entrar para indicar <ArrowRight size={15}/></button></div>}{user && !isOwnProfile && <form className="recommend-form" data-testid="recommendation-form" onSubmit={recommend}><label>Nome de quem vai receber<input data-testid="recommendation-name-input" required value={form.recipient_name} onChange={e => setForm({...form, recipient_name:e.target.value})} placeholder="Nome da pessoa"/></label><label>E-mail de destino<input data-testid="recommendation-email-input" type="email" required value={form.recipient_email} onChange={e => setForm({...form, recipient_email:e.target.value})} placeholder="amigo@email.com"/></label><label>Mensagem <span className="optional">opcional</span><textarea data-testid="recommendation-message-input" value={form.message} onChange={e => setForm({...form, message:e.target.value})} placeholder="Por que você recomenda este profissional?"/></label><button className="primary-btn wide" data-testid="recommendation-submit-button">Enviar indicação <Mail size={16}/></button></form>}<h2 className="portfolio-title">Voz da comunidade</h2>{profile.recommendations.length ? <div className="recommendation-list">{profile.recommendations.map((r, i) => <div className="recommendation-item" key={`${r.created_at}-${i}`} data-testid={`public-recommendation-${i}`}><b>{r.recommender_name}</b><p>indicou para {r.recipient_name}</p>{r.message && <small>{r.message}</small>}</div>)}</div> : <div className="empty-state" data-testid="public-empty-recommendations">Seja a primeira pessoa a indicar este trabalho.</div>}<h2 className="portfolio-title">Depoimentos</h2>{profile.reviews.length ? <div className="review-list">{profile.reviews.map((r, i) => <div className="review-card" key={`${r.created_at}-${i}`} data-testid={`public-review-${i}`}><div><b>{r.client_name}</b><span><Star size={13} fill="currentColor"/> {r.rating}</span></div><p>{r.testimonial}</p></div>)}</div> : <div className="empty-state" data-testid="public-empty-reviews">As avaliações de serviços concluídos aparecerão aqui.</div>}<a className="list-action" data-testid="public-open-link" href={shareLink} target="_blank" rel="noreferrer"><ExternalLink size={16}/> Abrir em nova aba <ArrowRight size={16}/></a></section></div></main>;
}

function About({onBack}) {
  return <main className="about-page"><button className="back-btn" data-testid="about-back-button" onClick={onBack}><ChevronLeft size={18}/> voltar</button><span className="section-kicker">COMO FUNCIONA</span><h1>Confiança que<br/><em>circula.</em></h1><div className="about-grid"><div><span className="step">01</span><h2>Escolha seu caminho</h2><p>Entre como cliente ou prestador. Seu espaço se adapta ao que você precisa fazer.</p></div><div><span className="step">02</span><h2>Combine com clareza</h2><p>Veja categorias, preços transparentes e profissionais recomendados pela comunidade.</p></div><div><span className="step">03</span><h2>Compartilhe a experiência</h2><p>Avalie, recomende e ajude a construir uma rede mais confiável para todos.</p></div></div></main>;
}