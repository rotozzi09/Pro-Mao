"""Backend tests for ProMão proposal acceptance / both-parties completion / reviews."""
import os
import time
import uuid
import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api"
PWD = "Promao123!"
TS = str(int(time.time()))


def new_session(role, tag):
    s = requests.Session()
    email = f"test_{role}_{tag}_{TS}_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register", json={"name": f"TEST {role} {tag}", "email": email, "password": PWD, "role": role})
    assert r.status_code == 200, f"register failed {r.status_code} {r.text[:300]}"
    data = r.json()
    assert data["email"] == email
    assert data["role"] == role
    assert "id" in data
    return s, data, email


@pytest.fixture(scope="module")
def actors():
    """client, provider A, provider B sessions"""
    c, cu, ce = new_session("client", "c1")
    p1, pu1, _ = new_session("provider", "p1")
    p2, pu2, _ = new_session("provider", "p2")
    return {"client": c, "client_user": cu, "client_email": ce,
            "p1": p1, "p1_user": pu1, "p2": p2, "p2_user": pu2}


def make_request(sess, service="TEST_instalar luminaria"):
    r = sess.post(f"{API}/requests", json={"service": service, "category": "Elétrica",
                                           "description": "TEST descricao detalhada do servico", "budget": "até R$ 250"})
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert d["status"] == "open" and "id" in d and "_id" not in d
    return d["id"]


def make_offer(sess, req_id, price=150.0):
    r = sess.post(f"{API}/requests/{req_id}/offers", json={"price": price, "eta": "2 dias", "conditions": "TEST condicoes"})
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert d["status"] == "pending" and d["client_completed"] is False and d["provider_completed"] is False
    assert "_id" not in d
    return d["id"]


# --- auth / session basics ---
class TestAuthBasics:
    def test_login_and_me(self, actors):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"email": actors["client_email"], "password": PWD})
        assert r.status_code == 200
        assert r.json()["email"] == actors["client_email"]
        assert "access_token" in s.cookies.get_dict()
        me = s.get(f"{API}/auth/me")
        assert me.status_code == 200 and me.json()["role"] == "client"

    def test_login_wrong_password(self, actors):
        r = requests.post(f"{API}/auth/login", json={"email": actors["client_email"], "password": "wrongpass"})
        assert r.status_code == 401

    def test_unauthenticated_requests(self):
        assert requests.get(f"{API}/requests").status_code == 401


# --- listing returns full documents ---
class TestListings:
    def test_list_requests_returns_full_docs(self, actors):
        rid = make_request(actors["client"])
        r = actors["client"].get(f"{API}/requests")
        assert r.status_code == 200
        items = r.json()
        mine = [i for i in items if i["id"] == rid]
        assert len(mine) == 1
        item = mine[0]
        for key in ["service", "category", "description", "status", "client_id"]:
            assert key in item, f"missing {key}"
        assert "_id" not in item

    def test_provider_sees_open_requests(self, actors):
        rid = make_request(actors["client"], "TEST_pedido aberto")
        r = actors["p1"].get(f"{API}/requests")
        assert r.status_code == 200
        assert any(i["id"] == rid for i in r.json())

    def test_list_offers_returns_full_docs(self, actors):
        rid = make_request(actors["client"])
        oid = make_offer(actors["p1"], rid)
        r = actors["client"].get(f"{API}/requests/{rid}/offers")
        assert r.status_code == 200
        offers = r.json()
        assert len(offers) == 1 and offers[0]["id"] == oid
        for key in ["provider_name", "price", "eta", "conditions", "status"]:
            assert key in offers[0]

    def test_offers_mine(self, actors):
        rid = make_request(actors["client"])
        oid = make_offer(actors["p1"], rid, 199.0)
        r = actors["p1"].get(f"{API}/offers/mine")
        assert r.status_code == 200
        found = [o for o in r.json() if o["id"] == oid]
        assert len(found) == 1
        assert found[0]["request"]["service"].startswith("TEST_")
        assert found[0]["request"]["status"] == "open"

    def test_offers_mine_forbidden_for_client(self, actors):
        assert actors["client"].get(f"{API}/offers/mine").status_code == 403


