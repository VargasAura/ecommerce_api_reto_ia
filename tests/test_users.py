def test_create_user_success(client):
    """Caso exitoso: POST /users/ persiste nombre y email y devuelve un id."""
    response = client.post(
        "/users/",
        json={"name": "Carlos Ruiz", "email": "carlos@example.com"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] >= 1
    assert body["name"] == "Carlos Ruiz"
    assert body["email"] == "carlos@example.com"


def test_create_user_missing_email(client):
    """Datos inválidos: falta email, FastAPI/Pydantic debe rechazar con 422."""
    response = client.post("/users/", json={"name": "Sin Email"})

    assert response.status_code == 422


def test_create_user_missing_name(client):
    """Datos inválidos: falta name, el cuerpo no cumple UserCreate."""
    response = client.post("/users/", json={"email": "solo@example.com"})

    assert response.status_code == 422


def test_create_user_empty_body(client):
    """Datos inválidos: cuerpo vacío no incluye los campos requeridos."""
    response = client.post("/users/", json={})

    assert response.status_code == 422


def test_create_user_wrong_types(client):
    """Datos inválidos: name y email no son strings."""
    response = client.post("/users/", json={"name": 123, "email": ["no-es-email"]})

    assert response.status_code == 422


def test_create_user_empty_strings(client):
    """Caso límite: strings vacíos son válidos para Pydantic (no hay min_length)."""
    response = client.post("/users/", json={"name": "", "email": ""})

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == ""
    assert body["email"] == ""


def test_create_user_duplicate_email_allowed(client):
    """Caso límite: el modelo no declara unique en email; se pueden repetir."""
    payload = {"name": "Uno", "email": "mismo@example.com"}
    first = client.post("/users/", json=payload)
    second = client.post("/users/", json={"name": "Dos", "email": "mismo@example.com"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] != second.json()["id"]


def test_get_user_endpoint_does_not_exist(client, sample_user):
    """Recurso inexistente: no hay GET /users/{id}; debe responder 404/405."""
    response = client.get(f"/users/{sample_user.id}")

    assert response.status_code in (404, 405)
