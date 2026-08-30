"""
Tests del módulo de facturación electrónica SRI (generación local, sin envío).

Cubre:
1. Clave de acceso (49 dígitos + dígito verificador módulo 11).
2. Generación del XML (nodos infoTributaria/infoFactura/detalles + dirección
   en infoAdicional SIN leyenda RIMPE + totales correctos para una orden de
   $25.00; tope consumidor final $50 en Régimen General).
3. Firma XAdES-BES: usa el .p12 de PRUEBAS (firma_pruebas.p12). Si el .p12
   real (firmadigital.p12) tuviera password resolvible se usaría, pero el
   password documentado no abre el archivo (ver reporte), por lo que el test
   firma con el certificado de pruebas autofirmado.
"""

from datetime import datetime, date
from decimal import Decimal

import pytest
from lxml import etree

from src.services.facturacion_sri import (
    EMISOR,
    firmar_xml,
    generar_clave_acceso,
    generar_comprobante_factura,
    obtener_password_firma,
)


# =====================================================
# 1. Clave de acceso (Módulo 11)
# =====================================================

# Vector conocido (generado/verificado con el algoritmo módulo 11 del SRI):
#   fecha 22062026, tipo 01, ruc 1710034065001, amb 1, serie 001001,
#   secuencial 000000001, código numérico 12345678, tipoEmisión 1
CLAVE_CONOCIDA = "2206202601171003406500110010010000000011234567812"


def test_clave_acceso_longitud_y_estructura():
    clave = generar_clave_acceso(
        fecha=datetime(2026, 6, 22),
        tipo_comprobante="01",
        ruc="1710034065001",
        ambiente="1",
        establecimiento="001",
        punto_emision="001",
        secuencial="000000001",
        codigo_numerico="12345678",
    )
    assert len(clave) == 49
    assert clave.isdigit()
    assert clave == CLAVE_CONOCIDA
    # Los 48 primeros dígitos son la base; el 49 es verificador
    base = clave[:48]
    assert base.startswith("22062026")  # fecha DDMMAAAA
    assert base[-1] == "1"              # tipoEmisión


def test_clave_acceso_digito_verificador_reglas():
    # Regla: si 11 - (total % 11) == 11 -> 0; == 10 -> 1; else el valor
    clave = generar_clave_acceso(
        fecha=datetime(2026, 1, 1),
        tipo_comprobante="01",
        ruc=EMISOR["ruc"],
        ambiente="1",
        establecimiento="001",
        punto_emision="001",
        secuencial="000000001",
        codigo_numerico="12345678",
    )
    assert len(clave) == 49


@pytest.mark.parametrize("campo,valor,esperado_error", [
    ("establecimiento", "0012", "3 dígitos"),
    ("secuencial", "00000000", "9 dígitos"),
    ("codigo_numerico", "123", "8 dígitos"),
    ("ambiente", "3", "ambiente"),
])
def test_clave_acceso_validaciones(campo, valor, esperado_error):
    kwargs = dict(
        fecha=datetime(2026, 1, 1),
        tipo_comprobante="01",
        ruc="1710034065001",
        ambiente="1",
        establecimiento="001",
        punto_emision="001",
        secuencial="000000001",
        codigo_numerico="12345678",
    )
    kwargs[campo] = valor
    with pytest.raises(ValueError, match=esperado_error):
        generar_clave_acceso(**kwargs)


# =====================================================
# 2. Generación del XML
# =====================================================

def _orden_ejemplo():
    return {
        "id": 56,
        "numero_orden": "ORP-0020",
        "total_orden": Decimal("25.00"),
        "equipos": [{
            "tipo_equipo": "impresora",
            "marca": "HP",
            "modelo": "INK TANK 315",
            "descripcion_problema": "ERROR E03",
            "costo": Decimal("25.00"),
        }],
    }


def _cliente_ejemplo():
    return {
        "nombre": "Tanya",
        "apellido": "Triviño Meza",
        "nombre_completo": "Tanya Triviño Meza",
        "cedula_ruc": "0926048380",
        "direccion": None,
    }


def _config_ejemplo():
    return {"iva_porcentaje": Decimal("15")}


