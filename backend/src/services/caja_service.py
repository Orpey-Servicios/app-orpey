"""
Servicio de Caja - Lógica de negocio del módulo de caja/arqueo.

Reglas centrales (contrato cerrado):
- SOLO una caja abierta a la vez (apertura única).
- El cierre es un arqueo: expected = monto_inicial + SUM(ingresos) - SUM(egresos)
  y difference = monto_contado - expected.
- SOLO dos tipos de movimiento: 'ingreso' | 'egreso'.
  El monto SIEMPRE es positivo en BD; el signo lo da el tipo.
  (Esto corrige el bug de abasto-app donde el arqueo ignoraba las ventas.)
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.models import (
    Caja,
    FacturaElectronica,
    MovimientoCaja,
    NotaVenta,
    OrdenServicio,
    Usuario,
)

# Orígenes de movimiento admitidos (CHECK en BD)
ORIGEN_PAGO_ORDEN = "pago_orden"
ORIGEN_INGRESO_MANUAL = "ingreso_manual"
ORIGEN_EGRESO_MANUAL = "egreso_manual"

TIPOS_VALIDOS = ("ingreso", "egreso")
ESTADO_ABIERTA = "abierta"
ESTADO_CERRADA = "cerrada"


async def obtener_caja_abierta(db: AsyncSession) -> Optional[Caja]:
    """Devuelve la caja abierta actual (o None si no hay). Orden by id desc."""
    result = await db.execute(
        select(Caja)
        .where(Caja.estado == ESTADO_ABIERTA)
        .order_by(Caja.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def abrir_caja(
    db: AsyncSession, usuario: Usuario, monto_inicial: Decimal
) -> Caja:
    """Abre la caja. Rechaza si ya hay una abierta."""
    if await obtener_caja_abierta(db):
        raise ValueError("Ya hay una caja abierta. Ciérrala antes de abrir otra.")

    caja = Caja(
        monto_inicial=monto_inicial,
        estado=ESTADO_ABIERTA,
        abierta_por=usuario.id,
    )
    db.add(caja)
    await db.commit()
    await db.refresh(caja)
    return caja


async def _movimientos_de(db: AsyncSession, caja_id: int) -> list:
    """Todos los movimientos de una caja ordenados por id."""
    result = await db.execute(
        select(MovimientoCaja)
        .where(MovimientoCaja.caja_id == caja_id)
        .order_by(MovimientoCaja.id)
    )
    return list(result.scalars().all())


async def cerrar_caja(
    db: AsyncSession,
    usuario: Usuario,
    caja: Caja,
    monto_contado: Decimal,
    nota: Optional[str] = None,
) -> Caja:
    """
    Cierra la caja haciendo el arqueo.
    expected = monto_inicial + SUM(ingresos) - SUM(egresos)
    diferencia = monto_contado - expected (positivo sobrante, negativo faltante).
    """
    if caja.estado == ESTADO_CERRADA:
        raise ValueError("La caja ya está cerrada.")

    movimientos = await _movimientos_de(db, caja.id)
    ingresos = sum(
        (Decimal(str(m.monto)) for m in movimientos if m.tipo == "ingreso"),
        Decimal("0.00"),
    )
    egresos = sum(
        (Decimal(str(m.monto)) for m in movimientos if m.tipo == "egreso"),
        Decimal("0.00"),
    )
    esperado = Decimal(str(caja.monto_inicial)) + ingresos - egresos
    monto_contado = Decimal(str(monto_contado))

    caja.monto_cierre = monto_contado
    caja.monto_esperado = esperado
    caja.diferencia = monto_contado - esperado
    caja.cerrada_por = usuario.id
    caja.cerrada_en = datetime.now()
    caja.nota_cierre = nota
    caja.estado = ESTADO_CERRADA

    await db.commit()
    await db.refresh(caja)
    return caja


async def registrar_movimiento(
    db: AsyncSession,
    usuario: Usuario,
    caja: Caja,
    tipo: str,
    monto: Decimal,
    descripcion: Optional[str] = None,
    origen: Optional[str] = None,
    referencia_id: Optional[int] = None,
    metodo_pago: Optional[str] = "",
) -> MovimientoCaja:
    """Crea y commitea un movimiento de caja. Monto siempre positivo."""
    movimiento = MovimientoCaja(
        caja_id=caja.id,
        tipo=tipo,
        origen=origen,
        referencia_id=referencia_id,
        monto=monto,
        descripcion=descripcion,
        metodo_pago=metodo_pago,
        creado_por=usuario.id,
    )
    db.add(movimiento)
    await db.commit()
    await db.refresh(movimiento)
    return movimiento


async def sumas_caja(db: AsyncSession, caja_id: int) -> tuple[Decimal, Decimal]:
    """Sumas de ingresos y egresos del período de una caja."""
    ingresos_suma = func.coalesce(
        func.sum(MovimientoCaja.monto).filter(MovimientoCaja.tipo == "ingreso"), 0
    )
    egresos_suma = func.coalesce(
        func.sum(MovimientoCaja.monto).filter(MovimientoCaja.tipo == "egreso"), 0
    )
    result = await db.execute(
        select(ingresos_suma, egresos_suma).where(
            MovimientoCaja.caja_id == caja_id
        )
    )
    ingresos, egresos = result.one()
    return Decimal(str(ingresos or 0)), Decimal(str(egresos or 0))


async def build_caja_response(db: AsyncSession, caja: Caja) -> dict:
    """Construye el dict de CajaResponse con los montos calculados."""
    ingresos, egresos = await sumas_caja(db, caja.id)
    monto_en_caja = None
    if caja.estado == ESTADO_ABIERTA:
        monto_en_caja = Decimal(str(caja.monto_inicial)) + ingresos - egresos

    return {
        "id": caja.id,
        "monto_inicial": caja.monto_inicial,
        "monto_cierre": caja.monto_cierre,
        "monto_esperado": caja.monto_esperado,
        "diferencia": caja.diferencia,
        "estado": caja.estado,
        "abierta_por": caja.abierta_por,
        "abierta_en": caja.abierta_en,
        "cerrada_por": caja.cerrada_por,
        "cerrada_en": caja.cerrada_en,
        "nota_cierre": caja.nota_cierre,
        "monto_en_caja": monto_en_caja,
        "ingresos": ingresos,
        "egresos": egresos,
    }


async def _suma_movimientos_dia(
    db: AsyncSession, tipo: str, hoy: date
) -> Decimal:
    """Suma de movimientos de un tipo con fecha created_en de hoy (sin importar caja)."""
    result = await db.execute(
        select(func.coalesce(func.sum(MovimientoCaja.monto), 0)).where(
            MovimientoCaja.tipo == tipo,
            func.date(MovimientoCaja.creado_en) == hoy,
        )
    )
    valor = result.scalar()
    return Decimal(str(valor or 0))


async def _caja_abierta_en_dia(db: AsyncSession, hoy: date) -> Optional[Caja]:
    """La caja (abierta o cerrada) que se abrió hoy, si existe."""
    result = await db.execute(
        select(Caja)
        .where(func.date(Caja.abierta_en) == hoy)
        .order_by(Caja.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def resumen_dia(db: AsyncSession, hoy: Optional[date] = None) -> dict:
    """
    Resumen financiero del día (Dashboard).

    Definiciones (contrato):
    - ingresos_hoy = SUM movimientos tipo ingreso con fecha de hoy (sin importar caja).
    - egresos_hoy = análogo.
    - esperado_hoy = monto_inicial caja de hoy + ingresos_hoy - egresos_hoy.
      Si no hay caja abierta HOY (con monto_inicial), esperado_hoy = ingresos_hoy - egresos_hoy.
    - facturado_hoy = SUM total facturas tipo '01' estado in (autorizado, recibida)
      con fecha_emision de hoy. NO cuentan NC '04' ni firmado/devuelta.
    - notas_venta_hoy = SUM total NV con fecha_emision de hoy.
    - pagos_hoy = ingresos_hoy.
    - ordenes_cerradas_hoy = count ordenes con fecha_cierre de hoy y abono >= total.
    """
    hoy = hoy or date.today()

    caja_abierta = await obtener_caja_abierta(db)
    caja_hoy = await _caja_abierta_en_dia(db, hoy)

    ingresos_hoy = await _suma_movimientos_dia(db, "ingreso", hoy)
    egresos_hoy = await _suma_movimientos_dia(db, "egreso", hoy)

    monto_inicial_hoy = Decimal(str(caja_hoy.monto_inicial)) if caja_hoy else Decimal("0.00")
    esperado_hoy = monto_inicial_hoy + ingresos_hoy - egresos_hoy

    facturado_result = await db.execute(
        select(func.coalesce(func.sum(FacturaElectronica.total), 0)).where(
            FacturaElectronica.tipo_comprobante == "01",
            FacturaElectronica.estado_sri.in_(["autorizado", "recibida"]),
            func.date(FacturaElectronica.fecha_emision) == hoy,
        )
    )
    facturado_hoy = Decimal(str(facturado_result.scalar() or 0))

    notas_result = await db.execute(
        select(func.coalesce(func.sum(NotaVenta.total), 0)).where(
            func.date(NotaVenta.fecha_emision) == hoy
        )
    )
    notas_venta_hoy = Decimal(str(notas_result.scalar() or 0))

    cerradas_result = await db.execute(
        select(func.count(OrdenServicio.id)).where(
            func.date(OrdenServicio.fecha_cierre) == hoy,
            OrdenServicio.abono >= OrdenServicio.total_orden,
        )
    )
    ordenes_cerradas_hoy = int(cerradas_result.scalar() or 0)

    caja_abierta_data = None
    if caja_abierta:
        caja_abierta_data = await build_caja_response(db, caja_abierta)

    return {
        "fecha": hoy,
        "caja_abierta": caja_abierta_data,
        "ingresos_hoy": ingresos_hoy,
        "egresos_hoy": egresos_hoy,
        "esperado_hoy": esperado_hoy,
        "facturado_hoy": facturado_hoy,
        "notas_venta_hoy": notas_venta_hoy,
        "pagos_hoy": ingresos_hoy,
        "ordenes_cerradas_hoy": ordenes_cerradas_hoy,
    }