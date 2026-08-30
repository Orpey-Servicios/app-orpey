"""
Router de Caja - Endpoints para el módulo de caja/arqueo diario.

Funcionalidades:
- POST /api/caja/abrir       → Abrir la caja del día (apertura única)
- POST /api/caja/cerrar      → Cerrar la caja (arqueo con expected vs closing)
- GET  /api/caja/actual      → Caja abierta actual (o null)
- POST /api/caja/movimientos → Registrar ingreso/egreso manual
- GET  /api/caja/movimientos → Listar movimientos de la caja actual
- GET  /api/caja/historial   → Historial de cajas (abiertas y cerradas)
- GET  /api/caja/resumen-dia → Resumen financiero del día (Dashboard)

REGLA DE NEGOCIO: todo cobro (pago de orden) pasa por una caja abierta.
El hook de pagos registra el movimiento 'pago_orden' atómicamente con el pago.
"""

from datetime import date
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.models.models import Caja, MovimientoCaja, Usuario
from src.schemas.schemas import (
    CajaAbrirRequest,
    CajaCerrarRequest,
    CajaResponse,
    MovimientoCajaCreate,
    MovimientoCajaResponse,
    ResumenDiaResponse,
)
from src.services import caja_service
from src.services.caja_service import (
    ORIGEN_EGRESO_MANUAL,
    ORIGEN_INGRESO_MANUAL,
)
from src.utils.auth import get_current_user, require_roles

router = APIRouter(
    prefix="/api/caja",
    tags=["Caja"],
)


@router.post(
    "/abrir",
    response_model=CajaResponse,
    status_code=201,
    summary="Abrir la caja del día",
)
async def abrir_caja(
    datos: CajaAbrirRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["admin", "asistente"])),
):
    """Abre la caja. Rechaza (400) si ya hay una abierta."""
    try:
        return await caja_service.build_caja_response(
            db,
            await caja_service.abrir_caja(db, current_user, datos.monto_inicial),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/cerrar",
    response_model=CajaResponse,
    summary="Cerrar la caja (arqueo)",
)
async def cerrar_caja(
    datos: CajaCerrarRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["admin", "asistente"])),
):
    """Cierra la caja calculando monto_esperado y diferencia."""
    # La caja a cerrar es la más reciente (abierta o cerrada): así distinguimos
    # 404 "no hay caja" de 400 "ya está cerrada".
    result = await db.execute(select(Caja).order_by(Caja.id.desc()).limit(1))
    caja = result.scalar_one_or_none()
    if not caja:
        raise HTTPException(status_code=404, detail="No hay caja abierta.")
    try:
        return await caja_service.build_caja_response(
            db,
            await caja_service.cerrar_caja(
                db, current_user, caja, datos.monto_contado, datos.nota_cierre
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/actual",
    summary="Caja abierta actual",
    description="Devuelve la caja abierta o null (el frontend necesita null, no 404).",
    dependencies=[Depends(require_roles(["admin", "asistente"]))],
)
async def caja_actual(db: AsyncSession = Depends(get_db)):
    caja = await caja_service.obtener_caja_abierta(db)
    if not caja:
        return {"caja": None}
    return {"caja": await caja_service.build_caja_response(db, caja)}


@router.post(
    "/movimientos",
    response_model=MovimientoCajaResponse,
    status_code=201,
    summary="Registrar movimiento manual (ingreso/egreso)",
)
async def registrar_movimiento(
    datos: MovimientoCajaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["admin", "asistente"])),
):
    """Registra un ingreso o egreso manual en la caja abierta."""
    caja = await caja_service.obtener_caja_abierta(db)
    if not caja:
        raise HTTPException(
            status_code=400,
            detail="No hay caja abierta. Abre la caja antes de registrar movimientos.",
        )
    origen = (
        ORIGEN_INGRESO_MANUAL if datos.tipo == "ingreso" else ORIGEN_EGRESO_MANUAL
    )
    return await caja_service.registrar_movimiento(
        db,
        current_user,
        caja,
        datos.tipo,
        datos.monto,
        descripcion=datos.descripcion,
        origen=origen,
        metodo_pago=datos.metodo_pago or "",
    )


@router.get(
    "/movimientos",
    response_model=List[MovimientoCajaResponse],
    summary="Listar movimientos de la caja actual",
    description="Si hay caja abierta devuelve sus movimientos; si no, [] (200). "
                "El query param opcional caja_id permite ver cajas cerradas.",
    dependencies=[Depends(require_roles(["admin", "asistente"]))],
)
async def listar_movimientos(
    caja_id: Optional[int] = Query(None, description="Caja específica (para ver cerradas)"),
    db: AsyncSession = Depends(get_db),
):
    if caja_id is None:
        caja = await caja_service.obtener_caja_abierta(db)
        if not caja:
            return []
        caja_id = caja.id
    result = await db.execute(
        select(MovimientoCaja)
        .where(MovimientoCaja.caja_id == caja_id)
        .order_by(MovimientoCaja.id)
    )
    return list(result.scalars().all())


@router.get(
    "/historial",
    response_model=List[CajaResponse],
    summary="Historial de cajas",
    description="Todas las cajas (abiertas y cerradas) ordenadas por abierta_en desc, con sumas.",
    dependencies=[Depends(require_roles(["admin", "asistente"]))],
)
async def historial_cajas(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Caja).order_by(Caja.abierta_en.desc(), Caja.id.desc())
    )
    cajas = result.scalars().all()
    return [await caja_service.build_caja_response(db, c) for c in cajas]


@router.get(
    "/resumen-dia",
    response_model=ResumenDiaResponse,
    summary="Resumen financiero del día (Dashboard)",
    description="Accesible para cualquier rol autenticado.",
)
async def resumen_dia(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return await caja_service.resumen_dia(db, date.today())