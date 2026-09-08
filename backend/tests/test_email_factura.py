"""
Tests unitarios y de integración para el envío de comprobantes electrónicos por correo (SMTP).
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.models import Cliente, ConfiguracionSistema, FacturaElectronica, Usuario, RolUsuario
from src.services.email_factura import (
    _generar_html_factura,
    enviar_factura_email,
    obtener_config_smtp,
    probar_conexion_smtp,
)


def test_generar_html_factura():
    """Valida que el HTML contenga los datos del cliente, comprobante y valores."""
    factura = MagicMock(spec=FacturaElectronica)
    factura.numero_documento = "001-001-000000021"
    factura.tipo_comprobante = "01"
    factura.clave_acceso = "0309202601096479423400120010010000000022338332719"
    factura.numero_autorizacion = "0309202601096479423400120010010000000022338332719"
    factura.fecha_emision = datetime(2026, 9, 8, 14, 30)
    factura.subtotal = Decimal("50.00")
    factura.iva = Decimal("7.50")
    factura.total = Decimal("57.50")

    cliente = MagicMock(spec=Cliente)
    cliente.nombre = "Carlos"
    cliente.apellido = "Andrade"
    cliente.cedula_ruc = "0923456789"
    cliente.email = "carlos@ejemplo.com"

    html = _generar_html_factura(factura, cliente)
    assert "001-001-000000021" in html
    assert "Carlos Andrade" in html
    assert "0309202601096479423400120010010000000022338332719" in html
    assert "57.50" in html
    assert "Factura Electrónica" in html
    assert "PDF (RIDE)" in html


@pytest.mark.asyncio
async def test_probar_conexion_smtp_mock():
    """Valida probar_conexion_smtp con smtplib mockeado."""
    config = {
        "smtp_host": "smtp.mailtrap.io",
        "smtp_port": 587,
        "smtp_usuario": "user123",
        "smtp_password": "secretpassword",
        "smtp_from_email": "facturacion@orpey.com",
        "smtp_from_nombre": "Orpey Servicios",
        "smtp_seguridad": "tls",
    }

    with patch("smtplib.SMTP") as mock_smtp:
        instancia = MagicMock()
        mock_smtp.return_value.__enter__.return_value = instancia

        res = await probar_conexion_smtp(config, "cliente@ejemplo.com")
        assert "exito" in res["mensaje"].lower() or "éxito" in res["mensaje"].lower()
        instancia.starttls.assert_called_once()
        instancia.login.assert_called_once_with("user123", "secretpassword")
        instancia.sendmail.assert_called_once()


@pytest.mark.asyncio
async def test_enviar_factura_email_sin_email_cliente():
    """Valida que si el cliente no tiene correo, retorne aviso sin lanzar excepción."""
    mock_db = MagicMock(spec=AsyncSession)

    factura = MagicMock(spec=FacturaElectronica)
    factura.id = 1
    factura.numero_documento = "001-001-000000001"
    factura.cliente_id = 10

    cliente = MagicMock(spec=Cliente)
    cliente.id = 10
    cliente.email = None

    async def mock_execute(query):
        mock_result = MagicMock()
        q_str = str(query).lower()
        if "from facturas_electronicas" in q_str:
            mock_result.scalar_one_or_none.return_value = factura
        elif "from clientes" in q_str:
            mock_result.scalar_one_or_none.return_value = cliente
        else:
            mock_result.scalar_one_or_none.return_value = None
        return mock_result

    mock_db.execute.side_effect = mock_execute

    resultado = await enviar_factura_email(mock_db, factura_id=1)
    assert resultado["enviado"] is False
    assert "no tiene correo" in resultado["motivo"]


@pytest.mark.asyncio
async def test_enviar_factura_email_sin_smtp_configurado():
    """Valida que si no hay SMTP configurado, no falle catastróficamente."""
    mock_db = MagicMock(spec=AsyncSession)

    factura = MagicMock(spec=FacturaElectronica)
    factura.id = 2
    factura.numero_documento = "001-001-000000002"
    factura.cliente_id = 11

    cliente = MagicMock(spec=Cliente)
    cliente.id = 11
    cliente.email = "test@correo.com"

    async def mock_execute(query):
        mock_result = MagicMock()
        q_str = str(query).lower()
        if "from facturas_electronicas" in q_str:
            mock_result.scalar_one_or_none.return_value = factura
        elif "from clientes" in q_str:
            mock_result.scalar_one_or_none.return_value = cliente
        elif "from configuracion_sistema" in q_str:
            mock_result.scalars.return_value.all.return_value = []
        return mock_result

    mock_db.execute.side_effect = mock_execute

    with patch.dict("os.environ", {}, clear=True):
        resultado = await enviar_factura_email(mock_db, factura_id=2)
        assert resultado["enviado"] is False
        assert "no configurado" in resultado["motivo"]


@pytest.mark.asyncio
async def test_enviar_factura_email_exito():
    """Valida el flujo completo de envío exitoso con PDF y XML adjuntos."""
    mock_db = MagicMock(spec=AsyncSession)

    factura = MagicMock(spec=FacturaElectronica)
    factura.id = 3
    factura.numero_documento = "001-001-000000003"
    factura.tipo_comprobante = "01"
    factura.clave_acceso = "0309202601096479423400120010010000000022338332719"
    factura.numero_autorizacion = "0309202601096479423400120010010000000022338332719"
    factura.fecha_emision = datetime(2026, 9, 8, 10, 0)
    factura.subtotal = Decimal("100.00")
    factura.iva = Decimal("15.00")
    factura.total = Decimal("115.00")
    factura.cliente_id = 12
    factura.orden_servicio_id = None
    factura.xml_firmado = "<factura>XML_FIRMADO</factura>"
    factura.xml_respuesta_sri = "<autorizacion><estado>AUTORIZADO</estado></autorizacion>"
    factura.email_enviado = False
    factura.fecha_envio_email = None

    cliente = MagicMock(spec=Cliente)
    cliente.id = 12
    cliente.nombre = "María"
    cliente.apellido = "Gómez"
    cliente.cedula_ruc = "0987654321"
    cliente.email = "maria@ejemplo.com"

    cfg_host = MagicMock(clave="smtp_host", valor="smtp.ejemplo.com")
    cfg_user = MagicMock(clave="smtp_usuario", valor="facturacion@orpey.com")
    cfg_pass = MagicMock(clave="smtp_password", valor="secreto123")

    async def mock_execute(query):
        mock_result = MagicMock()
        q_str = str(query).lower()
        if "from facturas_electronicas" in q_str:
            mock_result.scalar_one_or_none.return_value = factura
        elif "from clientes" in q_str:
            mock_result.scalar_one_or_none.return_value = cliente
        elif "from configuracion_sistema" in q_str:
            mock_result.scalars.return_value.all.return_value = [cfg_host, cfg_user, cfg_pass]
        return mock_result

    mock_db.execute.side_effect = mock_execute

    with patch("smtplib.SMTP") as mock_smtp, \
         patch("src.routers.facturacion._generar_pdf_factura", return_value=b"%PDF-1.4 dummy pdf"):
        instancia = MagicMock()
        mock_smtp.return_value.__enter__.return_value = instancia

        res = await enviar_factura_email(mock_db, factura_id=3)
        assert res["enviado"] is True
        assert res["destinatario"] == "maria@ejemplo.com"
        assert factura.email_enviado is True
        assert factura.fecha_envio_email is not None
        mock_db.commit.assert_called_once()
        instancia.sendmail.assert_called_once()

