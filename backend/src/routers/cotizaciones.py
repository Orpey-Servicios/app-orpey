"""
Router de Cotizaciones - Endpoints para gestionar cotizaciones/presupuestos.

Endpoints:
- POST /api/cotizaciones          → Crear cotización
- GET /api/cotizaciones           → Listar cotizaciones
- GET /api/cotizaciones/{id}      → Ver cotización
- PUT /api/cotizaciones/{id}      → Actualizar cotización
- POST /api/cotizaciones/{id}/aprobar → Aprobar y convertir en orden
"""

from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.models.models import Cotizacion, Cliente, EstadoCotizacion
from src.schemas.schemas import CotizacionCreate, CotizacionUpdate, CotizacionResponse

router = APIRouter(
    prefix="/api/cotizaciones",
    tags=["Cotizaciones"]
)


@router.post("/", response_model=CotizacionResponse, status_code=201)
async def crear_cotizacion(
    cotizacion: CotizacionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Crea una cotización nueva."""
    result = await db.execute(select(Cliente).where(Cliente.id == cotizacion.cliente_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    db_cotizacion = Cotizacion(**cotizacion.model_dump())
    db.add(db_cotizacion)
    await db.commit()
    await db.refresh(db_cotizacion)
    return db_cotizacion


@router.get("/", response_model=List[CotizacionResponse])
async def listar_cotizaciones(
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    cliente_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Lista todas las cotizaciones con filtros opcionales."""
    query = select(Cotizacion)

    if estado:
        query = query.where(Cotizacion.estado == EstadoCotizacion(estado))
    if cliente_id:
        query = query.where(Cotizacion.cliente_id == cliente_id)

    query = query.order_by(Cotizacion.id.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{cotizacion_id}", response_model=CotizacionResponse)
async def obtener_cotizacion(
    cotizacion_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene una cotización por ID."""
    result = await db.execute(select(Cotizacion).where(Cotizacion.id == cotizacion_id))
    cotizacion = result.scalar_one_or_none()

    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")

    return cotizacion


@router.put("/{cotizacion_id}", response_model=CotizacionResponse)
async def actualizar_cotizacion(
    cotizacion_id: int,
    datos: CotizacionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Actualiza una cotización."""
    result = await db.execute(select(Cotizacion).where(Cotizacion.id == cotizacion_id))
    cotizacion = result.scalar_one_or_none()

    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")

    datos_dict = datos.model_dump(exclude_unset=True)
    for campo, valor in datos_dict.items():
        setattr(cotizacion, campo, valor)

    await db.commit()
    await db.refresh(cotizacion)
    return cotizacion


@router.post("/{cotizacion_id}/aprobar", response_model=CotizacionResponse)
async def aprobar_cotizacion(
    cotizacion_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Aprueba una cotización.
    Cambia el estado a 'aprobada' y registra la fecha de aprobación.
    En el futuro, esto puede crear automáticamente una orden de servicio.
    """
    result = await db.execute(select(Cotizacion).where(Cotizacion.id == cotizacion_id))
    cotizacion = result.scalar_one_or_none()

    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")

    cotizacion.estado = EstadoCotizacion.aprobada
    cotizacion.fecha_aprobacion = datetime.now()

    await db.commit()
    await db.refresh(cotizacion)
    return cotizacion
