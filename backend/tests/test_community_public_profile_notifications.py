"""Regression tests for public provider profile, recommendations, and notification logging."""
import os
import time
import uuid

import pytest
import requests
from dotenv import dotenv_values


# Module: environment/base URL resolution
frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api"
PWD = "Promao123!"


def make_account(role: str, label: str):
    session = requests.Session()
    email = f"test_{role}_{label}_{int(time.time())}_{uuid.uuid4().hex[:8]}@example.com"
    payload = {"name": f"TEST {role} {label}", "email": email, "password": PWD, "role": role}
    response = session.post(f"{API}/auth/register", json=payload, timeout=20)
    assert response.status_code == 200, response.text
    user = response.json()
    assert user["email"] == email
    assert user["role"] == role
    assert "id" in user and isinstance(user["id"], str)
    return session, user


@pytest.fixture(scope="module")
def scenario_data():
    # Module: account setup and baseline data
    client, client_user = make_account("client", "community")
    provider_1, provider_1_user = make_account("provider", "publico")
    provider_2, provider_2_user = make_account("provider", "parceiro")

    catalog_response = provider_1.post(
        f"{API}/provider/catalog",
        json={
            "name": "Instalação de luminária",
            "category": "Elétrica",
            "price": 220,
            "includes_product": True,
            "product_requirements": "Cliente informa voltagem e modelo",
        },
        timeout=20,
    )
    assert catalog_response.status_code == 200, catalog_response.text
    assert catalog_response.json()["name"] == "Instalação de luminária"

    request_response = client.post(
        f"{API}/requests",
        json={
            "service": "Instalar 2 luminárias",
            "category": "Elétrica",
            "description": "Instalação em teto de gesso com acabamento",
            "budget": "até R$ 350",
        },
        timeout=20,
    )
    assert request_response.status_code == 200, request_response.text
    request_data = request_response.json()
    request_id = request_data["id"]
    assert request_data["status"] == "open"

    # Module: proposal creation + acceptance flow
    offer_response = provider_1.post(
        f"{API}/requests/{request_id}/offers",
        json={"price": 280, "eta": "2 dias", "conditions": "Visita técnica inclusa"},
        timeout=20,
    )
    assert offer_response.status_code == 200, offer_response.text
    offer_id = offer_response.json()["id"]
    assert offer_response.json()["status"] == "pending"

    accept_response = client.post(f"{API}/offers/{offer_id}/accept", timeout=20)
    assert accept_response.status_code == 200, accept_response.text
    assert accept_response.json()["ok"] is True

    # Module: completion + review flow
    complete_client = client.post(f"{API}/offers/{offer_id}/complete", timeout=20)
    assert complete_client.status_code == 200, complete_client.text
    complete_provider = provider_1.post(f"{API}/offers/{offer_id}/complete", timeout=20)
    assert complete_provider.status_code == 200, complete_provider.text
    assert complete_provider.json()["completed"] is True

    review_response = client.post(
        f"{API}/reviews",
        json={
            "offer_id": offer_id,
            "rating": 5,
            "testimonial": "Atendimento cuidadoso, pontual e com ótima comunicação.",
        },
        timeout=20,
    )
    assert review_response.status_code == 200, review_response.text
    assert review_response.json()["provider_id"] == provider_1_user["id"]

    return {
        "client": client,
        "provider_1": provider_1,
        "provider_2": provider_2,
        "client_user": client_user,
        "provider_1_user": provider_1_user,
        "provider_2_user": provider_2_user,
        "offer_id": offer_id,
    }


def test_public_profile_is_open_and_contains_expected_sections(scenario_data):
    # Module: public profile endpoint response shape and visibility
    provider_id = scenario_data["provider_1_user"]["id"]
    response = requests.get(f"{API}/providers/public/{provider_id}", timeout=20)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["provider"]["id"] == provider_id
    assert data["provider"]["role"] == "provider"
    assert f"/prestador/{provider_id}" in data["provider"]["share_url"]
    assert isinstance(data["catalog"], list)
    assert len(data["catalog"]) >= 1
    assert data["catalog"][0]["name"] == "Instalação de luminária"
    assert isinstance(data["reviews"], list)
    assert data["reviews_total"] >= 1
    assert data["rating_average"] >= 1


