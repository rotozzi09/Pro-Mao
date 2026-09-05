from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from pathlib import Path
from html import escape
import asyncio, logging, os, bcrypt, jwt, resend
from bson import ObjectId
from bson.errors import InvalidId

def oid(value: str):
    try: return ObjectId(value)
    except (InvalidId, TypeError): raise HTTPException(400, "Identificador inválido")

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")
client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]
app = FastAPI()
api = APIRouter(prefix="/api")
JWT_ALGORITHM = "HS256"
logger = logging.getLogger("promao")

class RegisterInput(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str

class LoginInput(BaseModel):
    email: EmailStr
    password: str

class RequestInput(BaseModel):
    service: str
    category: str
    description: str
    budget: Optional[str] = None

class ReviewInput(BaseModel):
    offer_id: str
    rating: int
    testimonial: str

class RecommendationInput(BaseModel):
    provider_id: str
    recipient_name: str
    recipient_email: EmailStr
    message: Optional[str] = None

class CatalogInput(BaseModel):
    name: str
    category: str
    price: float
    includes_product: bool = False
    product_requirements: Optional[str] = None

class OfferInput(BaseModel):
    price: float
    eta: str
    conditions: str

class PortfolioInput(BaseModel):
    image_data: str
    caption: str = ""
    client_email: Optional[EmailStr] = None

class MessageInput(BaseModel):
    text: str

def role_list(user):
    roles = user.get("roles") or [user.get("role")]
    return [role for role in roles if role in ["client", "provider"]]

def has_role(user, role: str):
    return role in role_list(user)

def provider_lookup(provider_id: str):
    return {"_id":oid(provider_id),"$or":[{"role":"provider"},{"roles":"provider"}]}

def public_user(user):
    roles = role_list(user)
    primary_role = user.get("role") if user.get("role") in roles else (roles[0] if roles else "client")
    return {"id": str(user.get("_id", user.get("id"))), "name": user["name"], "email": user["email"], "role": primary_role, "roles": roles, "google_linked": user.get("google_linked", False)}

def initials(name: str):
    return "".join(x[0] for x in name.split()[:2]).upper() or "PM"

def public_profile_url(provider_id: str):
    base_url = os.environ.get("FRONTEND_URL")
    return f"{base_url.rstrip('/')}/prestador/{provider_id}" if base_url else ""

def token(user):
    secret = os.environ["JWT_SECRET"]
    return jwt.encode({"sub": str(user["_id"]), "exp": datetime.now(timezone.utc) + timedelta(hours=12)}, secret, algorithm=JWT_ALGORITHM)

async def current_user(request: Request):
    raw = request.cookies.get("access_token") or request.cookies.get("session_token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if not raw:
        raise HTTPException(401, "Faça login para continuar")
    try:
        session = await db.user_sessions.find_one({"session_token": raw})
        if session:
            expires = datetime.fromisoformat(session["expires_at"]) if isinstance(session["expires_at"], str) else session["expires_at"]
            if expires.tzinfo is None: expires = expires.replace(tzinfo=timezone.utc)
            if expires > datetime.now(timezone.utc):
                user = await db.users.find_one({"_id": oid(session["user_id"])})
                if user: return user
        payload = jwt.decode(raw, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"_id": oid(payload["sub"])})
        if not user: raise HTTPException(401, "Conta não encontrada")
        return user
    except Exception:
        raise HTTPException(401, "Sessão expirada")

async def record_and_send_email(recipient_email: str, subject: str, html_content: str, event: str, user_id: Optional[str] = None, metadata: Optional[dict] = None):
    now = datetime.now(timezone.utc).isoformat()
    record = {"recipient_email": recipient_email, "subject": subject, "event": event, "user_id": user_id, "metadata": metadata or {}, "created_at": now, "status": "queued"}
    created = await db.email_notifications.insert_one(record)
    api_key = os.environ.get("RESEND_API_KEY")
    sender = os.environ.get("SENDER_EMAIL")
    if not api_key or not sender:
        await db.email_notifications.update_one({"_id": created.inserted_id}, {"$set": {"status": "skipped", "reason": "missing_email_configuration", "updated_at": now}})
        return
    try:
        resend.api_key = api_key
        email = await asyncio.to_thread(resend.Emails.send, {"from": sender, "to": [recipient_email], "subject": subject, "html": html_content})
        await db.email_notifications.update_one({"_id": created.inserted_id}, {"$set": {"status": "sent", "provider_id": email.get("id"), "updated_at": datetime.now(timezone.utc).isoformat()}})
    except Exception as exc:
        logger.exception("Falha ao enviar e-mail")
        await db.email_notifications.update_one({"_id": created.inserted_id}, {"$set": {"status": "failed", "reason": str(exc), "updated_at": datetime.now(timezone.utc).isoformat()}})

def schedule_email(*args, **kwargs):
    asyncio.create_task(record_and_send_email(*args, **kwargs))

@api.get("/")
async def root(): return {"message": "ProMão API"}

@api.post("/auth/register")
async def register(data: RegisterInput, response: Response):
    if data.role not in ["client", "provider"]: raise HTTPException(400, "Perfil inválido")
    email = data.email.lower()
    if await db.users.find_one({"email": email}): raise HTTPException(409, "Este e-mail já está cadastrado")
    user = {"name": data.name.strip(), "email": email, "password_hash": bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode(), "role": data.role, "roles": [data.role], "google_linked": False, "created_at": datetime.now(timezone.utc).isoformat()}
    result = await db.users.insert_one(user); user["_id"] = result.inserted_id
    response.set_cookie("access_token", token(user), httponly=True, samesite="none", secure=True, max_age=43200)
    return public_user(user)

@api.post("/auth/login")
async def login(data: LoginInput, response: Response):
    user = await db.users.find_one({"email": data.email.lower()})
    if not user or not bcrypt.checkpw(data.password.encode(), user["password_hash"].encode()): raise HTTPException(401, "E-mail ou senha incorretos")
    response.set_cookie("access_token", token(user), httponly=True, samesite="none", secure=True, max_age=43200)
    return public_user(user)

@api.get("/auth/me")
async def me(user=Depends(current_user)): return public_user(user)

@api.post("/users/enable-provider")
async def enable_provider(user=Depends(current_user)):
    roles = sorted(set(role_list(user) + ["client", "provider"]))
    await db.users.update_one({"_id":user["_id"]},{"$set":{"roles":roles,"provider_enabled_at":datetime.now(timezone.utc).isoformat()}})
    updated = await db.users.find_one({"_id":user["_id"]})
    return public_user(updated)

@api.post("/auth/logout")
async def logout(request: Request, response: Response):
    raw = request.cookies.get("session_token")
    if raw: await db.user_sessions.delete_one({"session_token": raw})
    response.delete_cookie("access_token"); return {"ok": True}

@api.post("/auth/google/session")
async def google_session(data: dict, response: Response):
    session_id = data.get("session_id")
    if not session_id: raise HTTPException(400, "Sessão Google ausente")
    import requests
    result = requests.get("https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data", headers={"X-Session-ID": session_id}, timeout=15)
    if result.status_code != 200: raise HTTPException(401, "Não foi possível validar o Google")
    info = result.json(); user = await db.users.find_one({"email": info["email"].lower()})
    if not user:
        user = {"name":info.get("name", "Usuário Google"),"email":info["email"].lower(),"password_hash":"google-oauth","role":"client","roles":["client"],"google_linked":True,"created_at":datetime.now(timezone.utc).isoformat()}
        created = await db.users.insert_one(user); user["_id"] = created.inserted_id
    else:
        await db.users.update_one({"_id":user["_id"]},{"$set":{"google_linked":True,"name":info.get("name",user["name"])}})
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    await db.user_sessions.insert_one({"user_id":str(user["_id"]),"session_token":info["session_token"],"expires_at":expires.isoformat()})
    response.set_cookie("session_token", info["session_token"], httponly=True, samesite="none", secure=True, max_age=604800)
    return public_user(user)

SERVICES = [
    {"id":"cleaning", "name":"Limpeza", "icon":"✦", "tone":"mint", "description":"Casa leve, rotina tranquila"},
    {"id":"electric", "name":"Elétrica", "icon":"ϟ", "tone":"gold", "description":"Energia funcionando bem"},
    {"id":"plumbing", "name":"Hidráulica", "icon":"◒", "tone":"blue", "description":"Cuidado para cada detalhe"},
    {"id":"painting", "name":"Pintura", "icon":"◉", "tone":"rose", "description":"Novas cores para viver"},
    {"id":"gardening", "name":"Jardinagem", "icon":"⌁", "tone":"green", "description":"Mais vida nos seus espaços"},
    {"id":"assembly", "name":"Montagem", "icon":"⊞", "tone":"violet", "description":"Tudo no lugar certo"},
    {"id":"other", "name":"Outras", "icon":"+", "tone":"slate", "description":"Encontre o que precisa"},
]

@api.get("/services")
async def services(): return SERVICES

@api.get("/providers")
async def providers(category: Optional[str] = None, q: Optional[str] = None):
    query = {"$or":[{"role":"provider"},{"roles":"provider"}]}
    if category and category != "Outras": query["category"] = category
    if q: query["$or"] = [{"name":{"$regex":q,"$options":"i"}},{"category":{"$regex":q,"$options":"i"}}]
    users = await db.users.find(query, {"_id":1,"name":1,"category":1,"services":1}).to_list(12)
    if not users:
        demo = [{"id":"demo-1","name":"Marina Alves","category":"Limpeza e organização","rating":4.9,"reviews":32,"price":"a partir de R$ 120","initials":"MA"},{"id":"demo-2","name":"Rafael Costa","category":"Elétrica residencial","rating":4.8,"reviews":18,"price":"a partir de R$ 90","initials":"RC"},{"id":"demo-3","name":"Júlia Martins","category":"Pintura e reparos","rating":5.0,"reviews":27,"price":"a partir de R$ 150","initials":"JM"}]
        if category: demo = [p for p in demo if category.lower() in p["category"].lower()]
        if q: demo = [p for p in demo if q.lower() in (p["name"] + p["category"]).lower()]
        return demo
    result = []
    for u in users:
        provider_id = str(u["_id"])
        first_catalog = await db.catalog.find_one({"provider_id": provider_id}, {"_id": 0})
        review_docs = await db.reviews.find({"provider_id": provider_id}, {"_id": 0, "rating": 1}).to_list(100)
        total = len(review_docs)
        avg = round(sum(r["rating"] for r in review_docs) / total, 1) if total else 5
        rec_count = await db.recommendations.count_documents({"provider_id": provider_id})
        result.append({"id":provider_id,"name":u["name"],"category":first_catalog.get("category") if first_catalog else u.get("category","Serviços gerais"),"rating":avg,"reviews":total,"recommendations":rec_count,"price":f"a partir de R$ {first_catalog['price']:.0f}" if first_catalog else "a combinar","initials":initials(u["name"])})
    return result

@api.post("/requests")
async def create_request(data: RequestInput, user=Depends(current_user)):
    item = data.model_dump(); item.update({"client_id": str(user["_id"]), "created_at": datetime.now(timezone.utc).isoformat(), "status":"open"})
    result = await db.requests.insert_one(item); item["id"] = str(result.inserted_id); item.pop("_id", None); return item

@api.get("/requests")
async def list_requests(mode: Optional[str] = None, user=Depends(current_user)):
    effective_mode = mode if mode in ["client", "provider"] else user.get("role")
    if effective_mode == "provider":
        if not has_role(user, "provider"): raise HTTPException(403, "Ative seu perfil de prestador para ver pedidos abertos")
        query = {"status":"open"}
    else:
        if not has_role(user, "client"): raise HTTPException(403, "Apenas clientes veem seus pedidos")
        query = {"client_id":str(user["_id"])}
    items = await db.requests.find(query).sort("created_at", -1).to_list(50)
    if effective_mode == "provider":
        offered = await db.offers.find({"provider_id":str(user["_id"])}, {"_id":0, "request_id":1}).to_list(200)
        offered_ids = {item.get("request_id") for item in offered}
        items = [item for item in items if str(item.get("_id")) not in offered_ids and item.get("client_id") != str(user["_id"])]
    for item in items: item["id"] = str(item.pop("_id"))
    return items

@api.post("/requests/{request_id}/offers")
async def create_offer(request_id: str, data: OfferInput, user=Depends(current_user)):
    if not has_role(user, "provider"): raise HTTPException(403, "Ative seu perfil de prestador para enviar propostas")
    req = await db.requests.find_one({"_id":oid(request_id)})
    if not req: raise HTTPException(404, "Pedido não encontrado")
    if req.get("client_id") == str(user["_id"]): raise HTTPException(400, "Você não pode enviar proposta para o próprio pedido")
    if req.get("status") != "open": raise HTTPException(400, "Este pedido não está mais aceitando propostas")
    existing = await db.offers.find_one({"request_id":request_id,"provider_id":str(user["_id"])}, {"_id": 1})
    if existing: raise HTTPException(409, "Você já enviou uma proposta para este pedido")
    offer = data.model_dump(); offer.update({"request_id":request_id,"provider_id":str(user["_id"]),"provider_name":user["name"],"status":"pending","client_completed":False,"provider_completed":False,"created_at":datetime.now(timezone.utc).isoformat()})
    result = await db.offers.insert_one(offer); offer["id"] = str(result.inserted_id); offer.pop("_id", None)
    client_user = await db.users.find_one({"_id":oid(req["client_id"])}, {"_id":0,"email":1,"name":1})
    if client_user:
        schedule_email(client_user["email"], "Você recebeu uma proposta na ProMão", f"<p>Olá, {escape(client_user['name'])}.</p><p><strong>{escape(user['name'])}</strong> enviou uma proposta para <strong>{escape(req.get('service','seu pedido'))}</strong>.</p>", "offer_created", req["client_id"], {"offer_id": offer["id"], "request_id": request_id})
    return offer

@api.get("/requests/{request_id}/offers")
async def list_offers(request_id: str, user=Depends(current_user)):
    req = await db.requests.find_one({"_id":oid(request_id)})
    if not req: raise HTTPException(404, "Pedido não encontrado")
    if req.get("client_id") == str(user["_id"]):
        items = await db.offers.find({"request_id":request_id}).sort("created_at", 1).to_list(50)
    elif has_role(user, "provider"):
        items = await db.offers.find({"request_id":request_id,"provider_id":str(user["_id"])}).to_list(50)
    else:
        raise HTTPException(403, "Você não faz parte deste pedido")
    for item in items:
        item["id"] = str(item.pop("_id"))
        item["reviewed"] = bool(await db.reviews.find_one({"offer_id": item["id"]}, {"_id": 1}))
    return items

@api.get("/offers/mine")
async def my_offers(user=Depends(current_user)):
    if not has_role(user, "provider"): raise HTTPException(403, "Ative seu perfil de prestador")
    offers = await db.offers.find({"provider_id":str(user["_id"])}).sort("created_at", -1).to_list(100)
    result = []
    for o in offers:
        o["id"] = str(o.pop("_id"))
        try:
            req = await db.requests.find_one({"_id":oid(o["request_id"])})
            if req: o["request"] = {"service":req.get("service"),"category":req.get("category"),"description":req.get("description"),"status":req.get("status")}
        except Exception: pass
        result.append(o)
    return result

@api.post("/offers/{offer_id}/accept")
async def accept_offer(offer_id: str, user=Depends(current_user)):
    if not has_role(user, "client"): raise HTTPException(403, "Apenas clientes aceitam propostas")
    offer = await db.offers.find_one({"_id":oid(offer_id)})
    if not offer: raise HTTPException(404, "Proposta não encontrada")
    req = await db.requests.find_one({"_id":oid(offer["request_id"])})
    if not req or req.get("client_id") != str(user["_id"]): raise HTTPException(403, "Este pedido não é seu")
    if req.get("status") != "open": raise HTTPException(400, "Este pedido já foi encaminhado")
    await db.offers.update_one({"_id":offer["_id"]},{"$set":{"status":"accepted","accepted_at":datetime.now(timezone.utc).isoformat()}})
    await db.offers.update_many({"request_id":offer["request_id"],"_id":{"$ne":offer["_id"]}},{"$set":{"status":"not_selected"}})
    await db.requests.update_one({"_id":req["_id"]},{"$set":{"status":"in_progress","accepted_offer_id":str(offer["_id"]),"accepted_provider_id":offer["provider_id"]}})
    provider = await db.users.find_one({"_id":oid(offer["provider_id"])}, {"_id":0,"email":1,"name":1})
    if provider:
        schedule_email(provider["email"], "Sua proposta foi aceita na ProMão", f"<p>Olá, {escape(provider['name'])}.</p><p>Sua proposta para <strong>{escape(req.get('service','um serviço'))}</strong> foi aceita. Combine os próximos passos com o cliente pela plataforma.</p>", "offer_accepted", offer["provider_id"], {"offer_id": str(offer["_id"]), "request_id": offer["request_id"]})
    return {"ok":True}

@api.post("/offers/{offer_id}/complete")
async def complete_offer(offer_id: str, user=Depends(current_user)):
    offer = await db.offers.find_one({"_id":oid(offer_id)})
    if not offer: raise HTTPException(404, "Proposta não encontrada")
    if offer.get("status") not in ["accepted","client_completed","provider_completed"]: raise HTTPException(400, "Proposta ainda não foi aceita")
    req = await db.requests.find_one({"_id":oid(offer["request_id"])})
    if not req: raise HTTPException(404, "Pedido não encontrado")
    field = None
    if has_role(user, "client") and req.get("client_id") == str(user["_id"]): field = "client_completed"
    elif has_role(user, "provider") and offer.get("provider_id") == str(user["_id"]): field = "provider_completed"
    else: raise HTTPException(403, "Você não faz parte desta contratação")
    updates = {field: True, f"{field}_at": datetime.now(timezone.utc).isoformat()}
    both = (field == "client_completed" and offer.get("provider_completed")) or (field == "provider_completed" and offer.get("client_completed"))
    if both:
        updates["status"] = "completed"; updates["completed_at"] = datetime.now(timezone.utc).isoformat()
        await db.requests.update_one({"_id":req["_id"]},{"$set":{"status":"completed"}})
    else:
        updates["status"] = field
    await db.offers.update_one({"_id":offer["_id"]},{"$set":updates})
    return {"ok":True, "completed": both}

async def chat_participants(offer_id: str, user):
    offer = await db.offers.find_one({"_id": oid(offer_id)})
    if not offer: raise HTTPException(404, "Conversa não encontrada")
    req = await db.requests.find_one({"_id": oid(offer["request_id"])})
    if not req: raise HTTPException(404, "Pedido não encontrado")
    if str(user["_id"]) != req.get("client_id") and str(user["_id"]) != offer.get("provider_id"):
        raise HTTPException(403, "Você não participa desta conversa")
    return offer, req

@api.get("/offers/{offer_id}/messages")
async def list_messages(offer_id: str, user=Depends(current_user)):
    offer, req = await chat_participants(offer_id, user)
    messages = await db.messages.find({"offer_id": offer_id}).sort("created_at", 1).to_list(200)
    for m in messages: m["id"] = str(m.pop("_id"))
    return messages

@api.post("/offers/{offer_id}/messages")
async def send_message(offer_id: str, data: MessageInput, user=Depends(current_user)):
    offer, req = await chat_participants(offer_id, user)
    text = data.text.strip()
    if not text: raise HTTPException(400, "Escreva uma mensagem")
    if len(text) > 1000: raise HTTPException(400, "A mensagem é muito longa")
    if not polite_check(text): raise HTTPException(400, "Por favor, use linguagem educada e respeitosa na conversa")
    if offer.get("status") in ("pending", "not_selected"): raise HTTPException(400, "A conversa abre após a proposta ser aceita")
    msg = {"offer_id": offer_id, "request_id": offer["request_id"], "sender_id": str(user["_id"]), "sender_name": user["name"], "text": text, "created_at": datetime.now(timezone.utc).isoformat()}
    result = await db.messages.insert_one(msg)
    msg["id"] = str(result.inserted_id); msg.pop("_id")
    return msg

@api.get("/provider/catalog")
async def provider_catalog(user=Depends(current_user)):
    items = await db.catalog.find({"provider_id":str(user["_id"])}).to_list(100)
    for item in items: item["id"] = str(item.pop("_id"))
    return items

@api.post("/provider/catalog")
async def add_catalog(data: CatalogInput, user=Depends(current_user)):
    if not has_role(user, "provider"): raise HTTPException(403, "Ative seu perfil de prestador para criar catálogo")
    item = data.model_dump(); item.update({"provider_id":str(user["_id"]),"created_at":datetime.now(timezone.utc).isoformat()})
    result = await db.catalog.insert_one(item); item["id"] = str(result.inserted_id); item.pop("_id", None); return item

@api.delete("/provider/catalog/{item_id}")
async def remove_catalog(item_id: str, user=Depends(current_user)):
    await db.catalog.delete_one({"_id":oid(item_id),"provider_id":str(user["_id"])})
    return {"ok":True}

@api.get("/portfolio")
async def portfolio(mode: Optional[str] = None, user=Depends(current_user)):
    query = {"provider_id":str(user["_id"])} if (mode == "provider" or user.get("role") == "provider") and has_role(user, "provider") else {"client_authorized":True}
    items = await db.portfolio.find(query).to_list(100)
    for item in items: item["id"] = str(item.pop("_id"))
    return items

@api.get("/portfolio/pending")
async def pending_portfolio(user=Depends(current_user)):
    if not has_role(user, "client"): raise HTTPException(403, "Apenas clientes autorizam fotos")
    items = await db.portfolio.find({"client_email":user["email"],"client_authorized":False}).to_list(100)
    for item in items: item["id"] = str(item.pop("_id"))
    return items

@api.post("/portfolio")
async def add_portfolio(data: PortfolioInput, user=Depends(current_user)):
    if not has_role(user, "provider"): raise HTTPException(403, "Ative seu perfil de prestador para publicar fotos")
    item = data.model_dump(); item.update({"provider_id":str(user["_id"]),"client_authorized":False,"created_at":datetime.now(timezone.utc).isoformat()})
    result = await db.portfolio.insert_one(item); item["id"] = str(result.inserted_id); item.pop("_id", None); return item

@api.post("/portfolio/{item_id}/authorize")
async def authorize_portfolio(item_id: str, user=Depends(current_user)):
    result = await db.portfolio.update_one({"_id":oid(item_id),"client_email":user["email"]},{"$set":{"client_authorized":True,"authorized_at":datetime.now(timezone.utc).isoformat()}})
    if not result.modified_count: raise HTTPException(403, "Esta foto não está vinculada a você")
    return {"ok":True}

RUDE_TERMS = ["idiota","imbecil","burro","otário","otario","lixo","merda","porra","cretino","estúpido","estupido","incompetente","ladrão","ladrao","desgraçad","desgracad"]

def polite_check(text: str):
    lower = text.lower()
    for term in RUDE_TERMS:
        if term in lower: return False
    return True

@api.get("/providers/public/{provider_id}")
async def public_provider_profile(provider_id: str):
    provider = await db.users.find_one(provider_lookup(provider_id), {"password_hash":0})
    if not provider: raise HTTPException(404, "Prestador não encontrado")
    catalog = await db.catalog.find({"provider_id":provider_id}, {"_id":0}).sort("created_at", -1).to_list(100)
    portfolio = await db.portfolio.find({"provider_id":provider_id,"client_authorized":True}, {"_id":0,"client_email":0}).sort("created_at", -1).to_list(24)
    reviews = await db.reviews.find({"provider_id":provider_id}, {"_id":0}).sort("created_at", -1).to_list(50)
    recommendations = await db.recommendations.find({"provider_id":provider_id}, {"_id":0,"recipient_email":0,"recommender_id":0}).sort("created_at", -1).to_list(12)
    recommendations_total = await db.recommendations.count_documents({"provider_id":provider_id})
    completed_services = await db.offers.count_documents({"provider_id":provider_id,"status":"completed"})
    total = len(reviews); avg = round(sum(i["rating"] for i in reviews)/total, 1) if total else 0
    primary_catalog = catalog[0] if catalog else {}
    return {
        "provider": {"id": str(provider["_id"]), "name": provider["name"], "role": provider.get("role", "provider"), "roles": role_list(provider), "initials": initials(provider["name"]), "category": primary_catalog.get("category", provider.get("category", "Serviços gerais")), "share_url": public_profile_url(provider_id)},
        "catalog": catalog,
        "portfolio": portfolio,
        "reviews": reviews,
        "rating_average": avg,
        "reviews_total": total,
        "recommendations": recommendations,
        "recommendations_total": recommendations_total,
        "completed_services": completed_services,
    }

@api.post("/recommendations")
async def create_recommendation(data: RecommendationInput, user=Depends(current_user)):
    provider = await db.users.find_one(provider_lookup(data.provider_id), {"password_hash":0})
    if not provider: raise HTTPException(404, "Prestador não encontrado")
    if str(provider["_id"]) == str(user["_id"]): raise HTTPException(400, "Você pode compartilhar seu perfil, mas a indicação precisa ser para outro profissional")
    clean_message = (data.message or "").strip()
    if clean_message and not polite_check(clean_message): raise HTTPException(400, "Por favor, use linguagem educada e respeitosa na indicação")
    item = {"provider_id":data.provider_id,"provider_name":provider["name"],"recommender_id":str(user["_id"]),"recommender_name":user["name"],"recommender_role":user.get("role", "client"),"recipient_name":data.recipient_name.strip(),"recipient_email":data.recipient_email.lower(),"message":clean_message,"created_at":datetime.now(timezone.utc).isoformat()}
    result = await db.recommendations.insert_one(item); item["id"] = str(result.inserted_id); item.pop("_id", None)
    link = public_profile_url(data.provider_id)
    message_block = f"<p>{escape(clean_message)}</p>" if clean_message else ""
    link_block = f"<p><a href='{escape(link)}'>Ver perfil público</a></p>" if link else ""
    html_content = f"<p>Olá, {escape(item['recipient_name'])}.</p><p><strong>{escape(user['name'])}</strong> indicou <strong>{escape(provider['name'])}</strong> na ProMão.</p>{message_block}{link_block}"
    schedule_email(item["recipient_email"], f"{user['name']} indicou um profissional na ProMão", html_content, "community_recommendation", str(user["_id"]), {"provider_id":data.provider_id,"recommendation_id":item["id"]})
    schedule_email(provider["email"], "Seu perfil foi indicado na ProMão", f"<p>Olá, {escape(provider['name'])}.</p><p><strong>{escape(user['name'])}</strong> recomendou seu trabalho para {escape(item['recipient_name'])}.</p>", "provider_recommended", data.provider_id, {"recommendation_id":item["id"]})
    return item

@api.get("/recommendations/mine")
async def my_recommendations(mode: Optional[str] = None, user=Depends(current_user)):
    query = {"provider_id":str(user["_id"])} if (mode == "provider" or user.get("role") == "provider") and has_role(user, "provider") else {"recommender_id":str(user["_id"])}
    items = await db.recommendations.find(query, {"_id":0}).sort("created_at", -1).to_list(100)
    return items

@api.get("/notifications/mine")
async def my_notifications(user=Depends(current_user)):
    items = await db.email_notifications.find({"user_id":str(user["_id"])}, {"_id":0}).sort("created_at", -1).to_list(30)
    return items

@api.post("/reviews")
async def review(data: ReviewInput, user=Depends(current_user)):
    if not has_role(user, "client"): raise HTTPException(403, "Apenas clientes avaliam")
    if data.rating < 1 or data.rating > 5: raise HTTPException(400, "Nota deve ser entre 1 e 5")
    if len(data.testimonial.strip()) < 10: raise HTTPException(400, "Escreva um depoimento com pelo menos 10 caracteres")
    if not polite_check(data.testimonial): raise HTTPException(400, "Por favor, use linguagem educada e respeitosa no depoimento")
    offer = await db.offers.find_one({"_id":oid(data.offer_id)})
    if not offer: raise HTTPException(404, "Contratação não encontrada")
    if offer.get("status") != "completed": raise HTTPException(400, "Só é possível avaliar após conclusão do serviço")
    req = await db.requests.find_one({"_id":oid(offer["request_id"])})
    if not req or req.get("client_id") != str(user["_id"]): raise HTTPException(403, "Você não contratou este serviço")
    existing = await db.reviews.find_one({"offer_id":data.offer_id,"client_id":str(user["_id"])})
    if existing: raise HTTPException(409, "Você já avaliou este atendimento")
    item = data.model_dump(); item.update({"provider_id":offer["provider_id"],"client_id":str(user["_id"]),"client_name":user["name"],"created_at":datetime.now(timezone.utc).isoformat()})
    result = await db.reviews.insert_one(item); item["id"] = str(result.inserted_id); item.pop("_id", None); return item

@api.get("/providers/{provider_id}/reviews")
async def provider_reviews(provider_id: str):
    items = await db.reviews.find({"provider_id":provider_id}).sort("created_at", -1).to_list(50)
    for item in items: item["id"] = str(item.pop("_id"))
    total = len(items); avg = round(sum(i["rating"] for i in items)/total, 1) if total else 0
    return {"reviews": items, "average": avg, "total": total}

@api.post("/auth/link-google")
async def link_google(user=Depends(current_user)):
    await db.users.update_one({"_id":user["_id"]},{"$set":{"google_linked":True}})
    return {"message":"Vínculo preparado. A conexão Google será ativada na próxima etapa.","google_linked":True}

app.include_router(api)
origins = [os.environ.get("FRONTEND_URL", "http://localhost:3000"), "http://localhost:3000"]
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=origins, allow_methods=["*"], allow_headers=["Content-Type", "Authorization", "Accept", "X-Requested-With"])

@app.middleware("http")
async def preserve_request_origin(request: Request, call_next):
    response = await call_next(request)
    origin = request.headers.get("origin")
    if origin:
        response.headers["access-control-allow-origin"] = origin
        response.headers["access-control-allow-credentials"] = "true"
        response.headers["access-control-allow-methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response.headers["access-control-allow-headers"] = "Content-Type, Authorization, Accept, X-Requested-With"
    return response

@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)

@app.on_event("shutdown")
async def shutdown(): client.close()