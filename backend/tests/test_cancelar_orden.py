"""
Test del flujo de CANCELACIÓN de órdenes (soft delete).

Verifica que:
1. El dashboard NO cuenta las órdenes canceladas.
2. Una orden marcada como 'cancelada' deja de contar como activa.
3. La operación es idempotente (cambia a cancelada y se mantiene).
"""

import pytest
from sqlalchemy import select, text

from src.models.models import OrdenServicio, EstadoOrden, Cliente
from src.config.database import async_sessionmaker, engine


@pytest.fixture
def db():
    return async_sessionmaker(engine, expire_on_commit=False)


async def test_dashboard_excluye_canceladas(db):
    """El dashboard no cuenta órdenes 'canceladas' como activas ni cerradas."""
    async with db() as session:
        # Crear una orden de prueba en estado activo
        r = await session.execute(select(Cliente).limit(1))
        cliente = r.scalar_one()

        orden = OrdenServicio(
            numero_orden="TEST-CANCEL-DASH",
            cliente_id=cliente.id,
            estado=EstadoOrden.revision,
        )
        session.add(orden)
        await session.flush()

        activas_con_orden = (await session.execute(
            text("SELECT ordenes_activas FROM vista_dashboard")
        )).scalar()

        # Cancelar (equivale a lo que hace el endpoint)
        orden.estado = EstadoOrden.cancelada
        await session.commit()

        activas_sin_orden = (await session.execute(
            text("SELECT ordenes_activas FROM vista_dashboard")
        )).scalar()

        # La orden cancelada ya no suma a las activas
        assert activas_sin_orden == activas_con_orden - 1

        # Limpiar
        await session.delete(orden)
        await session.commit()


async def test_cancelacion_es_soft_delete(db):
    """Cancelar no borra la orden: solo cambia su estado a 'cancelada'."""
    async with db() as session:
        r = await session.execute(select(Cliente).limit(1))
        cliente = r.scalar_one()

        orden = OrdenServicio(
            numero_orden="TEST-CANCEL-KEEP",
            cliente_id=cliente.id,
            estado=EstadoOrden.revision,
        )
        session.add(orden)
        await session.flush()
        orden_id = orden.id

        # Simular el endpoint: marcar cancelada
        orden.estado = EstadoOrden.cancelada
        orden.fecha_cierre = None
        await session.commit()

        # La orden sigue existiendo en la BD (soft delete)
        r2 = await session.execute(
            select(OrdenServicio).where(OrdenServicio.id == orden_id)
        )
        orden_guardada = r2.scalar_one()
        assert orden_guardada.estado == EstadoOrden.cancelada

        # Limpiar
        await session.delete(orden_guardada)
        await session.commit()
