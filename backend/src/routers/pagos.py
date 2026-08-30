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
from src.models.models import OrdenServicio, PagoOrden, EquipoOrden, MovimientoCaja, Usuario
from src.schemas.schemas import PagoCreate, PagoResponse
from src.services import caja_service
from src.utils.auth import get_current_user

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
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Registra un pago para una orden.

    **¿Qué hace este endpoint?**
    1. Verifica que la orden existe
    2. Verifica que hay una caja abierta (regla de negocio: todo cobro pasa por caja)
    3. Crea un registro en pagos_orden (historial)
    4. Crea el movimiento de caja 'pago_orden' (MISMA transacción, atómico)
    5. Suma el monto al campo abono de la orden
    6. Devuelve el pago registrado
    """
    # REGLA DE NEGOCIO: sin caja abierta no se registran pagos
    caja = await caja_service.obtener_caja_abierta(db)
    if not caja:
        raise HTTPException(
            status_code=400,
            detail="No hay caja abierta. Abre la caja en la sección Caja antes de registrar pagos.",
        )

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

    # Movimiento de caja 'pago_orden': MISMA transacción que el pago (atómico).
    # referencia_id se asigna tras el flush (pago.id). Nunca pago sin movimiento.
    movimiento = MovimientoCaja(
        caja_id=caja.id,
        tipo="ingreso",
        origen="pago_orden",
        monto=monto,
        metodo_pago=nuevo_pago.metodo_pago,
        creado_por=current_user.id,
    )
    db.add(movimiento)

    # flush: asigna id al pago y valida FKs antes del commit
    await db.flush()
    movimiento.referencia_id = nuevo_pago.id

    # Sumar el monto al abono actual de la orden
    orden.abono = nuevo_abono

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
