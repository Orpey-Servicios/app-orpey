"""
Servicio de Facturación Electrónica SRI (Ecuador) - Generación local.

Genera el XML de factura (comprobante 01) normativamente correcto según la
Ficha Técnica de Comprobantes Electrónicos y lo firma en XAdES-BES.

IMPORTANTE (envio al SRI):
- Este módulo SOLO GENERA el XML firmado localmente. NO transmite NADA al SRI
  (no SOAP, no HTTP externo). El ambiente por defecto es "1" (pruebas).
- La transmisión (recepción/autorización) es una fase futura.

Emisor (constante del negocio - RÉGIMEN GENERAL):
- RUC: 0964794234001
- Razón social: BALTODANO Catarine Daniel ABRAHAM
- Régimen: GENERAL (verificado en vivo con el SRI 28/08/2026)
- obligadoContabilidad "NO"
- Dirección: Guayaquil, Bastion Popular, Bloque 2, Solar 7
- Establecimiento 001 / Punto de emisión 001
- En Régimen General NO hay leyenda RIMPE en las facturas y el tope de
  consumidor final es $50 IVA incluido (no $200).

Seguridad de la firma digital (.p12):
- La RUTA puede venir de `configuracion_sistema` (clave `firma_p12_ruta`).
- La CONTRASEÑA NUNCA en código versionado. Resolución jerárquica:
    1. Variable de entorno `FIRMA_P12_PASSWORD`.
    2. Archivo protegido (perms 600): `$FIRMA_P12_PASSWORD_FILE` o
       `/home/skorggamor/agente-contador/.firma_p12.pass`
- Configuración para Daniel:
    export FIRMA_P12_PASSWORD='<password>'          # por sesión, o
    echo '<password>' > ~/agente-contador/.firma_p12.pass && chmod 600 ~/agente-contador/.firma_p12.pass
"""

import os
import secrets
import hashlib
import base64
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from lxml import etree
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography import x509

from src.models.models import FacturaElectronica
from src.utils.fechas import ahora_ecuador, ahora_ecuador_naive, ECUADOR_TZ


# =====================================================
# DATOS DEL EMISOR (RÉGIMEN GENERAL)
# =====================================================

EMISOR = {
    "ruc": "0964794234001",
    "razon_social": "BALTODANO Catarine Daniel ABRAHAM",
    "dir_matriz": "Guayaquil, Bastion Popular, Bloque 2, Solar 7",
    "establecimiento": "001",
    "punto_emision": "001",
    "obligado_contabilidad": "NO",
    "regimen": "Régimen General",
    # Límite de facturación a consumidor final (Régimen General = $50 IVA incluido,
    # Decreto 586 / Reglamento de comprobantes art. 19, Reglamento LRTI art. 4)
    "limite_consumidor_final": Decimal("50.00"),
}

# Tope de facturación a consumidor final sin identificación del comprador
# (Régimen General = $50 IVA incluido, no $200 como RIMPE Negocios Populares).
LIMITE_CONSUMIDOR_FINAL = Decimal("50.00")

TIPO_FACTURA = "01"          # Factura
TIPO_NOTA_CREDITO = "04"     # Nota de crédito (anulación)
TIPO_EMISION = "1"           # 1 = normal
MONEDA = "DOLAR"
COD_IMP_IVA = "2"            # Código de impuesto: IVA
# códigoPorcentaje del IVA 15% vigente (Catálogo SRI Tabla 17): 0=0%, 2=12% (histórico), 4=15% vigente
COD_PORC_IVA_15 = "4"        # códigoPorcentaje: IVA 15% vigente
TARIFA_IVA_15 = "15"
# Identificador estándar usado por el SRI para consumidor final sin cédula
IDENTIFICACION_CONSUMIDOR_FINAL = "9999999999999"

# DECISIÓN DE SIGNO DE LA NOTA DE CRÉDITO (revisar con el contador):
# El documento normativo /tmp/opencode/nota-credito-sri.md aún no existe, por lo
# que aplicamos el criterio estándar del SRI: los montos de la NC (totalSinImpuestos,
# valorModificacion, baseImponible, valor, precios del detalle) se expresan en
# POSITIVO, VERIFICADO EN VIVO (29/08/2026, ambiente de certificación):
# el XSD/SRI rechaza NC con montos negativos:
#   cvc-minInclusive-valid: Value '-47.83' is not facet-valid with respect
#   to minInclusive '0.0' for type 'totalSinImpuestos'
# El SRI interpreta el comprobante como NC por su tipo (04), sin negativos.
# Los montos PERSISTIDOS y los del XML son magnitudes positivas.
SIGNO_NOTA_CREDITO = Decimal("1")


def _nc_importe(valor: Decimal) -> str:
    """Formatea un monto de la NC con el signo del XML aplicado (ver SIGNO_NOTA_CREDITO)."""
    return _fmt(SIGNO_NOTA_CREDITO * valor)


def _fmt_fecha(valor) -> str:
    """Formatea datetime/date a DD/MM/AAAA para el XML del SRI."""
    return valor.strftime("%d/%m/%Y")


def _round2(valor: Decimal) -> Decimal:
    """Redondea a 2 decimales con ROUND_HALF_UP (regla del SRI)."""
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _fmt(valor: Decimal) -> str:
    """Formatea Decimal a cadena con 2 decimales para el XML (ej: '21.74')."""
    return f"{_round2(valor):.2f}"


# =====================================================
# 1. CLAVE DE ACCESO (Módulo 11)
# =====================================================