# --- acceptance flow ---
class TestAcceptance:
    def test_accept_sets_statuses(self, actors):
        rid = make_request(actors["client"])
        o1 = make_offer(actors["p1"], rid, 100.0)
        o2 = make_offer(actors["p2"], rid, 120.0)
        r = actors["client"].post(f"{API}/offers/{o1}/accept")
        assert r.status_code == 200 and r.json()["ok"] is True
        offers = {o["id"]: o for o in actors["client"].get(f"{API}/requests/{rid}/offers").json()}
        assert len(offers) == 2, "non-selected offers must remain visible"
        assert offers[o1]["status"] == "accepted"
        assert offers[o2]["status"] == "not_selected"
        req = [i for i in actors["client"].get(f"{API}/requests").json() if i["id"] == rid][0]
        assert req["status"] == "in_progress"
        assert req["accepted_offer_id"] == o1

    def test_provider_cannot_accept(self, actors):
        rid = make_request(actors["client"])
        oid = make_offer(actors["p1"], rid)
        assert actors["p1"].post(f"{API}/offers/{oid}/accept").status_code == 403

    def test_other_client_cannot_accept(self, actors):
        rid = make_request(actors["client"])
        oid = make_offer(actors["p1"], rid)
        other, _, _ = new_session("client", "intruder")
        assert other.post(f"{API}/offers/{oid}/accept").status_code == 403

    def test_offer_on_non_open_request_rejected(self, actors):
        rid = make_request(actors["client"])
        o1 = make_offer(actors["p1"], rid)
        actors["client"].post(f"{API}/offers/{o1}/accept")
        r = actors["p2"].post(f"{API}/requests/{rid}/offers", json={"price": 90.0, "eta": "1 dia", "conditions": "x"})
        assert r.status_code == 400
        assert "não está mais aceitando" in r.json()["detail"]

    def test_double_accept_rejected(self, actors):
        rid = make_request(actors["client"])
        o1 = make_offer(actors["p1"], rid)
        o2 = make_offer(actors["p2"], rid)
        assert actors["client"].post(f"{API}/offers/{o1}/accept").status_code == 200
        assert actors["client"].post(f"{API}/offers/{o2}/accept").status_code == 400

    def test_client_only_role_cannot_offer(self, actors):
        rid = make_request(actors["client"])
        r = actors["client"].post(f"{API}/requests/{rid}/offers", json={"price": 10.0, "eta": "1", "conditions": "x"})
        assert r.status_code == 403


# --- both-parties completion ---
class TestCompletion:
    def test_complete_before_accept_rejected(self, actors):
        rid = make_request(actors["client"])
        oid = make_offer(actors["p1"], rid)
        r = actors["client"].post(f"{API}/offers/{oid}/complete")
        assert r.status_code == 400

    def test_client_then_provider_completion(self, actors):
        rid = make_request(actors["client"])
        oid = make_offer(actors["p1"], rid)
        actors["client"].post(f"{API}/offers/{oid}/accept")
        r = actors["client"].post(f"{API}/offers/{oid}/complete")
        assert r.status_code == 200 and r.json()["completed"] is False
        o = actors["client"].get(f"{API}/requests/{rid}/offers").json()[0]
        assert o["status"] == "client_completed" and o["client_completed"] is True
        req = [i for i in actors["client"].get(f"{API}/requests").json() if i["id"] == rid][0]
        assert req["status"] == "in_progress"
        r2 = actors["p1"].post(f"{API}/offers/{oid}/complete")
        assert r2.status_code == 200 and r2.json()["completed"] is True
        o = actors["client"].get(f"{API}/requests/{rid}/offers").json()[0]
        assert o["status"] == "completed" and o["provider_completed"] is True
        req = [i for i in actors["client"].get(f"{API}/requests").json() if i["id"] == rid][0]
        assert req["status"] == "completed"

    def test_provider_then_client_completion(self, actors):
        rid = make_request(actors["client"])
        oid = make_offer(actors["p1"], rid)
        actors["client"].post(f"{API}/offers/{oid}/accept")
        r = actors["p1"].post(f"{API}/offers/{oid}/complete")
        assert r.status_code == 200 and r.json()["completed"] is False
        o = actors["client"].get(f"{API}/requests/{rid}/offers").json()[0]
        assert o["status"] == "provider_completed"
        r2 = actors["client"].post(f"{API}/offers/{oid}/complete")
        assert r2.status_code == 200 and r2.json()["completed"] is True

    def test_non_participant_cannot_complete(self, actors):
        rid = make_request(actors["client"])
        oid = make_offer(actors["p1"], rid)
        actors["client"].post(f"{API}/offers/{oid}/accept")
        assert actors["p2"].post(f"{API}/offers/{oid}/complete").status_code == 403
        other, _, _ = new_session("client", "outsider")
        assert other.post(f"{API}/offers/{oid}/complete").status_code == 403


def completed_offer(actors, price=250.0):
    rid = make_request(actors["client"])
    oid = make_offer(actors["p1"], rid, price)
    actors["client"].post(f"{API}/offers/{oid}/accept")
    actors["client"].post(f"{API}/offers/{oid}/complete")
    actors["p1"].post(f"{API}/offers/{oid}/complete")
    return rid, oid


