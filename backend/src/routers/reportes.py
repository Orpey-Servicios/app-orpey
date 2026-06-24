"""
Router de Reportes - Generación de PDFs y links de WhatsApp.

Endpoints:
- GET /api/reportes/orden/{id}/pdf → Genera PDF de orden de servicio
- GET /api/reportes/orden/{id}/whatsapp → Genera link de WhatsApp para la orden
- GET /api/reportes/cotizacion/{id}/whatsapp → Genera link de WhatsApp para cotización
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.config.database import get_db
from src.models.models import OrdenServicio, Cotizacion, Cliente, Tecnico
from src.services.pdf_generator import crear_pdf_orden
from src.services.whatsapp import generar_link_whatsapp, generar_mensaje_orden, generar_mensaje_cotizacion

router = APIRouter(
    prefix="/api/reportes",
    tags=["Reportes"]
)


@router.get(
    "/orden/{orden_id}/pdf",
    summary="Generar PDF de orden de servicio",
    description="Genera y descarga un PDF con los datos de la orden de servicio."
)
async def generar_pdf_orden(
    orden_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Genera un PDF de la orden de servicio.

    El PDF incluye:
    - Logo y nombre del negocio
    - Datos del cliente
    - Datos del equipo
    - Diagnóstico y trabajo
    - Datos financieros (total, abono, por cancelar)
    - Términos y condiciones
    """
    # Obtener la orden
    result = await db.execute(
        select(OrdenServicio)
        .options(joinedload(OrdenServicio.equipos))
        .where(OrdenServicio.id == orden_id)
    )
    orden = result.unique().scalar_one_or_none()

    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    # Obtener el cliente
    result = await db.execute(select(Cliente).where(Cliente.id == orden.cliente_id))
    cliente = result.scalar_one_or_none()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Obtener el técnico si existe
    tecnico = None
    if orden.tecnico_id:
        result = await db.execute(select(Tecnico).where(Tecnico.id == orden.tecnico_id))
        tecnico = result.scalar_one_or_none()

    # Obtener configuración del negocio
    from src.models.models import ConfiguracionSistema
    result = await db.execute(select(ConfiguracionSistema))
    config_rows = result.scalars().all()
    config_data = {row.clave: row.valor for row in config_rows if row.valor is not None}

    # Preparar datos para el PDF
    equipos_data = []
    for eq in orden.equipos:
        equipos_data.append({
            'tipo_equipo': eq.tipo_equipo.value if hasattr(eq.tipo_equipo, 'value') else str(eq.tipo_equipo or 'otro'),
            'marca': eq.marca or 'N/A',
            'modelo': eq.modelo or 'N/A',
            'cable': bool(eq.cable),
            'cargador': bool(eq.cargador),
            'contrasena': eq.contrasena or 'Ninguna',
            'descripcion_problema': eq.descripcion_problema or 'Sin descripción',
            'diagnostico': eq.diagnostico or 'Pendiente',
            'trabajo_a_realizar': eq.trabajo_a_realizar or 'Pendiente',
            'estado': eq.estado.value if hasattr(eq.estado, 'value') else str(eq.estado or 'revision'),
        })

    orden_data = {
        'numero_orden': orden.numero_orden,
        'equipos': equipos_data,
        'estado': orden.estado.value if hasattr(orden.estado, 'value') else str(orden.estado or 'revision'),
        'total_orden': float(orden.total_orden or 0),
        'abono': float(orden.abono or 0),
        'garantia_dias': int(orden.garantia_dias or 0),
        'fecha_ingreso': orden.fecha_ingreso.isoformat() if orden.fecha_ingreso else None,
    }

    # Agregar datos del técnico si existe
    if tecnico:
        orden_data['tecnico_nombre'] = tecnico.nombre
        orden_data['tecnico_apellido'] = tecnico.apellido
    else:
        orden_data['tecnico_nombre'] = 'No'
        orden_data['tecnico_apellido'] = 'asignado'

    cliente_data = {
        'nombre': cliente.nombre,
        'apellido': cliente.apellido,
        'telefono': cliente.telefono,
        'email': cliente.email or 'No registrado',
        'direccion': cliente.direccion or 'No registrada',
        'cedula_ruc': cliente.cedula_ruc or 'No registrado',
    }

    # Generar el PDF
    pdf_buffer = crear_pdf_orden(orden_data, cliente_data, config_data)

    # Devolver el PDF como archivo descargable
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=orden_{orden.numero_orden}.pdf"
        }
    )