def generar_clave_acceso(
    fecha: datetime,
    tipo_comprobante: str,
    ruc: str,
    ambiente: str,
    establecimiento: str,
    punto_emision: str,
    secuencial: str,
    codigo_numerico: str,
) -> str:
    """
    Genera la clave de acceso de 49 dígitos del SRI.

    Estructura (48 dígitos base + 1 dígito verificador):
      fecha (DDMMAAAA) + tipo (2) + ruc (13) + ambiente (1)
      + estab (3) + punto (3) + secuencial (9) + código numérico (8) + tipoEmisión (1)

    Dígito verificador (Módulo 11):
      Se toma la cadena base INVERTIDA y se multiplica cada dígito por la serie
      periódica 2,3,4,5,6,7. Suma total, residuo = total % 11, verificador = 11 - residuo.
      Excepciones: si da 11 -> 0; si da 10 -> 1.
    """
    fecha_str = fecha.strftime("%d%m%Y")

    if len(tipo_comprobante) != 2:
        raise ValueError("tipo_comprobante debe tener 2 dígitos")
    if len(ruc) != 13:
        raise ValueError("ruc debe tener 13 dígitos")
    if ambiente not in ("1", "2"):
        raise ValueError("ambiente debe ser '1' (pruebas) o '2' (producción)")
    if len(establecimiento) != 3:
        raise ValueError("establecimiento debe tener 3 dígitos")
    if len(punto_emision) != 3:
        raise ValueError("punto_emision debe tener 3 dígitos")
    if len(secuencial) != 9:
        raise ValueError("secuencial debe tener 9 dígitos")
    if len(codigo_numerico) != 8:
        raise ValueError("codigo_numerico debe tener 8 dígitos")

    base = (
        fecha_str
        + tipo_comprobante
        + ruc
        + ambiente
        + establecimiento
        + punto_emision
        + secuencial
        + codigo_numerico
        + TIPO_EMISION
    )

    if len(base) != 48:
        raise ValueError("La base de la clave de acceso debe tener 48 dígitos")

    # Módulo 11 sobre la cadena invertida
    factores = [2, 3, 4, 5, 6, 7]
    total = sum(int(char) * factores[i % 6] for i, char in enumerate(reversed(base)))
    digito = 11 - (total % 11)
    if digito == 11:
        digito = 0
    elif digito == 10:
        digito = 1

    return base + str(digito)


def generar_codigo_numerico() -> str:
    """Código numérico aleatorio de 8 dígitos (entropía de la clave)."""
    return f"{secrets.randbelow(100_000_000):08d}"


# =====================================================
# 2. CONSTRUCCIÓN DEL XML (estructura normativa)
# =====================================================

def _sub(parent: etree._Element, tag: str, text: str = "") -> etree._Element:
    el = etree.SubElement(parent, tag)
    el.text = text
    return el


def _crear_info_tributaria(
    emisor: dict,
    clave_acceso: str,
    secuencial: str,
    ambiente: str,
    cod_doc: str = TIPO_FACTURA,
) -> etree._Element:
    node = etree.Element("infoTributaria")
    _sub(node, "ambiente", ambiente)
    _sub(node, "tipoEmision", TIPO_EMISION)
    _sub(node, "razonSocial", emisor["razon_social"])
    _sub(node, "ruc", emisor["ruc"])
    _sub(node, "claveAcceso", clave_acceso)
    _sub(node, "codDoc", cod_doc)
    _sub(node, "estab", emisor["establecimiento"])
    _sub(node, "ptoEmi", emisor["punto_emision"])
    _sub(node, "secuencial", secuencial)
    _sub(node, "dirMatriz", emisor["dir_matriz"])
    return node


# El XSD/SRI exige direccionComprador con minLength 1 (rechaza vacía:
# cvc-minLength-valid ... for type 'direccionComprador', verificado en vivo
# 29/08/2026 con un cliente sin dirección). Si el comprador no tiene
# dirección registrada, se usa este placeholder legible.
DIRECCION_COMPRADOR_FALLBACK = "SIN DIRECCIÓN REGISTRADA"


def _crear_info_factura(
    fecha_emision: datetime,
    emisor: dict,
    cliente: dict,
    tipo_id: str,
    identificacion: str,
    subtotal: Decimal,
    iva: Decimal,
    total: Decimal,
) -> etree._Element:
    node = etree.Element("infoFactura")
    _sub(node, "fechaEmision", fecha_emision.strftime("%d/%m/%Y"))
    _sub(node, "dirEstablecimiento", emisor["dir_matriz"])
    _sub(node, "obligadoContabilidad", emisor["obligado_contabilidad"])
    _sub(node, "tipoIdentificacionComprador", tipo_id)
    _sub(node, "razonSocialComprador", cliente.get("nombre_completo", ""))
    _sub(node, "identificacionComprador", identificacion)
    _sub(node, "direccionComprador", cliente.get("direccion", "") or DIRECCION_COMPRADOR_FALLBACK)
    _sub(node, "totalSinImpuestos", _fmt(subtotal))
    _sub(node, "totalDescuento", "0.00")

    # totalConImpuestos -> totalImpuesto (IVA 15%)
    total_imp = _sub(node, "totalConImpuestos")
    ti = etree.SubElement(total_imp, "totalImpuesto")
    _sub(ti, "codigo", COD_IMP_IVA)
    _sub(ti, "codigoPorcentaje", COD_PORC_IVA_15)
    _sub(ti, "baseImponible", _fmt(subtotal))
    _sub(ti, "valor", _fmt(iva))

    _sub(node, "propina", "0.00")
    _sub(node, "importeTotal", _fmt(total))
    _sub(node, "moneda", MONEDA)

    # Forma de pago: 01 = sin utilización del sistema financiero (efectivo)
    pagos = _sub(node, "pagos")
    pago = etree.SubElement(pagos, "pago")
    _sub(pago, "formaPago", "01")
    _sub(pago, "total", _fmt(total))
    return node


def _crear_detalle(descripcion: str, subtotal: Decimal, iva: Decimal) -> etree._Element:
    detalle = etree.Element("detalle")
    # Un solo item "SERVICIO TÉCNICO" para el primer release (ver docstring del módulo)
    _sub(detalle, "codigoPrincipal", "001")
    _sub(detalle, "codigoAuxiliar", "001")
    _sub(detalle, "descripcion", descripcion.upper())
    _sub(detalle, "cantidad", "1")
    _sub(detalle, "precioUnitario", _fmt(subtotal))
    _sub(detalle, "descuento", "0.00")
    _sub(detalle, "precioTotalSinImpuesto", _fmt(subtotal))

    impuestos = _sub(detalle, "impuestos")
    impuesto = etree.SubElement(impuestos, "impuesto")
    _sub(impuesto, "codigo", COD_IMP_IVA)
    _sub(impuesto, "codigoPorcentaje", COD_PORC_IVA_15)
    _sub(impuesto, "tarifa", TARIFA_IVA_15)
    _sub(impuesto, "baseImponible", _fmt(subtotal))
    _sub(impuesto, "valor", _fmt(iva))
    return detalle


