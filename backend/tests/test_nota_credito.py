"""
Tests de la NOTA DE CRÉDITO (anulación de facturas, comprobante 04).

Cubre:
1. Generación del XML de NC: codDoc=04, numDocModificado=clave de la factura
   original, codDocModificado=01, signo (NEGATIVO por SIGNO_NOTA_CREDITO),
   totales consistentes, detalle descriptivo, firma XAdES-BES que no rompe.
2. Clave de acceso de NC tipo 04 válida (49 dígitos + dígito verificador).
3. Endpoint POST /api/facturacion/{id}/anular (BD SQLite aislada):
   - factura inexistente → 404
   - comprobante que ya es NC → 400
   - factura ya anulada (estado o NC vigente asociada) → 400
   - monto_anular > total → 400
   - factura en 'firmado'/'devuelta' → 400 (solo 'autorizado'/'recibida')
   - fecha de NC anterior a la factura → 400
   - flujo completo: NC persistida con factura_referenciada_id + original 'anulada'
   - anulación parcial → original 'anulada_parcial'
   - fallo de red → NC queda 'firmado', original NO se marca
4. Listado: GET /api/facturacion/ incluye NC con tipo, filtro ?tipo=01/04.

NUNCA se hacen llamadas reales al SRI: se mockea httpx.post (patrón de
tests/test_transmision_sri.py) o transmitir_y_autorizar directamente.
"""

import base64
from datetime import date, datetime
from decimal import Decimal

import httpx
import pytest
from lxml import etree

from src.services.facturacion_sri import (
    EMISOR,
    firmar_xml,
    generar_clave_acceso,
    generar_comprobante_nota_credito,
)


# =====================================================
# Claves de acceso de prueba determinísticas (49 dígitos)
# =====================================================

_FECHA_FIX = datetime(2026, 8, 28)


def _clave(tipo: str, secuencial: str) -> str:
    """Clave de acceso determinística para sembrar/asserts."""
    return generar_clave_acceso(
        fecha=_FECHA_FIX,
        tipo_comprobante=tipo,
        ruc=EMISOR["ruc"],
        ambiente="1",
        establecimiento="001",
        punto_emision="001",
        secuencial=secuencial,
        codigo_numerico="12345678",
    )


# =====================================================
# Datos de ejemplo (unit tests de generación XML)
# =====================================================

_KEY_FACTURA = _clave("01", "000000001")


def _factura_original():
    return {
        "clave_acceso": _KEY_FACTURA,
        "numero_documento": "001-001-000000001",
        "fecha_emision": datetime(2026, 8, 28),
        "total": Decimal("25.00"),
    }


def _cliente_ejemplo():
    return {
        "nombre": "Tanya",
        "apellido": "Triviño Meza",
        "nombre_completo": "Tanya Triviño Meza",
        "cedula_ruc": "0926048380",
        "direccion": "Bastion Popular, Bloque 2",
    }


def _config_ejemplo():
    return {"iva_porcentaje": Decimal("15")}


def _generar_nc(**overrides):
    """Genera un comprobante NC por defecto ($25 → subtotal 21.74 / iva 3.26)."""
    kwargs = dict(
        factura_original=_factura_original(),
        cliente=_cliente_ejemplo(),
        config=_config_ejemplo(),
        secuencial="000000001",
        motivo="Devolución del cliente",
        monto_anular=Decimal("25.00"),
        ambiente="1",
        fecha_emision=datetime(2026, 8, 29),
    )
    kwargs.update(overrides)
    return generar_comprobante_nota_credito(**kwargs)


def _digito_verificador(clave: str) -> str:
    """Recomputa el dígito verificador (módulo 11) de una clave de 49 dígitos."""
    base = clave[:48]
    factores = [2, 3, 4, 5, 6, 7]
    total = sum(int(c) * factores[i % 6] for i, c in enumerate(reversed(base)))
    digito = 11 - (total % 11)
    if digito == 11:
        digito = 0
    elif digito == 10:
        digito = 1
    return str(digito)


# =====================================================
# 1. Generación XML de NC
# =====================================================

