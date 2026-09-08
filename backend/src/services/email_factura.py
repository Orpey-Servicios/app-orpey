"""
Servicio de envío de comprobantes electrónicos por correo electrónico (SMTP).

Genera y despacha el correo electrónico al cliente con:
1. RIDE en PDF (generado dinámicamente con ReportLab).
2. XML firmado y autorizado por el SRI.

Permite:
- Envío automático al autorizarse una factura (vía síncrona o worker).
- Reenvío manual desde la interfaz de usuario.
- Prueba de conexión SMTP desde la pantalla de Configuración.
- Auditoría de envío en la base de datos (email_enviado, fecha_envio_email).
"""

import asyncio
import email.utils
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import os
import smtplib
import ssl
from typing import Any, Dict, List, Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.models import Cliente, ConfiguracionSistema, FacturaElectronica, OrdenServicio

logger = logging.getLogger("email-factura")

# Defaults para configuración SMTP
DEFAULT_SMTP_PORT = 587
DEFAULT_FROM_NOMBRE = "Orpey Servicios"


async def obtener_config_smtp(db: AsyncSession) -> Dict[str, Any]:
    """
    Obtiene la configuración SMTP almacenada en configuracion_sistema,
    con fallback a variables de entorno del sistema.
    """
    result = await db.execute(select(ConfiguracionSistema))
    cfg_rows = result.scalars().all()
    cfg_map = {row.clave: row.valor for row in cfg_rows}

    host = cfg_map.get("smtp_host") or os.environ.get("SMTP_HOST", "")
    port_str = cfg_map.get("smtp_port") or os.environ.get("SMTP_PORT", str(DEFAULT_SMTP_PORT))
    try:
        port = int(port_str)
    except (ValueError, TypeError):
        port = DEFAULT_SMTP_PORT

    usuario = cfg_map.get("smtp_usuario") or os.environ.get("SMTP_USER", "")
    password = cfg_map.get("smtp_password") or os.environ.get("SMTP_PASSWORD", "")
    from_email = cfg_map.get("smtp_from_email") or os.environ.get("SMTP_FROM", "") or usuario
    from_nombre = cfg_map.get("smtp_from_nombre") or os.environ.get("SMTP_FROM_NAME", DEFAULT_FROM_NOMBRE)
    seguridad = (cfg_map.get("smtp_seguridad") or os.environ.get("SMTP_SECURE", "tls")).lower()
    copia_oculta = cfg_map.get("smtp_copia_oculta") or os.environ.get("SMTP_BCC", "")

    return {
        "smtp_host": host.strip(),
        "smtp_port": port,
        "smtp_usuario": usuario.strip(),
        "smtp_password": password.strip(),
        "smtp_from_email": from_email.strip(),
        "smtp_from_nombre": from_nombre.strip(),
        "smtp_seguridad": seguridad,
        "smtp_copia_oculta": copia_oculta.strip() if copia_oculta else None,
        "configurado": bool(host.strip() and (usuario.strip() or port == 25)),
    }


def _enviar_smtp_sync(
    host: str,
    port: int,
    usuario: str,
    password: str,
    seguridad: str,
    remitente: str,
    destinatarios: List[str],
    mensaje_bytes: bytes,
    timeout: int = 30,
) -> None:
    """Envía un mensaje MIME vía SMTP de forma síncrona con timeout controlado."""
    seguridad = (seguridad or "tls").lower()

    if seguridad == "ssl" or port == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context, timeout=timeout) as server:
            if usuario and password:
                server.login(usuario, password)
            server.sendmail(remitente, destinatarios, mensaje_bytes)
    else:
        with smtplib.SMTP(host, port, timeout=timeout) as server:
            server.ehlo()
            if seguridad == "tls" or server.has_extn("STARTTLS"):
                context = ssl.create_default_context()
                server.starttls(context=context)
                server.ehlo()
            if usuario and password:
                server.login(usuario, password)
            server.sendmail(remitente, destinatarios, mensaje_bytes)