# =====================================================
# NOTA DE CRÉDITO (comprobante 04 — anulación de facturas)
# =====================================================

def _crear_info_nota_credito(
    fecha_emision: datetime,
    emisor: dict,
    cliente: dict,
    tipo_id: str,
    identificacion: str,
    factura_original: dict,
    subtotal: Decimal,
    iva: Decimal,
    valor_modificacion: Decimal,
    motivo: str,
) -> etree._Element:
    """Construye <infoNotaCredito> anulando la factura original.

    - codDocModificado="01": el sustento modificado es una factura.
    - numDocModificado = número de documento de la factura original
      (formato "001-001-000000001" exigido por el XSD/SRI; la clave de
      acceso completa es rechazada con cvc-pattern-valid).
    - Los montos (totalSinImpuestos, valorModificacion, totalConImpuestos)
      van POSITIVOS: el XSD/SRI exige minInclusive 0.0 (ver SIGNO_NOTA_CREDITO).
    """
    node = etree.Element("infoNotaCredito")
    _sub(node, "fechaEmision", _fmt_fecha(fecha_emision))
    _sub(node, "dirEstablecimiento", emisor["dir_matriz"])
    _sub(node, "tipoIdentificacionComprador", tipo_id)
    _sub(node, "razonSocialComprador", cliente.get("nombre_completo", ""))
    _sub(node, "identificacionComprador", identificacion)
    _sub(node, "obligadoContabilidad", emisor["obligado_contabilidad"])
    _sub(node, "codDocModificado", TIPO_FACTURA)
    _sub(node, "numDocModificado", factura_original["numero_documento"])
    _sub(node, "fechaEmisionDocSustento", _fmt_fecha(factura_original["fecha_emision"]))
    _sub(node, "totalSinImpuestos", _nc_importe(subtotal))
    _sub(node, "valorModificacion", _nc_importe(valor_modificacion))
    _sub(node, "moneda", MONEDA)

    total_imp = _sub(node, "totalConImpuestos")
    ti = etree.SubElement(total_imp, "totalImpuesto")
    _sub(ti, "codigo", COD_IMP_IVA)
    _sub(ti, "codigoPorcentaje", COD_PORC_IVA_15)
    _sub(ti, "baseImponible", _nc_importe(subtotal))
    _sub(ti, "valor", _nc_importe(iva))

    _sub(node, "motivo", motivo)
    return node


def _crear_detalle_nota_credito(descripcion: str, subtotal: Decimal, iva: Decimal) -> etree._Element:
    """Un solo detalle genérico que refleja el monto anulado (montos positivos).

    NOTA (decisión de diseño): el SRI acepta el detalle con un ítem descriptivo
    ("Anulación de factura 001-001-XXXX") en lugar de replicar los ítems
    originales, siempre que totalSinImpuestos/valorModificacion cuadren con la
    factura. El contador documenta el formato oficial en /tmp/opencode/nota-credito-sri.md.
    """
    detalle = etree.Element("detalle")
    _sub(detalle, "codigoInterno", "001")
    _sub(detalle, "codigoAdicional", "001")
    _sub(detalle, "descripcion", descripcion.upper())
    _sub(detalle, "cantidad", "1")
    _sub(detalle, "precioUnitario", _nc_importe(subtotal))
    _sub(detalle, "descuento", "0.00")
    _sub(detalle, "precioTotalSinImpuesto", _nc_importe(subtotal))

    impuestos = _sub(detalle, "impuestos")
    impuesto = etree.SubElement(impuestos, "impuesto")
    _sub(impuesto, "codigo", COD_IMP_IVA)
    _sub(impuesto, "codigoPorcentaje", COD_PORC_IVA_15)
    _sub(impuesto, "tarifa", TARIFA_IVA_15)
    _sub(impuesto, "baseImponible", _nc_importe(subtotal))
    _sub(impuesto, "valor", _nc_importe(iva))
    return detalle


def _crear_info_adicional(emisor: dict, cliente: Optional[dict] = None) -> etree._Element:
    """Metadatos libres: dirección del comprador (NC) o del emisor (factura).

    NOTA (Régimen General): la leyenda "Contribuyente Régimen RIMPE" NO aplica
    (era obligatoria solo para RIMPE). En Régimen General no hay leyenda de
    régimen obligatoria; se conserva la dirección como campo adicional.
    """
    node = etree.Element("infoAdicional")
    cam_dir = etree.SubElement(node, "campoAdicional")
    cam_dir.set("nombre", "Dirección")
    dir_cliente = (cliente or {}).get("direccion") if cliente else None
    cam_dir.text = (dir_cliente or "").strip() or emisor["dir_matriz"]
    return node


def _detectar_tipo_identificacion(cliente: dict) -> tuple[str, str]:
    """Devuelve (tipoIdentificacionComprador, identificacionComprador)."""
    ident = (cliente.get("cedula_ruc") or "").strip()
    if len(ident) == 10:
        return "05", ident          # Cédula
    if len(ident) == 13:
        return "04", ident          # RUC
    if len(ident) == 9:
        return "06", ident          # Pasaporte
    # Sin identificación -> consumidor final (placeholder estándar SRI)
    return "07", IDENTIFICACION_CONSUMIDOR_FINAL


# =====================================================
# 3. GENERACIÓN DEL COMPROBANTE
# =====================================================

