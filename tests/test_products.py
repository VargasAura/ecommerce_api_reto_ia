from models import Product


def test_list_products_empty(client):
    """Caso exitoso (catálogo vacío): GET /products/ devuelve lista vacía."""
    response = client.get("/products/")

    assert response.status_code == 200
    assert response.json() == []


def test_list_products_success(client, sample_products):
    """Caso exitoso: lista todos los productos sembrados con precio y stock."""
    cheap, expensive = sample_products

    response = client.get("/products/")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    by_id = {item["id"]: item for item in body}
    assert by_id[cheap.id]["name"] == "Cable USB"
    assert by_id[cheap.id]["price"] == 25.0
    assert by_id[cheap.id]["stock"] == 10
    assert by_id[expensive.id]["name"] == "Monitor"
    assert by_id[expensive.id]["price"] == 150.0


def test_get_single_product_does_not_exist(client, sample_products):
    """Recurso inexistente: no hay GET /products/{id}."""
    response = client.get("/products/1")

    assert response.status_code in (404, 405)


def test_create_product_via_http_not_available(client):
    """Recurso inexistente: no hay POST /products/; ProductCreate no está expuesto."""
    response = client.post(
        "/products/",
        json={"name": "Mouse", "price": 20.0, "stock": 3},
    )

    assert response.status_code in (404, 405)


def test_list_products_zero_and_negative_stock(client, db):
    """Caso límite: stock 0 y negativo se listan; el GET no filtra inventario."""
    db.add_all(
        [
            Product(name="Agotado", price=10.0, stock=0),
            Product(name="Deuda stock", price=10.0, stock=-2),
        ]
    )
    db.commit()

    response = client.get("/products/")

    assert response.status_code == 200
    stocks = {item["name"]: item["stock"] for item in response.json()}
    assert stocks["Agotado"] == 0
    assert stocks["Deuda stock"] == -2


def test_list_products_price_boundary(client, db):
    """Caso límite: precios 0, 100 y 100.01 se serializan (el descuento es en órdenes)."""
    db.add_all(
        [
            Product(name="Gratis", price=0.0, stock=1),
            Product(name="Umbral", price=100.0, stock=1),
            Product(name="Sobre umbral", price=100.01, stock=1),
        ]
    )
    db.commit()

    response = client.get("/products/")

    assert response.status_code == 200
    prices = {item["name"]: item["price"] for item in response.json()}
    assert prices["Gratis"] == 0.0
    assert prices["Umbral"] == 100.0
    assert prices["Sobre umbral"] == 100.01
