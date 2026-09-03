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
    provider_id: str
    rating: int
    testimonial: str

def public_user(user):
    return {"id": str(user.get("_id", user.get("id"))), "name": user["name"], "email": user["email"], "role": user["role"], "google_linked": user.get("google_linked", False)}

def token(user):
    secret = os.environ["JWT_SECRET"]
    return jwt.encode({"sub": str(user["_id"]), "exp": datetime.now(timezone.utc) + timedelta(hours=12)}, secret, algorithm=JWT_ALGORITHM)

async def current_user(request: Request):
    raw = request.cookies.get("access_token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if not raw:
        raise HTTPException(401, "Faça login para continuar")
    try:
        payload = jwt.decode(raw, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"_id": __import__("bson").ObjectId(payload["sub"])})
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
async def logout(response: Response):
    response.delete_cookie("access_token"); return {"ok": True}

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

@api.post("/reviews")
async def review(data: ReviewInput, user=Depends(current_user)):
    item = data.model_dump(); item.update({"client_id":str(user["_id"]),"client_name":user["name"],"created_at":datetime.now(timezone.utc).isoformat()})
    await db.reviews.insert_one(item); item.pop("_id", None); return item

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