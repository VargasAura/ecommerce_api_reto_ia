# Ecommerce API — Reto IA (Ingeniería de Software UIS)

API REST con FastAPI y SQLAlchemy para usuarios, catálogo de productos y procesamiento de órdenes.

Documentación interactiva (cuando el servidor está en marcha):

- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- Esquema OpenAPI: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

## Arquitectura

El proyecto sigue una separación en capas fina, típica de una API FastAPI pequeña:

```
Cliente HTTP (navegador, curl, pytest TestClient)
        │
        ▼
   main.py  →  rutas, reglas de negocio de órdenes, OpenAPI
        │
        ├── schemas.py   contratos Pydantic (entrada/salida, ejemplos)
        ├── models.py    tablas SQLAlchemy (User, Product, Order)
        └── database.py  motor, sesión y dependencia get_db()
                │
                ▼
         MySQL (producción)  /  SQLite en memoria (pruebas)
```

| Archivo | Responsabilidad |
|---|---|
| `main.py` | Aplicación FastAPI, tres endpoints, descuento y ajuste de stock. |
| `schemas.py` | Modelos Pydantic documentados para request/response y errores. |
| `models.py` | Entidades `User`, `Product`, `Order` y relación usuario–órdenes. |
| `database.py` | Lee `DATABASE_URL`, crea el engine y entrega sesiones por request. |
| `tests/` | Pruebas con `pytest` y `TestClient`; sustituyen la BD por SQLite. |

Al importar `main.py` se ejecuta `Base.metadata.create_all`: si las tablas no existen, se crean.

### Modelo de datos

- **User:** `id`, `name`, `email`. El email no es único.
- **Product:** `id`, `name`, `price`, `stock`. No hay endpoint de alta; hay que insertarlos en la BD.
- **Order:** `id`, `user_id` (FK a `users`), `total_price`, `created_at`. No guarda el detalle de líneas; solo el total.

### Comportamiento de una orden

1. Si el usuario no existe → **404** `"Usuario no encontrado"`.
2. Si algún id de producto no existe → **400** `"Producto {id} no existe"`.
3. Precio **mayor que 100**: se cobran `price - 10`; si no, `price`.
4. Por cada aparición en `product_ids` se resta **1** al stock (no se comprueba inventario).
5. `product_ids: []` crea una orden con total **0**.

## Endpoints

| Método | Ruta | Descripción | Éxito | Errores |
|---|---|---|---|---|
| `POST` | `/users/` | Crea un usuario (`name`, `email`). | `200` + `UserOut` | `422` cuerpo inválido |
| `GET` | `/products/` | Lista el catálogo (espera 2 s). | `200` + lista de `ProductOut` | — |
| `POST` | `/orders/` | Procesa la compra. | `200` + `OrderOut` | `404` usuario, `400` producto, `422` cuerpo |

No existen `GET /users/{id}`, `POST /products/` ni detalle de orden.

## Cómo ejecutar la API

### Opción recomendada: Docker Compose

Levanta la API y un MySQL 8 con volumen persistente (`ecommerce_mysql_data`). Los datos sobreviven a `docker compose down`; se borran con `docker compose down -v`.

```bash
cp .env.example .env
docker compose up --build
```

La API queda en [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). Compose espera a que MySQL pase el *healthcheck* antes de arrancar `api`, e inyecta `DATABASE_URL` hacia el host interno `db` (no uses `localhost` dentro del contenedor).

```bash
docker compose ps
docker compose logs -f api
docker compose down          # detiene; conserva el volumen MySQL
docker compose down -v       # detiene y borra datos de MySQL
```

MySQL no se publica en el host por defecto. Para inspeccionarlo:

```yaml
# en docker-compose.yml, servicio db:
ports:
  - "3306:3306"
```

O entra al contenedor:

```bash
docker compose exec db mysql -u ecommerce -p ecommerce
```

### Requisitos (sin Docker)

- Python 3.10+ (el pin de `requirements.txt` apunta a FastAPI 0.104 / Pydantic 2.5; en Python 3.14 conviene un entorno con ruedas compatibles de Pydantic).
- Servidor MySQL accesible (solo para correr la API contra datos reales).
- Dependencias de `requirements.txt`.

### 1. Entorno virtual e instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Si `pip install -r requirements.txt` falla al compilar `pydantic-core` (Python muy reciente), instala las mismas librerías sin pin de Pydantic:

```bash
pip install fastapi uvicorn sqlalchemy pydantic python-dotenv pytest httpx pymysql
```

### 2. Variables de entorno

Copia el ejemplo y ajusta usuario, contraseña, host y base:

