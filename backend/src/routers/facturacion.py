"""
Router de Facturación Electrónica SRI - Comprobantes electrónicos (factura 01).

Endpoints:
- POST /api/facturacion/generar           → Genera factura electrónica firmada (XAdES-BES)
- GET  /api/facturacion                   → Lista facturas electrónicas generadas
- GET  /api/facturacion/{id}/xml          → Descarga el XML firmado
- POST /api/facturacion/{id}/transmitir   → Transmite y autoriza al SRI (SOAP)

FLUJO (fase 2 - TRANSMISIÓN):
- `generar` SOLO genera y firma localmente (ambiente "1" por defecto).
- `transmitir` toma una factura firmada, la envía por SOAP al SRI (recepción
  + autorización), actualiza estado_sri y guarda el número/fecha de
  autorización (o el detalle de errores si es devuelta/no autorizada).
- GUARDA DE SEGURIDAD: no se transmite a producción (ambiente "2") sin
  confirmación explícita `confirmar_produccion: true` en el body.
- `forzar_ambiente` permite re-transmitir en pruebas una factura marcada como
  producción (o viceversa) para testing.
"""

import base64
import os
from datetime import datetime, time
from decimal import Decimal
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from src.config.database import get_db
from src.models.models import (
    FacturaElectronica, OrdenServicio, NotaVenta, Cliente, ConfiguracionSistema,
    Usuario, RolUsuario,
)
from src.schemas.schemas import (
    FacturaElectronicaCreate, FacturaElectronicaResponse, NotaCreditoRequest,
)
from src.services.facturacion_sri import (
    _round2,
    firmar_xml,
    generar_comprobante_factura,
    generar_comprobante_nota_credito,
    siguiente_secuencial,
    siguiente_secuencial_nota_credito,
    obtener_password_firma,
)
from src.services.transmision_sri import (
    ErrorTransmisionSRI,
    consultar_autorizacion,
    transmitir_y_autorizar,
)
from src.utils.auth import get_current_user

router = APIRouter(
    prefix="/api/facturacion",
    tags=["Facturación Electrónica SRI"],
)

# Ruta por defecto de la firma digital (configurable en configuracion_sistema)
FIRMA_P12_DEFAULT = "/home/skorggamor/agente-contador/firmadigital.p12"

# Colores para el PDF de factura
_FACTURA_PRIMARY = HexColor("#FBC305")
_FACTURA_SECONDARY = HexColor("#353534")
_FACTURA_ACCENT = HexColor("#E5E7EB")
_FACTURA_LIGHT = HexColor("#FFF3CC")
_FACTURA_WHITE = HexColor("#ffffff")
_FACTURA_DARK = HexColor("#1F2937")
_FACTURA_GRAY = HexColor("#6B7280")
_FACTURA_RED = HexColor("#DC2626")

# Datos del emisor (contribuyente)
_EMISOR_RAZON = "BALTODANO Catarine Daniel ABRAHAM"
_EMISOR_RUC = "0964794234001"
_EMISOR_DIRECCION = "Guayaquil, Bastión Popular, Bloque 2, Solar 7"
_EMISOR_REGIMEN = "Régimen General"


def _obtener_logo_factura(height: int = 45):
    """Carga el logo de Orpey para el PDF de factura."""
    rutas = [
        "/home/skorggamor/app-orpey/frontend/dist/logo-orpey.png",
        "/home/skorggamor/app-orpey/frontend/public/logo-orpey.png",
        "/home/skorggamor/app-orpey/datos-orpey/logo-orpey-png.png",
    ]
    for ruta in rutas:
        if os.path.exists(ruta):
            try:
                from reportlab.lib.utils import ImageReader
                img = ImageReader(ruta)
                w, h_img = img.getSize()
                if h_img > 0:
                    aspect = w / float(h_img)
                    actual_width = height * aspect
                    return Image(ruta, width=actual_width, height=height, kind='proportional')
                return Image(ruta, width=140, height=height, kind='proportional')
            except Exception:
                continue
    # Fallback: texto estilizado
    from reportlab.platypus.flowables import Flowable

    class _LogoFallback(Flowable):
        def __init__(self, w=None, h=None, width=None, height=None):
            Flowable.__init__(self)
            self.width = width if width is not None else (w if w is not None else 140)
            self.height = height if height is not None else (h if h is not None else 45)

        def wrap(self, availWidth, availHeight):
            return (self.width, self.height)

        def draw(self):
            self.canv.setFillColor(_FACTURA_SECONDARY)
            self.canv.roundRect(0, 0, self.width, self.height, 8, fill=1, stroke=0)
            self.canv.setFillColor(_FACTURA_PRIMARY)
            self.canv.setFont("Helvetica-Bold", 18)
            self.canv.drawCentredString(self.width / 2, self.height / 2 - 6, "ORPEY")
            self.canv.setFillColor(_FACTURA_WHITE)
            self.canv.setFont("Helvetica-Bold", 10)
            self.canv.drawString(12, 6, "SERVICIOS Técnicos")

    return _LogoFallback(width=140, height=height)