def test_nc_xml_estructura_coddoc_04():
    comp = _generar_nc()
    root = etree.fromstring(comp["xml"].encode())
    assert root.tag == "notaCredito"
    assert root.get("version") == "1.1.0"
    # Orden normativo: infoTributaria → infoNotaCredito → detalles → infoAdicional
    hijos = [child.tag for child in root]
    assert hijos == ["infoTributaria", "infoNotaCredito", "detalles", "infoAdicional"]

    trib = root.find("infoTributaria")
    assert trib.find("codDoc").text == "04"
    assert trib.find("ruc").text == EMISOR["ruc"]
    assert len(trib.find("claveAcceso").text) == 49
    assert trib.find("secuencial").text == "000000001"


def test_nc_xml_referencia_factura_original():
    comp = _generar_nc()
    info = etree.fromstring(comp["xml"].encode()).find("infoNotaCredito")
    # Referencia al documento sustento: factura (01) y su número de documento
    # (el XSD/SRI exige formato "001-001-000000001", NO la clave de acceso)
    assert info.find("codDocModificado").text == "01"
    assert info.find("numDocModificado").text == "001-001-000000001"
    assert info.find("fechaEmisionDocSustento").text == "28/08/2026"
    assert info.find("motivo").text == "Devolución del cliente"
    assert info.find("razonSocialComprador").text == "Tanya Triviño Meza"
    assert info.find("identificacionComprador").text == "0926048380"
    assert info.find("tipoIdentificacionComprador").text == "05"
    assert info.find("obligadoContabilidad").text == "NO"


def test_nc_xml_signo_positivo_totales():
    """Los montos de la NC van en POSITIVO — verificado en vivo 29/08/2026:
    el XSD/SRI rechaza negativos (cvc-minInclusive 0.0) y el tipo 04
    ya identifica la nota de crédito."""
    comp = _generar_nc()
    info = etree.fromstring(comp["xml"].encode()).find("infoNotaCredito")
    # $25 total → subtotal 21.74 / IVA 3.26, positivos
    assert info.find("totalSinImpuestos").text == "21.74"
    assert info.find("valorModificacion").text == "21.74"
    ti = info.find("totalConImpuestos/totalImpuesto")
    assert ti.find("codigo").text == "2"
    assert ti.find("codigoPorcentaje").text == "4"
    assert ti.find("baseImponible").text == "21.74"
    assert ti.find("valor").text == "3.26"

    # Los montos DEVUELTOS son magnitudes positivas (para BD/UI)
    assert comp["subtotal"] == Decimal("21.74")
    assert comp["iva"] == Decimal("3.26")
    assert comp["total"] == Decimal("25.00")


def test_nc_xml_detalle_descriptivo():
    comp = _generar_nc()
    detalle = etree.fromstring(comp["xml"].encode()).find("detalles/detalle")
    assert "ANULACIÓN DE FACTURA" in detalle.find("descripcion").text
    assert detalle.find("cantidad").text == "1"
    assert detalle.find("precioUnitario").text == "21.74"
    assert detalle.find("precioTotalSinImpuesto").text == "21.74"
    imp = detalle.find("impuestos/impuesto")
    assert imp.find("tarifa").text == "15"
    assert imp.find("baseImponible").text == "21.74"
    assert imp.find("valor").text == "3.26"


def test_nc_xml_direccion_cliente_en_info_adicional():
    """En la NC, infoAdicional lleva la dirección del COMPRADOR (no RIMPE)."""
    comp = _generar_nc()
    root = etree.fromstring(comp["xml"].encode())
    adicional = root.find("infoAdicional")
    campos = {c.get("nombre"): (c.text or "") for c in adicional.findall("campoAdicional")}
    assert campos.get("Dirección") == "Bastion Popular, Bloque 2"
    assert "RIMPE" not in " ".join(campos.values())


# =====================================================
# 2. Clave de acceso de NC (tipo 04)
# =====================================================

def test_nc_clave_acceso_04_valida():
    comp = _generar_nc()
    clave = comp["clave_acceso"]
    assert len(clave) == 49
    assert clave.isdigit()
    # Tipo de comprobante en la posición 9-10 = "04"
    assert clave[8:10] == "04"
    # Dígito verificador correcto (módulo 11)
    assert clave[-1] == _digito_verificador(clave)


