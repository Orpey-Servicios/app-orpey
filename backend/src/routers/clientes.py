"""
Router de Clientes - Endpoints para gestionar clientes.

Un router es un grupo de endpoints relacionados.
FastAPI los agrupa por tema: /clientes, /ordenes, etc.

Endpoints disponibles:
- POST /api/clientes        → Crear cliente nuevo
- GET /api/clientes         → Listar todos los clientes
- GET /api/clientes/{id}    → Ver un cliente específico
- PUT /api/clientes/{id}    → Actualizar cliente
- DELETE /api/clientes/{id} → Eliminar cliente
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.models.models import Cliente
from src.schemas.schemas import (
    ClienteCreate, ClienteUpdate, ClienteResponse
)

router = APIRouter(
    prefix="/api/clientes",  # Todas las rutas empiezan con /api/clientes
    tags=["Clientes"]        # Agrupa estos endpoints en Swagger UI
)


@router.post(
    "/",
    response_model=ClienteResponse,
    status_code=201,
    summary="Crear un nuevo cliente",
    description="Registra un cliente nuevo en el sistema. El nombre y apellido se capitalizan automáticamente."
)
async def crear_cliente(
    cliente: ClienteCreate,  # Pydantic valida los datos automáticamente
    db: AsyncSession = Depends(get_db)  # Inyecta la sesión de BD
):
    """
    Crea un cliente nuevo.

    **Ejemplo de uso:**
    ```json
    {
        "nombre": "gerardo",
        "apellido": "zumba",
        "telefono": "0985983416",
        "cedula_ruc": "0903803575"
    }
    ```
    El nombre se convierte automáticamente a "Gerardo" y apellido a "Zumba".
    """
    db_cliente = Cliente(**cliente.model_dump())
    db.add(db_cliente)
    await db.commit()
    await db.refresh(db_cliente)
    return db_cliente


@router.get(
    "/",
    response_model=List[ClienteResponse],
    summary="Listar todos los clientes",
    description="Devuelve una lista de todos los clientes. Se pueden filtrar por nombre."
)
async def listar_clientes(
    buscar: str = Query(None, description="Buscar por nombre o apellido"),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista todos los clientes.
    Si se pasa ?buscar=gerardo, filtra por nombre o apellido.
    """
    query = select(Cliente).where(Cliente.activo == True)

    if buscar:
        # Búsqueda insensible a mayúsculas/minúsculas
        query = query.where(
            Cliente.nombre.ilike(f"%{buscar}%") |
            Cliente.apellido.ilike(f"%{buscar}%")
        )

    query = query.order_by(Cliente.nombre)
    result = await db.execute(query)
    return result.scalars().all()


@router.get(
    "/{cliente_id}",
    response_model=ClienteResponse,
    summary="Obtener un cliente por ID",
    description="Devuelve los datos de un cliente específico."
)
async def obtener_cliente(
    cliente_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene un cliente por su ID.
    Si no existe, devuelve error 404.
    """
    result = await db.execute(select(Cliente).where(Cliente.id == cliente_id))
    cliente = result.scalar_one_or_none()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    return cliente


@router.put(
    "/{cliente_id}",
    response_model=ClienteResponse,
    summary="Actualizar un cliente",
    description="Actualiza los datos de un cliente existente. Solo los campos enviados se actualizan."
)
async def actualizar_cliente(
    cliente_id: int,
    datos: ClienteUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Actualiza un cliente.
    Solo los campos que envíes se actualizan, los demás se mantienen igual.
    """
    result = await db.execute(select(Cliente).where(Cliente.id == cliente_id))
    cliente = result.scalar_one_or_none()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Actualiza solo los campos que se enviaron (no None)
    datos_dict = datos.model_dump(exclude_unset=True)
    for campo, valor in datos_dict.items():
        setattr(cliente, campo, valor)

    await db.commit()
    await db.refresh(cliente)
    return cliente


@router.delete(
    "/{cliente_id}",
    status_code=204,
    summary="Eliminar un cliente",
    description="Elimina un cliente del sistema (desactivación lógica)."
)
async def eliminar_cliente(
    cliente_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Elimina un cliente (lo desactiva, no lo borra de la BD).
    Esto mantiene el historial de órdenes intacto.
    """
    result = await db.execute(select(Cliente).where(Cliente.id == cliente_id))
    cliente = result.scalar_one_or_none()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Desactivación lógica en lugar de borrado físico
    cliente.activo = False
    await db.commit()
    return None