def _generar_pdf_factura(factura, cliente, equipos=None):
    """
    Genera un PDF de factura electrónica con formato SRI.

    Args:
        factura: instancia de FacturaElectronica
        cliente: instancia de Cliente (o None)
        equipos: lista de EquipoOrden (o None)

    Returns:
        bytes del PDF generado
    """
    from reportlab.platypus import Image

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=15,
        bottomMargin=20,
        title=f"Factura {factura.numero_documento}",
    )

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        'SeccionFac', parent=styles['Heading2'], fontName='Helvetica-Bold',
        fontSize=10, textColor=_FACTURA_SECONDARY, spaceBefore=8, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        'CampoFac', parent=styles['Normal'], fontName='Helvetica',
        fontSize=9, textColor=_FACTURA_DARK, spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        'CampoFacR', parent=styles['CampoFac'], alignment=TA_RIGHT,
    ))
    styles.add(ParagraphStyle(
        'CampoFacB', parent=styles['CampoFac'], fontName='Helvetica-Bold',
    ))
    styles.add(ParagraphStyle(
        'SmallFac', parent=styles['Normal'], fontName='Helvetica',
        fontSize=7.5, textColor=_FACTURA_GRAY, spaceAfter=1,
    ))

    es_autorizada = factura.estado_sri == "autorizado"
    ambiente_str = "PRODUCCIÓN" if factura.ambiente == "2" else "PRUEBAS"

    # --- Fecha emisión formateada ---
    fecha_emision = factura.fecha_emision
    fecha_str = "N/A"
    hora_str = ""
    if fecha_emision:
        if isinstance(fecha_emision, str):
            try:
                dt = datetime.fromisoformat(fecha_emision.replace("Z", "+00:00"))
                fecha_str = dt.strftime("%d/%m/%Y")
                hora_str = dt.strftime("%H:%M")
            except ValueError:
                fecha_str = fecha_emision[:10]
        else:
            fecha_str = fecha_emision.strftime("%d/%m/%Y")
            hora_str = fecha_emision.strftime("%H:%M")

    contenido = []

    # ===================== ENCABEZADO =====================
    logo = _obtener_logo_factura(height=45)
    encabezado = [
        [
            logo,
            Paragraph(
                f"<b><font color='#353534' size='12'>FACTURA</font></b><br/>"
                f"<b><font color='#FBC305' size='11'>{factura.numero_documento}</font></b>",
                styles['Normal'],
            ),
            Paragraph(
                f"<b>Ambiente:</b> {ambiente_str}<br/>"
                f"<b>Fecha:</b> {fecha_str}",
                ParagraphStyle('FacFecha', parent=styles['Normal'], alignment=TA_RIGHT, leading=12),
            ),
        ]
    ]
    tabla_enc = Table(encabezado, colWidths=[150, 210, 140], hAlign='LEFT')
    tabla_enc.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
    ]))
    contenido.append(tabla_enc)
    contenido.append(HRFlowable(width="100%", thickness=2, color=_FACTURA_PRIMARY, spaceBefore=6, spaceAfter=6))

    # ===================== DATOS DEL EMISOR =====================
    contenido.append(Paragraph("DATOS DEL EMISOR", styles['SeccionFac']))
    emisor_data = [
        [Paragraph(f"<b>Razón Social:</b> {_EMISOR_RAZON}", styles['CampoFac'])],
        [Paragraph(f"<b>RUC:</b> {_EMISOR_RUC}", styles['CampoFac'])],
        [Paragraph(f"<b>Dirección:</b> {_EMISOR_DIRECCION}", styles['CampoFac'])],
        [Paragraph(f"<b>Régimen:</b> {_EMISOR_REGIMEN}", styles['CampoFac'])],
    ]
    t_emisor = Table(emisor_data, colWidths=[500], hAlign='LEFT')
    t_emisor.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), _FACTURA_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.5, _FACTURA_ACCENT),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    contenido.append(t_emisor)

    # ===================== CLAVE DE ACCESO =====================
    contenido.append(Spacer(1, 6))
    clave_data = [
        [Paragraph(f"<b>Clave de Acceso:</b> {factura.clave_acceso}", styles['CampoFacB'])]
    ]
    t_clave = Table(clave_data, colWidths=[500], hAlign='LEFT')
    t_clave.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), _FACTURA_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.5, _FACTURA_ACCENT),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    contenido.append(t_clave)

    # ===================== NÚMERO DE AUTORIZACIÓN =====================
    if es_autorizada and factura.numero_autorizacion:
        contenido.append(Spacer(1, 6))
        fecha_aut = ""
        if factura.fecha_autorizacion:
            if isinstance(factura.fecha_autorizacion, str):
                try:
                    dt = datetime.fromisoformat(factura.fecha_autorizacion.replace("Z", "+00:00"))
                    fecha_aut = dt.strftime("%d/%m/%Y %H:%M")
                except ValueError:
                    fecha_aut = str(factura.fecha_autorizacion)[:16]
            else:
                fecha_aut = factura.fecha_autorizacion.strftime("%d/%m/%Y %H:%M")
        auth_data = [
            [Paragraph(
                f"<b><font color='#16A34A' size='11'>N° Autorización: {factura.numero_autorizacion}</font></b>",
                styles['Normal'],
            )],
            [Paragraph(
                f"<b>Fecha Autorización:</b> {fecha_aut}",
                styles['CampoFac'],
            )],
        ]
        t_auth = Table(auth_data, colWidths=[500], hAlign='LEFT')
        t_auth.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor("#F0FDF4")),
            ('BOX', (0, 0), (-1, -1), 0.5, HexColor("#16A34A")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ]))
        contenido.append(t_auth)

    # ===================== DATOS DEL CLIENTE =====================
    contenido.append(Spacer(1, 8))
    contenido.append(Paragraph("DATOS DEL CLIENTE", styles['SeccionFac']))
    if cliente:
        cliente_filas = [
            [Paragraph(f"<b>Nombre:</b> {cliente.nombre} {cliente.apellido}", styles['CampoFac'])],
            [Paragraph(f"<b>Cédula/RUC:</b> {cliente.cedula_ruc or 'N/A'}", styles['CampoFac'])],
        ]
        if cliente.direccion:
            cliente_filas.append(
                Paragraph(f"<b>Dirección:</b> {cliente.direccion}", styles['CampoFac'])
            )
    else:
        cliente_filas = [[Paragraph("<i>Cliente no especificado</i>", styles['CampoFac'])]]
    t_cliente = Table(cliente_filas, colWidths=[500], hAlign='LEFT')
    t_cliente.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), _FACTURA_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.5, _FACTURA_ACCENT),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    contenido.append(t_cliente)

    # ===================== DETALLE =====================
    contenido.append(Spacer(1, 8))
    contenido.append(Paragraph("DETALLE", styles['SeccionFac']))

    header_style = ParagraphStyle(
        'DetHdr', parent=styles['Normal'], fontName='Helvetica-Bold',
        fontSize=8, textColor=_FACTURA_WHITE,
    )
    header_style_r = ParagraphStyle('DetHdrR', parent=header_style, alignment=TA_RIGHT)

    tabla_det = [[
        Paragraph("<b>Descripción</b>", header_style),
        Paragraph("<b>Subtotal</b>", header_style_r),
    ]]

    subtotal_val = float(factura.subtotal or 0)
    equipo_count = 0

    if equipos:
        for eq in equipos:
            tipo_map = {
                'pc_escritorio': 'PC', 'laptop': 'Laptop', 'impresora': 'Impresora',
                'telefono': 'Teléfono', 'otro': 'Otro',
            }
            tipo_label = tipo_map.get(
                eq.tipo_equipo.value if hasattr(eq.tipo_equipo, 'value') else str(eq.tipo_equipo),
                'Equipo',
            )
            desc_parts = [tipo_label]
            if eq.marca:
                desc_parts.append(eq.marca)
            if eq.modelo:
                desc_parts.append(eq.modelo)
            desc = " ".join(desc_parts)
            costo = float(eq.costo or 0)
            tabla_det.append([
                Paragraph(desc, styles['CampoFac']),
                Paragraph(f"$ {costo:.2f}", styles['CampoFacR']),
            ])
            equipo_count += 1

    if equipo_count == 0:
        tabla_det.append([
            Paragraph("SERVICIO TÉCNICO", styles['CampoFac']),
            Paragraph(f"$ {subtotal_val:.2f}", styles['CampoFacR']),
        ])

    total_val = float(factura.total or 0)
    iva_val = float(factura.iva or 0)

    tabla_det.append([Paragraph("", styles['CampoFac']), Paragraph("")])
    tabla_det.append([
        Paragraph("<b>Subtotal 15%</b>", styles['CampoFacB']),
        Paragraph(f"<b>$ {subtotal_val:.2f}</b>", styles['CampoFacR']),
    ])
    tabla_det.append([
        Paragraph("<b>IVA 15%</b>", styles['CampoFacB']),
        Paragraph(f"<b>$ {iva_val:.2f}</b>", styles['CampoFacR']),
    ])
    tabla_det.append([
        Paragraph("<b><font color='#353534' size='11'>TOTAL</font></b>", styles['Normal']),
        Paragraph(f"<b><font color='#353534' size='11'>$ {total_val:.2f}</font></b>", styles['CampoFacR']),
    ])

    t_det = Table(tabla_det, colWidths=[350, 150])
    estilos_det = [
        ('BACKGROUND', (0, 0), (-1, 0), _FACTURA_SECONDARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), _FACTURA_WHITE),
        ('GRID', (0, 0), (-1, 0), 0.5, _FACTURA_ACCENT),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]
    if len(tabla_det) > 1:
        estilos_det.append(('ROWBACKGROUNDS', (0, 1), (-1, len(tabla_det) - 4), [_FACTURA_WHITE, _FACTURA_LIGHT]))
    num = len(tabla_det)
    estilos_det.append(('LINEABOVE', (0, num - 3), (-1, num - 3), 0.5, _FACTURA_ACCENT))
    estilos_det.append(('LINEABOVE', (0, num - 1), (-1, num - 1), 1.5, _FACTURA_SECONDARY))
    estilos_det.append(('BACKGROUND', (0, num - 1), (-1, num - 1), _FACTURA_LIGHT))
    t_det.setStyle(TableStyle(estilos_det))
    contenido.append(t_det)

    # ===================== FOOTER =====================
    contenido.append(Spacer(1, 15))
    contenido.append(HRFlowable(width="100%", thickness=1.5, color=_FACTURA_PRIMARY, spaceBefore=6, spaceAfter=6))

    if es_autorizada:
        contenido.append(Paragraph(
            f"<b>N° Autorización:</b> {factura.numero_autorizacion}",
            ParagraphStyle('FootAuth', parent=styles['Normal'], fontName='Helvetica-Bold',
                           fontSize=9, textColor=_FACTURA_DARK),
        ))
        contenido.append(Paragraph(
            "<b>CONSULTE:</b> https://cel.sri.gob.ec/",
            styles['SmallFac'],
        ))
    else:
        warning_style = ParagraphStyle(
            'WarnFac', parent=styles['Normal'], fontName='Helvetica-Bold',
            fontSize=12, textColor=_FACTURA_RED, alignment=TA_CENTER, spaceBefore=6, spaceAfter=6,
        )
        contenido.append(Paragraph("DOCUMENTO SIN AUTORIZACIÓN", warning_style))

    doc.build(contenido)
    return buffer.getvalue()


