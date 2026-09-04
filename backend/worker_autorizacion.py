#!/usr/bin/env python3
"""
Worker de Autorización SRI — servicio de fondo que garantiza que NINGUNA factura
quede sin autorizar.

Escanea la base de datos por comprobantes en estado pendiente de autorización
(firmado / recibida / en_proceso) y consulta al SRI su autorización en loop.
Cuando el SRI autoriza, actualiza la BD con el número de autorización, la fecha
y el XML autorizado. Corre en segundo plano (monitor) cada `loop_seg`.

Esto replica el comportamiento de los sistemas certificados comerciales: aunque
el flujo síncrono de "transmitir" termine con estado EN PROCESO (porque el SRI
tarda), este worker de fondo SIGUE consultando hasta que sale el número, sin
bloquear la interfaz del usuario.

Uso:
    python3 worker_autorizacion.py [--una-vez] [--loop-seg 60]

Requiere que el backend esté corriendo (comparte la BD local orpey_db).
Sistema local de Daniel — no toca VPS ni AbastoAPP.
"""

import argparse
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select
from src.config.database import async_session
from src.models.models import FacturaElectronica, ConfiguracionSistema
from src.services.transmision_sri import consultar_autorizacion
from src.services.facturacion_sri import obtener_password_firma
from src.services.notificaciones import notificar_cambio_estado

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("worker-autorizacion")

# Estados que requieren consulta de autorización
ESTADOS_PENDIENTES = ("firmado", "recibida", "en_proceso")


async def _resolver_ruta_p12(db) -> str:
    """Resuelve la ruta del .p12 desde la configuración del sistema."""
    result = await db.execute(select(ConfiguracionSistema))
    cfg = {row.clave: row.valor for row in result.scalars().all()}
    return cfg.get("firma_p12_ruta") or "/home/skorggamor/agente-contador/firmadigital.p12"


async def procesar_pendiente(factura: FacturaElectronica, ruta_p12: str, pwd_firma: str) -> str:
    """
    Consulta la autorización de una factura pendiente y actualiza su estado si
    el SRI ya autorizó (o rechazó). Devuelve el nuevo estado.
    """
    try:
        resultado = consultar_autorizacion(
            clave_acceso=factura.clave_acceso,
            ambiente=str(factura.ambiente),
            ruta_p12=ruta_p12,
            password_p12=pwd_firma,
            timeout=40,
        )
    except Exception as exc:  # red/TLS/cert — no es definitivo; reintentar luego
        logger.warning("Factura %s: error consultando autorización: %s", factura.numero_documento, exc)
        return factura.estado_sri

    estado = resultado["estado"]

    if estado == "AUTORIZADO":
        numero = resultado.get("numero_autorizacion") or ""
        logger.info("✅ Factura %s AUTORIZADA. N°=%s", factura.numero_documento, numero)
        factura.estado_sri = "autorizado"
        if numero:
            factura.numero_autorizacion = numero
        fecha = resultado.get("fecha_autorizacion") or ""
        if fecha:
            from datetime import datetime
            try:
                factura.fecha_autorizacion = datetime.fromisoformat(fecha.replace("Z", "+00:00"))
            except ValueError:
                factura.fecha_autorizacion = None
        if resultado.get("xml_autorizado"):
            factura.xml_respuesta_sri = resultado["xml_autorizado"]
        await db.commit()
        # Notificar exitosamente (same session, tras commit)
        notificar_cambio_estado(
            factura.numero_documento,
            "autorizado",
            detalle=f"N° autorización: {numero}".strip(),
        )
        return "autorizado"

    elif estado in ("DEVUELTA", "NO AUTORIZADO"):
        logger.warning("⚠️ Factura %s con estado %s", factura.numero_documento, estado)
        factura.estado_sri = "devuelta" if estado == "DEVUELTA" else "no_autorizado"
        mensajes = resultado.get("mensajes") or []
        detalle = ""
        if mensajes:
            detalle = "\n".join(
                f"[{m.get('identificador','')}] {m.get('mensaje','')}".strip() for m in mensajes
            )
            factura.xml_respuesta_sri = detalle
        await db.commit()
        notificar_cambio_estado(factura.numero_documento, factura.estado_sri, detalle=detalle)
        return factura.estado_sri

    # EN PROCESO → sin cambios, se reconsulta en la próxima pasada.
    return factura.estado_sri


async def pasada(ruta_p12: str, pwd_firma: str) -> int:
    """Procesa todas las facturas pendientes en una pasada. Devuelve nº de pendientes."""
    async with async_session() as db:
        result = await db.execute(
            select(FacturaElectronica).where(FacturaElectronica.estado_sri.in_(ESTADOS_PENDIENTES))
        )
        pendientes = result.scalars().all()

        for factura in pendientes:
            try:
                await procesar_pendiente(factura, ruta_p12, pwd_firma)
            except Exception as exc:
                logger.error("Error procesando factura %s: %s", factura.numero_documento, exc)
        return len(pendientes)


async def loop(loop_seg: int, una_vez: bool) -> None:
    logger.info("Worker de autorización SRI iniciado (loop_seg=%ss)", loop_seg)
    while True:
        try:
            async with async_session() as db:
                ruta_p12 = await _resolver_ruta_p12(db)
            pwd_firma = obtener_password_firma()
            n = await pasada(ruta_p12, pwd_firma)
            if n:
                logger.info("Pasada completa: %d pendiente(s) procesado(s).", n)
            else:
                logger.debug("Sin facturas pendientes.")
        except Exception as exc:
            logger.error("Error en pasada: %s", exc)

        if una_vez:
            return
        await asyncio.sleep(loop_seg)


def main() -> None:
    parser = argparse.ArgumentParser(description="Worker de autorización SRI")
    parser.add_argument("--una-vez", action="store_true", help="Ejecutar una sola pasada y salir")
    parser.add_argument("--loop-seg", type=int, default=60, help="Segundos entre pasadas (default 60)")
    args = parser.parse_args()
    asyncio.run(loop(args.loop_seg, args.una_vez))


if __name__ == "__main__":
    main()