@router.get(
    "/orden/{orden_id}/whatsapp",
    summary="Generar link de WhatsApp para orden",
    description="Genera un link wa.me con mensaje prellenado para enviar la orden por WhatsApp."
)
async def generar_whatsapp_orden(
    orden_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Genera un link de WhatsApp para enviar la orden.

    El link abre WhatsApp Web/App con un mensaje prellenado.
    El usuario debe adjuntar el PDF manualmente.

    **Ejemplo de respuesta:**
    ```json
    {
        "link": "https://wa.me/593985983416?text=Hola+Gerardo...",
        "telefono": "593985983416",
        "mensaje": "Hola Gerardo, te saludo de Orpey Servicios..."
    }
    ```
    """
    # Obtener la orden
    result = await db.execute(
        select(OrdenServicio)
        .options(joinedload(OrdenServicio.equipos))
        .where(OrdenServicio.id == orden_id)
    )
    orden = result.unique().scalar_one_or_none()

    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    # Obtener el cliente
    result = await db.execute(select(Cliente).where(Cliente.id == orden.cliente_id))
    cliente = result.scalar_one_or_none()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Preparar datos del equipo
    if orden.equipos:
        eq = orden.equipos[0]
        tipo_equipo = eq.tipo_equipo.value if hasattr(eq.tipo_equipo, 'value') else str(eq.tipo_equipo)
        equipo_str = f"{tipo_equipo} {eq.marca or ''} {eq.modelo or ''}".strip()
    else:
        equipo_str = "Equipo(s)"
    estado_str = orden.estado.value if hasattr(orden.estado, 'value') else str(orden.estado)
    estado_display = estado_str.replace('_', ' ').title()

    # Generar mensaje y link
    nombre_completo = f"{cliente.nombre} {cliente.apellido}"
    mensaje = generar_mensaje_orden(
        numero_orden=orden.numero_orden,
        cliente_nombre=nombre_completo,
        equipo=equipo_str,
        estado=estado_display
    )

    link = generar_link_whatsapp(cliente.telefono, mensaje)

    return {
        "link": link,
        "telefono": cliente.telefono,
        "mensaje": mensaje
    }


@router.get(
    "/cotizacion/{cotizacion_id}/whatsapp",
    summary="Generar link de WhatsApp para cotización",
    description="Genera un link wa.me con mensaje prellenado para enviar la cotización por WhatsApp."
)
async def generar_whatsapp_cotizacion(
    cotizacion_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Genera un link de WhatsApp para enviar la cotización.
    """
    # Obtener la cotización
    result = await db.execute(select(Cotizacion).where(Cotizacion.id == cotizacion_id))
    cotizacion = result.scalar_one_or_none()

    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")

    # Obtener el cliente
    result = await db.execute(select(Cliente).where(Cliente.id == cotizacion.cliente_id))
    cliente = result.scalar_one_or_none()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Generar mensaje y link
    nombre_completo = f"{cliente.nombre} {cliente.apellido}"
    mensaje = generar_mensaje_cotizacion(
        numero_cotizacion=cotizacion.numero_cotizacion,
        cliente_nombre=nombre_completo,
        total=str(cotizacion.total)
    )

    link = generar_link_whatsapp(cliente.telefono, mensaje)

    return {
        "link": link,
        "telefono": cliente.telefono,
        "mensaje": mensaje
    }
