"""
Utilidades de autenticación - JWT y hashing de contraseñas.

Implementa autenticación simple con JWT (JSON Web Tokens).
Los tokens tienen una duración de 24 horas.

Flujo:
1. Usuario envía username + password
2. Backend verifica en la BD
3. Si es correcto, devuelve un JWT token
4. El frontend guarda el token y lo envía en cada request
"""

import os

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Depends, HTTPException, Header

from src.config.database import get_db
from src.models.models import Usuario, RolUsuario

# =====================================================
# POLÍTICA DE CONTRASEÑAS
# =====================================================
# bcrypt tiene un límite de 72 bytes por password. Si se supera, passlib
# lanza un error interno no controlado. Definimos límites claros para dar
# mensajes de error amigables en vez de "Error interno del servidor".
PASSWORD_MIN_LENGTH = 6
# 72 es el límite duro de bcrypt; por seguridad usamos 64 (cubrimos bytes UTF-8
# de contraseñas con acentos sin llegar nunca al límite en bytes).
PASSWORD_MAX_LENGTH = 64


def validar_password(password: str) -> None:
    """
    Valida una contraseña según la política del sistema.

    Lanza HTTPException(400) con un mensaje claro al usuario si no cumple.
    No devuelve nada si la contraseña es válida.

    Activación: se llama desde los endpoints que crean/cambian/validan
    contraseñas ANTES de hashearla.
    """
    if not password or not password.strip():
        raise HTTPException(
            status_code=400,
            detail="La contraseña no puede estar vacía."
        )
    if len(password) < PASSWORD_MIN_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"La contraseña debe tener al menos {PASSWORD_MIN_LENGTH} caracteres."
        )
    # Los caracteres UTF-8 (ñ, acentos, emojis) ocupan más de 1 byte.
    # Evaluamos por bytes para respetar el límite real de bcrypt (72 bytes).
    if len(password.encode("utf-8")) > PASSWORD_MAX_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=(
                f"La contraseña no puede superar {PASSWORD_MAX_LENGTH} bytes "
                "(caracteres especiales, acentos y emojis ocupan más de 1 byte)."
            )
        )


# =====================================================
# CONFIGURACIÓN
# =====================================================

# Clave secreta para firmar los tokens.
# PRIMERO lee de la variable de entorno JWT_SECRET_KEY (producción / deploy).
# Si no está definida, usa un fallback local para desarrollo.
# NUNCA commitear el valor de producción.
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "orpey-servicios-dev-secret-key-cambiar")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 horas

# Contexto para hashing de contraseñas (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hashea una contraseña usando bcrypt.
    El hash es irreversible: no se puede obtener la contraseña original.

    Maneja de forma segura el límite interno de bcrypt (72 bytes): si no se le
    puede aplicar la política de validación (ej. llamadas internas), trunca por
    bytes para jamás lanzar un "Error interno del servidor".
    """
    # En los endpoints se llama primero a validar_password(). Este guard actúa
    # como última red de seguridad para llamadas programáticas.
    try:
        validar_password(password)
    except HTTPException:
        # Truncar por bytes a 72 como pas bcrypt para no romper el proceso.
        b = password.encode("utf-8")[:72]
        password = b.decode("utf-8", errors="ignore")
    return pwd_context.hash(password)


def verificar_password(password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña coincide con su hash.
    Se usa cuando el usuario intenta loguearse.

    Si la contraseña ingresada supera el límite de bcrypt, en vez de lanzar un
    "Error interno del servidor" devuelve False (login falla de forma limpia,
    como si la contraseña fuera incorrecta — comportamiento seguro y esperado).
    """
    # Red de seguridad: si llega algo que no es str, rechaza sin romper.
    if not isinstance(password, str) or not isinstance(hashed_password, str):
        return False
    try:
        return pwd_context.verify(password, hashed_password)
    except (ValueError, TypeError):
        # bcrypt lanza ValueError cuando la password supera 72 bytes.
        # Tratamos el exceso como credencial inválida, no como error de servidor.
        return False


def crear_token_acceso(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crea un JWT token con los datos proporcionados.

    Args:
        data: Datos a incluir en el token (ej: {"sub": "admin"})
        expires_delta: Duración del token (default: 24 horas)

    Returns:
        String con el token JWT

    Ejemplo:
        token = crear_token_acceso({"sub": "admin", "rol": "admin"})
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decodificar_token(token: str) -> Optional[dict]:
    """
    Decodifica y verifica un JWT token.

    Args:
        token: El token JWT a verificar

    Returns:
        Diccionario con los datos del token, o None si es inválido

    Ejemplo:
        datos = decodificar_token("eyJhbGciOiJIUzI1NiIs...")
        # {"sub": "admin", "rol": "admin", "exp": 1234567890}
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db)
) -> Usuario:
    """
    Obtiene el usuario actual desde el token JWT en el header Authorization.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Token no proporcionado")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError()
    except ValueError:
        raise HTTPException(status_code=401, detail="Formato de autorización inválido. Use: Bearer <token>")

    payload = decodificar_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    usuario_id = int(payload.get("sub", 0))
    result = await db.execute(select(Usuario).where(Usuario.id == usuario_id))
    usuario = result.scalar_one_or_none()

    if not usuario:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    if not usuario.activo:
        raise HTTPException(status_code=403, detail="Usuario desactivado")

    return usuario


def require_roles(roles: list[str]):
    """
    Dependencia que verifica que el usuario tenga uno de los roles especificados.
    El rol 'admin' SIEMPRE tiene acceso sin importar lo que se requiera.

    Uso:
        @router.get("/usuarios", dependencies=[Depends(require_roles(["admin"]))])
        @router.get("/ordenes", dependencies=[Depends(require_roles(["tecnico", "asistente"]))])
    """
    async def role_checker(current_user: Usuario = Depends(get_current_user)):
        # Admin tiene acceso universal — hereda todos los roles
        if current_user.rol == RolUsuario.admin:
            return current_user

        rol_value = current_user.rol.value if hasattr(current_user.rol, 'value') else str(current_user.rol)
        if rol_value not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Se requiere uno de estos roles: {', '.join(roles)}"
            )
        return current_user
    return role_checker