def generar_comprobante_factura(
    orden: dict,
    cliente: dict,
    config: dict,
    secuencial: str,
    ambiente: str = "1",
) -> dict:
    """
    Construye el XML completo de factura electrónica.

    Args:
        orden: dict con id, numero_orden, total_orden y equipos (lista de dicts).
        cliente: dict con nombre/apellido/nombre_completo, cedula_ruc, direccion.
        config: dict con iva_porcentaje (entero/Decimal) y emisor (ruc, razon_social,
                dir_matriz, establecimiento, punto_emision, obligado_contabilidad).
        secuencial: 9 dígitos (2026000001).
        ambiente: "1" pruebas (default) o "2" producción.

    Returns:
        dict con clave_acceso, numero_documento, fecha_emision, ambiente,
        subtotal, iva, total, tipo_identificacion, identificacion, xml y errores.

    Raises:
        ValueError: si el comprobante viola reglas de negocio del SRI.
    """
    if ambiente not in ("1", "2"):
        raise ValueError("ambiente debe ser '1' (pruebas) o '2' (producción)")

    emisor = {**EMISOR, **config.get("emisor", {})}

    # --- Cálculos (Decimal, ROUND_HALF_UP a 2 decimales) ---
    iva_porcentaje = Decimal(str(config.get("iva_porcentaje", "15")))
    total = _round2(Decimal(str(orden["total_orden"])))
    subtotal = _round2(total / (1 + iva_porcentaje / Decimal("100")))
    iva = _round2(total - subtotal)
    # Reajuste defensivo: total >= subtotal + iva siempre debe cuadrar
    if total != subtotal + iva:
        iva = _round2(total - subtotal)

    # --- Validaciones de negocio ---
    errores: list[str] = []
    tipo_id, identificacion = _detectar_tipo_identificacion(cliente)
    # Régimen General: tope de consumidor final $50 IVA incluido.
    limite_cf = Decimal(str(emisor.get("limite_consumidor_final", LIMITE_CONSUMIDOR_FINAL)))

    if tipo_id == "07" and total > limite_cf:
        raise ValueError(
            f"Consumidor final sin identificación y total ${total:.2f} supera el "
            f"límite de ${limite_cf:.2f} (Régimen General). "
            "Se requiere RUC, cédula o pasaporte del comprador."
        )

    if tipo_id != "07" and total >= limite_cf and not identificacion:
        errores.append(f"Identificación del comprador incompleta para total >= ${limite_cf:.2f}")

    # --- Clave de acceso (hora Ecuador UTC-5 naive) ---
    fecha_emision = ahora_ecuador_naive()
    codigo_numerico = generar_codigo_numerico()
    clave_acceso = generar_clave_acceso(
        fecha=fecha_emision,
        tipo_comprobante=TIPO_FACTURA,
        ruc=emisor["ruc"],
        ambiente=ambiente,
        establecimiento=emisor["establecimiento"],
        punto_emision=emisor["punto_emision"],
        secuencial=secuencial,
        codigo_numerico=codigo_numerico,
    )
    numero_documento = (
        f"{emisor['establecimiento']}-{emisor['punto_emision']}-{secuencial}"
    )

    # --- Descripción del item (decisión de diseño documentada) ---
    descripcion = _descripcion_item(orden)

    # --- Árbol XML ---
    root = etree.Element("factura")
    root.set("id", "comprobante")
    root.set("version", "1.1.0")
    root.append(_crear_info_tributaria(emisor, clave_acceso, secuencial, ambiente))
    root.append(_crear_info_factura(
        fecha_emision, emisor, cliente, tipo_id, identificacion,
        subtotal, iva, total,
    ))
    detalles = etree.SubElement(root, "detalles")
    detalles.append(_crear_detalle(descripcion, subtotal, iva))
    root.append(_crear_info_adicional(emisor))

    xml_string = etree.tostring(root, encoding="unicode")

    return {
        "clave_acceso": clave_acceso,
        "numero_documento": numero_documento,
        "fecha_emision": fecha_emision,
        "ambiente": ambiente,
        "subtotal": subtotal,
        "iva": iva,
        "total": total,
        "tipo_identificacion": tipo_id,
        "identificacion": identificacion,
        "xml": xml_string,
        "errores": errores,
    }


def _descripcion_item(orden: dict) -> str:
    """
    Descripción del item de la factura.

    DECISIÓN DE DISEÑO (primer release): un SOLO item genérico
    "SERVICIO TÉCNICO - <descripción>" en lugar del detalle por equipo.
    Motivos: (a) la orden factura un total único; (b) evita desglosar precios
    por equipo cuando total_orden es del taller y suma = total (riesgo de que
    la suma de equipos no cuadre con el total); (c) más simple y seguro de
    validar contra XSD. Fase futura: desglose por equipo con precio_venta.
    """
    equipos = orden.get("equipos") or []
    if equipos:
        eq = equipos[0]
        partes = []
        tipo = eq.get("tipo_equipo") or ""
        if hasattr(tipo, "value"):
            tipo = tipo.value
        for campo in ("tipo_equipo", "marca", "modelo", "descripcion_problema"):
            valor = eq.get(campo)
            if valor and str(valor).strip():
                partes.append(str(valor).replace("\n", " ").strip())
        desc = " - ".join(partes) if partes else "Servicio técnico"
    else:
        desc = f"Servicio técnico {orden.get('numero_orden', '')}".strip()
    return f"SERVICIO TÉCNICO - {desc}"


