from typing import List

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    """Cuerpo de creación de un usuario."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"name": "Ana Perez", "email": "ana@example.com"},
            ]
        }
    )

    name: str = Field(
        ...,
        description="Nombre visible del usuario.",
        examples=["Ana Perez"],
    )
    email: str = Field(
        ...,
        description="Correo electrónico. El modelo no exige formato ni unicidad.",
        examples=["ana@example.com"],
    )


class UserOut(BaseModel):
    """Usuario persistido que devuelve POST /users/."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Identificador autogenerado.", examples=[1])
    name: str = Field(..., description="Nombre del usuario.", examples=["Ana Perez"])
    email: str = Field(
        ...,
        description="Correo electrónico almacenado.",
        examples=["ana@example.com"],
    )


class ProductCreate(BaseModel):
    """Esquema de producto para altas. Hoy no hay endpoint POST de productos."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"name": "Monitor", "price": 150.0, "stock": 5},
            ]
        }
    )

    name: str = Field(..., description="Nombre del producto.", examples=["Monitor"])
    price: float = Field(
        ...,
        description="Precio unitario. Si es mayor que 100, la orden aplica 10 de descuento.",
        examples=[150.0],
    )
    stock: int = Field(..., description="Unidades disponibles.", examples=[5])


class ProductOut(BaseModel):
    """Producto que lista GET /products/."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Identificador del producto.", examples=[1])
    name: str = Field(..., description="Nombre del producto.", examples=["Cable USB"])
    price: float = Field(..., description="Precio unitario actual.", examples=[25.0])
    stock: int = Field(..., description="Stock actual.", examples=[10])


class OrderCreate(BaseModel):
    """Cuerpo para registrar una orden.

    `product_ids` es una lista de identificadores: cada aparición cuenta como
    una unidad. No hay campo de cantidad por producto.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"user_id": 1, "product_ids": [1, 2]},
            ]
        }
    )

    user_id: int = Field(
        ...,
        description="Id del usuario que realiza la compra. Debe existir en la base de datos.",
        examples=[1],
    )
    product_ids: List[int] = Field(
        ...,
        description=(
            "Ids de productos a incluir. Los ids repetidos se cobran y descuentan "
            "del stock tantas veces como aparezcan."
        ),
        examples=[[1, 2]],
    )


class OrderOut(BaseModel):
    """Respuesta de una orden procesada."""

    status: str = Field(..., description="Resultado de la operación.", examples=["ok"])
    order_id: int = Field(..., description="Identificador de la orden creada.", examples=[1])
    total: float = Field(
        ...,
        description="Suma de precios. Cada ítem con precio > 100 resta 10.",
        examples=[165.0],
    )


class HTTPError(BaseModel):
    """Cuerpo estándar de error de FastAPI (`HTTPException`)."""

    detail: str = Field(..., examples=["Usuario no encontrado"])
