"""
Servicio para validación y consulta de Cédulas y RUCs en SRI Ecuador.

Valida el dígito verificador usando Módulo 10 y Módulo 11 según normativa
del Registro Civil y SRI del Ecuador, y consulta el catastro público en tiempo real.
"""

import re
import logging
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger("orpey.sri_consulta")

SRI_BASE_URL = "https://srienlinea.sri.gob.ec/sri-catastro-sujeto-servicio-internet/rest"
SRI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-EC,es;q=0.9,en;q=0.8",
    "Referer": "https://srienlinea.sri.gob.ec/"
}


def validar_identificacion_ecuador(identificacion: str) -> Dict[str, Any]:
    """
    Valida si una cédula (10 dígitos) o RUC (13 dígitos) es estructuralmente
    válido en Ecuador utilizando los algoritmos oficiales (Módulo 10 y Módulo 11).
    """
    limpio = re.sub(r"\D", "", identificacion or "")
    
    if len(limpio) not in (10, 13):
        return {
            "valido": False,
            "tipo": "INVALIDO",
            "mensaje": "La identificación debe tener 10 dígitos (Cédula) o 13 dígitos (RUC)."
        }

    provincia = int(limpio[:2])
    if not (1 <= provincia <= 24 or provincia == 30):
        return {
            "valido": False,
            "tipo": "INVALIDO",
            "mensaje": f"Código de provincia '{limpio[:2]}' inválido en Ecuador (debe ser 01-24 o 30)."
        }

    tercer_digito = int(limpio[2])

    # ─────────────────────────────────────────────────────────────
    # CASO 1: Cédula de Identidad (10 dígitos)
    # ─────────────────────────────────────────────────────────────
    if len(limpio) == 10:
        if tercer_digito >= 6:
            return {
                "valido": False,
                "tipo": "INVALIDO",
                "mensaje": "El tercer dígito de una cédula debe ser menor a 6."
            }
        
        # Módulo 10
        coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
        suma = 0
        for i in range(9):
            val = int(limpio[i]) * coeficientes[i]
            if val >= 10:
                val -= 9
            suma += val
        
        digito_verificador = (10 - (suma % 10)) % 10
        if digito_verificador != int(limpio[9]):
            return {
                "valido": False,
                "tipo": "INVALIDO",
                "mensaje": "Dígito verificador de cédula no coincide (número inválido)."
            }

        return {
            "valido": True,
            "tipo": "CEDULA",
            "mensaje": "Cédula de identidad válida."
        }

    # ─────────────────────────────────────────────────────────────
    # CASO 2: RUC (13 dígitos)
    # ─────────────────────────────────────────────────────────────
    # Los últimos dígitos representan el establecimiento (no deben ser todos cero)
    if limpio[-3:] == "000":
        return {
            "valido": False,
            "tipo": "INVALIDO",
            "mensaje": "El código de establecimiento de un RUC no puede ser 000."
        }

    # Subcaso 2.1: RUC Persona Natural (tercer dígito < 6)
    if tercer_digito < 6:
        # Los primeros 10 dígitos deben ser una cédula válida
        resultado_cedula = validar_identificacion_ecuador(limpio[:10])
        if not resultado_cedula["valido"]:
            return {
                "valido": False,
                "tipo": "INVALIDO",
                "mensaje": "Los primeros 10 dígitos del RUC de persona natural no forman una cédula válida."
            }
        return {
            "valido": True,
            "tipo": "RUC_NATURAL",
            "mensaje": "RUC de persona natural válido."
        }

    # Subcaso 2.2: RUC Sociedad Privada o Extranjeros sin cédula (tercer dígito == 9)
    if tercer_digito == 9:
        coeficientes = [4, 3, 2, 7, 6, 5, 4, 3, 2]
        suma = sum(int(limpio[i]) * coeficientes[i] for i in range(9))
        residuo = suma % 11
        digito_verificador = 0 if residuo == 0 else (11 - residuo)
        
        if digito_verificador == 10:
            return {
                "valido": False,
                "tipo": "INVALIDO",
                "mensaje": "RUC de sociedad privada inválido."
            }

        if digito_verificador != int(limpio[9]):
            return {
                "valido": False,
                "tipo": "INVALIDO",
                "mensaje": "Dígito verificador de RUC privado no coincide."
            }

        return {
            "valido": True,
            "tipo": "RUC_SOCIEDAD",
            "mensaje": "RUC de sociedad privada válido."
        }

    # Subcaso 2.3: RUC Entidad Pública (tercer dígito == 6)
    if tercer_digito == 6:
        if limpio[-4:] == "0000":
            return {
                "valido": False,
                "tipo": "INVALIDO",
                "mensaje": "El código de establecimiento público no puede ser 0000."
            }
        coeficientes = [3, 2, 7, 6, 5, 4, 3, 2]
        suma = sum(int(limpio[i]) * coeficientes[i] for i in range(8))
        residuo = suma % 11
        digito_verificador = 0 if residuo == 0 else (11 - residuo)
        
        if digito_verificador != int(limpio[8]):
            return {
                "valido": False,
                "tipo": "INVALIDO",
                "mensaje": "Dígito verificador de RUC público no coincide."
            }

        return {
            "valido": True,
            "tipo": "RUC_PUBLICO",
            "mensaje": "RUC de entidad pública válido."
        }

    return {
        "valido": False,
        "tipo": "INVALIDO",
        "mensaje": f"Tercer dígito '{tercer_digito}' no corresponde a una estructura de RUC válida."
    }


