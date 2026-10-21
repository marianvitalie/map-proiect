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


