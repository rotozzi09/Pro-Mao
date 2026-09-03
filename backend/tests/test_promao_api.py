"""Regression coverage for ProMão auth, catalog, and client request APIs."""
import os
import uuid
from pathlib import Path

import pytest
import requests


def _base_url():
    env = Path("/app/frontend/.env").read_text().splitlines()
    value = next(line.split("=", 1)[1] for line in env if line.startswith("REACT_APP_BACKEND_URL="))
    return value.rstrip("/")


BASE_URL = _base_url()


@pytest.fixture
def session():
    return requests.Session()


@pytest.fixture
def account(session):
    email = f"TEST_{uuid.uuid4().hex[:10]}@example.com"
    payload = {"name": "TEST Cliente", "email": email, "password": "Promao123!", "role": "client"}
    response = session.post(f"{BASE_URL}/api/auth/register", json=payload, timeout=15)
    assert response.status_code == 200, response.text
    return session, payload, response


def test_services_and_demo_providers(session):
    services = session.get(f"{BASE_URL}/api/services", timeout=15)
    providers = session.get(f"{BASE_URL}/api/providers", timeout=15)
    assert services.status_code == 200 and len(services.json()) == 7
    assert {item["name"] for item in services.json()} >= {"Limpeza", "Outras"}
    assert providers.status_code == 200 and len(providers.json()) > 0
    assert all("name" in item and "rating" in item for item in providers.json())


def test_register_sets_httponly_cookie_and_me(account):
    session, payload, response = account
    assert response.json()["email"] == payload["email"].lower()
    cookie = response.cookies.get("access_token")
    assert cookie
    assert any(c.name == "access_token" and c.has_nonstandard_attr("HttpOnly") for c in response.cookies)
    me = session.get(f"{BASE_URL}/api/auth/me", timeout=15)
    assert me.status_code == 200 and me.json()["role"] == "client"


def test_login_and_logout(session):
    email = f"TEST_{uuid.uuid4().hex[:10]}@example.com"
    payload = {"name": "TEST Login", "email": email, "password": "Promao123!", "role": "provider"}
    assert session.post(f"{BASE_URL}/api/auth/register", json=payload, timeout=15).status_code == 200
    session.post(f"{BASE_URL}/api/auth/logout", timeout=15)
    login = session.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": payload["password"]}, timeout=15)
    assert login.status_code == 200 and login.json()["role"] == "provider"
    assert session.post(f"{BASE_URL}/api/auth/logout", timeout=15).status_code == 200
    assert session.get(f"{BASE_URL}/api/auth/me", timeout=15).status_code == 401


def test_invalid_login_is_readable(session):
    response = session.post(f"{BASE_URL}/api/auth/login", json={"email": "missing@example.com", "password": "wrong"}, timeout=15)
    assert response.status_code == 401
    assert response.json()["detail"] == "E-mail ou senha incorretos"


def test_request_requires_auth(session):
    response = session.post(f"{BASE_URL}/api/requests", json={"service": "TEST", "category": "Elétrica", "description": "TEST"}, timeout=15)
    assert response.status_code == 401


def test_authenticated_request_persists(account):
    session, _, _ = account
    payload = {"service": "TEST instalar luminária", "category": "Elétrica", "description": "TEST detalhes", "budget": "até R$ 250"}
    response = session.post(f"{BASE_URL}/api/requests", json=payload, timeout=15)
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == payload["service"] and data["status"] == "open" and data["id"]


def test_cors_is_explicit_and_credentials_allowed(session):
    response = session.options(f"{BASE_URL}/api/auth/me", headers={"Origin": BASE_URL, "Access-Control-Request-Method": "GET"}, timeout=15)
    assert response.status_code in (200, 204, 400)
    assert response.headers.get("access-control-allow-credentials") == "true"