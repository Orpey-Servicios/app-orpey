"""
Tests del módulo de CAJA (apertura/cierre/arqueo + hook atómico en pagos).

Cubre las 11 reglas del contrato:
- Apertura única (rechaza doble apertura).
- Movimientos manuales requieren caja abierta.
- Arqueo de cierre: esperado = inicial + ingresos - egresos; diferencia = contado - esperado.
- Cierre sin caja abierta → 404.
- HOOK: cada pago genera un movimiento 'pago_orden' atómico (misma transacción).
- Pago sin caja abierta → 400 y NO crea pago.
- Resumen del día (facturado/notas/ordenes cerradas filtradas por hoy; NC excluida).
- Historial de cajas.

Usa una BD aislada (SQLite en archivo temporal por test) con dependency
override de get_db Y get_current_user. NUNCA toca la BD real.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.config.database import get_db
from src.main import app
from src.models.models import (
    Base,
    Caja,
    Cliente,
    ConfiguracionSistema,
    FacturaElectronica,
    MovimientoCaja,
    NotaVenta,
    OrdenServicio,
    RolUsuario,
    Usuario,
)
from src.utils.auth import get_current_user


async def _crear_engine_bd_prueba(tmp_path_factory):
    """Crea engine + esquema completo en un SQLite aislado."""
    db_file = tmp_path_factory.mktemp("orpey_caja_test") / "caja_test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine


async def _sembrar_datos(session_factory) -> dict:
    """Inserta usuario admin, cliente y orden pagable de prueba."""
    async with session_factory() as session:
        session.add(ConfiguracionSistema(clave="iva_porcentaje", valor="15"))
        admin = Usuario(
            username="admin", password_hash="x", rol=RolUsuario.admin, nombre="Admin"
        )
        cliente = Cliente(
            nombre="Ana", apellido="Pérez", telefono="0999999999", cedula_ruc="0999999999"
        )
        session.add_all([admin, cliente])
        await session.flush()

        orden = OrdenServicio(
            numero_orden="ORP-CAJA-001",
            cliente_id=cliente.id,
            estado="revision",
            total_orden=Decimal("100.00"),
            abono=Decimal("0.00"),
        )
        session.add(orden)
        await session.flush()

        ids = {"admin_id": admin.id, "cliente_id": cliente.id, "orden_id": orden.id}
        await session.commit()
        return ids


@pytest.fixture
async def cliente_api(tmp_path_factory):
    """Cliente HTTP con override de get_db + get_current_user hacia SQLite aislado."""
    engine = await _crear_engine_bd_prueba(tmp_path_factory)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    ids = await _sembrar_datos(session_factory)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def override_get_current_user():
        async with session_factory() as session:
            result = await session.execute(select(Usuario).where(Usuario.id == ids["admin_id"]))
            return result.scalar_one()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac, ids, session_factory
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
        await engine.dispose()


def _dec(valor) -> Decimal:
    return Decimal(str(valor))


async def _abrir(ac, monto=0):
    return await ac.post("/api/caja/abrir", json={"monto_inicial": monto})


async def _movimiento(ac, tipo, monto, descripcion=None):
    return await ac.post(
        "/api/caja/movimientos",
        json={"tipo": tipo, "monto": monto, "descripcion": descripcion},
    )


# =====================================================
# Apertura
# =====================================================

async def test_abrir_caja_exito(cliente_api):
    ac, _ids, _sf = cliente_api
    resp = await _abrir(ac, 50)
    assert resp.status_code == 201
    data = resp.json()
    assert data["estado"] == "abierta"
    assert _dec(data["monto_inicial"]) == Decimal("50.00")
    assert _dec(data["monto_en_caja"]) == Decimal("50.00")


async def test_abrir_caja_doble_apertura_rechazada(cliente_api):
    ac, _ids, _sf = cliente_api
    primera = await _abrir(ac, 10)
    assert primera.status_code == 201
    segunda = await _abrir(ac, 10)
    assert segunda.status_code == 400
    assert "Ya hay una caja abierta" in segunda.json()["detail"]


# =====================================================
# Movimientos manuales
# =====================================================

async def test_registrar_movimiento_sin_caja_abierta_rechazado(cliente_api):
    ac, _ids, _sf = cliente_api
    resp = await _movimiento(ac, "ingreso", 10)
    assert resp.status_code == 400
    assert "No hay caja abierta" in resp.json()["detail"]


async def test_registrar_egreso_manual(cliente_api):
    ac, _ids, _sf = cliente_api
    await _abrir(ac, 100)
    resp = await _movimiento(ac, "egreso", 20, "compra de repuesto")
    assert resp.status_code == 201
    data = resp.json()
    assert data["tipo"] == "egreso"
    assert data["origen"] == "egreso_manual"
    assert data["monto"] == "20.00"

    actual = await ac.get("/api/caja/actual")
    caja = actual.json()["caja"]
    assert _dec(caja["monto_en_caja"]) == Decimal("80.00")
    assert _dec(caja["egresos"]) == Decimal("20.00")


# =====================================================
# Arqueo de cierre
# =====================================================

async def test_cerrar_caja_arqueo_cuadre(cliente_api):
    ac, _ids, _sf = cliente_api
    await _abrir(ac, 100)
    await _movimiento(ac, "ingreso", 50)
    await _movimiento(ac, "egreso", 20)

    resp = await ac.post("/api/caja/cerrar", json={"monto_contado": 130})
    assert resp.status_code == 200
    data = resp.json()
    assert _dec(data["monto_esperado"]) == Decimal("130.00")
    assert _dec(data["diferencia"]) == Decimal("0.00")
    assert data["estado"] == "cerrada"
    assert data["cerrada_en"] is not None


async def test_cerrar_caja_sobrante_y_faltante(cliente_api):
    ac, _ids, _sf = cliente_api

    # Sobrante: contado 120 > esperado 100 → diferencia +20
    await _abrir(ac, 100)
    resp = await ac.post("/api/caja/cerrar", json={"monto_contado": 120})
    assert resp.status_code == 200
    assert _dec(resp.json()["diferencia"]) == Decimal("20.00")

    # Faltante: contado 80 < esperado 100 → diferencia -20
    await _abrir(ac, 100)
    resp = await ac.post("/api/caja/cerrar", json={"monto_contado": 80})
    assert resp.status_code == 200
    assert _dec(resp.json()["diferencia"]) == Decimal("-20.00")


async def test_cerrar_caja_sin_caja_abierta(cliente_api):
    ac, _ids, _sf = cliente_api
    resp = await ac.post("/api/caja/cerrar", json={"monto_contado": 0})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "No hay caja abierta."


# =====================================================
# HOOK atómico en pagos
# =====================================================

async def test_pago_crea_movimiento_caja_atomico(cliente_api):
    ac, ids, session_factory = cliente_api
    await _abrir(ac, 10)

    resp = await ac.post(
        f"/api/ordenes/{ids['orden_id']}/pagos",
        json={"monto": 25, "metodo_pago": "efectivo"},
    )
    assert resp.status_code == 201
    pago_id = resp.json()["id"]
    assert _dec(resp.json()["monto"]) == Decimal("25.00")

    async with session_factory() as session:
        result = await session.execute(
            select(MovimientoCaja).where(MovimientoCaja.origen == "pago_orden")
        )
        mov = result.scalar_one()
        assert mov.tipo == "ingreso"
        assert mov.referencia_id == pago_id
        assert _dec(mov.monto) == Decimal("25.00")
        assert mov.metodo_pago == "efectivo"

        # No queda pago sin movimiento: ambos nacieron en la misma transacción
        pago = (await session.execute(select(OrdenServicio))).scalars().first()
        assert pago is not None

        orden = (await session.execute(
            select(OrdenServicio).where(OrdenServicio.id == ids["orden_id"])
        )).scalar_one()
        assert _dec(orden.abono) == Decimal("25.00")


async def test_pago_sin_caja_abierta_rechazado(cliente_api):
    ac, ids, session_factory = cliente_api

    resp = await ac.post(
        f"/api/ordenes/{ids['orden_id']}/pagos",
        json={"monto": 25, "metodo_pago": "efectivo"},
    )
    assert resp.status_code == 400
    assert "No hay caja abierta" in resp.json()["detail"]

    async with session_factory() as session:
        n_pagos = len(
            (await session.execute(select(MovimientoCaja))).scalars().all()
        )
        assert n_pagos == 0
        orden = (await session.execute(
            select(OrdenServicio).where(OrdenServicio.id == ids["orden_id"])
        )).scalar_one()
        assert _dec(orden.abono) == Decimal("0.00")


# =====================================================
# Resumen del día
# =====================================================

async def test_resumen_dia(cliente_api):
    ac, ids, session_factory = cliente_api
    hoy = datetime.now().date()
    await _abrir(ac, 50)
    await ac.post(
        f"/api/ordenes/{ids['orden_id']}/pagos",
        json={"monto": 25, "metodo_pago": "efectivo"},
    )
    await _movimiento(ac, "egreso", 10, "luz")

    async with session_factory() as session:
        # Factura 01 autorizada hoy → cuenta
        session.add(FacturaElectronica(
            cliente_id=ids["cliente_id"], tipo_comprobante="01",
            estado_sri="autorizado", clave_acceso="0" * 49,
            numero_documento="001-001-000000001", xml_firmado="<x/>",
            subtotal=Decimal("5.00"), iva=Decimal("0.00"), total=Decimal("5.00"),
        ))
        # Factura 01 recibida hoy → cuenta
        session.add(FacturaElectronica(
            cliente_id=ids["cliente_id"], tipo_comprobante="01",
            estado_sri="recibida", clave_acceso="1" * 49,
            numero_documento="001-001-000000002", xml_firmado="<x/>",
            subtotal=Decimal("6.00"), iva=Decimal("0.00"), total=Decimal("6.00"),
        ))
        # NC 04 hoy → NO cuenta (tipo != '01')
        session.add(FacturaElectronica(
            cliente_id=ids["cliente_id"], tipo_comprobante="04",
            estado_sri="autorizado", clave_acceso="2" * 49,
            numero_documento="001-001-000000003", xml_firmado="<x/>",
            subtotal=Decimal("100.00"), iva=Decimal("0.00"), total=Decimal("100.00"),
        ))
        # Factura 01 de AYER → NO cuenta (fecha != hoy)
        session.add(FacturaElectronica(
            cliente_id=ids["cliente_id"], tipo_comprobante="01",
            estado_sri="autorizado", clave_acceso="3" * 49,
            numero_documento="001-001-000000004", xml_firmado="<x/>",
            subtotal=Decimal("1000.00"), iva=Decimal("0.00"), total=Decimal("1000.00"),
            fecha_emision=datetime.now() - timedelta(days=1),
        ))
        # Factura 01 firmado hoy → NO cuenta (estado no autorizado/recibida)
        session.add(FacturaElectronica(
            cliente_id=ids["cliente_id"], tipo_comprobante="01",
            estado_sri="firmado", clave_acceso="4" * 49,
            numero_documento="001-001-000000005", xml_firmado="<x/>",
            subtotal=Decimal("7.00"), iva=Decimal("0.00"), total=Decimal("7.00"),
        ))
        # Nota de venta hoy → cuenta
        session.add(NotaVenta(
            numero_nota="NV-CAJA-0001", orden_servicio_id=ids["orden_id"],
            cliente_id=ids["cliente_id"], subtotal=Decimal("30.00"),
            iva=Decimal("0.00"), total=Decimal("30.00"),
        ))
        # Orden cerrada HOY y pagada 100% → cuenta
        session.add(OrdenServicio(
            numero_orden="ORP-CAJA-002", cliente_id=ids["cliente_id"],
            estado="entregada", total_orden=Decimal("40.00"), abono=Decimal("40.00"),
            fecha_cierre=datetime.now(),
        ))
        # Orden cerrada AYER pagada 100% → NO cuenta
        session.add(OrdenServicio(
            numero_orden="ORP-CAJA-003", cliente_id=ids["cliente_id"],
            estado="entregada", total_orden=Decimal("50.00"), abono=Decimal("50.00"),
            fecha_cierre=datetime.now() - timedelta(days=1),
        ))
        await session.commit()

    resp = await ac.get("/api/caja/resumen-dia")
    assert resp.status_code == 200
    data = resp.json()
    assert data["fecha"] == hoy.isoformat()
    assert data["caja_abierta"] is not None
    assert _dec(data["ingresos_hoy"]) == Decimal("25.00")
    assert _dec(data["egresos_hoy"]) == Decimal("10.00")
    assert _dec(data["esperado_hoy"]) == Decimal("65.00")
    assert _dec(data["facturado_hoy"]) == Decimal("11.00")
    assert _dec(data["notas_venta_hoy"]) == Decimal("30.00")
    assert _dec(data["pagos_hoy"]) == Decimal("25.00")
    assert data["ordenes_cerradas_hoy"] == 1


# =====================================================
# Historial
# =====================================================

async def test_historial(cliente_api):
    ac, _ids, _sf = cliente_api
    await _abrir(ac, 100)
    await _movimiento(ac, "ingreso", 50)
    await ac.post("/api/caja/cerrar", json={"monto_contado": 150})
    await _abrir(ac, 20)

    resp = await ac.get("/api/caja/historial")
    assert resp.status_code == 200
    cajas = resp.json()
    assert len(cajas) == 2
    # Ordenadas de la más reciente a la más antigua
    assert cajas[0]["monto_inicial"] == "20.00"
    assert cajas[0]["estado"] == "abierta"
    assert cajas[1]["estado"] == "cerrada"
    assert _dec(cajas[1]["ingresos"]) == Decimal("50.00")
    assert _dec(cajas[1]["monto_esperado"]) == Decimal("150.00")