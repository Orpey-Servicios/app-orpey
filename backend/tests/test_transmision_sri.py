"""
Tests de la transmisión SOAP al SRI (recepción + autorización).

Cubre:
1. Parseo de respuestas de RECEPCIÓN: RECIBIDA y DEVUELTA (con errores, códigos 35/39).
2. Parseo de respuestas de AUTORIZACIÓN: AUTORIZADO, NO AUTORIZADO y EN PROCESO.
3. El XML autorizado (base64) se decodifica y queda como texto.
4. Endpoint POST /api/facturacion/{id}/transmitir (BD SQLite aislada):
   - factura inexistente → 404
   - factura firmada → transmite y persiste estado autorizado
   - guarda de seguridad: producción requiere confirmación
   - forzar_ambiente
5. El XML autorizado base64 se guarda DECODIFICADO en xml_respuesta_sri.

NUNCA se hacen llamadas reales al SRI: se mockea `httpx.post` con respuestas
SOAP fabricadas.
"""

import base64
from datetime import datetime
from decimal import Decimal

import httpx
import pytest


# =====================================================
# Responsables de fabricar respuestas SOAP del SRI
# =====================================================

def _soap_respuesta_recepcion(estado, mensajes=None):
    """Construye una respuesta SOAP de recepción."""

    def _msg(m):
        return (
            f"<mensaje><identificador>{m.get('identificador','')}</identificador>"
            f"<mensaje>{m.get('mensaje','')}</mensaje>"
            f"<informacionAdicional>{m.get('informacionAdicional','')}</informacionAdicional>"
            f"<tipo>{m.get('tipo','')}</tipo></mensaje>"
        )

    comp_msgs = "".join(_msg(m) for m in (mensajes or []))
    return (
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
        '<soap:Body><ns2:validarComprobanteResponse xmlns:ns2='
        '"http://ec.gob.sri.ws.recepcion"><RespuestaRecepcionComprobante>'
        f"<estado>{estado}</estado><comprobantes><comprobante>"
        "<claveAcceso>2808202601096479423400110010010000000011234567812</claveAcceso>"
        f"<mensajes>{comp_msgs}</mensajes></comprobante></comprobantes>"
        "</RespuestaRecepcionComprobante></ns2:validarComprobanteResponse>"
        "</soap:Body></soap:Envelope>"
    ).encode()


def _soap_respuesta_autorizacion(estado, numero="", fecha="", comp_xml=None, mensajes=None):
    """Construye una respuesta SOAP de autorización."""
    comp_b64 = ""
    if comp_xml is not None:
        comp_b64 = base64.b64encode(comp_xml.encode("utf-8")).decode("ascii")

    def _msg(m):
        return (
            f"<mensaje><identificador>{m.get('identificador','')}</identificador>"
            f"<mensaje>{m.get('mensaje','')}</mensaje>"
            f"<informacionAdicional>{m.get('informacionAdicional','')}</informacionAdicional>"
            f"<tipo>{m.get('tipo','')}</tipo></mensaje>"
        )

    msgs = "".join(_msg(m) for m in (mensajes or []))
    return (
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
        '<soap:Body><ns2:autorizacionComprobanteResponse xmlns:ns2='
        '"http://ec.gob.sri.ws.autorizacion"><autorizacion>'
        f"<estado>{estado}</estado>"
        f"<numeroAutorizacion>{numero}</numeroAutorizacion>"
        f"<fechaAutorizacion>{fecha}</fechaAutorizacion>"
        f"<comprobante>{comp_b64}</comprobante>"
        f"<mensajes>{msgs}</mensajes>"
        "</autorizacion></ns2:autorizacionComprobanteResponse>"
        "</soap:Body></soap:Envelope>"
    ).encode()


class _RespuestaFalsa:
    """Objeto con `.content` y `.raise_for_status()` para imitar httpx.Response."""

    def __init__(self, content: bytes):
        self.content = content
        self.status_code = 200

    def raise_for_status(self):
        return None


# =====================================================
# Unit tests: parseo de respuestas (sin HTTP)
# =====================================================

from src.services import transmision_sri as T


def test_parseo_recepcion_recibida():
    xml = _soap_respuesta_recepcion("RECIBIDA")
    r = T._parsear_recepcion(xml, "1")
    assert r["estado"] == "RECIBIDA"
    assert r["mensajes"] == []
    assert r["clave_acceso"] == "2808202601096479423400110010010000000011234567812"