async def probar_conexion_smtp(config: Dict[str, Any], email_destino: str) -> Dict[str, Any]:
    """
    Envía un correo de prueba para validar que los datos SMTP ingresados
    funcionan correctamente.
    """
    host = config.get("smtp_host", "").strip()
    port = int(config.get("smtp_port") or DEFAULT_SMTP_PORT)
    usuario = config.get("smtp_usuario", "").strip()
    password = config.get("smtp_password", "").strip()
    from_email = config.get("smtp_from_email", "").strip() or usuario
    from_nombre = config.get("smtp_from_nombre", "").strip() or DEFAULT_FROM_NOMBRE
    seguridad = config.get("smtp_seguridad", "tls")

    if not host:
        raise ValueError("El servidor SMTP (host) es obligatorio.")
    if not email_destino or "@" not in email_destino:
        raise ValueError("La dirección de correo destinatario no es válida.")

    # Construir mensaje de prueba
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Prueba de Configuración de Correo - Orpey Servicios"
    msg["From"] = f"{from_nombre} <{from_email}>"
    msg["To"] = email_destino
    msg["Date"] = email.utils.formatdate(localtime=True)

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin: 0; padding: 20px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f1f5f9; color: #1e293b;">
  <div style="max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.06); border: 1px solid #e2e8f0;">
    <div style="background: #1e293b; padding: 24px; text-align: center; border-bottom: 4px solid #FBC305;">
      <h1 style="color: #FBC305; margin: 0; font-size: 24px; letter-spacing: 1px;">ORPEY SERVICIOS</h1>
      <p style="color: #94a3b8; margin: 4px 0 0 0; font-size: 13px;">Taller de Servicio Técnico Especializado</p>
    </div>
    <div style="padding: 28px;">
      <div style="display: inline-block; background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 6px; padding: 6px 14px; color: #065f46; font-size: 13px; font-weight: 600; margin-bottom: 16px;">
        ✓ Conexión SMTP Exitosa
      </div>
      <h2 style="font-size: 18px; margin: 0 0 12px 0; color: #0f172a;">Prueba de Conexión de Correo Saliente</h2>
      <p style="line-height: 1.6; font-size: 14px; margin-bottom: 20px;">
        Este correo confirma que el servidor de correo saliente (SMTP) de <strong>Orpey Servicios</strong> ha sido configurado y validado correctamente.
      </p>
      <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; font-size: 13px;">
        <div style="margin-bottom: 6px;"><strong>Servidor:</strong> {host}:{port}</div>
        <div style="margin-bottom: 6px;"><strong>Usuario:</strong> {usuario}</div>
        <div style="margin-bottom: 6px;"><strong>Seguridad:</strong> {seguridad.upper()}</div>
        <div><strong>Fecha y Hora:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
      </div>
    </div>
    <div style="background: #f8fafc; padding: 16px; text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0;">
      Orpey Servicios © {datetime.now().year} — Mensaje de verificación automática
    </div>
  </div>