def generar_comprobante_nota_credito(
    factura_original: dict,
    cliente: dict,
    config: dict,
    secuencial: str,
    motivo: str,
    monto_anular: Decimal,
    ambiente: str = "1",
    fecha_emision: Optional[datetime] = None,
) -> dict:
    """
    Construye el XML completo de NOTA DE CRÉDITO electrónica (comprobante 04).

    Anula (total o parcialmente) una factura del MISMO emisor:
    - codDoc="04"; codDocModificado="01"; numDocModificado = clave de acceso
      de la factura original; fechaEmisionDocSustento = fecha de la factura.
    - SECUENCIAL INDEPENDIENTE de las facturas (llamar con
      siguiente_secuencial_nota_credito) — la serie de NC no comparte
      numeración con la de facturas.

    Args:
        factura_original: dict con clave_acceso, numero_documento, fecha_emision
                          (datetime/date) y total de la factura que se anula.
        cliente: dict con nombre/apellido/nombre_completo, cedula_ruc, direccion.
        config: dict con iva_porcentaje y emisor (mismo formato que la factura).
        secuencial: 9 dígitos independiente de las facturas (000000001...).
        motivo: texto de la anulación (va en <motivo>).
        monto_anular: monto TOTAL a anular (IVA incluido). Default del caller:
                      total de la factura (anulación total).
        ambiente: "1" pruebas (default) o "2" producción.
        fecha_emision: fecha de emisión de la NC (default: ahora). Debe ser
                       >= fecha de emisión de la factura (valida el caller).

    Returns:
        dict con clave_acceso, numero_documento, fecha_emision, ambiente,
        subtotal, iva, total (MAGNITUDES POSITIVAS), tipo_identificacion,
        identificacion, xml y errores.

    Raises:
        ValueError: si el comprobante viola reglas de negocio del SRI.
    """
    if ambiente not in ("1", "2"):
        raise ValueError("ambiente debe ser '1' (pruebas) o '2' (producción)")

    emisor = {**EMISOR, **config.get("emisor", {})}
    iva_porcentaje = Decimal(str(config.get("iva_porcentaje", "15")))

    # Recalculamos subtotal/IVA a partir del monto total anulado (regla SRI)
    monto_anular = _round2(monto_anular)
    subtotal_nc = _round2(monto_anular / (1 + iva_porcentaje / Decimal("100")))
    iva_nc = _round2(monto_anular - subtotal_nc)
    if subtotal_nc <= 0:
        raise ValueError(f"El monto a anular (${monto_anular:.2f}) no produce un subtotal válido")

    tipo_id, identificacion = _detectar_tipo_identificacion(cliente)

    fecha_emision = fecha_emision or ahora_ecuador_naive()
    codigo_numerico = generar_codigo_numerico()
    clave_acceso = generar_clave_acceso(
        fecha=fecha_emision,
        tipo_comprobante=TIPO_NOTA_CREDITO,
        ruc=emisor["ruc"],
        ambiente=ambiente,
        establecimiento=emisor["establecimiento"],
        punto_emision=emisor["punto_emision"],
        secuencial=secuencial,
        codigo_numerico=codigo_numerico,
    )
    numero_documento = (
        f"{emisor['establecimiento']}-{emisor['punto_emision']}-{secuencial}"
    )

    descripcion = f"Anulación de factura {factura_original['numero_documento']}"

    root = etree.Element("notaCredito")
    root.set("id", "comprobante")
    root.set("version", "1.1.0")
    root.append(_crear_info_tributaria(
        emisor, clave_acceso, secuencial, ambiente,
        cod_doc=TIPO_NOTA_CREDITO,
    ))
    root.append(_crear_info_nota_credito(
        fecha_emision, emisor, cliente, tipo_id, identificacion,
        factura_original, subtotal_nc, iva_nc, subtotal_nc, motivo,
    ))
    detalles = etree.SubElement(root, "detalles")
    detalles.append(_crear_detalle_nota_credito(descripcion, subtotal_nc, iva_nc))
    root.append(_crear_info_adicional(emisor, cliente))

    xml_string = etree.tostring(root, encoding="unicode")

    return {
        "clave_acceso": clave_acceso,
        "numero_documento": numero_documento,
        "fecha_emision": fecha_emision,
        "ambiente": ambiente,
        "subtotal": subtotal_nc,
        "iva": iva_nc,
        "total": monto_anular,
        "tipo_identificacion": tipo_id,
        "identificacion": identificacion,
        "xml": xml_string,
        "errores": [],
    }


# =====================================================
# 4. FIRMA XAdES-BES
# =====================================================

def obtener_password_firma(ruta_p12: Optional[str] = None) -> Optional[str]:
    """
    Resuelve la contraseña del .p12 SIN hardcodearla:
      1. Archivo protegido junto al .p12 (ej. /app/firma/.firma_p12.pass)
      2. Archivo en FIRMA_P12_PASSWORD_FILE o rutas conocidas
      3. Variable de entorno FIRMA_P12_PASSWORD
    """
    # 1. Probar archivo .pass junto al .p12
    if ruta_p12:
        sibling_pass = os.path.join(os.path.dirname(ruta_p12), ".firma_p12.pass")
        if os.path.exists(sibling_pass):
            try:
                with open(sibling_pass, "r", encoding="utf-8") as f:
                    val = f.read().strip()
                if val:
                    return val
            except OSError:
                pass

    # 2. Rutas conocidas de archivo .pass
    candidatos_pass = [
        os.environ.get("FIRMA_P12_PASSWORD_FILE"),
        "/app/firma/.firma_p12.pass",
        "/home/skorggamor/agente-contador/.firma_p12.pass",
    ]
    for c in candidatos_pass:
        if c and os.path.exists(c):
            try:
                with open(c, "r", encoding="utf-8") as f:
                    val = f.read().strip()
                if val:
                    return val
            except OSError:
                pass

    # 3. Variable de entorno
    pwd = os.environ.get("FIRMA_P12_PASSWORD")
    if pwd:
        return pwd

    return None



NS_DS = "http://www.w3.org/2000/09/xmldsig#"
NS_ETSI = "http://uri.etsi.org/01903/v1.3.2#"
NSMAP_XADES = {"ds": NS_DS, "etsi": NS_ETSI}


def _wrap_b64(b64_str: str, line_len: int = 76) -> str:
    """Envuelve base64 con saltos de línea cada 76 caracteres (formato PEM / XML-DSig)."""
    return "\n" + "\n".join(b64_str[i : i + line_len] for i in range(0, len(b64_str), line_len)) + "\n"