def test_parseo_recepcion_devuelta_con_errores():
    xml = _soap_respuesta_recepcion("DEVUELTA", mensajes=[
        {"identificador": "35", "mensaje": "ARCHIVO NO CUMPLE ESTRUCTURA XML",
         "informacionAdicional": "cvc-minLength", "tipo": "ERROR"},
        {"identificador": "39", "mensaje": "FIRMA ELECTRONICA",
         "informacionAdicional": "", "tipo": "ERROR"},
    ])
    r = T._parsear_recepcion(xml, "1")
    assert r["estado"] == "DEVUELTA"
    assert len(r["mensajes"]) == 2
    assert r["mensajes"][0]["identificador"] == "35"
    assert r["mensajes"][1]["identificador"] == "39"
    # El campo interno <mensaje> (texto) no se confunde con un mensaje extra
    assert r["mensajes"][0]["mensaje"] == "ARCHIVO NO CUMPLE ESTRUCTURA XML"


def test_parseo_autorizacion_autorizado_con_xml():
    xml_autorizado = "<factura id='comprobante' version='1.1.0'>...</factura>"
    numero = "2808202601096479423400110010010000000011234567812"
    fecha = "2026-08-28T10:00:00.000-05:00"
    xml = _soap_respuesta_autorizacion(
        "AUTORIZADO", numero=numero, fecha=fecha, comp_xml=xml_autorizado
    )
    r = T._parsear_autorizacion(xml, "clave", "1")
    assert r["estado"] == "AUTORIZADO"
    assert r["numero_autorizacion"] == numero
    assert r["fecha_autorizacion"] == fecha
    assert r["xml_autorizado"] == xml_autorizado


def test_parseo_autorizacion_no_autorizado():
    xml = _soap_respuesta_autorizacion("NO AUTORIZADO", mensajes=[
        {"identificador": "43", "mensaje": "FIRMA ELECTRONICA",
         "informacionAdicional": "", "tipo": "ERROR"},
    ])
    r = T._parsear_autorizacion(xml, "clave", "1")
    assert r["estado"] == "NO AUTORIZADO"
    assert r["numero_autorizacion"] == ""
    assert r["xml_autorizado"] is None
    assert len(r["mensajes"]) == 1


def test_parseo_autorizacion_en_proceso():
    xml = _soap_respuesta_autorizacion("EN PROCESO")
    r = T._parsear_autorizacion(xml, "clave", "1")
    assert r["estado"] == "EN PROCESO"
    assert r["numero_autorizacion"] == ""


def test_parseo_autorizacion_sin_registro_numero_0():
    """El SRI responde <numeroComprobantes>0</numeroComprobantes> (sin <autorizacion>)
    cuando el comprobante RECIBIDO aún no se ha autorizado. NO debe lanzar error:
    se interpreta como EN PROCESO para que la orquestación siga reintentando."""
    xml = (
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
        '<soap:Body><ns2:autorizacionComprobanteResponse xmlns:ns2='
        '"http://ec.gob.sri.ws.autorizacion"><RespuestaAutorizacionComprobante>'
        "<claveAccesoConsultada>2808202601096479423400110010010000000011234567812"
        "</claveAccesoConsultada>"
        "<numeroComprobantes>0</numeroComprobantes>"
        "<autorizaciones/></RespuestaAutorizacionComprobante>"
        "</ns2:autorizacionComprobanteResponse></soap:Body></soap:Envelope>"
    ).encode()
    r = T._parsear_autorizacion(xml, "clave", "1")
    assert r["estado"] == "EN PROCESO"
    assert r["numero_autorizacion"] == ""
    assert r["mensajes"] == []


