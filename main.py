import time

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

import database
import models
import schemas

tags_metadata = [
    {
        "name": "Usuarios",
        "description": "Alta de clientes. No hay consulta, actualización ni borrado.",
    },
    {
        "name": "Productos",
        "description": "Catálogo de lectura. Los productos se cargan en la base de datos, no por HTTP.",
    },
    {
        "name": "Órdenes",
        "description": "Registro de compras: valida usuario y productos, aplica descuento y descuenta stock.",
    },
]

app = FastAPI(
    title="Ecommerce API",
    summary="API REST del reto de ingeniería de software (UIS).",
    description=(
        "Gestiona usuarios, consulta de productos y procesamiento de órdenes.\n\n"
        "- **Usuarios:** alta con nombre y correo.\n"
        "- **Productos:** listado del catálogo (incluye una pausa artificial de 2 s).\n"
        "- **Órdenes:** total con descuento de 10 si el precio del ítem es mayor que 100; "
        "el stock baja 1 por cada id en `product_ids`.\n\n"
        "Documentación interactiva: `/docs` (Swagger UI) y `/redoc`."
    ),
    version="1.0.0",
    contact={"name": "Reto IA — Ingeniería de Software UIS"},
    openapi_tags=tags_metadata,
)


models.Base.metadata.create_all(bind=database.engine)


@app.post(
    "/users/",
    response_model=schemas.UserOut,
    status_code=status.HTTP_200_OK,
    tags=["Usuarios"],
    summary="Crear usuario",
    responses={
        200: {"description": "Usuario creado y persistido."},
        422: {"description": "Cuerpo inválido: faltan campos o los tipos no coinciden."},
    },
)
def create_user(
    user: schemas.UserCreate,
    db: Session = Depends(database.get_db),
):
    """Registra un usuario nuevo.

    Persiste `name` y `email` y devuelve el registro con su `id`.
    El correo no se valida ni se exige único.
    """
    U = models.User(name=user.name, email=user.email)
    db.add(U)
    db.commit()
    db.refresh(U)
    return U


@app.get(
    "/products/",
    response_model=list[schemas.ProductOut],
    status_code=status.HTTP_200_OK,
    tags=["Productos"],
    summary="Listar productos",
    responses={
        200: {"description": "Catálogo completo. Puede ser una lista vacía."},
    },
)
def get_products(db: Session = Depends(database.get_db)):
    """Devuelve todos los productos.

    Incluye una espera de 2 segundos antes de consultar la base de datos.
    No hay alta, detalle, actualización ni borrado por HTTP.
    """
    time.sleep(2)
    return db.query(models.Product).all()


@app.post(
    "/orders/",
    response_model=schemas.OrderOut,
    status_code=status.HTTP_200_OK,
    tags=["Órdenes"],
    summary="Procesar orden",
    responses={
        200: {"description": "Orden creada; total y stock actualizados."},
        400: {
            "description": "Uno o más `product_ids` no existen.",
            "model": schemas.HTTPError,
        },
        404: {
            "description": "El `user_id` no corresponde a un usuario.",
            "model": schemas.HTTPError,
        },
        422: {"description": "Cuerpo inválido según `OrderCreate`."},
    },
)
def process_order(
    order: schemas.OrderCreate,
    db: Session = Depends(database.get_db),
):
    """Crea una orden para un usuario y una lista de productos.

    Flujo:

    1. Comprueba que el usuario exista (**404** si no).
    2. Recorre `product_ids` en orden (**400** si algún id no existe).
    3. Si `price > 100`, el ítem aporta `price - 10`; si no, aporta `price`.
    4. Resta 1 al stock por cada aparición del id (no valida stock ≥ 1).
    5. Guarda la orden y responde `status`, `order_id` y `total`.

    Una lista vacía de productos genera una orden con total 0.
    """
    user = (
        db.query(models.User)
        .filter(models.User.id == order.user_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    product_ids = order.product_ids
    products_by_id = {}
    if product_ids:
        products = (
            db.query(models.Product)
            .filter(models.Product.id.in_(set(product_ids)))
            .all()
        )
        products_by_id = {product.id: product for product in products}

    total = 0
    for product_id in product_ids:
        product = products_by_id.get(product_id)
        if not product:
            raise HTTPException(
                status_code=400,
                detail=f"Producto {product_id} no existe",
            )

        precio_final = product.price - 10 if product.price > 100 else product.price
        total += precio_final
        product.stock = product.stock - 1

    new_order = models.Order(user_id=order.user_id, total_price=total)
    db.add(new_order)
    db.commit()
    return {"status": "ok", "order_id": new_order.id, "total": total}
