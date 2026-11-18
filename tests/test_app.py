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


def test_official_theme_sequence(client):
    """Verifica exact secventa de comenzi din enuntul oficial al Temei 1."""
    # Reset initial obligatoriu
    assert client.post("/reset").status_code == 204

    # 1. Adaugati un contact (Ana Pop, ana@example.com, work) -> 201 Created si id 1
    r1 = client.post(
        "/contacts",
        json={
            "name": "Ana Pop",
            "email": "ana@example.com",
            "phone": "0722334455",
            "category": "work",
        },
    )
    assert r1.status_code == 201
    b1 = r1.get_json()
    assert b1["id"] == 1
    assert b1["name"] == "Ana Pop"
    assert b1["email"] == "ana@example.com"

    # 2. Acelasi email, scris altfel -> 409 Conflict, nu 201
    r2 = client.post(
        "/contacts",
        json={
            "name": "Ana P.",
            "email": "Ana@Example.COM",
            "phone": "0733445566",
            "category": "friends",
        },
    )
    assert r2.status_code == 409
    assert r2.get_json()["error"] == "conflict"

    # 3. Cautare si filtru in aceeasi cerere -> se aplica amandoua
    r3 = client.get("/contacts?category=work&q=ana")
    assert r3.status_code == 200
    b3 = r3.get_json()
    assert len(b3) == 1
    assert b3[0]["id"] == 1
    assert b3[0]["name"] == "Ana Pop"

    # 4. Un id inexistent -> 404, cu error "not_found"
    r4 = client.get("/contacts/999")
    assert r4.status_code == 404
    assert r4.get_json()["error"] == "not_found"


def test_email_preserves_case_but_normalizes_comparison(client):
    """Emailul pastreaza caracterele originale la afisare, dar se compara normalizat."""
    client.post("/reset")
    user_email = "Marian.Vitalie@Example.COM"
    r = client.post(
        "/contacts",
        json={
            "name": "Vitalie Marian",
            "email": user_email,
            "phone": "0799887766",
            "category": "other",
        },
    )
    assert r.status_code == 201
    cid = r.get_json()["id"]

    # Verificam ca la citire forma originala a fost pastrata intacta
    fetched = client.get(f"/contacts/{cid}").get_json()
    assert fetched["email"] == user_email

    # Orice alta varianta de casing trebuie respinsa cu 409
    assert client.post(
        "/contacts",
        json={
            "name": "Alt Nume",
            "email": "marian.vitalie@example.com",
            "phone": "0711223344",
            "category": "friends",
        },
    ).status_code == 409


def test_delete_contact_twice_returns_404(client):
    """O a doua stergere pe aceeasi resursa trebuie sa esueze cu 404."""
    client.post("/reset")
    r = client.post(
        "/contacts",
        json={
            "name": "Ion",
            "email": "ion@example.com",
            "phone": "0711111111",
            "category": "friends",
        },
    )
    cid = r.get_json()["id"]

    # Prima stergere reuseste (204)
    assert client.delete(f"/contacts/{cid}").status_code == 204

    # A doua stergere esueaza (404)
    r2 = client.delete(f"/contacts/{cid}")
    assert r2.status_code == 404
    assert r2.get_json()["error"] == "not_found"


def test_list_contacts_no_matches_returns_empty_list(client):
    """Daca filtrele nu gasesc nimic, raspunsul este o lista goala cu codul 200."""
    client.post("/reset")
    client.post(
        "/contacts",
        json={
            "name": "George",
            "email": "george@example.com",
            "phone": "0722334455",
            "category": "work",
        },
    )

    r1 = client.get("/contacts?q=cineva_care_nu_exista")
    assert r1.status_code == 200
    assert r1.get_json() == []

    r2 = client.get("/contacts?category=family")
    assert r2.status_code == 200
    assert r2.get_json() == []


def test_reset_restarts_id_sequence_to_one(client):
    """Dupa /reset, alocarea id-urilor porneste din nou de la 1."""
    client.post("/reset")
    c1 = client.post(
        "/contacts",
        json={"name": "A", "email": "a@ex.com", "phone": "0711111111", "category": "work"},
    ).get_json()
    c2 = client.post(
        "/contacts",
        json={"name": "B", "email": "b@ex.com", "phone": "0722222222", "category": "work"},
    ).get_json()
    assert c1["id"] == 1
    assert c2["id"] == 2

    # Reset
    assert client.post("/reset").status_code == 204

    # Urmatorul contact creat trebuie sa aiba din nou id 1
    c3 = client.post(
        "/contacts",
        json={"name": "C", "email": "c@ex.com", "phone": "0733333333", "category": "work"},
    ).get_json()
    assert c3["id"] == 1


def test_create_contact_malformed_json_syntax(client):
    """Trimiterea unui JSON invalid sintactic este tratata cu 400 validation."""
    response = client.post(
        "/contacts",
        data='{"name": "Ana", "email": "ana@example.com"',  # lipseste acolada de inchidere
        content_type="application/json",
    )
    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "validation"
    assert "json" in body["message"].lower()


def test_admin_stats_unauthorized_without_credentials(client, monkeypatch):
    monkeypatch.setenv("ADMIN_USER", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret123")

    response = client.get("/admin/stats")
    assert response.status_code == 401
    body = response.get_json()
    assert body["error"] == "unauthorized"


def test_admin_stats_unauthorized_with_wrong_credentials(client, monkeypatch):
    monkeypatch.setenv("ADMIN_USER", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret123")

    import base64
    wrong_token = base64.b64encode(b"admin:wrong_password").decode("ascii")
    response = client.get(
        "/admin/stats",
        headers={"Authorization": f"Basic {wrong_token}"},
    )
    assert response.status_code == 401
    assert response.get_json()["error"] == "unauthorized"


def test_admin_stats_unauthorized_when_env_not_configured(client, monkeypatch):
    monkeypatch.delenv("ADMIN_USER", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)

    import base64
    token = base64.b64encode(b"admin:secret123").decode("ascii")
    response = client.get(
        "/admin/stats",
        headers={"Authorization": f"Basic {token}"},
    )
    assert response.status_code == 401
    assert response.get_json()["error"] == "unauthorized"


def test_admin_stats_authorized_success(client, monkeypatch):
    monkeypatch.setenv("ADMIN_USER", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret123")

    client.post("/reset")
    client.post(
        "/contacts",
        json={"name": "Ana", "email": "ana@example.com", "phone": "0711111111", "category": "work"},
    )

    import base64
    valid_token = base64.b64encode(b"admin:secret123").decode("ascii")
    response = client.get(
        "/admin/stats",
        headers={"Authorization": f"Basic {valid_token}"},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["total"] == 1
    assert body["by_category"]["work"] == 1
    assert body["by_category"]["friends"] == 0