def firmar_xml(xml_string: str, ruta_p12: str, password_p12: str) -> str:
    """
    Firma un comprobante XML en formato XAdES-BES estricto según la Ficha Técnica del SRI Ecuador.

    Estructura implementada:
      - Canonicalización: Canonical XML 1.0 (http://www.w3.org/TR/2001/REC-xml-c14n-20010315)
      - Algoritmo de firma: RSA-SHA1 (http://www.w3.org/2000/09/xmldsig#rsa-sha1)
      - Algoritmo de digest: SHA-1 (http://www.w3.org/2000/09/xmldsig#sha1)
      - Tres referencias en SignedInfo:
          1. #Signature-SignedProperties: Digest de etsi:SignedProperties (Tipo: http://uri.etsi.org/01903#SignedProperties)
          2. #Certificate: Digest de ds:KeyInfo
          3. #comprobante: Digest del documento XML raíz con transformación enveloped-signature
      - ds:KeyInfo contiene ds:X509Data (X509Certificate) y ds:KeyValue/ds:RSAKeyValue (Modulus y Exponent)
      - ds:Object con etsi:QualifyingProperties que alberga etsi:SignedProperties:
          * SigningTime con offset fijo de Ecuador (-05:00)
          * SigningCertificate con CertDigest (SHA-1) e IssuerSerial (X509IssuerName, X509SerialNumber)
          * SignedDataObjectProperties con DataObjectFormat para #comprobante
    """
    if not os.path.exists(ruta_p12):
        raise FileNotFoundError(f"Archivo de firma digital no encontrado: {ruta_p12}")
    if not password_p12:
        raise RuntimeError(
            "No se pudo resolver la contraseña de la firma digital (.p12). "
            "Configúrala con la variable de entorno FIRMA_P12_PASSWORD o en "
            "~/agente-contador/.firma_p12.pass (perms 600)."
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

    root = etree.fromstring(xml_string.encode("utf-8"))
    if not root.get("id"):
        root.set("id", "comprobante")

    # 1. Digest del documento raíz (#comprobante, enveloped-signature)
    doc_c14n = etree.tostring(root, method="c14n", exclusive=False, with_comments=False)
    doc_digest = base64.b64encode(hashlib.sha1(doc_c14n).digest()).decode("ascii")

    # Generación de identificadores pseudoaleatorios únicos
    r_sig = secrets.randbelow(900000) + 100000
    r_sinfo = secrets.randbelow(900000) + 100000
    r_sp = secrets.randbelow(900000) + 100000
    r_sp_ref = secrets.randbelow(900000) + 100000
    r_cert = secrets.randbelow(900000) + 100000
    r_doc_ref = secrets.randbelow(900000) + 100000
    r_sval = secrets.randbelow(900000) + 100000
    r_obj = secrets.randbelow(900000) + 100000

    sig_id = f"Signature{r_sig}"
    signed_info_id = f"Signature-SignedInfo{r_sinfo}"
    signed_props_id = f"{sig_id}-SignedProperties{r_sp}"
    signed_props_ref_id = f"SignedPropertiesID{r_sp_ref}"
    key_info_id = f"Certificate{r_cert}"
    doc_ref_id = f"Reference-ID-{r_doc_ref}"
    sig_val_id = f"SignatureValue{r_sval}"
    object_id = f"{sig_id}-Object{r_obj}"

    # Datos del certificado y clave pública
    cert_der = cert.public_bytes(Encoding.DER)
    cert_b64 = base64.b64encode(cert_der).decode("ascii")
    cert_digest = base64.b64encode(hashlib.sha1(cert_der).digest()).decode("ascii")
    issuer_name = cert.issuer.rfc4514_string()
    serial_number = str(cert.serial_number)

    pn = cert.public_key().public_numbers()
    mod_bytes = pn.n.to_bytes((pn.n.bit_length() + 7) // 8, "big")
    exp_bytes = pn.e.to_bytes((pn.e.bit_length() + 7) // 8, "big")
    mod_b64 = base64.b64encode(mod_bytes).decode("ascii")
    exp_b64 = base64.b64encode(exp_bytes).decode("ascii")

    # Hora de firma en Ecuador con offset UTC-5 obligatorio
    signing_time = ahora_ecuador().strftime("%Y-%m-%dT%H:%M:%S-05:00")

    # Construir nodo <ds:Signature>
    sig = etree.Element(f"{{{NS_DS}}}Signature", nsmap=NSMAP_XADES, Id=sig_id)

    # 2. Construir <ds:KeyInfo> dentro de sig para herencia correcta de namespaces
    key_info = etree.SubElement(sig, f"{{{NS_DS}}}KeyInfo", Id=key_info_id)
    x509_data = etree.SubElement(key_info, f"{{{NS_DS}}}X509Data")
    x509_cert = etree.SubElement(x509_data, f"{{{NS_DS}}}X509Certificate")
    x509_cert.text = _wrap_b64(cert_b64)
    key_val = etree.SubElement(key_info, f"{{{NS_DS}}}KeyValue")
    rsa_key_val = etree.SubElement(key_val, f"{{{NS_DS}}}RSAKeyValue")
    mod_el = etree.SubElement(rsa_key_val, f"{{{NS_DS}}}Modulus")
    mod_el.text = _wrap_b64(mod_b64)
    exp_el = etree.SubElement(rsa_key_val, f"{{{NS_DS}}}Exponent")
    exp_el.text = exp_b64

    # 3. Construir <ds:Object> con <etsi:QualifyingProperties> y <etsi:SignedProperties>
    obj = etree.SubElement(sig, f"{{{NS_DS}}}Object", Id=object_id)
    qual_props = etree.SubElement(obj, f"{{{NS_ETSI}}}QualifyingProperties", Target=f"#{sig_id}")
    signed_props = etree.SubElement(qual_props, f"{{{NS_ETSI}}}SignedProperties", Id=signed_props_id)
    s_sig_props = etree.SubElement(signed_props, f"{{{NS_ETSI}}}SignedSignatureProperties")
    s_time = etree.SubElement(s_sig_props, f"{{{NS_ETSI}}}SigningTime")
    s_time.text = signing_time

    s_cert = etree.SubElement(s_sig_props, f"{{{NS_ETSI}}}SigningCertificate")
    cert_el = etree.SubElement(s_cert, f"{{{NS_ETSI}}}Cert")
    c_digest = etree.SubElement(cert_el, f"{{{NS_ETSI}}}CertDigest")
    etree.SubElement(c_digest, f"{{{NS_DS}}}DigestMethod", Algorithm="http://www.w3.org/2000/09/xmldsig#sha1")
    d_val = etree.SubElement(c_digest, f"{{{NS_DS}}}DigestValue")
    d_val.text = cert_digest

    iss_ser = etree.SubElement(cert_el, f"{{{NS_ETSI}}}IssuerSerial")
    iss_name = etree.SubElement(iss_ser, f"{{{NS_DS}}}X509IssuerName")
    iss_name.text = issuer_name
    iss_num = etree.SubElement(iss_ser, f"{{{NS_DS}}}X509SerialNumber")
    iss_num.text = serial_number

    s_do_props = etree.SubElement(signed_props, f"{{{NS_ETSI}}}SignedDataObjectProperties")
    do_fmt = etree.SubElement(s_do_props, f"{{{NS_ETSI}}}DataObjectFormat", ObjectReference=f"#{doc_ref_id}")
    desc = etree.SubElement(do_fmt, f"{{{NS_ETSI}}}Description")
    desc.text = "contenido comprobante"
    m_type = etree.SubElement(do_fmt, f"{{{NS_ETSI}}}MimeType")
    m_type.text = "text/xml"

    # Calcular digests c14n mientras los elementos están dentro de sig
    key_info_c14n = etree.tostring(key_info, method="c14n", exclusive=False, with_comments=False)
    key_info_digest = base64.b64encode(hashlib.sha1(key_info_c14n).digest()).decode("ascii")

    sp_c14n = etree.tostring(signed_props, method="c14n", exclusive=False, with_comments=False)
    sp_digest = base64.b64encode(hashlib.sha1(sp_c14n).digest()).decode("ascii")

    # 4. Construir <ds:SignedInfo> con las 3 referencias
    signed_info = etree.Element(f"{{{NS_DS}}}SignedInfo", Id=signed_info_id)
    etree.SubElement(signed_info, f"{{{NS_DS}}}CanonicalizationMethod", Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
    etree.SubElement(signed_info, f"{{{NS_DS}}}SignatureMethod", Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1")

    # Ref 1: SignedProperties
    ref1 = etree.SubElement(
        signed_info, f"{{{NS_DS}}}Reference",
        Id=signed_props_ref_id,
        Type="http://uri.etsi.org/01903#SignedProperties",
        URI=f"#{signed_props_id}",
    )
    etree.SubElement(ref1, f"{{{NS_DS}}}DigestMethod", Algorithm="http://www.w3.org/2000/09/xmldsig#sha1")
    ref1_val = etree.SubElement(ref1, f"{{{NS_DS}}}DigestValue")
    ref1_val.text = sp_digest

    # Ref 2: Certificate (KeyInfo)
    ref2 = etree.SubElement(signed_info, f"{{{NS_DS}}}Reference", URI=f"#{key_info_id}")
    etree.SubElement(ref2, f"{{{NS_DS}}}DigestMethod", Algorithm="http://www.w3.org/2000/09/xmldsig#sha1")
    ref2_val = etree.SubElement(ref2, f"{{{NS_DS}}}DigestValue")
    ref2_val.text = key_info_digest

    # Ref 3: Documento raíz (#comprobante)
    ref3 = etree.SubElement(signed_info, f"{{{NS_DS}}}Reference", Id=doc_ref_id, URI="#comprobante")
    transforms = etree.SubElement(ref3, f"{{{NS_DS}}}Transforms")
    etree.SubElement(transforms, f"{{{NS_DS}}}Transform", Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature")
    etree.SubElement(ref3, f"{{{NS_DS}}}DigestMethod", Algorithm="http://www.w3.org/2000/09/xmldsig#sha1")
    ref3_val = etree.SubElement(ref3, f"{{{NS_DS}}}DigestValue")
    ref3_val.text = doc_digest

    # Insertar SignedInfo al inicio de Signature
    sig.insert(0, signed_info)

    # 5. Firmar SignedInfo con RSA-SHA1
    sinfo_c14n = etree.tostring(signed_info, method="c14n", exclusive=False, with_comments=False)
    sig_bytes = key.sign(sinfo_c14n, padding.PKCS1v15(), hashes.SHA1())
    sig_b64 = base64.b64encode(sig_bytes).decode("ascii")

    # Insertar SignatureValue entre SignedInfo y KeyInfo
    sig_val_el = etree.Element(f"{{{NS_DS}}}SignatureValue", Id=sig_val_id)
    sig_val_el.text = _wrap_b64(sig_b64)
    sig.insert(1, sig_val_el)

    root.append(sig)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8").decode("utf-8")


def validar_firma_xml(xml_firmado: str) -> bool:
    """
    Verifica matemáticamente de forma offline que la firma XAdES-BES sea válida:
      1. Coincidencia del SHA-1 del certificado DER con CertDigest.
      2. Coincidencia del digest c14n de KeyInfo.
      3. Coincidencia del digest c14n de SignedProperties.
      4. Coincidencia del digest c14n del documento envolvente (#comprobante).
      5. Verificación criptográfica RSA-SHA1 de SignatureValue sobre SignedInfo c14n.

    Retorna True si todo es válido; lanza excepción si algo falla.
    """
    root = etree.fromstring(xml_firmado.encode("utf-8"))
    ns = {"ds": NS_DS, "etsi": NS_ETSI}
    sig = root.find("ds:Signature", ns)
    if sig is None:
        raise ValueError("El XML no contiene nodo ds:Signature")

    sinfo = sig.find("ds:SignedInfo", ns)
    keyinfo = sig.find("ds:KeyInfo", ns)
    sprops = sig.find(".//etsi:SignedProperties", ns)
    cert_node = sig.find(".//ds:X509Certificate", ns)
    if any(x is None for x in (sinfo, keyinfo, sprops, cert_node)):
        raise ValueError("El nodo Signature carece de elementos XAdES-BES obligatorios")

    cert_der = base64.b64decode("".join(cert_node.text.split()))
    cert_obj = x509.load_der_x509_certificate(cert_der)

    # 1. Cert SHA-1
    c_sha1 = hashlib.sha1(cert_der).digest()
    exp_c_sha1 = base64.b64decode(sig.find(".//etsi:CertDigest/ds:DigestValue", ns).text)
    if c_sha1 != exp_c_sha1:
        raise ValueError("El CertDigest no coincide con el certificado X509")

    # 2. KeyInfo digest
    ki_c14n = etree.tostring(keyinfo, method="c14n", exclusive=False, with_comments=False)
    ki_sha1 = hashlib.sha1(ki_c14n).digest()
    exp_ki_sha1 = base64.b64decode(sinfo.findall("ds:Reference", ns)[1].find("ds:DigestValue", ns).text)
    if ki_sha1 != exp_ki_sha1:
        raise ValueError("El digest de KeyInfo no coincide")

    # 3. SignedProperties digest
    sp_c14n = etree.tostring(sprops, method="c14n", exclusive=False, with_comments=False)
    sp_sha1 = hashlib.sha1(sp_c14n).digest()
    exp_sp_sha1 = base64.b64decode(sinfo.findall("ds:Reference", ns)[0].find("ds:DigestValue", ns).text)
    if sp_sha1 != exp_sp_sha1:
        raise ValueError("El digest de SignedProperties no coincide")

    # 4. Doc digest (remover Signature del documento envolvente)
    doc_copy = etree.fromstring(xml_firmado.encode("utf-8"))
    sig_in_copy = doc_copy.find("ds:Signature", ns)
    if sig_in_copy is not None:
        doc_copy.remove(sig_in_copy)
    doc_c14n = etree.tostring(doc_copy, method="c14n", exclusive=False, with_comments=False)
    doc_sha1 = hashlib.sha1(doc_c14n).digest()
    exp_doc_sha1 = base64.b64decode(sinfo.findall("ds:Reference", ns)[2].find("ds:DigestValue", ns).text)
    if doc_sha1 != exp_doc_sha1:
        raise ValueError("El digest del documento XML no coincide con el calculado")

    # 5. Firma RSA-SHA1
    sinfo_c14n = etree.tostring(sinfo, method="c14n", exclusive=False, with_comments=False)
    sig_val = base64.b64decode("".join(sig.find("ds:SignatureValue", ns).text.split()))
    pub = cert_obj.public_key()
    pub.verify(sig_val, sinfo_c14n, padding.PKCS1v15(), hashes.SHA1())
    return True


def obtener_info_certificado(ruta_p12: str, password_p12: str) -> dict:
    """
    Inspecciona un archivo .p12 y extrae metadatos de vigencia y emisor
    sin revelar la contraseña ni la clave privada.
    """
    if not os.path.exists(ruta_p12):
        raise FileNotFoundError(f"Archivo .p12 no encontrado: {ruta_p12}")
    if not password_p12:
        raise ValueError("Contraseña de firma no provista")

    with open(ruta_p12, "rb") as f:
        p12_data = f.read()

    key, cert, _extra = pkcs12.load_key_and_certificates(
        p12_data, password_p12.encode("utf-8")
    )
    if cert is None:
        raise ValueError("El archivo .p12 no contiene un certificado válido")

    now_utc = datetime.now(timezone.utc)
    valido_hasta = cert.not_valid_after_utc
    valido_desde = cert.not_valid_before_utc
    dias_restantes = (valido_hasta - now_utc).days
    activo = valido_hasta > now_utc

    # Extraer titular legible y RUC
    subject_str = cert.subject.rfc4514_string()
    issuer_str = cert.issuer.rfc4514_string()

    # Intentar parsear CN y RUC
    cn = ""
    ruc = ""
    for rdn in cert.subject.rdns:
        for attr in rdn:
            if attr.oid._name == "commonName":
                cn = attr.value
            # OID 2.5.4.97 = organizationIdentifier o 2.5.4.5 = serialNumber (RUC en ANFAC)
            if attr.oid.dotted_string in ("2.5.4.97", "2.5.4.5", "1.3.6.1.4.1.37442.10.4"):
                if len(str(attr.value)) == 13 and not ruc:
                    ruc = str(attr.value)

    return {
        "activo": activo,
        "dias_restantes": dias_restantes,
        "valido_desde": valido_desde.isoformat(),
        "valido_hasta": valido_hasta.isoformat(),
        "titular": cn or subject_str,
        "emisor": issuer_str,
        "serial": str(cert.serial_number),
        "ruc": ruc or "0964794234001",
        "ruta": ruta_p12,
    }


# =====================================================
# 5. SERIALIZACIÓN DE RESPUESTA
# =====================================================

def serializar_respuesta(comprobante: dict, estado: str = "generado",
                         xml_firmado: Optional[str] = None) -> dict:
    """Normaliza la respuesta de un comprobante (estado + datos + errores)."""
    errores = comprobante.get("errores") or []
    return {
        "estado": "error" if errores else estado,
        "clave_acceso": comprobante["clave_acceso"],
        "numero_documento": comprobante["numero_documento"],
        "ambiente": comprobante["ambiente"],
        "fecha_emision": comprobante["fecha_emision"],
        "subtotal": comprobante["subtotal"],
        "iva": comprobante["iva"],
        "total": comprobante["total"],
        "tipo_identificacion": comprobante.get("tipo_identificacion"),
        "identificacion": comprobante.get("identificacion"),
        "xml_firmado": xml_firmado or comprobante.get("xml"),
        "errores": errores,
    }


async def siguiente_secuencial(db, ambiente: str = "1") -> str:
    """
    Calcula el siguiente secuencial (9 dígitos) de FACTURAS mirando las
    facturas ya generadas (mismo establecimiento/punto de emisión 001-001).
    Usa el máximo secuencial existente + 1 para evitar duplicación ante borrados.
    """
    from sqlalchemy import or_, select

    result = await db.execute(
        select(FacturaElectronica.numero_documento).where(
            FacturaElectronica.ambiente == ambiente,
            or_(
                FacturaElectronica.tipo_comprobante != TIPO_NOTA_CREDITO,
                FacturaElectronica.tipo_comprobante.is_(None),
            ),
        )
    )
    docs = result.scalars().all()
    max_sec = 0
    for doc in docs:
        try:
            sec = int(doc.split("-")[-1])
            if sec > max_sec:
                max_sec = sec
        except (ValueError, IndexError):
            pass
    return f"{max_sec + 1:09d}"


async def siguiente_secuencial_nota_credito(db, ambiente: str = "1") -> str:
    """
    Calcula el siguiente secuencial (9 dígitos) de NOTAS DE CRÉDITO.
    Serial independiente de las facturas (SRI).
    Usa el máximo secuencial existente + 1.
    """
    from sqlalchemy import select

    result = await db.execute(
        select(FacturaElectronica.numero_documento).where(
            FacturaElectronica.ambiente == ambiente,
            FacturaElectronica.tipo_comprobante == TIPO_NOTA_CREDITO,
        )
    )
    docs = result.scalars().all()
    max_sec = 0
    for doc in docs:
        try:
            sec = int(doc.split("-")[-1])
            if sec > max_sec:
                max_sec = sec
        except (ValueError, IndexError):
            pass
    return f"{max_sec + 1:09d}"