async def get_current_user_optional(
    authorization: str = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> Optional[Usuario]:
    """Igual que get_current_user pero devuelve None si no hay token válido."""
    if not authorization:
        return None
    try:
        return await get_current_user(authorization, db)
    except HTTPException:
        return None


def _es_admin(current_user: Optional[Usuario]) -> bool:
    if current_user is None:
        return False
    return current_user.rol == RolUsuario.admin


async def _cargar_fuente(datos: FacturaElectronicaCreate, db: AsyncSession):
    """
    Carga la orden (o nota de venta) con su cliente y equipos.
    Devuelve (orden_dict, cliente_dict, cliente_id).
    Solo LECTURA — nunca modifica datos de órdenes/clientes.
    """
    if datos.orden_servicio_id:
        result = await db.execute(
            select(OrdenServicio)
            .options(
                joinedload(OrdenServicio.cliente),
                selectinload(OrdenServicio.equipos),
            )
            .where(OrdenServicio.id == datos.orden_servicio_id)
        )
        orden = result.scalar_one_or_none()
        if not orden:
            raise HTTPException(status_code=404, detail="Orden de servicio no encontrada")
        cliente: Cliente = orden.cliente
        equipos = orden.equipos
    else:
        result = await db.execute(
            select(NotaVenta).where(NotaVenta.id == datos.nota_venta_id)
        )
        nota = result.scalar_one_or_none()
        if not nota:
            raise HTTPException(status_code=404, detail="Nota de venta no encontrada")
        result = await db.execute(
            select(Cliente).where(Cliente.id == nota.cliente_id)
        )
        cliente = result.scalar_one_or_none()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente de la nota de venta no encontrado")
        result = await db.execute(
            select(OrdenServicio).where(OrdenServicio.id == nota.orden_servicio_id)
        )
        orden = result.scalar_one_or_none()
        equipos = []

    cliente_id = cliente.id

    orden_dict = {
        "id": orden.id,
        "numero_orden": orden.numero_orden,
        "total_orden": orden.total_orden,
        "abono": orden.abono,
        "estado": orden.estado.value if hasattr(orden.estado, "value") else str(orden.estado),
        "equipos": [
            {
                "tipo_equipo": eq.tipo_equipo,
                "marca": eq.marca,
                "modelo": eq.modelo,
                "descripcion_problema": eq.descripcion_problema,
                "costo": eq.costo,
            }
            for eq in (equipos or [])
        ],
    }
    cliente_dict = {
        "nombre": cliente.nombre,
        "apellido": cliente.apellido,
        "nombre_completo": f"{cliente.nombre} {cliente.apellido}".strip(),
        "cedula_ruc": cliente.cedula_ruc,
        "direccion": cliente.direccion,
    }
    return orden_dict, cliente_dict, cliente_id


@router.post(
    "/generar",
    response_model=FacturaElectronicaResponse,
    status_code=201,
    summary="Generar factura electrónica",
    description=(
        "Genera el XML de factura electrónica (comprobante 01) firmado en "
        "XAdES-BES con los datos reales de la orden/nota. Ambiente '1' "
        "(pruebas) por defecto. NO transmite al SRI."
    ),
)
async def generar_factura_electronica(
    datos: FacturaElectronicaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Usuario] = Depends(get_current_user_optional),
):
    """Genera, firma y persiste una factura electrónica en modo pruebas."""
    # Ambiente "2" (producción) requiere override explícito de admin
    if datos.ambiente == "2" and not _es_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Ambiente de producción '2' solo disponible para administradores",
        )

    if not datos.orden_servicio_id and not datos.nota_venta_id:
        raise HTTPException(
            status_code=400,
            detail="Debe indicar orden_servicio_id o nota_venta_id",
        )
    if datos.orden_servicio_id and datos.nota_venta_id:
        raise HTTPException(
            status_code=400,
            detail="Indique solo uno de los dos: orden_servicio_id o nota_venta_id",
        )

    # Configuración del sistema (IVA + firma digital)
    result = await db.execute(select(ConfiguracionSistema))
    cfg_rows = result.scalars().all()
    cfg = {row.clave: row.valor for row in cfg_rows}
    config = {"iva_porcentaje": Decimal(str(cfg.get("iva_porcentaje", "15")))}
    ruta_p12 = cfg.get("firma_p12_ruta") or FIRMA_P12_DEFAULT

    # Cargar orden/cliente (solo LECTURA)
    orden_dict, cliente_dict, cliente_id = await _cargar_fuente(datos, db)

    # Validación anti-duplicado (integridad SRI): una sola factura electrónica
    # por orden/nota. Se revisa ANTES de firmar para no gastar la firma en un
    # comprobante inválido.
    if datos.orden_servicio_id:
        result = await db.execute(
            select(FacturaElectronica.id).where(
                FacturaElectronica.orden_servicio_id == datos.orden_servicio_id
            )
        )
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=400,
                detail="La orden de servicio ya tiene una factura electrónica asociada",
            )
    else:
        result = await db.execute(
            select(FacturaElectronica.id).where(
                FacturaElectronica.nota_venta_id == datos.nota_venta_id
            )
        )
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=400,
                detail="La nota de venta ya tiene una factura electrónica asociada",
            )

    # Regla de pago (misma que notas de venta): la orden debe estar al 100%.
    # Comparaciones con Decimal para evitar problemas de precisión.
    total_orden = Decimal(str(orden_dict["total_orden"]))
    abono_orden = Decimal(str(orden_dict["abono"]))
    if total_orden - abono_orden > Decimal("0"):
        raise HTTPException(
            status_code=400,
            detail="La orden debe estar pagada al 100% para generar una factura.",
        )

    # Regla de estado: solo se facturan servicios entregados o terminados
    # (paridad con la UI). Evita facturar órdenes en revisión/reparación.
    if orden_dict["estado"] not in ("entregada", "terminada"):
        raise HTTPException(
            status_code=400,
            detail=(
                "La orden debe estar entregada o terminada para generar una "
                "factura electrónica."
            ),
        )

    # Siguiente secuencial y generación del comprobante (validaciones de negocio)
    secuencial = await siguiente_secuencial(db, datos.ambiente)
    try:
        comprobante = generar_comprobante_factura(
            orden_dict, cliente_dict, config, secuencial, ambiente=datos.ambiente
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Firmar XAdES-BES (si falla → 500, aún nada en BD)
    password_p12 = obtener_password_firma()
    try:
        xml_firmado = firmar_xml(comprobante["xml"], ruta_p12, password_p12)
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo firmar el XML: {exc}",
        )

    # Persistir (rollback si falla, no dejar datos a medias)
    factura = FacturaElectronica(
        orden_servicio_id=datos.orden_servicio_id,
        nota_venta_id=datos.nota_venta_id,
        cliente_id=cliente_id,
        clave_acceso=comprobante["clave_acceso"],
        numero_documento=comprobante["numero_documento"],
        ambiente=comprobante["ambiente"],
        estado_sri="firmado",
        xml_firmado=xml_firmado,
        subtotal=comprobante["subtotal"],
        iva=comprobante["iva"],
        total=comprobante["total"],
    )
    db.add(factura)
    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al guardar la factura en la BD: {exc}",
        )
    await db.refresh(factura)

    return factura


