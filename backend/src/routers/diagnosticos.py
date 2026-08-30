"""
Router de Diagnósticos - Flujo del diagnóstico técnico interno (V3).

Es el CORAZÓN del proceso de venta en Orpey:
  1. El TÉCNICO recibe el equipo y llena el diagnóstico interno
     (enciende, disco, memoria, procesador, repuestos con proveedor/costo, etc.)
  2. El DUEÑO (que puede estar en otra ubicación) revisa los
     "diagnósticos activos" y decide: APROBAR ✅ o RECHAZAR ❌
     con comentario, e indica qué instalar al equipo.
  3. El diagnostico se puede enviar por WhatsApp para cerrar la venta.

Endpoints:
- POST /api/equipos/{id}/diagnostico   → Técnico guarda el diagnóstico (+repuestos)
- POST /api/equipos/{id}/aprobar       → Dueño aprueba (comentario + qué instalar)
- POST /api/equipos/{id}/rechazar      → Dueño rechaza (comentario)
- GET  /api/diagnosticos               → Listar diagnósticos activos/pendientes
- GET  /api/diagnosticos/{id}/whatsapp → Link WhatsApp del diagnóstico
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.config.database import get_db
from src.models.models import EquipoOrden, DiagnosticoRepuesto, OrdenServicio, Cliente, Tecnico
from src.schemas.schemas import (
    DiagnosticoGuardar, AprobarDiagnostico, RechazarDiagnostico,
    EquipoResponse, DiagnosticoActivoResponse
)
from src.services.whatsapp import generar_link_whatsapp

router = APIRouter(
    prefix="/api",
    tags=["Diagnósticos Técnicos"]
)


def _valor_enum(valor):
    """Devuelve el valor limpio de un enum (TipoEquipo.impresora → 'impresora')."""
    return valor.value if hasattr(valor, "value") else valor


# ------------------------------------------------------------
# 1) TÉCNICO: Guardar el diagnóstico de un equipo
# ------------------------------------------------------------
@router.put(
    "/equipos/{equipo_id}/diagnostico",
    response_model=EquipoResponse,
    summary="Guardar diagnóstico del técnico",
    description="El técnico guarda los datos del diagnóstico interno del equipo, incluyendo el desglose de repuestos por proveedor."
)
async def guardar_diagnostico(
    equipo_id: int,
    datos: DiagnosticoGuardar,
    db: AsyncSession = Depends(get_db)
):
    """Guarda/actualiza el diagnóstico técnico de un equipo."""
    result = await db.execute(
        select(EquipoOrden).options(joinedload(EquipoOrden.repuestos)).where(EquipoOrden.id == equipo_id)
    )
    equipo = result.unique().scalar_one_or_none()
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    # Copiar los campos de diagnóstico al equipo
    for campo in ("enciende", "tipo_disco", "capacidad_disco", "tipo_memoria",
                  "capacidad_memoria", "slot_m2", "slot_caddy", "procesador", "diagnostico",
                  "toma_papel", "nivel_tinta", "calidad_impresion", "pantalla_rota", "pin_carga"):
        valor = getattr(datos, campo, None)
        if valor is not None:
            setattr(equipo, campo, valor)

    # Marcar como pendiente de aprobación del dueño
    # (solo si aún no ha sido aprobado o rechazado)
    if equipo.estado_aprobacion not in ("aprobado", "rechazado"):
        equipo.estado_aprobacion = "pendiente"

    # Manejar el desglose de repuestos (proveedor + repuesto + costo)
    if datos.repuestos is not None:
        # Eliminar repuestos que ya existían para reemplazarlos
        for viejo in list(equipo.repuestos):
            await db.delete(viejo)
        # Insertar los repuestos nuevos
        nuevos = []
        for r in datos.repuestos:
            if r.repuesto or r.proveedor:  # solo guardar filas con contenido
                nuevos.append(DiagnosticoRepuesto(
                    equipo_id=equipo.id,
                    proveedor=r.proveedor,
                    repuesto=r.repuesto,
                    costo=r.costo or Decimal("0.00"),
                ))
        equipo.repuestos = nuevos

    await db.commit()
    # Recargar con repuestos para devolverlos en la respuesta
    result2 = await db.execute(
        select(EquipoOrden).options(joinedload(EquipoOrden.repuestos)).where(EquipoOrden.id == equipo_id)
    )
    equipo = result2.unique().scalar_one()
    return equipo


# ------------------------------------------------------------
# 2) DUEÑO: Aprobar un diagnóstico (con comentario y decisión)
# ------------------------------------------------------------
@router.post(
    "/equipos/{equipo_id}/aprobar",
    response_model=EquipoResponse,
    summary="Aprobar diagnóstico (dueño)",
    description="El dueño aprueba el diagnóstico, escribe un comentario e indica qué se va a instalar al equipo."
)
async def aprobar_diagnostico(
    equipo_id: int,
    datos: AprobarDiagnostico,
    db: AsyncSession = Depends(get_db)
):
    """Marca el diagnóstico como aprobado por el dueño."""
    result = await db.execute(
        select(EquipoOrden)
        .options(joinedload(EquipoOrden.repuestos), joinedload(EquipoOrden.orden))
        .where(EquipoOrden.id == equipo_id)
    )
    equipo = result.unique().scalar_one_or_none()
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    equipo.estado_aprobacion = "aprobado"
    if datos.comentario is not None:
        equipo.comentario_dueño = datos.comentario
    if datos.instalacion_decision is not None:
        equipo.instalacion_decision = datos.instalacion_decision
    if datos.precio_venta is not None:
        equipo.precio_venta = datos.precio_venta

    # Pasar la orden a estado "en_reparacion" al aprobar el diagnóstico
    if equipo.orden:
        equipo.orden.estado = "en_reparacion"

    await db.commit()
    await db.refresh(equipo)
    return equipo


# ------------------------------------------------------------
# 3) DUEÑO: Rechazar un diagnóstico (con comentario)
# ------------------------------------------------------------
@router.post(
    "/equipos/{equipo_id}/rechazar",
    response_model=EquipoResponse,
    summary="Rechazar diagnóstico (dueño)",
    description="El dueño rechaza el diagnóstico y deja un comentario con el motivo."
)
async def rechazar_diagnostico(
    equipo_id: int,
    datos: RechazarDiagnostico,
    db: AsyncSession = Depends(get_db)
):
    """Marca el diagnóstico como rechazado por el dueño."""
    result = await db.execute(
        select(EquipoOrden).options(joinedload(EquipoOrden.repuestos)).where(EquipoOrden.id == equipo_id)
    )
    equipo = result.unique().scalar_one_or_none()
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    equipo.estado_aprobacion = "rechazado"
    if datos.comentario is not None:
        equipo.comentario_dueño = datos.comentario

    await db.commit()
    await db.refresh(equipo)
    return equipo


# ------------------------------------------------------------
# 4) DUEÑO: Listar diagnósticos activos / pendientes
# ------------------------------------------------------------
@router.get(
    "/diagnosticos",
    response_model=List[dict],
    summary="Listar diagnósticos",
    description="Lista los equipos con diagnóstico pendiente de aprobación (o filtrado por estado)."
)
async def listar_diagnosticos(
    estado: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Devuelve todos los equipos con su diagnóstico, el cliente y la orden.
    El dueño usa esta vista para decidir aprobar o rechazar.

    Filtros:
    - estado: pendiente | aprobado | rechazado (si se omite, devuelve todos)
    """
    # Consultar equipos con su orden y cliente
    query = (
        select(EquipoOrden)
        .join(EquipoOrden.orden)
        .options(joinedload(EquipoOrden.repuestos))
        .options(joinedload(EquipoOrden.orden).joinedload(OrdenServicio.cliente))
        .options(joinedload(EquipoOrden.orden).joinedload(OrdenServicio.tecnico))
        .where(OrdenServicio.estado == "revision")
    )

    if estado:
        query = query.where(EquipoOrden.estado_aprobacion == estado)
    else:
        # Por defecto: devolver TODOS los equipos que tienen diagnóstico revisado
        # (los que el técnico ya llenó aunque sean pendientes de aprobación).
        # Solo mostramos los equipos que tienen al menos un dato de diagnóstico.
        query = query.where(
            (EquipoOrden.diagnostico.isnot(None))
            | (EquipoOrden.enciende.isnot(None))
            | (EquipoOrden.tipo_disco.isnot(None))
        )

    query = query.order_by(EquipoOrden.updated_at.desc())
    result = await db.execute(query)
    equipos = result.unique().scalars().all()

    # Construir la respuesta enriquecida para el dueño
    respuesta = []
    for eq in equipos:
        cliente = eq.orden.cliente
        tecnico = eq.orden.tecnico
        respuesta.append({
            "equipo": {
                "id": eq.id,
                "tipo_equipo": _valor_enum(eq.tipo_equipo),
                "marca": eq.marca,
                "modelo": eq.modelo,
                "descripcion_problema": eq.descripcion_problema,
                "enciende": eq.enciende,
                "tipo_disco": eq.tipo_disco,
                "capacidad_disco": eq.capacidad_disco,
                "tipo_memoria": eq.tipo_memoria,
                "capacidad_memoria": eq.capacidad_memoria,
                "slot_m2": eq.slot_m2,
                "slot_caddy": eq.slot_caddy,
                "procesador": eq.procesador,
                "diagnostico": eq.diagnostico,
                "toma_papel": getattr(eq, "toma_papel", None),
                "nivel_tinta": getattr(eq, "nivel_tinta", None),
                "calidad_impresion": getattr(eq, "calidad_impresion", None),
                "pantalla_rota": getattr(eq, "pantalla_rota", None),
                "pin_carga": getattr(eq, "pin_carga", None),
                "costo": str(eq.costo or 0),
                "estado": eq.estado,
                "estado_aprobacion": eq.estado_aprobacion,
                "comentario_dueño": eq.comentario_dueño,
                "instalacion_decision": eq.instalacion_decision,
                "precio_venta": str(eq.precio_venta) if eq.precio_venta else None,
                "repuestos": [
                    {"id": r.id, "proveedor": r.proveedor, "repuesto": r.repuesto, "costo": str(r.costo or 0)}
                    for r in eq.repuestos
                ],
            },
            "cliente": {
                "id": cliente.id,
                "nombre": f"{cliente.nombre} {cliente.apellido}",
                "telefono": cliente.telefono,
                "email": cliente.email,
            },
            "tecnico": f"{tecnico.nombre} {tecnico.apellido}" if tecnico else None,
            "orden_id": eq.orden_id,
            "numero_orden": eq.orden.numero_orden,
        })
    return respuesta


