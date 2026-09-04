"""
Notificaciones de autorización SRI — avisa a Daniel cuando una factura
se autoriza (o es devuelta) sin que tenga que estar pendiente.

Vías de notificación (independientes entre sí, todas opcionales):
1. LOCAL  → notify-send (notificación de escritorio del sistema local).
            Requiere DISPLAY + notify-send (entorno gráfico de Daniel).
2. TELEGRAM → enviar mensaje a un chat vía bot. Se activa si existen:
            TELEGRAM_BOT_TOKEN (token del bot) y
            TELEGRAM_CHAT_ID (chat/destino, ej. Daniel o grupo).
            Es la vía más confiable para no perderse el aviso.

Se integra con worker_autorizacion.py: al detectar un cambio de estado
(pendiente → autorizado/devuelto), llama a notificar_cambio_estado().
No bloquea ni derriba el worker si la notificación falla (try/except).
"""

import logging
import os
import shutil
import subprocess

logger = logging.getLogger("notificaciones")


def _notificar_local(titulo: str, mensaje: str) -> None:
    """Notificación de escritorio vía notify-send (best effort, no bloquea)."""
    try:
        notify = shutil.which("notify-send")
        if not notify or not os.environ.get("DISPLAY"):
            return  # sin entorno gráfico → silencioso
        subprocess.Popen(
            [notify, "-u", "normal", "-a", "Orpey", titulo, mensaje],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("[notify-send] %s", titulo)
    except Exception as exc:
        logger.debug("notify-send no disponible: %s", exc)


def _notificar_telegram(mensaje: str) -> None:
    """Envía mensaje a Telegram si hay bot configurado (best effort)."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return  # no configurado → silencioso
    try:
        import httpx
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        with httpx.Client(timeout=10) as client:
            resp = client.post(url, json={"chat_id": chat_id, "text": mensaje})
            if resp.status_code != 200:
                logger.warning("Telegram respondió %s: %s", resp.status_code, resp.text[:120])
        logger.info("[telegram] enviado a chat %s", chat_id)
    except Exception as exc:
        logger.warning("Fallo al notificar por Telegram: %s", exc)


def notificar_cambio_estado(numero_documento: str, estado: str, detalle: str = "") -> None:
    """Avisa del cambio de estado de una factura por todas las vías activas."""
    if estado == "autorizado":
        titulo = f"✅ Factura {numero_documento} AUTORIZADA"
        mensaje = f"Factura {numero_documento} autorizada por el SRI.\n{detalle}".strip()
    elif estado in ("devuelta", "no_autorizado"):
        titulo = f"⚠️ Factura {numero_documento} {estado.upper()}"
        mensaje = f"Factura {numero_documento} marcada como {estado}.\n{detalle}".strip()
    else:
        return  # solo avisamos cambios relevantes

    logger.info("NOTIFICACIÓN: %s", titulo)
    _notificar_local(titulo, mensaje)
    _notificar_telegram(mensaje)