def test_client_can_recommend_provider_with_polite_message(scenario_data):
    # Module: client recommendation happy path
    response = scenario_data["client"].post(
        f"{API}/recommendations",
        json={
            "provider_id": scenario_data["provider_1_user"]["id"],
            "recipient_name": "Maria Amiga",
            "recipient_email": "maria.amiga@example.com",
            "message": "Profissional confiável e muito educado no atendimento.",
        },
        timeout=20,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["recommender_role"] == "client"
    assert data["provider_id"] == scenario_data["provider_1_user"]["id"]


def test_provider_can_recommend_another_provider(scenario_data):
    # Module: provider-to-provider recommendation allowed
    response = scenario_data["provider_2"].post(
        f"{API}/recommendations",
        json={
            "provider_id": scenario_data["provider_1_user"]["id"],
            "recipient_name": "Carlos Cliente",
            "recipient_email": "carlos.cliente@example.com",
            "message": "Indico com confiança para serviços residenciais.",
        },
        timeout=20,
    )
    assert response.status_code == 200, response.text
    assert response.json()["recommender_role"] == "provider"


def test_provider_cannot_recommend_self(scenario_data):
    # Module: self-recommendation guard
    response = scenario_data["provider_1"].post(
        f"{API}/recommendations",
        json={
            "provider_id": scenario_data["provider_1_user"]["id"],
            "recipient_name": "Auto Indicação",
            "recipient_email": "auto.indicacao@example.com",
            "message": "Mensagem educada",
        },
        timeout=20,
    )
    assert response.status_code == 400
    assert "indicação" in response.json()["detail"].lower()


def test_recommendation_blocks_rude_language(scenario_data):
    # Module: polite language validation on recommendations
    response = scenario_data["client"].post(
        f"{API}/recommendations",
        json={
            "provider_id": scenario_data["provider_1_user"]["id"],
            "recipient_name": "João",
            "recipient_email": "joao@example.com",
            "message": "Esse profissional é idiota",
        },
        timeout=20,
    )
    assert response.status_code == 400
    assert "linguagem educada" in response.json()["detail"].lower()


def test_recommendations_mine_for_provider_and_client(scenario_data):
    # Module: recommendations listing (received for provider / sent for client)
    provider_mine = scenario_data["provider_1"].get(f"{API}/recommendations/mine", timeout=20)
    assert provider_mine.status_code == 200
    provider_items = provider_mine.json()
    assert len(provider_items) >= 2
    assert all(item["provider_id"] == scenario_data["provider_1_user"]["id"] for item in provider_items)

    client_mine = scenario_data["client"].get(f"{API}/recommendations/mine", timeout=20)
    assert client_mine.status_code == 200
    client_items = client_mine.json()
    assert any(item["recipient_name"] == "Maria Amiga" for item in client_items)
    assert all(item["recommender_id"] == scenario_data["client_user"]["id"] for item in client_items)


def test_notifications_recorded_as_skipped_when_email_not_configured(scenario_data):
    # Module: skipped email notifications persistence without Resend credentials
    client_notifications = scenario_data["client"].get(f"{API}/notifications/mine", timeout=20)
    provider_notifications = scenario_data["provider_1"].get(f"{API}/notifications/mine", timeout=20)
    assert client_notifications.status_code == 200
    assert provider_notifications.status_code == 200

    client_items = client_notifications.json()
    provider_items = provider_notifications.json()

    assert any(
        i.get("status") == "skipped" and i.get("reason") == "missing_email_configuration"
        for i in client_items
    )
    assert any(
        i.get("status") == "skipped" and i.get("reason") == "missing_email_configuration"
        for i in provider_items
    )


def test_completed_offer_cannot_be_reviewed_twice(scenario_data):
    # Module: duplicate review protection for completed service
    second_review = scenario_data["client"].post(
        f"{API}/reviews",
        json={
            "offer_id": scenario_data["offer_id"],
            "rating": 5,
            "testimonial": "Tentativa de segunda avaliação educada.",
        },
        timeout=20,
    )
    assert second_review.status_code == 409
    assert "já avaliou" in second_review.json()["detail"].lower()