@router.get(
    "/",
    response_model=list[FacturaElectronicaResponse],
    summary="Listar comprobantes electrónicos",
    description=(
        "Lista facturas (01) y notas de crédito (04). Parámetro opcional "
        "'tipo' para filtrar ('01' factura / '04' nota de crédito); sin filtro "
        "muestra todo, con columna tipo_comprobante para distinguir."
    ),
)
async def listar_facturas(
    tipo: Optional[str] = Query(
        default=None,
        description="Filtro por tipo de comprobante: '01' (factura) o '04' (nota de crédito). Sin valor: todos.",
    ),
    db: AsyncSession = Depends(get_db),
):
    q = select(FacturaElectronica)
    if tipo in ("01", "04"):
        q = q.where(FacturaElectronica.tipo_comprobante == tipo)
    q = q.order_by(FacturaElectronica.id.desc())
    result = await db.execute(q)
    return result.scalars().all()


@router.get(
    "/{factura_id}/xml",
    summary="Descargar XML de la factura",
    description=(
        "Devuelve el XML autorizado (con número de autorización) si la factura "
        "está autorizada; en caso contrario devuelve el XML firmado."
    ),
)
async def descargar_xml(factura_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FacturaElectronica).where(FacturaElectronica.id == factura_id))
    factura = result.scalar_one_or_none()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura electrónica no encontrada")

    # Si está autorizada y tiene xml_respuesta_sri con contenido XML, servir ese
    xml_contenido = factura.xml_firmado
    if (
        factura.estado_sri == "autorizado"
        and factura.xml_respuesta_sri
        and "<comprobante" in factura.xml_respuesta_sri
    ):
        xml_contenido = factura.xml_respuesta_sri

    return Response(
        content=xml_contenido,
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="{factura.clave_acceso}.xml"'
        },
    )