</body>
</html>"""

    msg.attach(MIMEText(html, "html", "utf-8"))

    # Ejecutar en threadpool
    await asyncio.to_thread(
        _enviar_smtp_sync,
        host=host,
        port=port,
        usuario=usuario,
        password=password,
        seguridad=seguridad,
        remitente=from_email,
        destinatarios=[email_destino],
        mensaje_bytes=msg.as_bytes(),
    )
    return {"mensaje": f"Correo de prueba enviado con éxito a {email_destino}"}


def _generar_html_factura(factura: FacturaElectronica, cliente: Optional[Cliente]) -> str:
    """Construye la plantilla HTML del correo para el comprobante electrónico."""
    tipo_desc = "Factura Electrónica" if factura.tipo_comprobante == "01" else "Nota de Crédito"
    nombre_cliente = f"{cliente.nombre} {cliente.apellido}".strip() if cliente else "Estimado(a) Cliente"
    id_cliente = cliente.cedula_ruc if cliente and cliente.cedula_ruc else "Consumidor Final"

    fecha_fmt = (
        factura.fecha_emision.strftime("%d/%m/%Y")
        if factura.fecha_emision
        else datetime.now().strftime("%d/%m/%Y")
    )
    num_auth = factura.numero_autorizacion or factura.clave_acceso
    subtotal_fmt = f"{float(factura.subtotal or 0):,.2f}"
    iva_fmt = f"{float(factura.iva or 0):,.2f}"
    total_fmt = f"{float(factura.total or 0):,.2f}"

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{tipo_desc} - Orpey Servicios</title>
</head>
<body style="margin: 0; padding: 20px 0; background-color: #f1f5f9; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #1e293b;">
  <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.06); border: 1px solid #e2e8f0;">
    
    <!-- Encabezado -->
    <div style="background: #1e293b; padding: 28px 24px; text-align: center; border-bottom: 4px solid #FBC305;">
      <h1 style="color: #FBC305; margin: 0; font-size: 26px; font-weight: 800; letter-spacing: 1px;">ORPEY SERVICIOS</h1>
      <p style="color: #94a3b8; margin: 6px 0 0 0; font-size: 13px;">Servicio Técnico y Soluciones Informáticas</p>
    </div>

    <!-- Contenido Principal -->
    <div style="padding: 30px 24px;">
      <div style="display: inline-block; background: #eff6ff; border: 1px solid #bfdbfe; color: #1d4ed8; font-size: 12px; font-weight: 700; padding: 4px 12px; border-radius: 9999px; text-transform: uppercase; margin-bottom: 16px; letter-spacing: 0.5px;">
        {tipo_desc} Autorizada por el SRI
      </div>

      <h2 style="margin: 0 0 14px 0; font-size: 20px; color: #0f172a;">
        Hola, {nombre_cliente}
      </h2>

      <p style="font-size: 14px; line-height: 1.6; color: #475569; margin: 0 0 20px 0;">
        Le informamos que se ha emitido y autorizado su <strong>{tipo_desc.lower()}</strong> en el Servicio de Rentas Internas (SRI). Adjunto a este correo encontrará su archivo <strong>PDF (RIDE)</strong> y el archivo legal <strong>XML firmado</strong>.
      </p>

      <!-- Tabla Resumen del Comprobante -->
      <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px; background: #f8fafc; border-radius: 8px; overflow: hidden; border: 1px solid #e2e8f0;">
        <tbody>
          <tr>
            <td style="padding: 10px 14px; font-size: 13px; color: #64748b; border-bottom: 1px solid #e2e8f0; width: 40%;"><strong>N° de Comprobante:</strong></td>
            <td style="padding: 10px 14px; font-size: 13px; font-weight: 600; color: #0f172a; border-bottom: 1px solid #e2e8f0;">{factura.numero_documento}</td>
          </tr>
          <tr>
            <td style="padding: 10px 14px; font-size: 13px; color: #64748b; border-bottom: 1px solid #e2e8f0;"><strong>Fecha de Emisión:</strong></td>
            <td style="padding: 10px 14px; font-size: 13px; color: #0f172a; border-bottom: 1px solid #e2e8f0;">{fecha_fmt}</td>
          </tr>
          <tr>
            <td style="padding: 10px 14px; font-size: 13px; color: #64748b; border-bottom: 1px solid #e2e8f0;"><strong>RUC / Cédula Cliente:</strong></td>
            <td style="padding: 10px 14px; font-size: 13px; color: #0f172a; border-bottom: 1px solid #e2e8f0;">{id_cliente}</td>
          </tr>
          <tr>
            <td style="padding: 10px 14px; font-size: 13px; color: #64748b; border-bottom: 1px solid #e2e8f0;"><strong>Subtotal:</strong></td>
            <td style="padding: 10px 14px; font-size: 13px; color: #0f172a; border-bottom: 1px solid #e2e8f0;">$ {subtotal_fmt}</td>
          </tr>
          <tr>
            <td style="padding: 10px 14px; font-size: 13px; color: #64748b; border-bottom: 1px solid #e2e8f0;"><strong>IVA (15%):</strong></td>
            <td style="padding: 10px 14px; font-size: 13px; color: #0f172a; border-bottom: 1px solid #e2e8f0;">$ {iva_fmt}</td>
          </tr>
          <tr style="background: #fffbeb;">
            <td style="padding: 12px 14px; font-size: 14px; color: #92400e; font-weight: 700;"><strong>TOTAL:</strong></td>
            <td style="padding: 12px 14px; font-size: 16px; color: #92400e; font-weight: 800;">$ {total_fmt}</td>
          </tr>
        </tbody>
      </table>

      <!-- Bloque de Clave de Acceso y Autorización -->
      <div style="background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 8px; padding: 14px; margin-bottom: 24px; font-size: 12px;">
        <div style="color: #64748b; margin-bottom: 4px;"><strong>Número de Autorización SRI:</strong></div>
        <div style="font-family: monospace; color: #0f172a; word-break: break-all; font-size: 12px; margin-bottom: 10px;">{num_auth}</div>
        
        <div style="color: #64748b; margin-bottom: 4px;"><strong>Clave de Acceso:</strong></div>
        <div style="font-family: monospace; color: #0f172a; word-break: break-all; font-size: 12px;">{factura.clave_acceso}</div>
      </div>

      <!-- Sección de Adjuntos -->
      <div style="background: #f1f5f9; border-radius: 8px; padding: 14px; font-size: 13px; color: #334155;">
        <div style="font-weight: 700; margin-bottom: 6px; color: #0f172a;">📎 Archivos Adjuntos a este Correo:</div>
        <ul style="margin: 0; padding-left: 20px; line-height: 1.6;">
          <li><strong>Factura-{factura.numero_documento}.pdf</strong>: Representación Gráfica (RIDE)</li>
          <li><strong>{factura.clave_acceso}.xml</strong>: Comprobante Tributario Electrónico Oficial</li>
        </ul>
      </div>
    </div>

    <!-- Pie de página -->
    <div style="background: #f8fafc; padding: 20px; text-align: center; border-top: 1px solid #e2e8f0; font-size: 12px; color: #64748b; line-height: 1.5;">
      <p style="margin: 0 0 6px 0;"><strong>Orpey Servicios</strong> — Guayaquil, Bastión Popular, Bloque 2, Solar 7</p>
      <p style="margin: 0; color: #94a3b8;">Este es un mensaje generado automáticamente. Por favor no responda a este correo.</p>
    </div>
  </div>
</body>
</html>"""