def test_autorizacion_clave_70_en_procesamiento_es_en_proceso():
    """[70] CLAVE DE ACCESO EN PROCESAMIENTO NO es rechazo: se normaliza a
    EN PROCESO para que la orquestación reintente (verificado en vivo 29/08/2026).
    Si no se normalizara, el SRI respondería con un comprobante de estado no
    concluyente + mensaje 70 que terminaba marcado como 'devuelta' en la BD."""
    xml = (
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
        '<soap:Body><ns2:autorizacionComprobanteResponse xmlns:ns2='
        '"http://ec.gob.sri.ws.autorizacion"><RespuestaAutorizacionComprobante>'
        "<claveAccesoConsultada>2908202604096479423400110010010000000027183657412"
        "</claveAccesoConsultada>"
        "<numeroComprobantes>1</numeroComprobantes><autorizaciones>"
        "<autorizacion><estado>en proceso</estado><numeroAutorizacion/>"
        "<fechaAutorizacion/>"
        "<mensajes><mensaje><identificador>70</identificador>"
        "<mensaje>CLAVE DE ACCESO EN PROCESAMIENTO</mensaje>"
        "<informacionAdicional>VALOR DEVUELTO POR EL PROCEDIMIENTO: SI"
        "</informacionAdicional><tipo>INFORMATIVO</tipo></mensaje>"
        "</mensajes></autorizacion></autorizaciones>"
        "</RespuestaAutorizacionComprobante>"
        "</ns2:autorizacionComprobanteResponse></soap:Body></soap:Envelope>"
    ).encode()
    r = T._parsear_autorizacion(xml, "clave70", "1")
    assert r["estado"] == "EN PROCESO"
    assert r["mensajes"][0]["identificador"] == "70"


def test_recepcion_clave_70_en_procesamiento_es_recibida():
    """[70] en la respuesta de RECEPCIÓN (reenvío de clave o inmediatamente
    después de RECIBIDA) no es un rechazo: se normaliza a RECIBIDA."""
    xml = (
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
        '<soap:Body><ns2:validarComprobanteResponse xmlns:ns2='
        '"http://ec.gob.sri.ws.recepcion"><RespuestaRecepcionComprobante>'
        "<estado>DEVUELTA</estado><comprobantes><comprobante>"
        "<claveAcceso>2908202604096479423400110010010000000027183657412"
        "</claveAcceso><mensajes><mensaje><identificador>70</identificador>"
        "<mensaje>CLAVE DE ACCESO EN PROCESAMIENTO</mensaje>"
        "<informacionAdicional>VALOR DEVUELTO POR EL PROCEDIMIENTO: SI"
        "</informacionAdicional><tipo>INFORMATIVO</tipo></mensaje>"
        "</mensajes></comprobante></comprobantes>"
        "</RespuestaRecepcionComprobante></ns2:validarComprobanteResponse>"
        "</soap:Body></soap:Envelope>"
    ).encode()
    r = T._parsear_recepcion(xml, "1")
    assert r["estado"] == "RECIBIDA"


def test_transmitir_comprobante_mockea_http(monkeypatch):
    """transmitir_comprobante usa HTTP mockeado y parsea RECIBIDA."""
    rta = _RespuestaFalsa(_soap_respuesta_recepcion("RECIBIDA"))

    def fake_post(url, **kwargs):
        assert "celcer.sri.gob.ec" in url
        return rta

    monkeypatch.setattr(httpx, "post", fake_post)
    r = T.transmitir_comprobante("<factura/>", ambiente="1")
    assert r["estado"] == "RECIBIDA"


def test_consultar_autorizacion_devuelve_xml_decodificado(monkeypatch):
    """El XML autorizado base64 se guarda decodificado."""
    numero = "2808202601096479423400110010010000000011234567812"
    xml_autorizado = "<factura id='comprobante'>AUTORIZADO</factura>"
    rta = _RespuestaFalsa(_soap_respuesta_autorizacion(
        "AUTORIZADO", numero=numero, comp_xml=xml_autorizado
    ))

    def fake_post(url, **kwargs):
        assert "Autorizacion" in url
        return rta

    monkeypatch.setattr(httpx, "post", fake_post)
    r = T.consultar_autorizacion("clave", ambiente="1")
    assert r["xml_autorizado"] == xml_autorizado
    assert r["numero_autorizacion"] == numero


# =====================================================
# Endpoint /transmitir (BD aislada + HTTP mockeado)
# =====================================================

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.config.database import get_db
from src.main import app
from src.models.models import (
    Base, Cliente, ConfiguracionSistema, EstadoOrden, EquipoOrden,
    FacturaElectronica, OrdenServicio,
)

RUTA_P12_REAL = "/home/skorggamor/agente-contador/firmadigital.p12"
XML_FIRMADO = "<factura id='comprobante' version='1.1.0'>FIRMADO</factura>"


