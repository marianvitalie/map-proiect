import pytest

from src.app import APP_NAME, app, store, validate_contact


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert "uptime_seconds" in body


def test_version_reads_environment(client, monkeypatch):
    monkeypatch.setenv("APP_COMMIT", "abc1234")
    body = client.get("/version").get_json()
    assert body["commit"] == "abc1234"
    assert body["app"] == APP_NAME
    assert body["version"]
    assert body["built_at"]


def test_reset_returns_no_content(client):
    assert client.post("/reset").status_code == 204


def test_reset_rejects_get(client):
    assert client.get("/reset").status_code == 405


def test_reset_clears_store(client):
    store.next_id = 42
    store.contacts[1] = {"id": 1, "name": "Test"}
    client.post("/reset")
    assert store.next_id == 1
    assert store.contacts == {}


def test_home_returns_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.content_type.startswith("text/html")


def test_unknown_route_returns_not_found(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.get_json()["error"] == "not_found"


def test_validate_contact_valid():
    valid_data = {
        "name": "Ana Pop",
        "email": "ana@example.com",
        "phone": "0722334455",
        "category": "work",
    }
    assert validate_contact(valid_data) is None

    # Cu prefix '+' la telefon
    valid_with_plus = dict(valid_data, phone="+0722334455")
    assert validate_contact(valid_with_plus) is None

    # Nume cu lungime la limita superioara (L = 50)
    valid_limit_name = dict(valid_data, name="A" * 50)
    assert validate_contact(valid_limit_name) is None


def test_validate_contact_missing_fields():
    data = {
        "name": "Ana Pop",
        "email": "ana@example.com",
        "phone": "0722334455",
        "category": "work",
    }
    for field in ("name", "email", "phone", "category"):
        incomplete = dict(data)
        del incomplete[field]
        err = validate_contact(incomplete)
        assert err is not None
        assert f"Missing required field: '{field}'" in err


def test_validate_contact_invalid_name():
    base = {
        "name": "Ana Pop",
        "email": "ana@example.com",
        "phone": "0722334455",
        "category": "work",
    }
    # Sir gol
    assert validate_contact(dict(base, name="")) is not None
    # Doar spatii albe
    assert validate_contact(dict(base, name="   ")) is not None
    # Peste limita de L=50 caractere (51 caractere)
    assert validate_contact(dict(base, name="A" * 51)) is not None
    # Tip greșit (nu este șir de caractere)
    assert validate_contact(dict(base, name=123)) is not None


def test_validate_contact_invalid_email():
    base = {
        "name": "Ana Pop",
        "email": "ana@example.com",
        "phone": "0722334455",
        "category": "work",
    }
    # Fara @
    assert validate_contact(dict(base, email="anaexample.com")) is not None
    # Doua @
    assert validate_contact(dict(base, email="ana@@example.com")) is not None
    # Fara text inainte de @
    assert validate_contact(dict(base, email="@example.com")) is not None
    # Fara punct dupa @
    assert validate_contact(dict(base, email="ana@examplecom")) is not None
    # Tip greșit
    assert validate_contact(dict(base, email=None)) is not None


def test_validate_contact_invalid_phone():
    base = {
        "name": "Ana Pop",
        "email": "ana@example.com",
        "phone": "0722334455",
        "category": "work",
    }
    # 9 cifre (prea scurt)
    assert validate_contact(dict(base, phone="072233445")) is not None
    # 11 cifre (prea lung)
    assert validate_contact(dict(base, phone="07223344555")) is not None
    # Contine litere
    assert validate_contact(dict(base, phone="072233445a")) is not None
    # Semnul '+' in interior
    assert validate_contact(dict(base, phone="0722+33445")) is not None
    # Semnul '+' dublu
    assert validate_contact(dict(base, phone="++0722334455")) is not None
    # Tip greșit (număr în loc de șir)
    assert validate_contact(dict(base, phone=722334455)) is not None


def test_validate_contact_invalid_category():
    base = {
        "name": "Ana Pop",
        "email": "ana@example.com",
        "phone": "0722334455",
        "category": "work",
    }
    # Categorie inexistenta
    assert validate_contact(dict(base, category="unknown")) is not None
    # Categorie scrisa gresit sau goala
    assert validate_contact(dict(base, category="")) is not None
    # Tip greșit
    assert validate_contact(dict(base, category=12)) is not None


def test_validate_contact_invalid_payload_type():
    assert validate_contact(None) is not None
    assert validate_contact(["not", "a", "dict"]) is not None
    assert validate_contact("string") is not None


def test_create_contact_success(client):
    client.post("/reset")
    c1 = {
        "name": "Ana Pop",
        "email": "ana@example.com",
        "phone": "0722334455",
        "category": "work",
    }
    r1 = client.post("/contacts", json=c1)
    assert r1.status_code == 201
    body1 = r1.get_json()
    assert body1["id"] == 1
    assert body1["name"] == c1["name"]
    assert body1["email"] == c1["email"]
    assert body1["phone"] == c1["phone"]
    assert body1["category"] == c1["category"]

    c2 = {
        "name": "Dan Ionescu",
        "email": "dan@example.com",
        "phone": "+0733112233",
        "category": "friends",
    }
    r2 = client.post("/contacts", json=c2)
    assert r2.status_code == 201
    body2 = r2.get_json()
    assert body2["id"] == 2


def test_create_contact_duplicate_email_conflict(client):
    client.post("/reset")
    c1 = {
        "name": "Ana Pop",
        "email": "Ana@Example.COM",
        "phone": "0722334455",
        "category": "work",
    }
    r1 = client.post("/contacts", json=c1)
    assert r1.status_code == 201

    c2 = {
        "name": "Ana P.",
        "email": "ana@example.com",
        "phone": "0733445566",
        "category": "friends",
    }
    r2 = client.post("/contacts", json=c2)
    assert r2.status_code == 409
    body2 = r2.get_json()
    assert body2["error"] == "conflict"
    assert "already exists" in body2["message"].lower()


def test_create_contact_validation_failure(client):
    client.post("/reset")
    # Câmp lipsă
    r1 = client.post(
        "/contacts",
        json={"name": "Test", "email": "test@example.com", "phone": "0711223344"},
    )
    assert r1.status_code == 400
    assert r1.get_json()["error"] == "validation"

    # Non-JSON body
    r2 = client.post(
        "/contacts",
        data="not a json string",
        content_type="application/json",
    )
    assert r2.status_code == 400
    assert r2.get_json()["error"] == "validation"


def test_list_contacts_empty(client):
    client.post("/reset")
    response = client.get("/contacts")
    assert response.status_code == 200
    assert response.get_json() == []


def test_list_contacts_sorted_by_name(client):
    client.post("/reset")
    client.post("/contacts", json={"name": "Vasile", "email": "v@example.com", "phone": "0711111111", "category": "work"})
    client.post("/contacts", json={"name": "Ana", "email": "a@example.com", "phone": "0722222222", "category": "friends"})
    client.post("/contacts", json={"name": "Dan", "email": "d@example.com", "phone": "0733333333", "category": "family"})

    response = client.get("/contacts")
    assert response.status_code == 200
    names = [c["name"] for c in response.get_json()]
    assert names == ["Ana", "Dan", "Vasile"]


def test_list_contacts_tie_breaker_by_id(client):
    client.post("/reset")
    client.post("/contacts", json={"name": "Ana Pop", "email": "ana1@example.com", "phone": "0711111111", "category": "work"})
    client.post("/contacts", json={"name": "Ana Pop", "email": "ana2@example.com", "phone": "0722222222", "category": "friends"})

    response = client.get("/contacts")
    assert response.status_code == 200
    ids = [c["id"] for c in response.get_json()]
    assert ids == [1, 2]


def test_list_contacts_filter_by_category(client):
    client.post("/reset")
    client.post("/contacts", json={"name": "Ana", "email": "ana@example.com", "phone": "0711111111", "category": "work"})
    client.post("/contacts", json={"name": "Dan", "email": "dan@example.com", "phone": "0722222222", "category": "friends"})

    response = client.get("/contacts?category=work")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["name"] == "Ana"
    assert data[0]["category"] == "work"


def test_list_contacts_search_by_name_case_insensitive(client):
    client.post("/reset")
    client.post("/contacts", json={"name": "Ana Pop", "email": "ana@example.com", "phone": "0711111111", "category": "work"})
    client.post("/contacts", json={"name": "Roxana Ionescu", "email": "roxana@example.com", "phone": "0722222222", "category": "work"})
    client.post("/contacts", json={"name": "Dan Ilie", "email": "dan@example.com", "phone": "0733333333", "category": "friends"})

    # Căutare 'ana' (litere mici) trebuie să găsească 'Ana Pop' și 'Roxana Ionescu'
    response = client.get("/contacts?q=ana")
    assert response.status_code == 200
    names = [c["name"] for c in response.get_json()]
    assert names == ["Ana Pop", "Roxana Ionescu"]


def test_list_contacts_combined_filter_and_search(client):
    client.post("/reset")
    client.post("/contacts", json={"name": "Ana Pop", "email": "ana@example.com", "phone": "0711111111", "category": "work"})
    client.post("/contacts", json={"name": "Roxana", "email": "roxana@example.com", "phone": "0722222222", "category": "friends"})
    client.post("/contacts", json={"name": "Mihai", "email": "mihai@example.com", "phone": "0733333333", "category": "work"})

    # Se cer ambele: category=work și q=ana -> doar 'Ana Pop'
    response = client.get("/contacts?category=work&q=ana")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["name"] == "Ana Pop"


def test_get_contact_by_id_success(client):
    client.post("/reset")
    c = {"name": "Ana Pop", "email": "ana@example.com", "phone": "0711111111", "category": "work"}
    created = client.post("/contacts", json=c).get_json()

    response = client.get(f"/contacts/{created['id']}")
    assert response.status_code == 200
    body = response.get_json()
    assert body["id"] == created["id"]
    assert body["name"] == "Ana Pop"
    assert body["email"] == "ana@example.com"


def test_get_contact_by_id_not_found(client):
    client.post("/reset")
    response = client.get("/contacts/999")
    assert response.status_code == 404
    body = response.get_json()
    assert body["error"] == "not_found"
    assert "not found" in body["message"].lower()


def test_delete_contact_success(client):
    client.post("/reset")
    c = {"name": "Ana Pop", "email": "ana@example.com", "phone": "0711111111", "category": "work"}
    created = client.post("/contacts", json=c).get_json()

    # Stergerea trebuie sa intoarca 204 FARA corp
    del_res = client.delete(f"/contacts/{created['id']}")
    assert del_res.status_code == 204
    assert del_res.data == b""

    # Un GET ulterior pe acel id trebuie sa intoarca 404
    get_res = client.get(f"/contacts/{created['id']}")
    assert get_res.status_code == 404


def test_delete_contact_not_found(client):
    client.post("/reset")
    response = client.delete("/contacts/999")
    assert response.status_code == 404
    body = response.get_json()
    assert body["error"] == "not_found"


def test_stats_empty(client):
    client.post("/reset")
    response = client.get("/stats")
    assert response.status_code == 200
    body = response.get_json()
    assert body["total"] == 0
    assert body["by_category"] == {
        "family": 0,
        "friends": 0,
        "other": 0,
        "work": 0,
    }


def test_stats_populated(client):
    client.post("/reset")
    client.post("/contacts", json={"name": "Ana", "email": "ana@example.com", "phone": "0711111111", "category": "work"})
    client.post("/contacts", json={"name": "Dan", "email": "dan@example.com", "phone": "0722222222", "category": "work"})
    client.post("/contacts", json={"name": "Mihai", "email": "mihai@example.com", "phone": "0733333333", "category": "friends"})
    client.post("/contacts", json={"name": "Elena", "email": "elena@example.com", "phone": "0744444444", "category": "family"})

    response = client.get("/stats")
    assert response.status_code == 200
    body = response.get_json()
    assert body["total"] == 4
    assert body["by_category"]["work"] == 2
    assert body["by_category"]["friends"] == 1
    assert body["by_category"]["family"] == 1
    assert body["by_category"]["other"] == 0


def test_stats_after_delete(client):
    client.post("/reset")
    c1 = client.post("/contacts", json={"name": "Ana", "email": "ana@example.com", "phone": "0711111111", "category": "work"}).get_json()
    client.post("/contacts", json={"name": "Dan", "email": "dan@example.com", "phone": "0722222222", "category": "friends"})

    # Inainte de stergere: total 2
    assert client.get("/stats").get_json()["total"] == 2

    # Dupa stergerea contactului 'Ana' (work): total devine 1, work devine 0
    client.delete(f"/contacts/{c1['id']}")
    body = client.get("/stats").get_json()
    assert body["total"] == 1
    assert body["by_category"]["work"] == 0
    assert body["by_category"]["friends"] == 1