def test_nc_clave_acceso_usa_secuencial_y_fecha():
    """La clave de la NC lleva fecha/estab/pto/secuencial propios (01, serie 001-001)."""
    comp = _generar_nc(secuencial="000000007", fecha_emision=datetime(2026, 8, 29))
    clave = comp["clave_acceso"]
    assert clave[8:10] == "04"
    assert "29082026" in clave[:20]  # fecha DDMMAAAA
    assert "001001000000007" in clave  # establecimiento-punto-secuencial


# =====================================================
# 3. Firma XAdES-BES de la NC
# =====================================================

RUTA_P12_PRUEBAS = "/home/skorggamor/agente-contador/firma_pruebas.p12"
PASSWORD_PRUEBAS = "firma-pruebas-orpey-2026"


def test_nc_firma_no_rompe_estructura():
    """El mismo pipeline de firma (XAdES-BES) firma la NC sin romper el XML."""
    comp = _generar_nc()
    xml_firmado = firmar_xml(comp["xml"], RUTA_P12_PRUEBAS, PASSWORD_PRUEBAS)
    root = etree.fromstring(xml_firmado.encode())
    # La firma va al final (después de infoAdicional)
    assert root[-1].tag.endswith("Signature")
    sig = root.find("{http://www.w3.org/2000/09/xmldsig#}Signature")
    assert sig is not None
    x509 = sig.find(".//{http://www.w3.org/2000/09/xmldsig#}X509Certificate")
    assert x509 is not None and x509.text


# =====================================================
# Endpoint /anular — BD aislada
# =====================================================

from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.config.database import get_db
from src.main import app
from src.models.models import (
    Base,
    Cliente,
    ConfiguracionSistema,
    FacturaElectronica,
)
from src.services.transmision_sri import ErrorTransmisionSRI

RUTA_P12_REAL = "/home/skorggamor/agente-contador/firmadigital.p12"
XML_FIRMADO = "<factura id='comprobante' version='1.1.0'>FIRMADO</factura>"