async def _crear_engine_bd_prueba(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("orpey_trans") / "orpey_trans.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine


async def _sembrar_factura(session_factory):
    async with session_factory() as s:
        s.add_all([
            ConfiguracionSistema(clave="iva_porcentaje", valor="15"),
            ConfiguracionSistema(clave="firma_p12_ruta", valor=RUTA_P12_REAL),
        ])
        cli = Cliente(nombre="Tanya", apellido="Triviño Meza",
                      telefono="0999999999", cedula_ruc="0926048380")
        s.add(cli)
        await s.flush()
        orden = OrdenServicio(numero_orden="ORP-TRANS-001", cliente_id=cli.id,
                              estado=EstadoOrden.entregada,
                              total_orden=Decimal("25.00"), abono=Decimal("25.00"))
        s.add(orden)
        await s.flush()
        s.add(EquipoOrden(orden_id=orden.id, tipo_equipo="impresora",
                          marca="HP", modelo="INK TANK 315",
                          descripcion_problema="ERROR E03", costo=Decimal("25.00")))
        fac = FacturaElectronica(
            orden_servicio_id=orden.id, cliente_id=cli.id,
            clave_acceso="2808202601096479423400110010010000000011234567812",
            numero_documento="001-001-000000001", ambiente="1",
            estado_sri="firmado", xml_firmado=XML_FIRMADO,
            subtotal=Decimal("21.74"), iva=Decimal("3.26"), total=Decimal("25.00"),
        )
        s.add(fac)
        await s.flush()
        fac_id = fac.id
        await s.commit()
        return fac_id


@pytest.fixture
async def cliente_api(tmp_path_factory):
    engine = await _crear_engine_bd_prueba(tmp_path_factory)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    fac_id = await _sembrar_factura(session_factory)

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
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://test") as ac:
            yield ac, session_factory, fac_id
    finally:
        app.dependency_overrides.pop(get_db, None)
        await engine.dispose()


def _mock_transmision(monkeypatch, recepcion_estado="RECIBIDA",
                      aut_estado="AUTORIZADO", xml_autorizado=None,
                      numero="2808202601096479423400110010010000000011234567812",
                      fecha="2026-08-28T10:00:00.000-05:00"):
    """Mockea httpx.post para responder recepción y luego autorización."""
    numero_autorizacion = numero
    fmgs = []
    if recepcion_estado == "DEVUELTA":
        fmgs = [{"identificador": "35", "mensaje": "ARCHIVO NO CUMPLE ESTRUCTURA XML",
                 "informacionAdicional": "cvc-minLength", "tipo": "ERROR"}]

    def fake_post(url, **kwargs):
        if "Recepcion" in url:
            return _RespuestaFalsa(_soap_respuesta_recepcion(recepcion_estado, fmgs))
        if "Autorizacion" in url:
            axml = xml_autorizado if xml_autorizado is not None else "<factura>AUTORIZADO</factura>"
            amsgs = []
            if aut_estado == "NO AUTORIZADO":
                amsgs = [{"identificador": "43", "mensaje": "FIRMA ELECTRONICA",
                          "informacionAdicional": "", "tipo": "ERROR"}]
            if aut_estado == "EN PROCESO":
                amsgs = []
            return _RespuestaFalsa(_soap_respuesta_autorizacion(
                aut_estado, numero=numero_autorizacion, fecha=fecha,
                comp_xml=(axml if aut_estado == "AUTORIZADO" else None), mensajes=amsgs))
        raise AssertionError(f"URL inesperada: {url}")

    monkeypatch.setattr(httpx, "post", fake_post)


# --- tests del endpoint ---

async def test_transmitir_factura_inexistente_404(cliente_api):
    ac, _sf, _id = cliente_api
    resp = await ac.post("/api/facturacion/999999/transmitir", json={})
    assert resp.status_code == 404
    assert "no encontrada" in resp.json()["detail"]


async def test_transmitir_factura_firmada_persiste_autorizado(cliente_api, monkeypatch):
    ac, sf, fac_id = cliente_api
    _mock_transmision(monkeypatch, recepcion_estado="RECIBIDA", aut_estado="AUTORIZADO",
                      xml_autorizado="<factura>AUTORIZADO_FINAL</factura>")
    resp = await ac.post(f"/api/facturacion/{fac_id}/transmitir", json={})
    assert resp.status_code == 200
    data = resp.json()["data"] if isinstance(resp.json(), dict) and "data" in resp.json() else resp.json()
    # La respuesta del endpoint devuelve dict con claves; revisar persistencia en BD
    async with sf() as s:
        from sqlalchemy import select
        from src.models.models import FacturaElectronica
        fac = (await s.execute(select(FacturaElectronica).where(
            FacturaElectronica.id == fac_id))).scalar_one()
        assert fac.estado_sri == "autorizado"
        assert fac.numero_autorizacion == "2808202601096479423400110010010000000011234567812"
        assert fac.fecha_autorizacion is not None
        # EL XML AUTORIZADO BASE64 SE GUARDA DECODIFICADO
        assert fac.xml_respuesta_sri == "<factura>AUTORIZADO_FINAL</factura>"


async def test_transmitir_factura_devuelta_guarda_errores(cliente_api, monkeypatch):
    ac, sf, fac_id = cliente_api
    _mock_transmision(monkeypatch, recepcion_estado="DEVUELTA")
    resp = await ac.post(f"/api/facturacion/{fac_id}/transmitir", json={})
    assert resp.status_code == 200
    async with sf() as s:
        from sqlalchemy import select
        from src.models.models import FacturaElectronica
        fac = (await s.execute(select(FacturaElectronica).where(
            FacturaElectronica.id == fac_id))).scalar_one()
        assert fac.estado_sri == "devuelta"
        assert "35" in fac.xml_respuesta_sri
        assert "ARCHIVO NO CUMPLE ESTRUCTURA XML" in fac.xml_respuesta_sri


async def test_transmitir_factura_no_autorizada(cliente_api, monkeypatch):
    ac, sf, fac_id = cliente_api
    _mock_transmision(monkeypatch, recepcion_estado="RECIBIDA", aut_estado="NO AUTORIZADO")
    resp = await ac.post(f"/api/facturacion/{fac_id}/transmitir", json={})
    assert resp.status_code == 200
    async with sf() as s:
        from sqlalchemy import select
        from src.models.models import FacturaElectronica
        fac = (await s.execute(select(FacturaElectronica).where(
            FacturaElectronica.id == fac_id))).scalar_one()
        assert fac.estado_sri == "no_autorizado"


async def test_transmitir_produccion_requiere_confirmacion(cliente_api, monkeypatch):
    """Ambiente producción sin confirmar → 403."""
    ac, sf, fac_id = cliente_api
    _mock_transmision(monkeypatch, recepcion_estado="RECIBIDA", aut_estado="AUTORIZADO")
    resp = await ac.post(
        f"/api/facturacion/{fac_id}/transmitir",
        json={"forzar_ambiente": "2"},
    )
    assert resp.status_code == 403
    assert "confirmar_produccion" in resp.json()["detail"]


async def test_transmitir_en_proceso_reintenta_y_envia(cliente_api, monkeypatch):
    """EN PROCESO en la 1ª consulta; a la 2ª AUTORIZADO (simula reintento)."""
    ac, sf, fac_id = cliente_api
    calls = {"n": 0}
    numero = "2808202601096479423400110010010000000011234567812"

    def fake_post(url, **kwargs):
        if "Recepcion" in url:
            return _RespuestaFalsa(_soap_respuesta_recepcion("RECIBIDA"))
        if "Autorizacion" in url:
            calls["n"] += 1
            if calls["n"] == 1:
                return _RespuestaFalsa(_soap_respuesta_autorizacion("EN PROCESO"))
            return _RespuestaFalsa(_soap_respuesta_autorizacion(
                "AUTORIZADO", numero=numero, comp_xml="<factura>AUT</factura>"))
        raise AssertionError(url)

    monkeypatch.setattr(httpx, "post", fake_post)
    resp = await ac.post(f"/api/facturacion/{fac_id}/transmitir", json={})
    assert resp.status_code == 200
    assert calls["n"] >= 2
    async with sf() as s:
        from sqlalchemy import select
        from src.models.models import FacturaElectronica
        fac = (await s.execute(select(FacturaElectronica).where(
            FacturaElectronica.id == fac_id))).scalar_one()
        assert fac.estado_sri == "autorizado"
