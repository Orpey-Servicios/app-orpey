"""
Router de Notas de Venta - Generación de notas de venta (facturación simple).

Endpoints:
- POST /api/notas-venta          → Crear nota de venta desde una orden
- GET /api/notas-venta           → Listar notas de venta
- GET /api/notas-venta/{id}      → Ver nota de venta
- GET /api/notas-venta/{id}/pdf  → Generar PDF de nota de venta

La nota de venta se genera a partir de una orden cerrada/entregada.
Calcula automáticamente subtotal, IVA (15%) y total.
"""

from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.models.models import NotaVenta, OrdenServicio, Cliente, ConfiguracionSistema
from src.schemas.schemas import NotaVentaCreate, NotaVentaResponse
from src.services.pdf_generator import crear_pdf_nota_venta

router = APIRouter(
    prefix="/api/notas-venta",
    tags=["Notas de Venta"]
)


@router.post(
    "/",
    response_model=NotaVentaResponse,
    status_code=201,
    summary="Crear nota de venta",
    description="Genera una nota de venta a partir de una orden de servicio."
)
async def crear_nota_venta(
    datos: NotaVentaCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Crea una nota de venta a partir de una orden.

    **Cálculos automáticos:**
    - IVA: 15% del subtotal (configurable en el sistema)
    - Subtotal: total_orden / 1.15
    - Total: subtotal + IVA

    **Ejemplo:**
    Si la orden tiene un total de $115.00:
    - Subtotal: $100.00
    - IVA (15%): $15.00
    - Total: $115.00
    """
    # Verificar que la orden existe
    result = await db.execute(select(OrdenServicio).where(OrdenServicio.id == datos.orden_servicio_id))
    orden = result.scalar_one_or_none()

    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    # Obtener el IVA configurado
    result = await db.execute(
        select(ConfiguracionSistema).where(ConfiguracionSistema.clave == "iva_porcentaje")
    )
    config_iva = result.scalar_one_or_none()
    iva_porcentaje = Decimal(config_iva.valor) if config_iva else Decimal("15")

    # Calcular subtotal e IVA
    total_orden = Decimal(str(orden.total_orden))
    subtotal = total_orden / (1 + (iva_porcentaje / 100))
    iva = total_orden - subtotal

    # Crear la nota de venta (el número se genera con trigger en la BD)
    nota_venta = NotaVenta(
        orden_servicio_id=datos.orden_servicio_id,
        cliente_id=datos.cliente_id,
        subtotal=subtotal,
        iva=iva,
        total=total_orden,
    )

    db.add(nota_venta)
    await db.commit()
    await db.refresh(nota_venta)

    return nota_venta


@router.get(
    "/",
    response_model=list[NotaVentaResponse],
    summary="Listar notas de venta",
    description="Lista todas las notas de venta generadas."
)
async def listar_notas_venta(
    db: AsyncSession = Depends(get_db)
):
    """Lista todas las notas de venta."""
    result = await db.execute(select(NotaVenta).order_by(NotaVenta.id.desc()))
    return result.scalars().all()


@router.get(
    "/{nota_id}",
    response_model=NotaVentaResponse,
    summary="Obtener nota de venta",
    description="Obtiene una nota de venta específica."
)
async def obtener_nota_venta(
    nota_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene una nota de venta por ID."""
    result = await db.execute(select(NotaVenta).where(NotaVenta.id == nota_id))
    nota = result.scalar_one_or_none()

    if not nota:
        raise HTTPException(status_code=404, detail="Nota de venta no encontrada")

    return nota


@router.get(
    "/{nota_id}/pdf",
    summary="Generar PDF de nota de venta",
    description="Genera y descarga un PDF de la nota de venta."
)
async def generar_pdf_nota(
    nota_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Genera un PDF de la nota de venta.

    Incluye:
    - Logo y nombre del negocio
    - Datos del cliente
    - Detalle del servicio
    - Totales (subtotal, IVA, total)
    """
    # Obtener la nota
    result = await db.execute(select(NotaVenta).where(NotaVenta.id == nota_id))
    nota = result.scalar_one_or_none()

    if not nota:
        raise HTTPException(status_code=404, detail="Nota de venta no encontrada")

    # Obtener la orden
    result = await db.execute(select(OrdenServicio).where(OrdenServicio.id == nota.orden_servicio_id))
    orden = result.scalar_one_or_none()

    # Obtener el cliente
    result = await db.execute(select(Cliente).where(Cliente.id == nota.cliente_id))
    cliente = result.scalar_one_or_none()

    # Obtener configuración
    result = await db.execute(select(ConfiguracionSistema))
    config_rows = result.scalars().all()
    config_data = {row.clave: row.valor for row in config_rows}

    # Preparar datos
    nota_data = {
        'numero_nota': nota.numero_nota,
        'fecha_emision': nota.fecha_emision.isoformat() if nota.fecha_emision else None,
        'subtotal': float(nota.subtotal),
        'iva': float(nota.iva),
        'total': float(nota.total),
    }

    orden_data = {
        'numero_orden': orden.numero_orden,
        'tipo_equipo': orden.tipo_equipo.value if hasattr(orden.tipo_equipo, 'value') else str(orden.tipo_equipo),
        'marca': orden.marca,
        'modelo': orden.modelo,
        'descripcion_problema': orden.descripcion_problema,
    }

    cliente_data = {
        'nombre': cliente.nombre,
        'apellido': cliente.apellido,
        'telefono': cliente.telefono,
        'cedula_ruc': cliente.cedula_ruc or 'No registrado',
    }

    # Generar PDF
    pdf_buffer = crear_pdf_nota_venta(nota_data, orden_data, cliente_data, config_data)

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=nota_venta_{nota.numero_nota}.pdf"
        }
    )