@router.get(
    "/{factura_id}/pdf",
    summary="Descargar PDF de la factura electrónica",
    description=(
        "Genera y devuelve un PDF con formato de factura electrónica SRI: "
        "datos del emisor, cliente, detalle, IVA, total y número de autorización."
    ),
)
async def descargar_pdf(factura_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(FacturaElectronica).where(FacturaElectronica.id == factura_id)
    )
    factura = result.scalar_one_or_none()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura electrónica no encontrada")

    # Cargar cliente
    cliente = None
    if factura.cliente_id:
        result = await db.execute(select(Cliente).where(Cliente.id == factura.cliente_id))
        cliente = result.scalar_one_or_none()

    # Cargar equipos de la orden (si existe)
    equipos = []
    if factura.orden_servicio_id:
        result = await db.execute(
            select(OrdenServicio)
            .options(selectinload(OrdenServicio.equipos))
            .where(OrdenServicio.id == factura.orden_servicio_id)
        )
        orden = result.scalar_one_or_none()
        if orden and orden.equipos:
            equipos = orden.equipos

    pdf_bytes = _generar_pdf_factura(factura, cliente, equipos)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{factura.clave_acceso}.pdf"'
        },
    )


@router.post(
    "/{factura_id}/consultar-autorizacion",
    summary="Consultar estado de autorización ante el SRI",
    description=(
        "Consulta al SRI la autorización actual de la factura sin retransmitir. "
        "Si el SRI responde AUTORIZADO, actualiza el estado y guarda el XML. "
        "Requiere rol admin."
    ),
)
async def consultar_estado_autorizacion(
    factura_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Usuario] = Depends(get_current_user_optional),
):
    if not _es_admin(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores pueden consultar autorización")

    result = await db.execute(
        select(FacturaElectronica).where(FacturaElectronica.id == factura_id)
    )
    factura = result.scalar_one_or_none()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura electrónica no encontrada")

    # Cargar ruta p12 desde configuración del sistema
    result = await db.execute(select(ConfiguracionSistema))
    cfg_rows = result.scalars().all()
    cfg = {row.clave: row.valor for row in cfg_rows}
    ruta_p12 = cfg.get("firma_p12_ruta") or FIRMA_P12_DEFAULT

    try:
        resultado = consultar_autorizacion(
            clave_acceso=factura.clave_acceso,
            ambiente=factura.ambiente,
            ruta_p12=ruta_p12,
        )
    except ErrorTransmisionSRI as exc:
        raise HTTPException(
            status_code=502,
            detail=f"No se pudo consultar al SRI: {exc}",
        ) from exc
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al consultar autorización: {exc}",
        )

    estado = (resultado.get("estado") or "").upper()

    if estado == "AUTORIZADO":
        factura.estado_sri = "autorizado"
        factura.numero_autorizacion = resultado.get("numero_autorizacion")
        if resultado.get("xml_autorizado"):
            factura.xml_respuesta_sri = resultado["xml_autorizado"]
        if resultado.get("fecha_autorizacion"):
            try:
                factura.fecha_autorizacion = datetime.fromisoformat(
                    resultado["fecha_autorizacion"].replace("Z", "+00:00")
                )
            except ValueError:
                factura.fecha_autorizacion = None
    elif estado == "EN PROCESO":
        pass  # No cambiar nada, aún procesando
    else:
        # DEVUELTA / NO AUTORIZADO u otro estado
        estado_sri_map = {
            "DEVUELTA": "devuelta",
            "NO AUTORIZADO": "no_autorizado",
        }
        factura.estado_sri = estado_sri_map.get(estado, "recibida")
        errores = resultado.get("mensajes") or []
        if errores:
            factura.xml_respuesta_sri = _formatear_errores(errores)

    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al guardar el resultado de la consulta: {exc}",
        )
    await db.refresh(factura)

    return {
        "id": factura.id,
        "estado_sri": factura.estado_sri,
        "numero_autorizacion": factura.numero_autorizacion,
        "fecha_autorizacion": factura.fecha_autorizacion,
    }


