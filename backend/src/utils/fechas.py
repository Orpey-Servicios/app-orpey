"""
Utilidades de manejo de fechas y zona horaria para Ecuador (UTC-5).

Centraliza el manejo de zona horaria del sistema para evitar desfases con el SRI:
- Ecuador no tiene horario de verano (DST), por lo que el offset fijo es siempre UTC-5.
- PostgreSQL en asyncpg usa TIMESTAMP WITHOUT TIME ZONE (naive), por lo que
  las fechas para BD deben ser naive en hora local de Ecuador.
- El SRI devuelve fechas con offset ISO 8601 (ej. 2026-09-08T14:55:46-05:00) o UTC ("Z").
"""

from datetime import datetime, timezone, timedelta
from typing import Optional

# Offset fijo de Ecuador: UTC-5 sin horario de verano
ECUADOR_TZ = timezone(timedelta(hours=-5))


def ahora_ecuador() -> datetime:
    """Retorna la fecha y hora actual con zona horaria de Ecuador (UTC-5 aware)."""
    return datetime.now(ECUADOR_TZ)


def ahora_ecuador_naive() -> datetime:
    """
    Retorna la fecha y hora actual en Ecuador como datetime naive (sin tzinfo).
    Apropiado para columnas DateTime / TIMESTAMP WITHOUT TIME ZONE de PostgreSQL.
    """
    return datetime.now(ECUADOR_TZ).replace(tzinfo=None)


def parsear_fecha_sri(fecha_str: Optional[str]) -> Optional[datetime]:
    """
    Parsea una fecha/hora emitida o devuelta por el SRI (formato ISO 8601,
    con offset tipo '-05:00' o sufijo 'Z'), la convierte a hora de Ecuador
    y la retorna como naive para persistir en PostgreSQL sin errores de tipo.
    """
    if not fecha_str or not str(fecha_str).strip():
        return None
    try:
        texto = str(fecha_str).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(texto)
        if dt.tzinfo is not None:
            dt = dt.astimezone(ECUADOR_TZ).replace(tzinfo=None)
        return dt
    except (ValueError, TypeError):
        return None


def formatear_fecha_sri(dt: Optional[datetime]) -> str:
    """Formatea fecha a DD/MM/AAAA para el XML de comprobantes del SRI."""
    if not dt:
        return ""
    return dt.strftime("%d/%m/%Y")