async def _crear_engine_bd_prueba(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("orpey_nc") / "orpey_nc.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine


async def _sembrar_datos(session_factory) -> dict:
    """Siembra un cliente y facturas en varios estados (más una NC vigente)."""
    async with session_factory() as s:
        s.add_all([
            ConfiguracionSistema(clave="iva_porcentaje", valor="15"),
            ConfiguracionSistema(clave="firma_p12_ruta", valor=RUTA_P12_REAL),
        ])
        cli = Cliente(nombre="Tanya", apellido="Triviño Meza",
                      telefono="0999999999", cedula_ruc="0926048380",
                      direccion="Bastion Popular, Bloque 2")
        s.add(cli)
        await s.flush()
        cid = cli.id

        def _fac(secuencial, estado, total):
            fac = FacturaElectronica(
                orden_servicio_id=None, nota_venta_id=None, cliente_id=cid,
                tipo_comprobante="01",
                clave_acceso=_clave("01", secuencial),
                numero_documento=f"001-001-{secuencial}",
                ambiente="1", estado_sri=estado, xml_firmado=XML_FIRMADO,
                subtotal=Decimal("21.74"), iva=Decimal("3.26"),
                total=Decimal(str(total)),
            )
            s.add(fac)
            return fac

        # Facturas recibidas (anulables): para flujo total, parcial y fallo de red
        f_rec = _fac("000000001", "recibida", 25.00)
        f_rec2 = _fac("000000002", "recibida", 25.00)
        f_rec3 = _fac("000000003", "recibida", 25.00)
        # No anulables por estado
        f_firmado = _fac("000000004", "firmado", 30.00)
        f_devuelta = _fac("000000005", "devuelta", 40.00)
        # Ya anulada por NC vigente (guarda anti-doble) → 400
        f_anulada = _fac("000000006", "recibida", 60.00)
        # Ya anulada por estado propio (otra convención) → 400
        f_marcada = _fac("000000007", "anulada_parcial", 50.00)
        await s.flush()

        nc_existente = FacturaElectronica(
            orden_servicio_id=None, nota_venta_id=None, cliente_id=cid,
            tipo_comprobante="04", factura_referenciada_id=f_anulada.id,
            motivo_anulacion="Anulación total previa", valor_anulacion=Decimal("52.17"),
            clave_acceso=_clave("04", "000000001"),
            numero_documento="001-001-000000001", ambiente="1",
            estado_sri="autorizado", xml_firmado=XML_FIRMADO,
            subtotal=Decimal("52.17"), iva=Decimal("7.83"), total=Decimal("60.00"),
        )
        s.add(nc_existente)
        await s.flush()
        ids = {
            "cliente_id": cid,
            "recibida": f_rec.id,
            "recibida2": f_rec2.id,
            "recibida3": f_rec3.id,
            "firmado": f_firmado.id,
            "devuelta": f_devuelta.id,
            "anulada": f_anulada.id,
            "marcada": f_marcada.id,
            "nc_existente": nc_existente.id,
        }
        await s.commit()
        return ids


@pytest.fixture
async def cliente_api(tmp_path_factory):
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
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://test") as ac:
            yield ac, session_factory, ids
    finally:
        app.dependency_overrides.pop(get_db, None)
        await engine.dispose()


# --- fábrica de respuestas SOAP falsas (recepción/autorización) ---

def _resp_falsa(content: bytes):
    class _R:
        def __init__(self, content):
            self.content = content
            self.status_code = 200
        def raise_for_status(self):
            return None
    return _R(content)


def _soap_recepcion(estado: str) -> bytes:
    return (
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
        '<soap:Body><ns2:validarComprobanteResponse xmlns:ns2='
        '"http://ec.gob.sri.ws.recepcion"><RespuestaRecepcionComprobante>'
        f"<estado>{estado}</estado></RespuestaRecepcionComprobante>"
        "</ns2:validarComprobanteResponse></soap:Body></soap:Envelope>"
    ).encode()


def _soap_autorizacion(estado: str, comp_xml=None, numero="2808202601096479423400110010010000000011234567812") -> bytes:
    b64 = ""
    if comp_xml is not None:
        b64 = base64.b64encode(comp_xml.encode("utf-8")).decode("ascii")
    return (
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
        '<soap:Body><ns2:autorizacionComprobanteResponse xmlns:ns2='
        '"http://ec.gob.sri.ws.autorizacion"><autorizacion>'
        f"<estado>{estado}</estado><numeroAutorizacion>{numero}</numeroAutorizacion>"
        f"<comprobante>{b64}</comprobante>"
        "</autorizacion></ns2:autorizacionComprobanteResponse>"
        "</soap:Body></soap:Envelope>"
    ).encode()


def _mock_transmision(monkeypatch, aut_estado="AUTORIZADO", numero="2808202601096479423400110010010000000011234567812"):
    """Mockea httpx.post: recepción RECIBIDA + autorización con el estado dado."""
    def fake_post(url, **kwargs):
        if "Recepcion" in url:
            return _resp_falsa(_soap_recepcion("RECIBIDA"))
        if "Autorizacion" in url:
            comp = "<notaCredito>AUTORIZADA</notaCredito>" if aut_estado == "AUTORIZADO" else None
            return _resp_falsa(_soap_autorizacion(aut_estado, comp_xml=comp, numero=numero))
        raise AssertionError(f"URL inesperada: {url}")
    monkeypatch.setattr(httpx, "post", fake_post)


# --- validaciones del endpoint ---

async def test_anular_factura_inexistente_404(cliente_api):
    ac, _sf, _ids = cliente_api
    resp = await ac.post("/api/facturacion/999999/anular", json={"motivo": "Error"})
    assert resp.status_code == 404
    assert "no encontrada" in resp.json()["detail"]


async def test_anular_nota_credito_rechazada_400(cliente_api):
    """No se anula una NC con otra NC: el comprobante debe ser factura (01)."""
    ac, _sf, ids = cliente_api
    resp = await ac.post(
        f"/api/facturacion/{ids['nc_existente']}/anular", json={"motivo": "x"}
    )
    assert resp.status_code == 400
    assert "nota de crédito" in resp.json()["detail"]


async def test_anular_monto_mayor_total_400(cliente_api):
    ac, _sf, ids = cliente_api
    resp = await ac.post(
        f"/api/facturacion/{ids['recibida']}/anular",
        json={"motivo": "x", "monto_anular": 30.00},  # total factura = 25.00
    )
    assert resp.status_code == 400
    assert "supera el total" in resp.json()["detail"]


async def test_anular_factura_firmado_400(cliente_api):
    """Factura SOLO firmada (nunca recibida/autorizada) no es anulable."""
    ac, _sf, ids = cliente_api
    resp = await ac.post(
        f"/api/facturacion/{ids['firmado']}/anular", json={"motivo": "x"}
    )
    assert resp.status_code == 400
    assert "autorizado' o 'recibida'" in resp.json()["detail"]


async def test_anular_factura_devuelta_400(cliente_api):
    ac, _sf, ids = cliente_api
    resp = await ac.post(
        f"/api/facturacion/{ids['devuelta']}/anular", json={"motivo": "x"}
    )
    assert resp.status_code == 400
    assert "autorizado' o 'recibida'" in resp.json()["detail"]


async def test_anular_factura_con_nc_vigente_400(cliente_api):
    """Ya existe una NC vigente (autorizada) asociada → rechazada."""
    ac, _sf, ids = cliente_api
    resp = await ac.post(
        f"/api/facturacion/{ids['anulada']}/anular", json={"motivo": "x"}
    )
    assert resp.status_code == 400
    assert "nota de crédito asociada" in resp.json()["detail"]


async def test_anular_factura_marcada_anulada_400(cliente_api):
    """La factura ya está marcada como anulada (estado propio) → rechazada."""
    ac, _sf, ids = cliente_api
    resp = await ac.post(
        f"/api/facturacion/{ids['marcada']}/anular", json={"motivo": "x"}
    )
    assert resp.status_code == 400
    assert "nota de crédito asociada" in resp.json()["detail"]


async def test_anular_fecha_anterior_a_factura_400(cliente_api):
    ac, _sf, ids = cliente_api
    resp = await ac.post(
        f"/api/facturacion/{ids['recibida']}/anular",
        json={"motivo": "x", "fecha_autorizada": "2020-01-01"},
    )
    assert resp.status_code == 400
    assert "no puede ser anterior" in resp.json()["detail"]


# --- flujo completo (transmisión mockeada) ---

async def test_flujo_completo_anulacion_total(cliente_api, monkeypatch):
    """Crear NC → transmitir (mock) → NC vigente y factura original 'anulada'."""
    ac, sf, ids = cliente_api
    numero = "2808202601096479423400110010010000000011234567812"
    _mock_transmision(monkeypatch, aut_estado="AUTORIZADO", numero=numero)

    resp = await ac.post(
        f"/api/facturacion/{ids['recibida']}/anular",
        json={"motivo": "Devolución total del cliente"},
    )
    assert resp.status_code == 200
    data = resp.json()

    nc = data["nota_credito"]
    assert nc["tipo_comprobante"] == "04"
    assert nc["factura_referenciada_id"] == ids["recibida"]
    assert nc["motivo_anulacion"] == "Devolución total del cliente"
    assert nc["estado_sri"] == "autorizado"
    assert nc["numero_autorizacion"] == numero
    # SECUENCIAL INDEPENDIENTE: la NC creada aquí es la 2ª de la serie NC
    # (el seed ya consume el 000000001); las facturas van en el 7 → no comparte.
    assert nc["numero_documento"] == "001-001-000000002"
    assert len(nc["clave_acceso"]) == 49 and nc["clave_acceso"][8:10] == "04"
    # valor_anulacion = subtotal anulado (magnitud positiva)
    assert nc["valor_anulacion"] == "21.74"

    assert data["factura_original"]["estado_sri"] == "anulada"
    assert data["transmision"]["estado"] == "AUTORIZADO"

    # Persistencia en BD
    async with sf() as s:
        nc_db = (await s.execute(select(FacturaElectronica).where(
            FacturaElectronica.id == nc["id"]))).scalar_one()
        assert nc_db.tipo_comprobante == "04"
        assert nc_db.factura_referenciada_id == ids["recibida"]
        assert nc_db.numero_autorizacion == numero
        # El XML autorizado se guarda decodificado
        assert nc_db.xml_respuesta_sri == "<notaCredito>AUTORIZADA</notaCredito>"
        assert nc_db.valor_anulacion == Decimal("21.74")
        orig = (await s.execute(select(FacturaElectronica).where(
            FacturaElectronica.id == ids["recibida"]))).scalar_one()
        assert orig.estado_sri == "anulada"


async def test_anulacion_parcial_marca_anulada_parcial(cliente_api, monkeypatch):
    """monto_anular < total → NC parcial y factura original 'anulada_parcial'."""
    ac, sf, ids = cliente_api
    _mock_transmision(monkeypatch, aut_estado="AUTORIZADO")

    resp = await ac.post(
        f"/api/facturacion/{ids['recibida2']}/anular",
        json={"motivo": "Anula parcialmente", "monto_anular": 10.00},
    )
    assert resp.status_code == 200
    data = resp.json()
    nc = data["nota_credito"]
    # $10 total → subtotal 8.70 / IVA 1.30
    assert nc["subtotal"] == "8.70"
    assert nc["iva"] == "1.30"
    assert nc["total"] == "10.00"
    assert nc["valor_anulacion"] == "8.70"

    assert data["factura_original"]["estado_sri"] == "anulada_parcial"

    async with sf() as s:
        orig = (await s.execute(select(FacturaElectronica).where(
            FacturaElectronica.id == ids["recibida2"]))).scalar_one()
        assert orig.estado_sri == "anulada_parcial"


async def test_anular_fallo_red_deja_nc_firmado(cliente_api, monkeypatch):
    """Fallo de red al transmitir → NC persiste 'firmado' y original NO se marca."""
    import src.routers.facturacion as F

    ac, sf, ids = cliente_api

    def fake_transmitir(*args, **kwargs):
        raise ErrorTransmisionSRI("red simulada caída")

    monkeypatch.setattr(F, "transmitir_y_autorizar", fake_transmitir)

    resp = await ac.post(
        f"/api/facturacion/{ids['recibida3']}/anular",
        json={"motivo": "Sin conexión"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["nota_credito"]["estado_sri"] == "firmado"
    assert data["transmision"]["estado"] == "fallo_red"
    assert "error" in data["transmision"]
    # La factura original NO se marca como anulada
    assert data["factura_original"]["estado_sri"] == "recibida"

    async with sf() as s:
        nc_db = (await s.execute(select(FacturaElectronica).where(
            FacturaElectronica.factura_referenciada_id == ids["recibida3"],
        ))).scalar_one()
        assert nc_db.estado_sri == "firmado"
        assert nc_db.factura_referenciada_id == ids["recibida3"]


# --- listado con tipo ---

async def test_listado_incluye_nc_por_defecto(cliente_api):
    """Sin filtro: el listado devuelve facturas y NCs con su tipo_comprobante."""
    ac, _sf, _ids = cliente_api
    resp = await ac.get("/api/facturacion/")
    assert resp.status_code == 200
    comprobantes = resp.json()
    tipos = [c["tipo_comprobante"] for c in comprobantes]
    assert "01" in tipos and "04" in tipos
    # NCs traen referencia a la factura anulada
    ncs = [c for c in comprobantes if c["tipo_comprobante"] == "04"]
    assert ncs and ncs[0]["factura_referenciada_id"] is not None


async def test_listado_filtro_por_tipo(cliente_api):
    ac, _sf, _ids = cliente_api
    nc = (await ac.get("/api/facturacion/?tipo=04")).json()
    fac = (await ac.get("/api/facturacion/?tipo=01")).json()
    assert nc and all(c["tipo_comprobante"] == "04" for c in nc)
    assert fac and all(c["tipo_comprobante"] == "01" for c in fac)
    # El listado completo tiene ambos tipos
    total = (await ac.get("/api/facturacion/")).json()
    assert len(total) == len(nc) + len(fac)


async def test_descargar_xml_nc(cliente_api, monkeypatch):
    """GET /{id}/xml sirve también el XML firmado de una NC."""
    ac, _sf, ids = cliente_api
    _mock_transmision(monkeypatch)
    resp = await ac.post(
        f"/api/facturacion/{ids['recibida3']}/anular",
        json={"motivo": "Para descargar el XML"},
    )
    nc = resp.json()["nota_credito"]

    xml_resp = await ac.get(f"/api/facturacion/{nc['id']}/xml")
    assert xml_resp.status_code == 200
    assert xml_resp.headers["content-type"].startswith("application/xml")
    assert f'{nc["clave_acceso"]}.xml' in xml_resp.headers["content-disposition"]
    assert "<notaCredito" in xml_resp.text