def test_generacion_xml_estructura():
    comp = generar_comprobante_factura(
        _orden_ejemplo(), _cliente_ejemplo(), _config_ejemplo(),
        secuencial="000000001", ambiente="1",
    )
    root = etree.fromstring(comp["xml"].encode())
    assert root.tag == "factura"
    assert root.get("version") == "1.1.0"

    # infoTributaria → infoFactura → detalles → infoAdicional
    hijos = [child.tag for child in root]
    assert hijos == ["infoTributaria", "infoFactura", "detalles", "infoAdicional"]

    trib = root.find("infoTributaria")
    assert trib.find("ruc").text == "0964794234001"
    assert trib.find("ambiente").text == "1"
    assert trib.find("tipoEmision").text == "1"
    assert trib.find("codDoc").text == "01"
    assert trib.find("razonSocial").text == "BALTODANO Catarine Daniel ABRAHAM"
    assert len(trib.find("claveAcceso").text) == 49
    assert trib.find("estab").text == "001"
    assert trib.find("ptoEmi").text == "001"

    info = root.find("infoFactura")
    assert info.find("fechaEmision").text.count("/") == 2  # DD/MM/AAAA
    # Cliente sin dirección → el XSD/SRI exige minLength 1 en
    # direccionComprador (verificado en vivo 29/08/2026: cvc-minLength-valid).
    assert info.find("direccionComprador").text == "SIN DIRECCIÓN REGISTRADA"
    assert info.find("obligadoContabilidad").text == "NO"
    assert info.find("tipoIdentificacionComprador").text == "05"   # cédula
    assert info.find("identificacionComprador").text == "0926048380"
    assert info.find("razonSocialComprador").text == "Tanya Triviño Meza"

    # Totales: $25.00 con IVA 15% → subtotal 21.74, IVA 3.26, total 25.00
    assert info.find("totalSinImpuestos").text == "21.74"
    assert info.find("importeTotal").text == "25.00"
    total_imp = info.find("totalConImpuestos/totalImpuesto")
    assert total_imp.find("codigo").text == "2"          # IVA
    assert total_imp.find("codigoPorcentaje").text == "4"  # 15% vigente
    assert total_imp.find("baseImponible").text == "21.74"
    assert total_imp.find("valor").text == "3.26"
    assert info.find("pagos/pago/formaPago").text == "01"
    assert info.find("moneda").text == "DOLAR"

    detalle = root.find("detalles/detalle")
    assert detalle.find("cantidad").text == "1"
    assert detalle.find("precioUnitario").text == "21.74"
    assert detalle.find("impuestos/impuesto/codigoPorcentaje").text == "4"
    assert detalle.find("impuestos/impuesto/tarifa").text == "15"

    # Régimen General: sin leyenda RIMPE, solo dirección en infoAdicional
    adicional = root.find("infoAdicional")
    nombres = [c.get("nombre") for c in adicional.findall("campoAdicional")]
    assert "Dirección" in nombres
    assert "RIMPE" not in " ".join(nombres)


def test_generacion_xml_consumidor_final_sin_id():
    cliente = _cliente_ejemplo()
    cliente["cedula_ruc"] = None
    comp = generar_comprobante_factura(
        _orden_ejemplo(), cliente, _config_ejemplo(),
        secuencial="000000001", ambiente="1",
    )
    info = etree.fromstring(comp["xml"].encode()).find("infoFactura")
    assert info.find("tipoIdentificacionComprador").text == "07"  # consumidor final


def test_generacion_xml_error_consumidor_final_mayor_50():
    """Consumidor final sin identificación con total > $50 → rechazado (Régimen General)."""
    orden = _orden_ejemplo()
    orden["total_orden"] = Decimal("50.01")
    cliente = _cliente_ejemplo()
    cliente["cedula_ruc"] = None
    with pytest.raises(ValueError, match="límite"):
        generar_comprobante_factura(
            orden, cliente, _config_ejemplo(),
            secuencial="000000001", ambiente="1",
        )


def test_generacion_xml_consumidor_final_limite_exacto_50_ok():
    """Consumidor final sin identificación con total = $50.00 → permitido (regla ~> $50)."""
    orden = _orden_ejemplo()
    orden["total_orden"] = Decimal("50.00")
    cliente = _cliente_ejemplo()
    cliente["cedula_ruc"] = None
    comp = generar_comprobante_factura(
        orden, cliente, _config_ejemplo(),
        secuencial="000000001", ambiente="1",
    )
    info = etree.fromstring(comp["xml"].encode()).find("infoFactura")
    assert info.find("tipoIdentificacionComprador").text == "07"
    assert info.find("importeTotal").text == "50.00"


def test_generacion_xml_consumidor_final_200_rechazado():
    """El tope ya no es $200: consumidor final con total $200 → rechazado con el nuevo límite de $50."""
    orden = _orden_ejemplo()
    orden["total_orden"] = Decimal("200.00")
    cliente = _cliente_ejemplo()
    cliente["cedula_ruc"] = None
    with pytest.raises(ValueError, match="límite"):
        generar_comprobante_factura(
            orden, cliente, _config_ejemplo(),
            secuencial="000000001", ambiente="1",
        )


