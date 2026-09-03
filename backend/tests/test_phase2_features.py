"""Regression checks for provider catalog, requests/offers, and portfolio authorization."""
import uuid
import requests
from pathlib import Path

BASE_URL = next(line.split("=", 1)[1] for line in Path("/app/frontend/.env").read_text().splitlines() if line.startswith("REACT_APP_BACKEND_URL=")).rstrip("/")


def account(role):
    s = requests.Session()
    email = f"TEST_{role}_{uuid.uuid4().hex[:10]}@example.com"
    payload = {"name": f"TEST {role}", "email": email, "password": "Promao123!", "role": role}
    r = s.post(f"{BASE_URL}/api/auth/register", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    payload["email"] = payload["email"].lower()
    return s, payload


def test_catalog_request_offer_and_portfolio_authorization():
    client, client_payload = account("client")
    provider, _ = account("provider")

    catalog = provider.post(f"{BASE_URL}/api/provider/catalog", json={
        "name": "TEST Instalação", "category": "Elétrica", "price": 175,
        "includes_product": True, "product_requirements": "TEST voltagem"
    }, timeout=15)
    assert catalog.status_code == 200 and catalog.json()["includes_product"] is True
    assert provider.get(f"{BASE_URL}/api/provider/catalog", timeout=15).json()[0]["name"] == "TEST Instalação"

    request = client.post(f"{BASE_URL}/api/requests", json={
        "service": "TEST luminária", "category": "Elétrica", "description": "TEST pedido"
    }, timeout=15)
    assert request.status_code == 200
    request_id = request.json()["id"]
    offer = provider.post(f"{BASE_URL}/api/requests/{request_id}/offers", json={
        "price": 250, "eta": "2 dias", "conditions": "TEST visita técnica"
    }, timeout=15)
    assert offer.status_code == 200 and offer.json()["eta"] == "2 dias"

    photo = provider.post(f"{BASE_URL}/api/portfolio", json={
        "image_data": "data:image/png;base64,TEST", "caption": "TEST antes e depois",
        "client_email": client_payload["email"]
    }, timeout=15)
    assert photo.status_code == 200 and photo.json()["client_authorized"] is False
    photo_id = photo.json()["id"]
    pending = client.get(f"{BASE_URL}/api/portfolio/pending", timeout=15)
    assert pending.status_code == 200 and any(p["id"] == photo_id for p in pending.json())
    assert client.post(f"{BASE_URL}/api/portfolio/{photo_id}/authorize", timeout=15).status_code == 200
    public = client.get(f"{BASE_URL}/api/portfolio", timeout=15)
    assert public.status_code == 200 and any(p["id"] == photo_id for p in public.json())