async def enviar_factura_email(
    db: AsyncSession,
    factura_id: int,
    destinatario_override: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Despacha el comprobante electrónico (PDF + XML) al correo del cliente.
    Si el cliente no tiene correo o no hay servidor SMTP configurado, registra
    el motivo sin lanzar error fatal.
    """
    result = await db.execute(
        select(FacturaElectronica).where(FacturaElectronica.id == factura_id)
    )
    factura = result.scalar_one_or_none()
    if not factura:
        raise ValueError(f"No existe la factura con ID {factura_id}")

    # Cargar cliente
    cliente = None
    if factura.cliente_id:
        res_cli = await db.execute(select(Cliente).where(Cliente.id == factura.cliente_id))
        cliente = res_cli.scalar_one_or_none()

    destinatario = (destinatario_override or (cliente.email if cliente else None) or "").strip()
    if not destinatario or "@" not in destinatario:
        logger.info(
            "Factura %s: el cliente (ID %s) no tiene correo electrónico válido. Envío omitido.",
            factura.numero_documento,
            factura.cliente_id,
        )
        return {
            "enviado": False,
            "motivo": "El cliente no tiene correo electrónico registrado.",
            "destinatario": None,
        }

    # Verificar configuración SMTP
    config = await obtener_config_smtp(db)
    if not config["configurado"]:
        logger.warning(
            "Factura %s: servidor SMTP no configurado en el sistema. Omitiendo envío de correo.",
            factura.numero_documento,
        )
        return {
            "enviado": False,
            "motivo": "Servidor SMTP no configurado en Configuración del Sistema.",
            "destinatario": destinatario,
        }

    # Cargar equipos de la orden si corresponde para el PDF
    equipos = []
    if factura.orden_servicio_id:
        res_ord = await db.execute(
            select(OrdenServicio)
            .options(selectinload(OrdenServicio.equipos))
            .where(OrdenServicio.id == factura.orden_servicio_id)
        )
        orden = res_ord.scalar_one_or_none()
        if orden and orden.equipos:
            equipos = orden.equipos

    # Generar PDF RIDE en memoria
    from src.routers.facturacion import _generar_pdf_factura

    pdf_bytes = _generar_pdf_factura(factura, cliente, equipos)

    # Obtener XML para adjuntar
    # Preferimos xml_respuesta_sri si contiene el XML autorizado con nodo <autorizacion>
    xml_contenido = factura.xml_firmado
    if factura.xml_respuesta_sri and factura.xml_respuesta_sri.strip().startswith("<"):
        xml_contenido = factura.xml_respuesta_sri
    xml_bytes = xml_contenido.encode("utf-8") if isinstance(xml_contenido, str) else xml_contenido

    # Construir mensaje MIME
    tipo_desc = "Factura" if factura.tipo_comprobante == "01" else "Nota de Crédito"
    asunto = f"Comprobante Electrónico ({tipo_desc}) N° {factura.numero_documento} - {config['smtp_from_nombre']}"

    msg = MIMEMultipart("mixed")
    msg["Subject"] = asunto
    msg["From"] = f"{config['smtp_from_nombre']} <{config['smtp_from_email']}>"
    msg["To"] = destinatario
    msg["Date"] = email.utils.formatdate(localtime=True)

    destinatarios_lista = [destinatario]
    if config["smtp_copia_oculta"]:
        destinatarios_lista.append(config["smtp_copia_oculta"])

    # Adjuntar cuerpo HTML
    html_cuerpo = _generar_html_factura(factura, cliente)
    msg_html = MIMEText(html_cuerpo, "html", "utf-8")
    msg.attach(msg_html)

    # Adjuntar PDF RIDE
    nombre_pdf = f"Factura-{factura.numero_documento}.pdf"
    adjunto_pdf = MIMEApplication(pdf_bytes, _subtype="pdf")
    adjunto_pdf.add_header("Content-Disposition", "attachment", filename=nombre_pdf)
    msg.attach(adjunto_pdf)

    # Adjuntar XML legal
    nombre_xml = f"{factura.clave_acceso}.xml"
    adjunto_xml = MIMEApplication(xml_bytes, _subtype="xml")
    adjunto_xml.add_header("Content-Disposition", "attachment", filename=nombre_xml)
    msg.attach(adjunto_xml)

    # Despachar por SMTP
    logger.info("Enviando factura %s por correo a %s...", factura.numero_documento, destinatario)
    try:
        await asyncio.to_thread(
            _enviar_smtp_sync,
            host=config["smtp_host"],
            port=config["smtp_port"],
            usuario=config["smtp_usuario"],
            password=config["smtp_password"],
            seguridad=config["smtp_seguridad"],
            remitente=config["smtp_from_email"],
            destinatarios=destinatarios_lista,
            mensaje_bytes=msg.as_bytes(),
        )
    except Exception as exc:
        logger.error("Error al enviar factura %s por correo a %s: %s", factura.numero_documento, destinatario, exc)
        return {
            "enviado": False,
            "motivo": f"Fallo en servidor de correo: {exc}",
            "destinatario": destinatario,
        }

    # Actualizar auditoría en BD
    factura.email_enviado = True
    factura.fecha_envio_email = datetime.now()
    try:
        await db.commit()
    except Exception as db_exc:
        logger.warning("Factura %s enviada pero no se pudo actualizar fecha_envio_email: %s", factura.numero_documento, db_exc)

    logger.info("✅ Factura %s enviada exitosamente a %s", factura.numero_documento, destinatario)
    return {
        "enviado": True,
        "destinatario": destinatario,
        "mensaje": f"Comprobante enviado exitosamente a {destinatario}",
    }


async def tarea_enviar_factura_segundo_plano(factura_id: int, destinatario_override: Optional[str] = None) -> None:
    """
    Ejecuta el envío de factura en segundo plano abriendo su propia sesión asíncrona de base de datos.
    Útil para invocar con asyncio.create_task() sin depender del ciclo de vida del request HTTP.
    """
    from src.config.database import async_session

    try:
        async with async_session() as db:
            await enviar_factura_email(db, factura_id, destinatario_override)
    except Exception as exc:
        logger.error("Error en tarea en segundo plano de envío de factura %s: %s", factura_id, exc)
