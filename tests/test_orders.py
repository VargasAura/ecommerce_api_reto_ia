import pytest

from models import Product


def test_create_order_success_without_discount(client, sample_user, sample_products):
    """Caso exitoso: producto <= 100 no aplica descuento; se descuenta 1 de stock."""
    cheap, _expensive = sample_products

    response = client.post(
        "/orders/",
        json={"user_id": sample_user.id, "product_ids": [cheap.id]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["order_id"] >= 1
    assert body["total"] == 25.0

    catalog = client.get("/products/").json()
    stock_after = next(item["stock"] for item in catalog if item["id"] == cheap.id)
    assert stock_after == 9


def test_create_order_success_with_discount(client, sample_user, sample_products):
    """Caso exitoso: precio > 100 resta 10 al total (150 -> 140)."""
    _cheap, expensive = sample_products

    response = client.post(
        "/orders/",
        json={"user_id": sample_user.id, "product_ids": [expensive.id]},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 140.0


def test_create_order_multiple_products(client, sample_user, sample_products):
    """Caso exitoso: suma precios (con y sin descuento) de varios productos."""
    cheap, expensive = sample_products

    response = client.post(
        "/orders/",
        json={"user_id": sample_user.id, "product_ids": [cheap.id, expensive.id]},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 165.0


def test_create_order_user_not_found(client, sample_products):
    """Recurso inexistente: user_id que no está en la BD responde 404."""
    cheap, _ = sample_products

    response = client.post(
        "/orders/",
        json={"user_id": 9999, "product_ids": [cheap.id]},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Usuario no encontrado"


def test_create_order_product_not_found(client, sample_user):
    """Recurso inexistente: product_id desconocido responde 400."""
    response = client.post(
        "/orders/",
        json={"user_id": sample_user.id, "product_ids": [8888]},
    )

    assert response.status_code == 400
    assert "8888" in response.json()["detail"]


def test_create_order_mixed_existing_and_missing_product(
    client, sample_user, sample_products
):
    """Recurso inexistente: si un id de la lista no existe, la orden falla."""
    cheap, _ = sample_products

    response = client.post(
        "/orders/",
        json={"user_id": sample_user.id, "product_ids": [cheap.id, 7777]},
    )

    assert response.status_code == 400
    assert "7777" in response.json()["detail"]


def test_create_order_missing_fields(client):
    """Datos inválidos: sin user_id ni product_ids el esquema OrderCreate falla."""
    response = client.post("/orders/", json={})

    assert response.status_code == 422


def test_create_order_invalid_types(client):
    """Datos inválidos: user_id no es int y product_ids no es lista de int."""
    response = client.post(
        "/orders/",
        json={"user_id": "uno", "product_ids": "1,2"},
    )

    assert response.status_code == 422


def test_create_order_product_ids_with_strings(client, sample_user):
    """Datos inválidos: elementos de product_ids deben ser enteros."""
    response = client.post(
        "/orders/",
        json={"user_id": sample_user.id, "product_ids": ["abc"]},
    )

    assert response.status_code == 422


def test_create_order_empty_product_list(client, sample_user):
    """Caso límite: lista vacía crea orden con total 0 (no hay validación min_items)."""
    response = client.post(
        "/orders/",
        json={"user_id": sample_user.id, "product_ids": []},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["total"] == 0


def test_create_order_duplicate_product_ids(client, sample_user, sample_products):
    """Caso límite: el mismo id repetido suma dos veces y resta stock dos veces."""
    cheap, _ = sample_products

    response = client.post(
        "/orders/",
        json={"user_id": sample_user.id, "product_ids": [cheap.id, cheap.id]},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 50.0

    catalog = client.get("/products/").json()
    stock_after = next(item["stock"] for item in catalog if item["id"] == cheap.id)
    assert stock_after == 8


def test_create_order_price_exactly_100_has_no_discount(client, sample_user, db):
    """Caso límite: price > 100 es estricto; 100.0 no recibe los 10 de descuento."""
    product = Product(name="Umbral", price=100.0, stock=2)
    db.add(product)
    db.commit()
    db.refresh(product)

    response = client.post(
        "/orders/",
        json={"user_id": sample_user.id, "product_ids": [product.id]},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 100.0


def test_create_order_price_just_over_100_gets_discount(client, sample_user, db):
    """Caso límite: 100.01 sí aplica descuento (total 90.01)."""
    product = Product(name="Justo encima", price=100.01, stock=2)
    db.add(product)
    db.commit()
    db.refresh(product)

    response = client.post(
        "/orders/",
        json={"user_id": sample_user.id, "product_ids": [product.id]},
    )

    assert response.status_code == 200
    assert response.json()["total"] == pytest.approx(90.01)


def test_create_order_zero_stock_still_decrements(client, sample_user, db):
    """Caso límite: stock 0 no se valida; el pedido sigue y deja stock negativo."""
    product = Product(name="Agotado", price=20.0, stock=0)
    db.add(product)
    db.commit()
    db.refresh(product)

    response = client.post(
        "/orders/",
        json={"user_id": sample_user.id, "product_ids": [product.id]},
    )

    assert response.status_code == 200
    catalog = client.get("/products/").json()
    stock_after = next(item["stock"] for item in catalog if item["id"] == product.id)
    assert stock_after == -1