class TransmitirRequest(BaseModel):
    """
    Body del POST /api/facturacion/{id}/transmitir.

    - forzar_ambiente: "1" | "2" | null. Si se indica, sobreescribe el ambiente
      de la factura (útil para re-transmitir en pruebas una factura de
      producción o viceversa). null = usar el ambiente de la factura.
    - confirmar_produccion: si true, permite transmitir una factura cuyo
      ambiente efectivo es "2" (producción) de forma consciente.
    """
    forzar_ambiente: Optional[str] = None
    confirmar_produccion: bool = False


@router.post(
    "/{factura_id}/transmitir",
    summary="Transmitir y autorizar factura al SRI",
    description=(
        "Toma el XML firmado de la factura, lo transmite al SRI (recepción + "
        "autorización SOAP), actualiza estado_sri ('autorizado' / 'devuelta' / "
        "'no_autorizado') y guarda número/fecha de autorización o el detalle "
        "de errores en xml_respuesta_sri."
    ),
)
async def transmitir_factura(
    factura_id: int,
    datos: TransmitirRequest,
    db: AsyncSession = Depends(get_db),
):
    """Transmite una factura firmada al SRI y persiste el resultado."""
    result = await db.execute(
        select(FacturaElectronica).where(FacturaElectronica.id == factura_id)
    )
    factura = result.scalar_one_or_none()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura electrónica no encontrada")

    if not factura.xml_firmado:
        raise HTTPException(
            status_code=400,
            detail="La factura no tiene XML firmado para transmitir",
        )

    # Ambiente efectivo (override para testing)
    ambiente = factura.ambiente
    if datos.forzar_ambiente:
        if datos.forzar_ambiente not in ("1", "2"):
            raise HTTPException(
                status_code=400,
                detail="forzar_ambiente debe ser '1', '2' o null",
            )
        ambiente = datos.forzar_ambiente

    # GUARDA DE SEGURIDAD: producción requiere confirmación explícita
    if ambiente == "2" and not datos.confirmar_produccion:
        raise HTTPException(
            status_code=403,
            detail=(
                "Transmitir a PRODUCCIÓN (ambiente '2') requiere confirmación "
                "explícita. Envía confirmar_produccion: true para proceder."
            ),
        )

    # Resolver ruta del .p12 desde configuración del sistema
    result = await db.execute(select(ConfiguracionSistema))
    cfg_rows = result.scalars().all()
    cfg = {row.clave: row.valor for row in cfg_rows}
    ruta_p12 = cfg.get("firma_p12_ruta") or FIRMA_P12_DEFAULT

    try:
        resultado = transmitir_y_autorizar(
            clave_acceso=factura.clave_acceso,
            xml_firmado=factura.xml_firmado,
            ambiente=ambiente,
            ruta_p12=ruta_p12,
        )
    except ErrorTransmisionSRI as exc:
        raise HTTPException(
            status_code=502,
            detail=f"No se pudo transmitir al SRI: {exc}",
        ) from exc
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al transmitir: {exc}",
        )

    recepcion = resultado["recepcion"]
    autorizacion = resultado["autorizacion"]

    estado_final = recepcion["estado"]
    if recepcion["estado"] == "RECIBIDA" and autorizacion:
        estado_final = autorizacion["estado"]

    # Persistir según el resultado
    errores = recepcion["mensajes"] or (autorizacion["mensajes"] if autorizacion else [])
    if estado_final == "AUTORIZADO" and autorizacion:
        factura.estado_sri = "autorizado"
        factura.numero_autorizacion = autorizacion.get("numero_autorizacion")
        factura.xml_respuesta_sri = (
            autorizacion.get("xml_autorizado") or factura.xml_firmado
        )
        if autorizacion.get("fecha_autorizacion"):
            from datetime import datetime
            try:
                factura.fecha_autorizacion = datetime.fromisoformat(
                    autorizacion["fecha_autorizacion"].replace("Z", "+00:00")
                )
            except ValueError:
                factura.fecha_autorizacion = None
    elif estado_final == "DEVUELTA":
        factura.estado_sri = "devuelta"
        factura.xml_respuesta_sri = _formatear_errores(errores)
    elif estado_final == "NO AUTORIZADO":
        factura.estado_sri = "no_autorizado"
        factura.xml_respuesta_sri = _formatear_errores(errores)
    else:  # EN PROCESO / RECIBIDA sin autorización (no concluyente)
        factura.estado_sri = "recibida"
        factura.xml_respuesta_sri = _formatear_errores(errores)

    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al guardar el resultado de la transmisión: {exc}",
        )
    await db.refresh(factura)

    return {
        "id": factura.id,
        "clave_acceso": factura.clave_acceso,
        "estado_sri": factura.estado_sri,
        "numero_autorizacion": factura.numero_autorizacion,
        "fecha_autorizacion": factura.fecha_autorizacion,
        "errores": errores,
    }