```bash
cp .env.example .env
```

Contenido esperado (ver `.env.example`): `MYSQL_*` para Compose y `DATABASE_URL` si corres uvicorn en el host contra `localhost`.

`database.py` carga `.env` con `python-dotenv` y **aborta el arranque** si `DATABASE_URL` no está definida.

Crea la base en MySQL si aún no existe, por ejemplo:

```sql
CREATE DATABASE ecommerce CHARACTER SET utf8mb4;
```

Las tablas `users`, `products` y `orders` se crean solas al iniciar la app.

### 3. Arranque

Desde la raíz del repositorio:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Comprueba que responde:

```bash
curl -s http://127.0.0.1:8000/docs
```

### 4. Uso rápido (curl)

Alta de usuario:

```bash
curl -s -X POST http://127.0.0.1:8000/users/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Ana Perez", "email": "ana@example.com"}'
```

Catálogo (tarda ~2 s):

```bash
curl -s http://127.0.0.1:8000/products/
```

Orden (requiere un `user_id` existente y `product_ids` que existan en la tabla `products`):

```bash
curl -s -X POST http://127.0.0.1:8000/orders/ \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "product_ids": [1, 2]}'
```

Para probar órdenes de punta a punta hace falta al menos un producto en MySQL, por ejemplo:

```sql
INSERT INTO products (name, price, stock) VALUES ('Cable USB', 25, 10), ('Monitor', 150, 5);
```

## Pruebas

Las pruebas unitarias están en `tests/` y usan **pytest** + **TestClient**. No necesitan MySQL: `conftest.py` fija `DATABASE_URL` a SQLite en memoria **antes** de importar la app, sustituye `get_db` y anula el `sleep(2)` de `GET /products/`.

Cada prueba deja la base vacía (create/drop de tablas). Los productos de ejemplo se insertan por ORM porque no hay `POST /products/`.

### Ejecutar el suite

```bash
source .venv/bin/activate
pytest -v
```

Otras formas útiles:

```bash
pytest -v tests/test_users.py
pytest -v tests/test_products.py
pytest -v tests/test_orders.py
pytest -q
```

Se esperan **28** pruebas en verde.

### Qué cubre cada archivo

**`tests/test_users.py`**

| Prueba | Valida |
|---|---|
| `test_create_user_success` | Alta correcta con `id`, nombre y email. |
| `test_create_user_missing_email` / `_missing_name` / `_empty_body` | Campos obligatorios ausentes → 422. |
| `test_create_user_wrong_types` | Tipos incorrectos → 422. |
| `test_create_user_empty_strings` | Strings vacíos son aceptados. |
| `test_create_user_duplicate_email_allowed` | Emails repetidos permitidos. |
| `test_get_user_endpoint_does_not_exist` | No hay `GET /users/{id}`. |

**`tests/test_products.py`**

| Prueba | Valida |
|---|---|
| `test_list_products_empty` | Lista vacía. |
| `test_list_products_success` | Serializa nombre, precio y stock. |
| `test_get_single_product_does_not_exist` | No hay `GET /products/{id}`. |
| `test_create_product_via_http_not_available` | No hay `POST /products/`. |
| `test_list_products_zero_and_negative_stock` | Stock 0 y negativo se listan. |
| `test_list_products_price_boundary` | Precios 0, 100 y 100.01. |

**`tests/test_orders.py`**

| Prueba | Valida |
|---|---|
| `test_create_order_success_without_discount` | Precio ≤ 100 sin descuento; stock −1. |
| `test_create_order_success_with_discount` | Precio > 100 resta 10. |
| `test_create_order_multiple_products` | Suma de varios ítems. |
| `test_create_order_user_not_found` | Usuario inexistente → 404. |
| `test_create_order_product_not_found` | Producto inexistente → 400. |
| `test_create_order_mixed_existing_and_missing_product` | Un id inválido tumba la orden. |
| `test_create_order_missing_fields` / `_invalid_types` / `_product_ids_with_strings` | 422. |
| `test_create_order_empty_product_list` | Lista vacía → total 0. |
| `test_create_order_duplicate_product_ids` | Id repetido se cobra y descuenta dos veces. |
| `test_create_order_price_exactly_100_has_no_discount` | Umbral estricto `> 100`. |
| `test_create_order_price_just_over_100_gets_discount` | 100.01 sí descuenta. |
| `test_create_order_zero_stock_still_decrements` | Stock 0 queda en −1. |

Las pruebas **no** levantan uvicorn ni tocan la base configurada en `.env`. Para una prueba manual de la API en marcha, usa `/docs` o los `curl` de la sección anterior.