# --- reviews ---
class TestReviews:
    def test_review_requires_completed_offer(self, actors):
        rid = make_request(actors["client"])
        oid = make_offer(actors["p1"], rid)
        actors["client"].post(f"{API}/offers/{oid}/accept")
        r = actors["client"].post(f"{API}/reviews", json={"offer_id": oid, "rating": 5, "testimonial": "Atendimento excelente e pontual"})
        assert r.status_code == 400
        assert "conclus" in r.json()["detail"]

    def test_polite_review_success_and_aggregation(self, actors):
        _, oid = completed_offer(actors)
        r = actors["client"].post(f"{API}/reviews", json={"offer_id": oid, "rating": 5, "testimonial": "Serviço impecável, muito atencioso."})
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["rating"] == 5 and d["offer_id"] == oid and "_id" not in d
        assert d["client_name"].startswith("TEST client")
        pid = actors["p1_user"]["id"]
        agg = requests.get(f"{API}/providers/{pid}/reviews")
        assert agg.status_code == 200
        body = agg.json()
        assert body["total"] >= 1
        assert 1 <= body["average"] <= 5
        assert any(i["offer_id"] == oid for i in body["reviews"])
        assert all("_id" not in i for i in body["reviews"])

    def test_duplicate_review_409(self, actors):
        _, oid = completed_offer(actors)
        first = actors["client"].post(f"{API}/reviews", json={"offer_id": oid, "rating": 4, "testimonial": "Trabalho bem feito, recomendo."})
        assert first.status_code == 200
        second = actors["client"].post(f"{API}/reviews", json={"offer_id": oid, "rating": 5, "testimonial": "Outro depoimento educado aqui."})
        assert second.status_code == 409
        assert second.json()["detail"] == "Você já avaliou este atendimento"

    @pytest.mark.parametrize("word", ["idiota", "lixo", "merda", "incompetente"])
    def test_rude_language_blocked(self, actors, word):
        _, oid = completed_offer(actors)
        r = actors["client"].post(f"{API}/reviews", json={"offer_id": oid, "rating": 1, "testimonial": f"O prestador foi {word} demais"})
        assert r.status_code == 400
        assert r.json()["detail"] == "Por favor, use linguagem educada e respeitosa no depoimento"

    def test_short_testimonial_blocked(self, actors):
        _, oid = completed_offer(actors)
        r = actors["client"].post(f"{API}/reviews", json={"offer_id": oid, "rating": 5, "testimonial": "otimo"})
        assert r.status_code == 400
        assert "10 caracteres" in r.json()["detail"]

    @pytest.mark.parametrize("rating", [0, 6, -1])
    def test_invalid_rating(self, actors, rating):
        _, oid = completed_offer(actors)
        r = actors["client"].post(f"{API}/reviews", json={"offer_id": oid, "rating": rating, "testimonial": "Depoimento educado e valido"})
        assert r.status_code == 400

    def test_provider_cannot_review(self, actors):
        _, oid = completed_offer(actors)
        r = actors["p1"].post(f"{API}/reviews", json={"offer_id": oid, "rating": 5, "testimonial": "Depoimento educado e valido"})
        assert r.status_code == 403

    def test_other_client_cannot_review(self, actors):
        _, oid = completed_offer(actors)
        other, _, _ = new_session("client", "reviewer")
        r = other.post(f"{API}/reviews", json={"offer_id": oid, "rating": 5, "testimonial": "Depoimento educado e valido"})
        assert r.status_code == 403


# --- edge cases on ids ---
class TestEdgeCases:
    def test_accept_invalid_offer_id(self, actors):
        r = actors["client"].post(f"{API}/offers/notanobjectid/accept")
        assert r.status_code in (400, 404, 422), f"got {r.status_code}"

    def test_accept_missing_offer_id(self, actors):
        r = actors["client"].post(f"{API}/offers/64b7f3f3f3f3f3f3f3f3f3f3/accept")
        assert r.status_code == 404

    def test_offers_for_unknown_request(self, actors):
        r = actors["client"].get(f"{API}/requests/64b7f3f3f3f3f3f3f3f3f3f3/offers")
        assert r.status_code == 200 and r.json() == []


# --- security / duplicate guards (suspected gaps) ---
class TestGuardGaps:
    def test_provider_cannot_offer_twice_on_same_request(self, actors):
        rid = make_request(actors["client"])
        make_offer(actors["p1"], rid, 100.0)
        r = actors["p1"].post(f"{API}/requests/{rid}/offers", json={"price": 111.0, "eta": "3 dias", "conditions": "dup"})
        assert r.status_code in (400, 409), f"duplicate offer from same provider allowed (status {r.status_code})"

    def test_offers_of_other_users_request_not_public(self, actors):
        rid = make_request(actors["client"])
        make_offer(actors["p1"], rid, 100.0)
        outsider, _, _ = new_session("client", "peeker")
        r = outsider.get(f"{API}/requests/{rid}/offers")
        assert r.status_code in (403, 404), f"any authenticated user can read another client's offers (status {r.status_code})"

    def test_complete_invalid_object_id(self, actors):
        r = actors["client"].post(f"{API}/offers/bogusid/complete")
        assert r.status_code in (400, 404, 422), f"got {r.status_code}"

    def test_review_invalid_object_id(self, actors):
        r = actors["client"].post(f"{API}/reviews", json={"offer_id": "bogusid", "rating": 5, "testimonial": "Depoimento educado valido"})
        assert r.status_code in (400, 404, 422), f"got {r.status_code}"