def _formatear_errores(mensajes) -> str:
    """Formatea la lista de mensajes del SRI como texto para xml_respuesta_sri."""
    if not mensajes:
        return ""
    lineas = []
    for m in mensajes:
        lineas.append(
            f"[{m.get('identificador')}] {m.get('mensaje')} "
            f"{m.get('informacionAdicional', '')}".strip()
        )
    return "\n".join(lineas)


def _serializar(comprobante: FacturaElectronica) -> dict:
    """Serializa un comprobante (factura o NC) a dict JSON-compatible."""
    return FacturaElectronicaResponse.model_validate(comprobante).model_dump(mode="json")


def _aplicar_resultado_transmision(
    comprobante: FacturaElectronica,
    resultado: dict,
    estado_final: str,
    recepcion: dict,
    autorizacion: Optional[dict],
    errores: list,
) -> None:
    """Persiste el resultado de la transmisión sobre el comprobante (patrón de
    transmitir_factura, reutilizado por el flujo de nota de crédito)."""
    if estado_final == "AUTORIZADO" and autorizacion:
        comprobante.estado_sri = "autorizado"
        comprobante.numero_autorizacion = autorizacion.get("numero_autorizacion")
        comprobante.xml_respuesta_sri = (
            autorizacion.get("xml_autorizado") or comprobante.xml_firmado
        )
        if autorizacion.get("fecha_autorizacion"):
            try:
                comprobante.fecha_autorizacion = datetime.fromisoformat(
                    autorizacion["fecha_autorizacion"].replace("Z", "+00:00")
                )
            except ValueError:
                comprobante.fecha_autorizacion = None
    elif estado_final == "DEVUELTA":
        comprobante.estado_sri = "devuelta"
        comprobante.xml_respuesta_sri = _formatear_errores(errores)
    elif estado_final == "NO AUTORIZADO":
        comprobante.estado_sri = "no_autorizado"
        comprobante.xml_respuesta_sri = _formatear_errores(errores)
    else:  # EN PROCESO / RECIBIDA sin autorización (no concluyente)
        comprobante.estado_sri = "recibida"
        comprobante.xml_respuesta_sri = _formatear_errores(errores)


