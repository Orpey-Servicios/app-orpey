"""
Router de Notas - Endpoints para gestionar notas internas de órdenes.

Cada nota interna queda registrada con:
- Quién la escribió (creado_por)
- Cuándo se escribió (created_at)
- El contenido

Endpoints:
- POST /api/ordenes/{orden_id}/notas  → Agregar una nota
- GET  /api/ordenes/{orden_id}/notas  → Listar notas de una orden
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.models.models import OrdenServicio, NotaOrden
from src.schemas.schemas import NotaCreate, NotaResponse

router = APIRouter(
    prefix="/api/ordenes",
    tags=["Notas Internas"],
)


@router.post(
    "/{orden_id}/notas",
    response_model=NotaResponse,
    status_code=201,
    summary="Agregar una nota interna a una orden",
    description="Agrega una nota interna con registro de autor y fecha."
)
async def agregar_nota(
    orden_id: int,
    datos: NotaCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Agrega una nota interna a una orden.

    **¿Qué hace este endpoint?**
    1. Verifica que la orden existe
    2. Crea la nota con el contenido, el autor y la fecha actual
    3. Devuelve la nota creada
    """
    # Verificar que la orden existe
    result = await db.execute(
        select(OrdenServicio).where(OrdenServicio.id == orden_id)
    )
    orden = result.scalar_one_or_none()

    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    # Crear la nota
    nueva_nota = NotaOrden(
        orden_id=orden_id,
        contenido=datos.contenido,
        creado_por=datos.creado_por,
    )
    db.add(nueva_nota)

    await db.commit()
    await db.refresh(nueva_nota)

    return nueva_nota


@router.get(
    "/{orden_id}/notas",
    response_model=List[NotaResponse],
    summary="Listar notas internas de una orden",
    description="Devuelve el historial de notas internas de una orden."
)
async def listar_notas(
    orden_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Lista todas las notas internas de una orden,
    ordenadas de la más reciente a la más antigua.
    """
    result = await db.execute(
        select(NotaOrden)
        .where(NotaOrden.orden_id == orden_id)
        .order_by(NotaOrden.created_at.desc())
    )
    return result.scalars().all()