# ------------------------------------------------------------
# 5) WhatsApp: Link del diagnóstico para el dueño
# ------------------------------------------------------------
@router.get(
    "/diagnosticos/{equipo_id}/whatsapp",
    summary="WhatsApp del diagnóstico",
    description="Genera un link de WhatsApp con los datos del diagnóstico para que el dueño llame al cliente y cierre la venta."
)
async def whatsapp_diagnostico(
    equipo_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Genera un mensaje de WhatsApp prellenado con el diagnóstico del equipo."""
    result = await db.execute(
        select(EquipoOrden)
        .options(joinedload(EquipoOrden.repuestos),
                 joinedload(EquipoOrden.orden).joinedload(OrdenServicio.cliente))
        .where(EquipoOrden.id == equipo_id)
    )
    equipo = result.unique().scalar_one_or_none()
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    cliente = equipo.orden.cliente
    telefono = cliente.telefono or ""

    # Armar mensaje con los datos del diagnóstico
    repuestos_lineas = ""
    if equipo.repuestos:
        lineas = []
        for r in equipo.repuestos:
            linea = f"  - {r.proveedor or ''}: {r.repuesto or ''} (${r.costo or 0})"
            lineas.append(linea)
        repuestos_lineas = "\n".join(lineas)

    mensaje = (
        f"📋 *Diagnóstico técnico* — {equipo.orden.numero_orden}\n"
        f"👤 Cliente: {cliente.nombre} {cliente.apellido}\n"
        f"📞 Tlf: {telefono}\n"
        f"🖥️ Equipo: {_valor_enum(equipo.tipo_equipo)} {equipo.marca or ''} {equipo.modelo or ''}\n"
        f"⚡ Enciende: {equipo.enciende or '—'}\n"
        f"💾 Disco: {equipo.tipo_disco or '—'} · {equipo.capacidad_disco or ''}\n"
        f"🧠 Memoria: {equipo.tipo_memoria or '—'} · {equipo.capacidad_memoria or ''}\n"
        f"⬆️ Slot M2: {equipo.slot_m2 or '—'} · Caddy: {equipo.slot_caddy or '—'}\n"
        f"🔧 Procesador: {equipo.procesador or '—'}\n"
    )
    if _valor_enum(equipo.tipo_equipo) == 'impresora':
        mensaje += (
            f"🖨️ Toma papel: {getattr(equipo, 'toma_papel', '') or '—'}\n"
            f"💧 Nivel tinta: {getattr(equipo, 'nivel_tinta', '') or '—'}\n"
            f"📄 Calidad imp.: {getattr(equipo, 'calidad_impresion', '') or '—'}\n"
        )
    elif _valor_enum(equipo.tipo_equipo) == 'telefono':
        mensaje += (
            f"📱 Pantalla rota: {getattr(equipo, 'pantalla_rota', '') or '—'}\n"
            f"🔌 Pin de carga: {getattr(equipo, 'pin_carga', '') or '—'}\n"
        )

    if equipo.diagnostico:
        mensaje += f"\n🩺 Diagnóstico:\n{equipo.diagnostico}\n"
    if repuestos_lineas:
        mensaje += f"\n💲 Repuestos:\n{repuestos_lineas}\n"

    link = generar_link_whatsapp(telefono, mensaje)
    return {"link": link, "mensaje": mensaje}
