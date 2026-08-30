"""
Tests de validaciones de negocio del POST /api/facturacion/generar.

Cubre las reglas agregadas para proteger la integridad SRI:
1. ANTI-DUPLICADO: rechazar si la orden/nota ya tiene una factura electrónica.
2. REGLA DE PAGO: la orden debe estar pagada al 100% (abono >= total).
   (misma regla que el router de notas de venta).
3. Orden inexistente → 404.
4. Happy path: orden pagada sin factura → 201.

Los tests usan una BD aislada (SQLite en archivo temporal por test) con
dependency override de get_db. NUNCA tocan la BD real de producción.
"""

from decimal import Decimal

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.config.database import get_db
from src.main import app
from src.models.models import (
    Base,
    Cliente,
    ConfiguracionSistema,
    EstadoOrden,
    EquipoOrden,
    NotaVenta,
    OrdenServicio,
)

RUTA_P12_REAL = "/home/skorggamor/agente-contador/firmadigital.p12"


async def _crear_engine_bd_prueba(tmp_path_factory):
    """Crea engine + esquema completo en un SQLite aislado."""
    db_file = tmp_path_factory.mktemp("orpey_test") / "orpey_test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine


async def _sembrar_datos(session_factory) -> dict:
    """Inserta clientes, órdenes y nota de venta de prueba. Devuelve sus IDs."""
    async with session_factory() as session:
        session.add_all([
            ConfiguracionSistema(clave="iva_porcentaje", valor="15"),
            ConfiguracionSistema(clave="firma_p12_ruta", valor=RUTA_P12_REAL),
        ])
        cliente_pagada = Cliente(
            nombre="Tanya", apellido="Triviño Meza",
            telefono="0999999999", cedula_ruc="0926048380",
        )
        cliente_no_pagada = Cliente(
            nombre="Pedro", apellido="Pérez",
            telefono="0988888888", cedula_ruc="0912345678",
        )
        session.add_all([cliente_pagada, cliente_no_pagada])
        await session.flush()

        orden_pagada = OrdenServicio(
            numero_orden="ORP-TEST-001", cliente_id=cliente_pagada.id,
            estado=EstadoOrden.entregada,
            total_orden=Decimal("25.00"), abono=Decimal("25.00"),
        )
        orden_no_pagada = OrdenServicio(
            numero_orden="ORP-TEST-002", cliente_id=cliente_no_pagada.id,
            estado=EstadoOrden.entregada,
            total_orden=Decimal("50.00"), abono=Decimal("10.00"),
        )
        orden_para_nota = OrdenServicio(
            numero_orden="ORP-TEST-003", cliente_id=cliente_pagada.id,
            estado=EstadoOrden.entregada,
            total_orden=Decimal("30.00"), abono=Decimal("30.00"),
        )
        # Pagada al 100% pero AÚN NO entregada (en reparación) → factura rechazada
        orden_sin_entregar = OrdenServicio(
            numero_orden="ORP-TEST-004", cliente_id=cliente_pagada.id,
            estado=EstadoOrden.en_reparacion,
            total_orden=Decimal("40.00"), abono=Decimal("40.00"),
        )
        session.add_all([orden_pagada, orden_no_pagada, orden_para_nota, orden_sin_entregar])
        await session.flush()

        session.add(EquipoOrden(
            orden_id=orden_pagada.id,
            tipo_equipo="impresora", marca="HP", modelo="INK TANK 315",
            descripcion_problema="ERROR E03", costo=Decimal("25.00"),
        ))
        nota = NotaVenta(
            numero_nota="NOTA-TEST-0001",
            orden_servicio_id=orden_para_nota.id,
            cliente_id=cliente_pagada.id,
            subtotal=Decimal("26.09"), iva=Decimal("3.91"),
            total=Decimal("30.00"),
        )
        session.add(nota)
        await session.flush()
        ids = {
            "orden_pagada": orden_pagada.id,
            "orden_no_pagada": orden_no_pagada.id,
            "nota_venta": nota.id,
            "orden_sin_entregar": orden_sin_entregar.id,
        }
        await session.commit()
        return ids


