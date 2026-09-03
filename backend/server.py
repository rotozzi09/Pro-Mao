from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from pathlib import Path
import os, bcrypt, jwt
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

def public_user(user):
    return {"id": str(user.get("_id", user.get("id"))), "name": user["name"], "email": user["email"], "role": user["role"], "google_linked": user.get("google_linked", False)}

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

@api.get("/")
async def root(): return {"message": "ProMão API"}

@api.post("/auth/register")
async def register(data: RegisterInput, response: Response):
    if data.role not in ["client", "provider"]: raise HTTPException(400, "Perfil inválido")
    email = data.email.lower()
    if await db.users.find_one({"email": email}): raise HTTPException(409, "Este e-mail já está cadastrado")
    user = {"name": data.name.strip(), "email": email, "password_hash": bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode(), "role": data.role, "google_linked": False, "created_at": datetime.now(timezone.utc).isoformat()}
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
        user = {"name":info.get("name", "Usuário Google"),"email":info["email"].lower(),"password_hash":"google-oauth","role":"client","google_linked":True,"created_at":datetime.now(timezone.utc).isoformat()}
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
    query = {"role":"provider"}
    if category and category != "Outras": query["category"] = category
    if q: query["$or"] = [{"name":{"$regex":q,"$options":"i"}},{"category":{"$regex":q,"$options":"i"}}]
    users = await db.users.find(query, {"_id":1,"name":1,"category":1,"services":1}).to_list(12)
    if not users:
        demo = [{"id":"demo-1","name":"Marina Alves","category":"Limpeza e organização","rating":4.9,"reviews":32,"price":"a partir de R$ 120","initials":"MA"},{"id":"demo-2","name":"Rafael Costa","category":"Elétrica residencial","rating":4.8,"reviews":18,"price":"a partir de R$ 90","initials":"RC"},{"id":"demo-3","name":"Júlia Martins","category":"Pintura e reparos","rating":5.0,"reviews":27,"price":"a partir de R$ 150","initials":"JM"}]
        if category: demo = [p for p in demo if category.lower() in p["category"].lower()]
        if q: demo = [p for p in demo if q.lower() in (p["name"] + p["category"]).lower()]
        return demo
    return [{"id":str(u["_id"]),"name":u["name"],"category":u.get("category","Serviços gerais"),"rating":5,"reviews":0,"price":"a combinar","initials":"".join(x[0] for x in u["name"].split()[:2])} for u in users]

@api.post("/requests")
async def create_request(data: RequestInput, user=Depends(current_user)):
    item = data.model_dump(); item.update({"client_id": str(user["_id"]), "created_at": datetime.now(timezone.utc).isoformat(), "status":"open"})
    result = await db.requests.insert_one(item); item["id"] = str(result.inserted_id); item.pop("_id", None); return item

@api.get("/requests")
async def list_requests(user=Depends(current_user)):
    query = {"client_id":str(user["_id"])} if user["role"] == "client" else {"status":"open"}
    items = await db.requests.find(query).sort("created_at", -1).to_list(50)
    for item in items: item["id"] = str(item.pop("_id"))
    return items

@api.post("/requests/{request_id}/offers")
async def create_offer(request_id: str, data: OfferInput, user=Depends(current_user)):
    if user["role"] != "provider": raise HTTPException(403, "Apenas prestadores podem enviar propostas")
    req = await db.requests.find_one({"_id":oid(request_id)})
    if not req: raise HTTPException(404, "Pedido não encontrado")
    if req.get("status") != "open": raise HTTPException(400, "Este pedido não está mais aceitando propostas")
    offer = data.model_dump(); offer.update({"request_id":request_id,"provider_id":str(user["_id"]),"provider_name":user["name"],"status":"pending","client_completed":False,"provider_completed":False,"created_at":datetime.now(timezone.utc).isoformat()})
    result = await db.offers.insert_one(offer); offer["id"] = str(result.inserted_id); offer.pop("_id", None); return offer

@api.get("/requests/{request_id}/offers")
async def list_offers(request_id: str, user=Depends(current_user)):
    req = await db.requests.find_one({"_id":oid(request_id)})
    if not req: raise HTTPException(404, "Pedido não encontrado")
    if user["role"] == "client":
        if req.get("client_id") != str(user["_id"]): raise HTTPException(403, "Este pedido não é seu")
        items = await db.offers.find({"request_id":request_id}).sort("created_at", 1).to_list(50)
    else:
        items = await db.offers.find({"request_id":request_id,"provider_id":str(user["_id"])}).to_list(50)
    for item in items: item["id"] = str(item.pop("_id"))
    return items

