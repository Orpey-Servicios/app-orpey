"""
Servicio de WhatsApp - Genera links para enviar mensajes por WhatsApp.

No usa la API oficial de WhatsApp Business (que cuesta dinero).
En su lugar, usa el protocolo wa.me que abre WhatsApp Web/App con un mensaje prellenado.

El usuario solo tiene que adjuntar el PDF descargado y enviar.
"""


def generar_link_whatsapp(telefono: str, mensaje: str) -> str:
    """
    Genera un link de WhatsApp con mensaje prellenado.

    Args:
        telefono: Número de teléfono (ej: "0985983416")
        mensaje: Texto del mensaje

    Returns:
        URL de wa.me lista para abrir

    Ejemplo de uso:
        link = generar_link_whatsapp("0985983416", "Hola Gerardo, tu orden ORP-0001 está lista")
        # Resultado: https://wa.me/593985983416?text=Hola+Gerardo...
    """
    # Limpiar el teléfono: quitar espacios, guiones, paréntesis
    telefono_limpio = telefono.strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')

    # Agregar código de país Ecuador (593) si no lo tiene
    if telefono_limpio.startswith('0'):
        # Quitar el 0 inicial y agregar 593
        telefono_limpio = '593' + telefono_limpio[1:]
    elif not telefono_limpio.startswith('593'):
        telefono_limpio = '593' + telefono_limpio

    # Codificar el mensaje para URL (espacios se convierten en +)
    from urllib.parse import quote
    mensaje_codificado = quote(mensaje)

    return f"https://wa.me/{telefono_limpio}?text={mensaje_codificado}"


def generar_mensaje_orden(numero_orden: str, cliente_nombre: str, equipo: str, estado: str) -> str:
    """
    Genera un mensaje prellenado para enviar una orden de servicio.

    Args:
        numero_orden: Número de orden (ej: "ORP-0001")
        cliente_nombre: Nombre del cliente
        equipo: Descripción del equipo (ej: "HP Laptop 15DA")
        estado: Estado actual de la orden

    Returns:
        Texto del mensaje listo para enviar por WhatsApp
    """
    mensaje = (
        f"Hola {cliente_nombre}, te saludo de Orpey Servicios.\n"
        f"\n"
        f"📋 *Orden de Servicio N° {numero_orden}*\n"
        f"🖥️ Equipo: {equipo}\n"
        f"📌 Estado: {estado}\n"
        f"\n"
        f"Adjunto te envío la orden de servicio con los detalles.\n"
        f"Cualquier consulta estamos a tu disposición.\n"
        f"\n"
        f"_Orpey Servicios Técnicos_\n"
        f"_Guayaquil, Ecuador_"
    )

    return mensaje


def generar_mensaje_cotizacion(numero_cotizacion: str, cliente_nombre: str, total: str) -> str:
    """
    Genera un mensaje prellenado para enviar una cotización.
    """
    mensaje = (
        f"Hola {cliente_nombre}, te saludo de Orpey Servicios.\n"
        f"\n"
        f"💰 *Cotización N° {numero_cotizacion}*\n"
        f"💵 Total: ${total}\n"
        f"\n"
        f"Te envío la cotización para tu revisión.\n"
        f"Quedamos atentos a tu respuesta.\n"
        f"\n"
        f"_Orpey Servicios Técnicos_\n"
        f"_Guayaquil, Ecuador_"
    )

    return mensaje