@pytest.fixture
async def cliente_api(tmp_path_factory):
    """Cliente HTTP con override de get_db hacia una BD SQLite aislada.

    Devuelve (AsyncClient, ids): ids = {"orden_pagada", "orden_no_pagada",
    "nota_venta"} de la BD sembrada.
    """
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

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac, ids
    finally:
        app.dependency_overrides.pop(get_db, None)
        await engine.dispose()


async def _post_generar(cliente_api, payload):
    ac, _ids = cliente_api
    return await ac.post("/api/facturacion/generar", json=payload)


# =====================================================
# Regla de pago
# =====================================================

async def test_factura_rechaza_orden_no_pagada(cliente_api):
    """Orden con abono < total → 400 con detalle claro."""
    _ac, ids = cliente_api
    resp = await _post_generar(cliente_api, {
        "orden_servicio_id": ids["orden_no_pagada"],  # abono 10 < total 50
        "ambiente": "1",
    })
    assert resp.status_code == 400
    assert "pagada al 100%" in resp.json()["detail"]


# =====================================================
# Regla de estado (paridad con la UI)
# =====================================================

async def test_factura_rechaza_orden_pagada_sin_entregar(cliente_api):
    """Orden pagada 100% pero en reparación → 400 (no facturable)."""
    _ac, ids = cliente_api
    resp = await _post_generar(cliente_api, {
        "orden_servicio_id": ids["orden_sin_entregar"],
        "ambiente": "1",
    })
    assert resp.status_code == 400
    assert "entregada o terminada" in resp.json()["detail"]


# =====================================================
# Anti-duplicado
# =====================================================

async def test_factura_rechaza_duplicada_por_orden(cliente_api):
    """Segunda factura para la misma orden → 400."""
    _ac, ids = cliente_api
    payload = {"orden_servicio_id": ids["orden_pagada"], "ambiente": "1"}
    primera = await _post_generar(cliente_api, payload)
    assert primera.status_code == 201

    duplicada = await _post_generar(cliente_api, payload)
    assert duplicada.status_code == 400
    assert (
        "ya tiene una factura electrónica asociada"
        in duplicada.json()["detail"]
    )


async def test_factura_rechaza_duplicada_por_nota_venta(cliente_api):
    """Segunda factura para la misma nota de venta → 400."""
    _ac, ids = cliente_api
    payload = {"nota_venta_id": ids["nota_venta"], "ambiente": "1"}
    primera = await _post_generar(cliente_api, payload)
    assert primera.status_code == 201

    duplicada = await _post_generar(cliente_api, payload)
    assert duplicada.status_code == 400
    assert (
        "ya tiene una factura electrónica asociada"
        in duplicada.json()["detail"]
    )


# =====================================================
# Orden inexistente / happy path
# =====================================================

async def test_factura_orden_inexistente_404(cliente_api):
    """Orden que no existe → 404 (comportamiento ya existente)."""
    resp = await _post_generar(cliente_api, {
        "orden_servicio_id": 999999,
        "ambiente": "1",
    })
    assert resp.status_code == 404
    assert "no encontrada" in resp.json()["detail"]


async def test_factura_happy_path_orden_pagada(cliente_api):
    """Orden pagada sin factura previa → 201 con comprobante firmado."""
    _ac, ids = cliente_api
    resp = await _post_generar(cliente_api, {
        "orden_servicio_id": ids["orden_pagada"],  # 25.00 pagada
        "ambiente": "1",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["orden_servicio_id"] == ids["orden_pagada"]
    assert data["ambiente"] == "1"
    assert data["estado_sri"] == "firmado"
    assert len(data["clave_acceso"]) == 49
    assert data["clave_acceso"].isdigit()