@api.get("/offers/mine")
async def my_offers(user=Depends(current_user)):
    if user["role"] != "provider": raise HTTPException(403, "Apenas prestadores")
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
    if user["role"] != "client": raise HTTPException(403, "Apenas clientes aceitam propostas")
    offer = await db.offers.find_one({"_id":oid(offer_id)})
    if not offer: raise HTTPException(404, "Proposta não encontrada")
    req = await db.requests.find_one({"_id":oid(offer["request_id"])})
    if not req or req.get("client_id") != str(user["_id"]): raise HTTPException(403, "Este pedido não é seu")
    if req.get("status") != "open": raise HTTPException(400, "Este pedido já foi encaminhado")
    await db.offers.update_one({"_id":offer["_id"]},{"$set":{"status":"accepted","accepted_at":datetime.now(timezone.utc).isoformat()}})
    await db.offers.update_many({"request_id":offer["request_id"],"_id":{"$ne":offer["_id"]}},{"$set":{"status":"not_selected"}})
    await db.requests.update_one({"_id":req["_id"]},{"$set":{"status":"in_progress","accepted_offer_id":str(offer["_id"]),"accepted_provider_id":offer["provider_id"]}})
    return {"ok":True}

@api.post("/offers/{offer_id}/complete")
async def complete_offer(offer_id: str, user=Depends(current_user)):
    offer = await db.offers.find_one({"_id":oid(offer_id)})
    if not offer: raise HTTPException(404, "Proposta não encontrada")
    if offer.get("status") not in ["accepted","client_completed","provider_completed"]: raise HTTPException(400, "Proposta ainda não foi aceita")
    req = await db.requests.find_one({"_id":oid(offer["request_id"])})
    if not req: raise HTTPException(404, "Pedido não encontrado")
    field = None
    if user["role"] == "client" and req.get("client_id") == str(user["_id"]): field = "client_completed"
    elif user["role"] == "provider" and offer.get("provider_id") == str(user["_id"]): field = "provider_completed"
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

@api.get("/provider/catalog")
async def provider_catalog(user=Depends(current_user)):
    items = await db.catalog.find({"provider_id":str(user["_id"])}).to_list(100)
    for item in items: item["id"] = str(item.pop("_id"))
    return items

@api.post("/provider/catalog")
async def add_catalog(data: CatalogInput, user=Depends(current_user)):
    if user["role"] != "provider": raise HTTPException(403, "Apenas prestadores possuem catálogo")
    item = data.model_dump(); item.update({"provider_id":str(user["_id"]),"created_at":datetime.now(timezone.utc).isoformat()})
    result = await db.catalog.insert_one(item); item["id"] = str(result.inserted_id); item.pop("_id", None); return item

@api.delete("/provider/catalog/{item_id}")
async def remove_catalog(item_id: str, user=Depends(current_user)):
    await db.catalog.delete_one({"_id":oid(item_id),"provider_id":str(user["_id"])})
    return {"ok":True}

@api.get("/portfolio")
async def portfolio(user=Depends(current_user)):
    query = {"provider_id":str(user["_id"])} if user["role"] == "provider" else {"client_authorized":True}
    items = await db.portfolio.find(query).to_list(100)
    for item in items: item["id"] = str(item.pop("_id"))
    return items

@api.get("/portfolio/pending")
async def pending_portfolio(user=Depends(current_user)):
    if user["role"] != "client": raise HTTPException(403, "Apenas clientes autorizam fotos")
    items = await db.portfolio.find({"client_email":user["email"],"client_authorized":False}).to_list(100)
    for item in items: item["id"] = str(item.pop("_id"))
    return items

@api.post("/portfolio")
async def add_portfolio(data: PortfolioInput, user=Depends(current_user)):
    if user["role"] != "provider": raise HTTPException(403, "Apenas prestadores podem publicar fotos")
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

@api.post("/reviews")
async def review(data: ReviewInput, user=Depends(current_user)):
    if user["role"] != "client": raise HTTPException(403, "Apenas clientes avaliam")
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
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

@app.middleware("http")
async def preserve_request_origin(request: Request, call_next):
    response = await call_next(request)
    origin = request.headers.get("origin")
    if origin:
        response.headers["access-control-allow-origin"] = origin
        response.headers["access-control-allow-credentials"] = "true"
        response.headers["access-control-allow-methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response.headers["access-control-allow-headers"] = "*"
    return response

@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)

@app.on_event("shutdown")
async def shutdown(): client.close()