"""
Router de Pagos - Endpoints para gestionar pagos/abonos de órdenes.

Cada pago que registra el cliente:
1. Se guarda en la tabla pagos_orden (historial)
2. Se suma al campo abono de la orden

Endpoints:
- POST /api/ordenes/{orden_id}/pagos  → Registrar un pago
- GET  /api/ordenes/{orden_id}/pagos  → Listar historial de pagos
"""

from decimal import Decimal
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.models.models import OrdenServicio, PagoOrden, EquipoOrden
from src.schemas.schemas import PagoCreate, PagoResponse

router = APIRouter(
    prefix="/api/ordenes",
    tags=["Pagos"],
)


@router.post(
    "/{orden_id}/pagos",
    response_model=PagoResponse,
    status_code=201,
    summary="Registrar un pago en una orden",
    description="Registra un pago/abono del cliente y lo suma al campo abono de la orden."
)
async def registrar_pago(
    orden_id: int,
    datos: PagoCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Registra un pago para una orden.

    **¿Qué hace este endpoint?**
    1. Verifica que la orden existe
    2. Crea un registro en pagos_orden (historial)
    3. Suma el monto al campo abono de la orden
    4. Devuelve el pago registrado
    """
    # Verificar que la orden existe
    result = await db.execute(
        select(OrdenServicio).where(OrdenServicio.id == orden_id)
    )
    orden = result.scalar_one_or_none()

    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    # Auto-asignar equipo_id cuando la orden tiene un solo equipo
    # y el pago no fue asignado a ninguno (prevención del bug de pagos sin asignar)
    equipo_id_final = datos.equipo_id
    if not equipo_id_final:
        equipos_result = await db.execute(
            select(EquipoOrden).where(EquipoOrden.orden_id == orden_id)
        )
        equipos = equipos_result.scalars().all()
        if len(equipos) == 1:
            equipo_id_final = equipos[0].id

    # Validar que el pago no exceda el monto total de la orden
    monto = Decimal(str(datos.monto))
    abono_actual = orden.abono or Decimal("0.00")
    total_orden = orden.total_orden or Decimal("0.00")
    nuevo_abono = abono_actual + monto

    if nuevo_abono > total_orden:
        saldo_pendiente = total_orden - abono_actual
        raise HTTPException(
            status_code=400,
            detail=f"El pago de ${monto:.2f} excede el saldo pendiente de ${saldo_pendiente:.2f}. "
                   f"El abono total (${nuevo_abono:.2f}) no puede superar el total de la orden (${total_orden:.2f}). "
                   f"Para agregar un abono mayor, primero edita el monto total de la orden."
        )

    # Crear el registro de pago
    nuevo_pago = PagoOrden(
        orden_id=orden_id,
        monto=monto,
        metodo_pago=datos.metodo_pago,
        equipo_id=equipo_id_final,
    )
    db.add(nuevo_pago)

    # Sumar el monto al abono actual de la orden
    orden.abono = (orden.abono or Decimal("0.00")) + monto

    await db.commit()
    await db.refresh(nuevo_pago)

    # Cargar la relación equipo para el response
    await db.refresh(nuevo_pago, attribute_names=["equipo"])

    return PagoResponse.from_orm_with_equipo(nuevo_pago)


@router.get(
    "/{orden_id}/pagos",
    response_model=List[PagoResponse],
    summary="Listar pagos de una orden",
    description="Devuelve el historial de pagos registrados para una orden."
)
async def listar_pagos(
    orden_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Lista todos los pagos registrados para una orden,
    ordenados del más reciente al más antiguo.
    """
    result = await db.execute(
        select(PagoOrden)
        .options(selectinload(PagoOrden.equipo))
        .where(PagoOrden.orden_id == orden_id)
        .order_by(PagoOrden.created_at.desc())
    )
    pagos = result.scalars().all()
    return [PagoResponse.from_orm_with_equipo(p) for p in pagos]
