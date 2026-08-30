"""
Servicio de Transmisión SOAP al SRI (Ecuador) - Recepción y Autorización.

Este módulo toma el XML firmado (XAdES-BES) generado por `facturacion_sri.py`
y lo transmite a los web services del SRI para convertirlo en un comprobante
REAL con número de autorización.

FUNCIONAMIENTO:
- Recepción  (`validarComprobante`): envía el XML firmado y recibe
  RECIBIDA / DEVUELTA (+ mensajes de error con identificador).
- Autorización (`autorizacionComprobante`): consulta por claveAcceso y recibe
  AUTORIZADO / NO AUTORIZADO / EN PROCESO, con el número y fecha de
  autorización y, si AUTORIZADO, el XML autorizado (base64).

SEGURIDAD (WS-Security X509):
- Los WS del SRI exigen firma digital del contribuyente en el SOAP:
  header `wsse:Security` con `wsse:BinarySecurityToken` (X509 del .p12) y una
  `ds:Signature` que firma el `<soap:Body>` (Reference URI="#Body",
  transform enveloped).
- La firma SOAP (no es la del comprobante) se construye con `signxml` sobre
  el body del envelope (igual que la firma XAdES del comprobante).
- IMPORTANTE (verificado con el SRI real de certificación): el header NO debe
  llevar `soapenv:mustUnderstand`, y los hijos de la operación deben ir en
  namespace NO calificado (elementFormDefault="unqualified" en el WSDL).

AMBIENTES:
- "1" = PRUEBAS (certificación): celcer.sri.gob.ec
- "2" = PRODUCCIÓN: cel.sri.gob.ec

Manejo de errores:
- Las respuestas DEVUELTA / NO AUTORIZADO se devuelven con su detalle
  (código + mensaje) para que el usuario vea POR QUÉ falló.
- Los errores de RED (timeout, TLS, conexión) se elevan como excepción clara
  y NO se confunden con un rechazo del SRI.
"""

import base64
import logging
from typing import Optional

from lxml import etree

from src.services.facturacion_sri import (
    EMISOR,
    obtener_password_firma,
    firmar_xml,
    generar_comprobante_factura,
)

logger = logging.getLogger(__name__)

# =====================================================
# CONFIGURACIÓN DE ENDPOINTS Y NAMESPACES
# =====================================================

WSDL_RECEPCION = {
    "1": "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline",
    "2": "https://cel.sri.gob.ec/comprobanteselectronicos-ws/RecepcionComprobantesOffline",
}
WSDL_AUTORIZACION = {
    "1": "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline",
    "2": "https://cel.sri.gob.ec/comprobanteselectronicos-ws/AutorizacionComprobantesOffline",
}

NS_SOAP = "http://schemas.xmlsoap.org/soap/envelope/"
NS_WSSE = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"
NS_WSU = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd"
NS_DS = "http://www.w3.org/2000/09/xmldsig#"

# elementFormDefault="unqualified": los hijos de la operación van SIN namespace
NS_RECEPCION = "http://ec.gob.sri.ws.recepcion"
NS_AUTORIZACION = "http://ec.gob.sri.ws.autorizacion"

# Ruta por defecto de la firma digital (configurable en configuracion_sistema)
FIRMA_P12_DEFAULT = "/home/skorggamor/agente-contador/firmadigital.p12"


# =====================================================
# Excepciones del módulo
# =====================================================

class ErrorTransmisionSRI(Exception):
    """Error de RED/TLS al transmitir al SRI (no confundir con rechazo)."""


# =====================================================
# Helper: carga del .p12 (certificado + clave privada)
# =====================================================

def _cargar_p12(ruta_p12: str, password_p12: str) -> tuple:
    """
    Carga el .p12 del contribuyente y devuelve (key, cert, cert_der).

    Args:
        ruta_p12: ruta al archivo .p12.
        password_p12: contraseña del .p12 (resuelta por obtener_password_firma()).

    Raises:
        RuntimeError: si el .p12 no se puede leer o no contiene clave/certificado
                      válidos (indicación de password incorrecto).
        FileNotFoundError: si no existe el archivo.
    """
    from cryptography.hazmat.primitives.serialization import (
        pkcs12,
        Encoding,
    )

    if not ruta_p12 or not __import__("os").path.exists(ruta_p12):
        raise FileNotFoundError(
            f"Archivo de firma digital no encontrado: {ruta_p12}"
        )
    if not password_p12:
        raise RuntimeError(
            "No se pudo resolver la contraseña de la firma digital (.p12). "
            "Configúrala con FIRMA_P12_PASSWORD o ~/agente-contador/.firma_p12.pass"
        )

    with open(ruta_p12, "rb") as f:
        p12_data = f.read()
    key, cert, _extra = pkcs12.load_key_and_certificates(
        p12_data, password_p12.encode("utf-8")
    )
    if key is None or cert is None:
        raise RuntimeError(
            f"El .p12 {ruta_p12} no contiene una clave privada y certificado "
            "válidos (¿password incorrecto?)."
        )
    cert_der = cert.public_bytes(Encoding.DER)
    return key, cert, cert_der