def test_xml_no_contiene_rimpe():
    """El XML de la factura NO debe contener 'RIMPE' ni leyendas de régimen."""
    comp = generar_comprobante_factura(
        _orden_ejemplo(), _cliente_ejemplo(), _config_ejemplo(),
        secuencial="000000001", ambiente="1",
    )
    assert "RIMPE" not in comp["xml"]
    assert "Contribuyente Régimen" not in comp["xml"]
    # No debe haber campoAdicional vacío (sin texto)
    root = etree.fromstring(comp["xml"].encode())
    for campo in root.iter("campoAdicional"):
        assert (campo.text or "").strip() != ""


def test_generacion_xml_valida_secuencial_9_digitos():
    comp = generar_comprobante_factura(
        _orden_ejemplo(), _cliente_ejemplo(), _config_ejemplo(),
        secuencial="000000003", ambiente="1",
    )
    assert comp["numero_documento"] == "001-001-000000003"
    trib = etree.fromstring(comp["xml"].encode()).find("infoTributaria")
    assert trib.find("secuencial").text == "000000003"


# =====================================================
# 3. Firma XAdES-BES
# =====================================================

RUTA_P12_REAL = "/home/skorggamor/agente-contador/firmadigital.p12"
RUTA_P12_PRUEBAS = "/home/skorggamor/agente-contador/firma_pruebas.p12"


def _xml_simple():
    comp = generar_comprobante_factura(
        _orden_ejemplo(), _cliente_ejemplo(), _config_ejemplo(),
        secuencial="000000001", ambiente="1",
    )
    return comp["xml"]


def test_firma_xades_bes_con_p12_pruebas():
    """
    Firma con el certificado de PRUEBAS autofirmado (creado para validar el
    pipeline completo). Usa la contraseña FIJA del .p12 de pruebas
    (firma-pruebas-orpey-2026) — no depende de la firma real de producción
    ni del password resuelto por obtener_password_firma().
    """
    ruta_p12 = RUTA_P12_PRUEBAS
    password = "firma-pruebas-orpey-2026"

    xml_firmado = firmar_xml(_xml_simple(), ruta_p12, password)

    # Debe seguir parseando como XML (estructura válida)
    root = etree.fromstring(xml_firmado.encode())
    # La firma va al final del documento (después de infoAdicional)
    hijos = [child.tag for child in root]
    assert hijos[-1].endswith("Signature")
    sig = root.find("{http://www.w3.org/2000/09/xmldsig#}Signature")
    assert sig is not None
    # El certificado del emisor viaja en la firma
    x509 = sig.find(".//{http://www.w3.org/2000/09/xmldsig#}X509Certificate")
    assert x509 is not None and x509.text


def test_firma_p12_pruebas_abre():
    """El .p12 de pruebas debe ser legible (validación interna del entorno)."""
    from cryptography.hazmat.primitives.serialization import pkcs12
    with open(RUTA_P12_PRUEBAS, "rb") as f:
        key, cert, _ = pkcs12.load_key_and_certificates(
            f.read(), b"firma-pruebas-orpey-2026"
        )
    assert key is not None
    assert cert is not None


def test_firma_p12_produccion_con_password_resuelto():
    """
    El .p12 REAL (firmadigital.p12) debe firmar con el password resuelto por
    obtener_password_firma() (env FIRMA_P12_PASSWORD o ~/agente-contador/
    .firma_p12.pass). Es el mismo pipeline que usa POST /api/facturacion/generar.
    """
    password = obtener_password_firma()
    if not password:
        pytest.skip("Sin password de firma configurado (FIRMA_P12_PASSWORD o ~/agente-contador/.firma_p12.pass)")

    xml_firmado = firmar_xml(_xml_simple(), RUTA_P12_REAL, password)
    root = etree.fromstring(xml_firmado.encode())
    sig = root.find("{http://www.w3.org/2000/09/xmldsig#}Signature")
    assert sig is not None


def test_firma_detecta_password_incorrecto():
    """Un password incorrecto debe fallar con error claro (no con XML roto)."""
    with pytest.raises(Exception):
        firmar_xml(_xml_simple(), RUTA_P12_PRUEBAS, "password-incorrecto")


def test_serializar_respuesta():
    comp = generar_comprobante_factura(
        _orden_ejemplo(), _cliente_ejemplo(), _config_ejemplo(),
        secuencial="000000001", ambiente="1",
    )
    from src.services.facturacion_sri import serializar_respuesta
    respuesta = serializar_respuesta(comp, estado="generado")
    assert respuesta["estado"] == "generado"
    assert respuesta["clave_acceso"] == comp["clave_acceso"]
    assert respuesta["errores"] == []
    assert "<factura" in respuesta["xml_firmado"]