def separar_nombres_apellidos(razon_social: str, tipo_contribuyente: str = "PERSONA NATURAL") -> Dict[str, str]:
    """
    Desglosa la Razón Social devuelta por el SRI en 'nombre' y 'apellido'.
    En el SRI/Registro Civil para personas naturales el orden es:
    APELLIDO_PATERNO APELLIDO_MATERNO PRIMER_NOMBRE SEGUNDO_NOMBRE...
    """
    if not razon_social:
        return {"nombre": "", "apellido": ""}

    partes = [p.strip() for p in razon_social.split() if p.strip()]
    if not partes:
        return {"nombre": "", "apellido": ""}

    es_sociedad = "SOCIEDAD" in tipo_contribuyente.upper() or "PUBLICA" in tipo_contribuyente.upper()
    if es_sociedad or len(partes) == 1:
        if len(partes) == 1:
            return {"nombre": partes[0].title(), "apellido": "(Sociedad)"}
        mitad = max(1, len(partes) // 2)
        return {
            "nombre": " ".join(partes[:mitad]).title(),
            "apellido": " ".join(partes[mitad:]).title()
        }

    # Caso Persona Natural
    if len(partes) == 2:
        return {
            "apellido": partes[0].title(),
            "nombre": partes[1].title()
        }
    elif len(partes) == 3:
        return {
            "apellido": f"{partes[0].title()} {partes[1].title()}",
            "nombre": partes[2].title()
        }
    else:
        return {
            "apellido": f"{partes[0].title()} {partes[1].title()}",
            "nombre": " ".join(p.title() for p in partes[2:])
        }


async def consultar_sri(identificacion: str) -> Dict[str, Any]:
    """
    Consulta en tiempo real al catastro público del SRI.
    Acepta tanto Cédula (10 dígitos) como RUC (13 dígitos).
    Devuelve los datos del cliente normalizados listos para registro.
    """
    limpio = re.sub(r"\D", "", identificacion or "")
    validacion = validar_identificacion_ecuador(limpio)

    if not validacion["valido"]:
        return {
            "encontrado": False,
            "valido": False,
            "identificacion": limpio,
            "mensaje": validacion["mensaje"]
        }

    # Si es cédula de 10 dígitos, en el SRI se consulta con el sufijo 001
    ruc_a_consultar = f"{limpio}001" if len(limpio) == 10 else limpio

    url_contribuyente = f"{SRI_BASE_URL}/ConsolidadoContribuyente/obtenerPorNumerosRuc?&ruc={ruc_a_consultar}"
    url_establecimiento = f"{SRI_BASE_URL}/Establecimiento/consultarPorNumeroRuc?numeroRuc={ruc_a_consultar}"

    datos_contribuyente = None
    datos_establecimiento = None

    try:
        async with httpx.AsyncClient(headers=SRI_HEADERS, timeout=6.0, verify=True) as client:
            resp_contribuyente = await client.get(url_contribuyente)
            if resp_contribuyente.status_code == 200:
                body = resp_contribuyente.json()
                if isinstance(body, list) and len(body) > 0:
                    datos_contribuyente = body[0]
            
            # Consultar establecimientos para obtener dirección
            if datos_contribuyente:
                try:
                    resp_est = await client.get(url_establecimiento)
                    if resp_est.status_code == 200:
                        body_est = resp_est.json()
                        if isinstance(body_est, list) and len(body_est) > 0:
                            # Preferir matriz o el primer establecimiento abierto
                            matriz = next((e for e in body_est if e.get("matriz") == "SI"), body_est[0])
                            datos_establecimiento = matriz
                except Exception as e:
                    logger.warning(f"No se pudo consultar establecimiento en SRI para {ruc_a_consultar}: {e}")

    except httpx.TimeoutException:
        logger.error(f"Timeout al consultar SRI para {ruc_a_consultar}")
        return {
            "encontrado": False,
            "valido": True,
            "identificacion": limpio,
            "mensaje": "El servicio del SRI no respondió a tiempo. Puedes ingresar los datos manualmente."
        }
    except Exception as e:
        logger.error(f"Error consultando SRI para {ruc_a_consultar}: {e}")
        return {
            "encontrado": False,
            "valido": True,
            "identificacion": limpio,
            "mensaje": f"No se pudo conectar con el SRI: {str(e)}"
        }

    if not datos_contribuyente:
        tipo_id = "cédula" if len(limpio) == 10 else "RUC"
        return {
            "encontrado": False,
            "valido": True,
            "identificacion": limpio,
            "mensaje": f"La {tipo_id} es válida pero no registra actividades en el catastro del SRI. Complete los datos manualmente."
        }

    # Procesar y normalizar la información obtenida
    razon_social = (datos_contribuyente.get("razonSocial") or "").strip()
    tipo_contribuyente = (datos_contribuyente.get("tipoContribuyente") or "PERSONA NATURAL").strip()
    estado = (datos_contribuyente.get("estadoContribuyenteRuc") or "ACTIVO").strip()
    regimen = datos_contribuyente.get("regimen")
    obligado_contabilidad = datos_contribuyente.get("obligadoLlevarContabilidad") or "NO"

    es_sociedad = "SOCIEDAD" in tipo_contribuyente.upper() or "PUBLICA" in tipo_contribuyente.upper()
    tipo_persona = "juridica" if es_sociedad else "natural"

    nombres_desglosados = separar_nombres_apellidos(razon_social, tipo_contribuyente)

    direccion = ""
    nombre_comercial = None
    if datos_establecimiento:
        direccion = (datos_establecimiento.get("direccionCompleta") or "").strip()
        # Normalizar barras separadoras preservando 'S/N' (Sin Número)
        dir_temp = re.sub(r"(?i)\bS\s*/\s*N\b", "__SN__", direccion)
        dir_temp = re.sub(r"\s*/\s*", ", ", dir_temp)
        direccion = dir_temp.replace("__SN__", "S/N")
        nombre_comercial = datos_establecimiento.get("nombreFantasiaComercial")

    return {
        "encontrado": True,
        "valido": True,
        "identificacion": limpio,
        "ruc_consultado": ruc_a_consultar,
        "razon_social": razon_social,
        "nombre": nombres_desglosados["nombre"],
        "apellido": nombres_desglosados["apellido"],
        "nombre_comercial": nombre_comercial,
        "direccion": direccion,
        "tipo_persona": tipo_persona,
        "tipo_contribuyente": tipo_contribuyente,
        "estado": estado,
        "regimen": regimen,
        "obligado_contabilidad": obligado_contabilidad,
        "actividad_economica": datos_contribuyente.get("actividadEconomicaPrincipal"),
        "mensaje": f"Contribuyente encontrado: {razon_social}"
    }