@router.post(
    "/{factura_id}/anular",
    summary="Anular factura con nota de crédito (SRI)",
    description=(
        "Genera, firma, persiste y transmite al SRI una NOTA DE CRÉDITO (04) "
        "que anula (total o parcialmente) la factura indicada. Si la NC queda "
        "'autorizado' o 'recibida', la factura original se marca como "
        "'anulada' (o 'anulada_parcial' si monto_anular < total). Si la "
        "transmisión falla por red, la NC queda 'firmado' y se reporta."
    ),
)
async def anular_factura(
    factura_id: int,
    datos: NotaCreditoRequest,
    db: AsyncSession = Depends(get_db),
):
    """Genera y transmite la nota de crédito que anula una factura."""
    result = await db.execute(
        select(FacturaElectronica).where(FacturaElectronica.id == factura_id)
    )
    factura = result.scalar_one_or_none()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura electrónica no encontrada")

    if factura.tipo_comprobante == "04":
        raise HTTPException(
            status_code=400,
            detail="El comprobante indicado es una nota de crédito; solo se anulan facturas (01).",
        )

    # --- Reglas anti-doble anulación ---
    # 1) La propia factura ya está marcada como anulada por una NC previa.
    if factura.estado_sri in ("anulada", "anulada_parcial"):
        raise HTTPException(
            status_code=400,
            detail="La factura ya tiene una nota de crédito asociada",
        )
    # 2) Existe una NC vigente (autorizada/recibida/en proceso) que la referencia.
    #    Las devueltas/no autorizadas NO cuentan: dejan la factura anulable.
    result = await db.execute(
        select(FacturaElectronica.id).where(
            FacturaElectronica.factura_referenciada_id == factura.id,
            FacturaElectronica.estado_sri.notin_(["no_autorizado", "devuelta"]),
        )
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=400,
            detail="La factura ya tiene una nota de crédito asociada",
        )

    # --- Estado anulable (decisión documentada) ---
    # Se permite anular facturas 'autorizado' o 'recibida'. En ambiente de
    # certificación (1) la autorización no siempre se materializa con número,
    # por lo que 'recibida' también se considera anulable (utilidad real de
    # pruebas y operación). Facturas 'firmado'/'devuelta'/'no_autorizado' NO.
    if factura.estado_sri not in ("autorizado", "recibida"):
        raise HTTPException(
            status_code=400,
            detail=(
                "Solo se pueden anular facturas en estado 'autorizado' o 'recibida'. "
                f"La factura está en '{factura.estado_sri}'."
            ),
        )

    total_factura = Decimal(str(factura.total))
    monto_anular = (
        _round2(datos.monto_anular)
        if datos.monto_anular is not None
        else _round2(total_factura)
    )
    if monto_anular > total_factura:
        raise HTTPException(
            status_code=400,
            detail=(
                f"El monto a anular (${monto_anular:.2f}) supera el total de "
                f"la factura (${total_factura:.2f})."
            ),
        )
    if monto_anular <= 0:
        raise HTTPException(
            status_code=400,
            detail="El monto a anular debe ser mayor a cero.",
        )

    # Fecha de emisión de la NC (debe ser >= fecha de la factura)
    fecha_emision_nc: Optional[datetime] = None
    if datos.fecha_autorizada is not None:
        fecha_base = factura.fecha_emision.date() if factura.fecha_emision else None
        if fecha_base and datos.fecha_autorizada < fecha_base:
            raise HTTPException(
                status_code=400,
                detail=(
                    "La fecha de la nota de crédito no puede ser anterior a la "
                    "fecha de emisión de la factura original."
                ),
            )
        fecha_emision_nc = datetime.combine(datos.fecha_autorizada, time.min)

    # Configuración del sistema (IVA + firma digital)
    result = await db.execute(select(ConfiguracionSistema))
    cfg_rows = result.scalars().all()
    cfg = {row.clave: row.valor for row in cfg_rows}
    config = {"iva_porcentaje": Decimal(str(cfg.get("iva_porcentaje", "15")))}
    ruta_p12 = cfg.get("firma_p12_ruta") or FIRMA_P12_DEFAULT

    # Cliente + factura original (solo LECTURA)
    result = await db.execute(select(Cliente).where(Cliente.id == factura.cliente_id))
    cliente_obj = result.scalar_one_or_none()
    if not cliente_obj:
        raise HTTPException(
            status_code=500,
            detail="Cliente de la factura original no encontrado",
        )
    cliente_dict = {
        "nombre": cliente_obj.nombre,
        "apellido": cliente_obj.apellido,
        "nombre_completo": f"{cliente_obj.nombre} {cliente_obj.apellido}".strip(),
        "cedula_ruc": cliente_obj.cedula_ruc,
        "direccion": cliente_obj.direccion,
    }
    factura_original = {
        "id": factura.id,
        "clave_acceso": factura.clave_acceso,
        "numero_documento": factura.numero_documento,
        "fecha_emision": factura.fecha_emision,
        "total": factura.total,
    }

    # Secuencial independiente de las facturas
    secuencial = await siguiente_secuencial_nota_credito(db, factura.ambiente)

    # Generación del XML de NC (validaciones de negocio)
    try:
        comprobante = generar_comprobante_nota_credito(
            factura_original=factura_original,
            cliente=cliente_dict,
            config=config,
            secuencial=secuencial,
            motivo=datos.motivo,
            monto_anular=monto_anular,
            ambiente=factura.ambiente,
            fecha_emision=fecha_emision_nc,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Firma XAdES-BES (si falla → 500, aún nada en BD)
    password_p12 = obtener_password_firma()
    try:
        xml_firmado = firmar_xml(comprobante["xml"], ruta_p12, password_p12)
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo firmar el XML: {exc}",
        )

    # Persistir NC (rollback si falla, no dejar datos a medias)
    nota_credito = FacturaElectronica(
        orden_servicio_id=None,
        nota_venta_id=None,
        cliente_id=factura.cliente_id,
        tipo_comprobante="04",
        factura_referenciada_id=factura.id,
        motivo_anulacion=datos.motivo,
        # valor_anulacion = subtotal anulado (valorModificacion), montos positivos
        valor_anulacion=comprobante["subtotal"],
        clave_acceso=comprobante["clave_acceso"],
        numero_documento=comprobante["numero_documento"],
        ambiente=comprobante["ambiente"],
        estado_sri="firmado",
        xml_firmado=xml_firmado,
        subtotal=comprobante["subtotal"],
        iva=comprobante["iva"],
        total=comprobante["total"],
    )
    db.add(nota_credito)
    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al guardar la nota de crédito en la BD: {exc}",
        )
    await db.refresh(nota_credito)

    # --- Transmisión automática (recepción + autorización) ---
    # Si falla por red/firma, la NC queda 'firmado' (recuperable con
    # POST /{id}/transmitir) y se reporta; la factura original NO se marca.
    transmision: dict = {"estado": "no_intentada"}
    try:
        resultado = transmitir_y_autorizar(
            clave_acceso=nota_credito.clave_acceso,
            xml_firmado=xml_firmado,
            ambiente=factura.ambiente,
            ruta_p12=ruta_p12,
        )
    except ErrorTransmisionSRI as exc:
        transmision = {"estado": "fallo_red", "error": str(exc)}
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        transmision = {"estado": "fallo_interno", "error": str(exc)}

    if "error" in transmision:
        return {
            "nota_credito": _serializar(nota_credito),
            "factura_original": _serializar(factura),
            "transmision": transmision,
        }

    recepcion = resultado["recepcion"]
    autorizacion = resultado["autorizacion"]
    estado_final = recepcion["estado"]
    if recepcion["estado"] == "RECIBIDA" and autorizacion:
        estado_final = autorizacion["estado"]

    errores = recepcion["mensajes"] or (autorizacion["mensajes"] if autorizacion else [])
    _aplicar_resultado_transmision(
        nota_credito, resultado, estado_final, recepcion, autorizacion, errores
    )
    transmision = {"estado": estado_final, "errores": errores}

    # Si la NC quedó vigente (autorizado o recibida) → marcar la factura original
    if nota_credito.estado_sri in ("autorizado", "recibida"):
        factura.estado_sri = (
            "anulada" if monto_anular >= total_factura else "anulada_parcial"
        )

    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al guardar el resultado de la anulación: {exc}",
        )
    await db.refresh(nota_credito)
    await db.refresh(factura)

    return {
        "nota_credito": _serializar(nota_credito),
        "factura_original": _serializar(factura),
        "transmision": transmision,
    }