# =====================================================
# Construcción del envelope SOAP firmado (WS-Security)
# =====================================================

def _construir_envelope(
    operacion: str,
    ns_operacion: str,
    cuerpo: list,
    key,
    cert,
    cert_der: bytes,
) -> bytes:
    """
    Construye el envelope SOAP 1.1 firmado con WS-Security X509.

    Args:
        operacion: nombre de la operación (p.ej. "validarComprobante").
        ns_operacion: namespace de la operación.
        cuerpo: lista de (tag, text) hijos de la operación (sin namespace,
                según elementFormDefault="unqualified").
        key/cert: clave privada y certificado del .p12.
        cert_der: certificado en DER.

    Returns:
        bytes del envelope SOAP completo (XML UTF-8, con declaración).
    """
    env = etree.Element(
        f"{{{NS_SOAP}}}Envelope",
        nsmap={
            "soapenv": NS_SOAP,
            "xsd": "http://www.w3.org/2001/XMLSchema",
            "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        },
    )
    header = etree.SubElement(env, f"{{{NS_SOAP}}}Header")
    security = etree.SubElement(
        header, f"{{{NS_WSSE}}}Security", nsmap={"wsse": NS_WSSE, "wsu": NS_WSU}
    )
    # NOTA (verificada contra el SRI real): NO se pone soapenv:mustUnderstand.
    # Rampart lo interpreta como "no entendido" y responde MustUnderstand fault.

    bst = etree.SubElement(security, f"{{{NS_WSSE}}}BinarySecurityToken")
    bst.set(f"{{{NS_WSU}}}Id", "X509Token")
    bst.set(
        "EncodingType",
        "http://docs.oasis-open.org/wss/2004/01/"
        "oasis-200401-wss-soap-message-security-1.0#Base64Binary",
    )
    bst.set(
        "ValueType",
        "http://docs.oasis-open.org/wss/2004/01/"
        "oasis-200401-wss-x509-token-profile-1.0#X509v3",
    )
    bst.text = base64.b64encode(cert_der).decode("ascii")

    # Placeholder de firma: signxml lo completa "in place" (sin mover nodos,
    # manteniendo consistente la canonicalización del body).
    sig_ph = etree.SubElement(security, f"{{{NS_DS}}}Signature", nsmap={"ds": NS_DS})
    sig_ph.set("Id", "placeholder")

    body = etree.SubElement(env, f"{{{NS_SOAP}}}Body")
    body.set(f"{{{NS_WSU}}}Id", "Body")
    oper = etree.SubElement(body, f"{{{ns_operacion}}}{operacion}")
    for tag, text in cuerpo:
        etree.SubElement(oper, tag).text = text

    # Firma enveloped del body (Reference URI="#Body")
    from signxml import XMLSigner, methods
    signer = XMLSigner(
        method=methods.enveloped,
        signature_algorithm="rsa-sha256",
        digest_algorithm="sha256",
    )
    signer.sign(env, key=key, cert=[cert], reference_uri="#Body")

    # Agregar SecurityTokenReference al certificado en KeyInfo (estándar WSSE)
    sig = env.find(f".//{{{NS_WSSE}}}Security/{{{NS_DS}}}Signature")
    keyinfo = sig.find(f"{{{NS_DS}}}KeyInfo")
    if keyinfo is not None:
        stri = etree.SubElement(keyinfo, f"{{{NS_WSSE}}}SecurityTokenReference")
        ref = etree.SubElement(
            stri, f"{{{NS_WSSE}}}Reference", nsmap={"wsse": NS_WSSE}
        )
        ref.set("URI", "#X509Token")
        ref.set(
            "ValueType",
            "http://docs.oasis-open.org/wss/2004/01/"
            "oasis-200401-wss-x509-token-profile-1.0#X509v3",
        )

    return etree.tostring(env, xml_declaration=True, encoding="UTF-8")


# =====================================================
# Parseo de respuestas
# =====================================================

def _localname(el) -> str:
    """Devuelve el nombre local de un elemento (sin prefijo/namespace)."""
    return etree.QName(el).localname if el is not None else ""


def _find_local(root, nombre: str):
    """Busca un elemento por nombre local en cualquier nivel (sin namespace)."""
    for el in root.iter():
        if _localname(el) == nombre:
            return el
    return None


def _findall_local(root, nombre: str) -> list:
    return [el for el in root.iter() if _localname(el) == nombre]


def _findtext_local(el, nombre: str) -> str:
    """Lee el texto de un hijo por nombre local."""
    for ch in el:
        if _localname(ch) == nombre:
            return (ch.text or "").strip()
    return ""


def _parsear_mensajes(container) -> list:
    """Extrae lista de mensajes [{identificador, mensaje, informacionAdicional, tipo}].

    El contenedor <mensajes> tiene hijos <mensaje> (cada uno con su propio
    sub-campo <mensaje> para el texto). Solo se procesan los HIJOS DIRECTOS del
    contenedor para no confundir el campo <mensaje> interno con un mensaje nuevo.
    """
    mensajes = []
    for m in container:
        if _localname(m) != "mensaje":
            continue
        mensajes.append({
            "identificador": _findtext_local(m, "identificador"),
            "mensaje": _findtext_local(m, "mensaje"),
            "informacionAdicional": _findtext_local(m, "informacionAdicional"),
            "tipo": _findtext_local(m, "tipo"),
        })
    return mensajes


def _es_clave_en_procesamiento(mensajes: list) -> bool:
    """True si el SRI indica [70] CLAVE DE ACCESO EN PROCESAMIENTO.

    El [70] no es un rechazo: el comprobante ya fue recibido efectivamente y
    está en la cola de autorización. Aparece al reenviar la misma clave o al
    consultar la autorización inmediatamente después de RECIBIDA.
    """
    return any(
        (m.get("identificador") or "").strip() == "70"
        and "PROCESAMIENTO" in (m.get("mensaje") or "").upper()
        for m in mensajes
    )


# =====================================================
# Recepción
# =====================================================

def transmitir_comprobante(
    xml_firmado: str,
    ambiente: str = "1",
    ruta_p12: Optional[str] = None,
    password_p12: Optional[str] = None,
    timeout: int = 30,
) -> dict:
    """
    Transmite (recepción) un comprobante firmado al SRI.

    Construye el SOAP de recepción firmado (WS-Security X509), lo POSTea al
    WSDL correspondiente y parsea la respuesta.

    Args:
        xml_firmado: XML firmado en XAdES-BES (string).
        ambiente: "1" = pruebas (default) | "2" = producción.
        ruta_p12: ruta al .p12 (default FIRMA_P12_DEFAULT).
        password_p12: contraseña del .p12 (default la resuelta automáticamente).
        timeout: timeout del POST en segundos.

    Returns:
        dict con {estado, mensajes[], clave_acceso, ambiente}.

    Raises:
        ErrorTransmisionSRI: si falla la red/TLS al llegar al SRI.
    """
    if ambiente not in ("1", "2"):
        raise ValueError("ambiente debe ser '1' (pruebas) o '2' (producción)")
    ruta = ruta_p12 or FIRMA_P12_DEFAULT
    pwd = password_p12 if password_p12 is not None else obtener_password_firma()

    key, cert, cert_der = _cargar_p12(ruta, pwd)
    b64_xml = base64.b64encode(xml_firmado.encode("utf-8")).decode("ascii")
    payload = _construir_envelope(
        "validarComprobante",
        NS_RECEPCION,
        [("xml", b64_xml)],
        key, cert, cert_der,
    )

    try:
        import httpx
        resp = httpx.post(
            WSDL_RECEPCION[ambiente],
            content=payload,
            headers={"Content-Type": "text/xml; charset=utf-8"},
            timeout=timeout,
        )
        resp.raise_for_status()
        resp_xml = resp.content
    except httpx.HTTPError as exc:
        raise ErrorTransmisionSRI(
            f"Error de red al transmitir al SRI (recepción, ambiente {ambiente}): "
            f"{type(exc).__name__}: {exc}. Verifica conectividad/TLS o la VPN."
        ) from exc

    return _parsear_recepcion(resp_xml, ambiente)


def _parsear_recepcion(resp_xml: bytes, ambiente: str) -> dict:
    """Parsea la respuesta SOAP de recepción (RECIBIDA / DEVUELTA)."""
    try:
        root = etree.fromstring(resp_xml)
    except etree.XMLSyntaxError as exc:
        raise ErrorTransmisionSRI(
            f"El SRI devolvió una respuesta que no es XML válido: {exc}"
        ) from exc

    fault = root.find(f".//{{{NS_SOAP}}}Fault/{{{NS_SOAP}}}faultstring")
    if fault is not None:
        raise ErrorTransmisionSRI(f"Fault del SRI (recepción): {fault.text}")

    respuesta = _find_local(root, "RespuestaRecepcionComprobante")
    if respuesta is None:
        raise ErrorTransmisionSRI(
            "El SRI no devolvió RespuestaRecepcionComprobante en la respuesta."
        )

    estado = _findtext_local(respuesta, "estado")
    mensajes = []
    clave = ""
    comprobantes = _find_local(respuesta, "comprobantes")
    if comprobantes is not None:
        comp = _find_local(comprobantes, "comprobante")
        if comp is not None:
            clave = _findtext_local(comp, "claveAcceso")
            mcont = _find_local(comp, "mensajes")
            if mcont is not None:
                mensajes = _parsear_mensajes(mcont)

    # [70] "CLAVE DE ACCESO EN PROCESAMIENTO" NO es un rechazo: significa que
    # el comprobante ya fue recibido y está en cola de autorización (pasa al
    # reenviar la misma clave o consultar justo después de RECIBIDA).
    # Normalizar a RECIBIDA para no marcar un envío válido como DEVUELTA.
    if estado != "RECIBIDA" and _es_clave_en_procesamiento(mensajes):
        logger.info(
            "Recepción SRI: [70] clave en procesamiento para %s; " "tratado como RECIBIDA.", clave
        )
        estado = "RECIBIDA"

    logger.info("Recepción SRI: estado=%s clave=%s", estado, clave)
    return {
        "estado": estado,
        "mensajes": mensajes,
        "clave_acceso": clave,
        "ambiente": ambiente,
    }


# =====================================================
# Autorización
# =====================================================

def consultar_autorizacion(
    clave_acceso: str,
    ambiente: str = "1",
    ruta_p12: Optional[str] = None,
    password_p12: Optional[str] = None,
    timeout: int = 30,
) -> dict:
    """
    Consulta la autorización de un comprobante por su clave de acceso.

    Args:
        clave_acceso: clave de acceso de 49 dígitos.
        ambiente: "1" = pruebas (default) | "2" = producción.

    Returns:
        dict con {estado, numero_autorizacion, fecha_autorizacion,
                  xml_autorizado, mensajes[], clave_acceso}.

    Raises:
        ErrorTransmisionSRI: si falla la red/TLS.
    """
    if ambiente not in ("1", "2"):
        raise ValueError("ambiente debe ser '1' (pruebas) o '2' (producción)")
    ruta = ruta_p12 or FIRMA_P12_DEFAULT
    pwd = password_p12 if password_p12 is not None else obtener_password_firma()

    key, cert, cert_der = _cargar_p12(ruta, pwd)
    payload = _construir_envelope(
        "autorizacionComprobante",
        NS_AUTORIZACION,
        # El WSDL de autorización espera <claveAccesoComprobante> (no <claveAcceso>).
        # Verificado en vivo: el SRI devuelve Fault "unexpected element ... claveAcceso.
        # Expected elements are <{}claveAccesoComprobante>" si se manda el nombre
        # incorrecto.
        [("claveAccesoComprobante", clave_acceso)],
        key, cert, cert_der,
    )

    try:
        import httpx
        resp = httpx.post(
            WSDL_AUTORIZACION[ambiente],
            content=payload,
            headers={"Content-Type": "text/xml; charset=utf-8"},
            timeout=timeout,
        )
        resp.raise_for_status()
        resp_xml = resp.content
    except httpx.HTTPError as exc:
        raise ErrorTransmisionSRI(
            f"Error de red al consultar autorización al SRI (ambiente {ambiente}): "
            f"{type(exc).__name__}: {exc}. Verifica conectividad/TLS o la VPN."
        ) from exc

    return _parsear_autorizacion(resp_xml, clave_acceso, ambiente)


def _parsear_autorizacion(resp_xml: bytes, clave_acceso: str, ambiente: str) -> dict:
    """Parsea la respuesta SOAP de autorización."""
    try:
        root = etree.fromstring(resp_xml)
    except etree.XMLSyntaxError as exc:
        raise ErrorTransmisionSRI(
            f"El SRI devolvió una respuesta que no es XML válido: {exc}"
        ) from exc

    fault = root.find(f".//{{{NS_SOAP}}}Fault/{{{NS_SOAP}}}faultstring")
    if fault is not None:
        raise ErrorTransmisionSRI(f"Fault del SRI (autorización): {fault.text}")

    auth = _find_local(root, "autorizacion")
    if auth is None:
        # El SRI devolvió la respuesta sin elementos <autorizacion> (p.ej.
        # <numeroComprobantes>0</numeroComprobantes> con <autorizaciones/>
        # vacío). Esto ocurre justo después de RECIBIDA, mientras el SRI
        # procesa el comprobante. NO es un error: se interpreta como pendiente
        # (EN PROCESO) para que la orquestación siga reintentando.
        logger.info(
            "Autorización SRI sin registro ('numeroComprobantes'=0 o vacío) "
            "para clave %s; tratado como EN PROCESO.", clave_acceso
        )
        return {
            "estado": "EN PROCESO",
            "numero_autorizacion": "",
            "fecha_autorizacion": "",
            "xml_autorizado": None,
            "mensajes": [],
            "clave_acceso": clave_acceso,
            "ambiente": ambiente,
        }

    estado = _findtext_local(auth, "estado")
    numero = _findtext_local(auth, "numeroAutorizacion")
    fecha = _findtext_local(auth, "fechaAutorizacion")
    comp_b64 = _findtext_local(auth, "comprobante")

    xml_autorizado = None
    if comp_b64:
        try:
            xml_autorizado = base64.b64decode(comp_b64).decode("utf-8")
        except Exception:
            xml_autorizado = None

    mensajes = []
    mcont = _find_local(auth, "mensajes")
    if mcont is not None:
        mensajes = _parsear_mensajes(mcont)

    # [70] "CLAVE DE ACCESO EN PROCESAMIENTO" en la consulta de autorización:
    # el SRI aún procesa el comprobante. NO es "devuelta"/"no autorizado":
    # normalizar a EN PROCESO para que la orquestación siga reintentando
    # (verificado en vivo 29/08/2026: la NC recién recibida devolvió [70]
    # en la consulta inmediata y quedaba marcada erróneamente como devuelta).
    if (estado or "").upper() not in ("AUTORIZADO", "NO AUTORIZADO") and _es_clave_en_procesamiento(mensajes):
        logger.info(
            "Autorización SRI: [70] clave en procesamiento para %s; "
            "tratado como EN PROCESO.", clave_acceso
        )
        estado = "EN PROCESO"

    logger.info("Autorización SRI: estado=%s numero=%s", estado, numero)
    return {
        "estado": estado,
        "numero_autorizacion": numero,
        "fecha_autorizacion": fecha,
        "xml_autorizado": xml_autorizado,
        "mensajes": mensajes,
        "clave_acceso": clave_acceso,
        "ambiente": ambiente,
    }


# =====================================================
# Orquestación: transmitir + autorizar
# =====================================================

def transmitir_y_autorizar(
    clave_acceso: str,
    xml_firmado: str,
    ambiente: str = "1",
    ruta_p12: Optional[str] = None,
    password_p12: Optional[str] = None,
    reintentos_autorizacion: int = 6,
    espera_seg: int = 3,
) -> dict:
    """
    Orquesta el flujo completo: recepción → autorización.

    1. Transmite el comprobante (recepción).
    2. Si RECIBIDA, consulta la autorización con reintentos cortos ante
       estado EN PROCESO.
    3. Devuelve el resultado completo.

    Returns:
        dict con {recepcion, autorizacion, estado_final} donde recepcion es el
        dict de transmitir_comprobante y autorizacion el de consultar_autorizacion
        (o None si no se llegó a autorizar).
    """
    import time

    recepcion = transmitir_comprobante(
        xml_firmado, ambiente, ruta_p12, password_p12
    )
    resultado = {
        "recepcion": recepcion,
        "autorizacion": None,
        "estado_final": recepcion["estado"],
    }

    if recepcion["estado"] != "RECIBIDA":
        logger.warning("Comprobante no recibido: estado=%s", recepcion["estado"])
        return resultado

    intento = 0
    while True:
        autorizacion = consultar_autorizacion(
            clave_acceso, ambiente, ruta_p12, password_p12
        )
        resultado["autorizacion"] = autorizacion
        resultado["estado_final"] = autorizacion["estado"]
        if autorizacion["estado"] in ("AUTORIZADO", "NO AUTORIZADO"):
            return resultado
        # EN PROCESO → reintentar con espera
        intento += 1
        if intento >= reintentos_autorizacion:
            logger.info("Autorización sigue EN PROCESO tras %d intentos", intento)
            return resultado
        time.sleep(espera_seg)
