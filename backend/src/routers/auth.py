"""
Router de Autenticación - Login y gestión de usuarios.

Endpoints:
- POST /api/auth/login → Iniciar sesión y obtener token JWT
- GET /api/auth/me → Verificar token y obtener datos del usuario
- POST /api/auth/cambiar-password → Cambiar contraseña

La autenticación usa JWT (JSON Web Tokens).
El token dura 24 horas.

Flujo:
1. Usuario envía username + password a /api/auth/login
2. Backend verifica en la BD
3. Si es correcto, devuelve un token JWT
4. El frontend guarda el token
5. En cada request, el frontend envía el token en el header: Authorization: Bearer <token>
6. El backend verifica el token y devuelve los datos del usuario
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.models.models import Usuario, RolUsuario
from src.utils.auth import hash_password, verificar_password, crear_token_acceso, decodificar_token, get_current_user
from src.models.models import Usuario

router = APIRouter(
    prefix="/api/auth",
    tags=["Autenticación"]
)


# =====================================================
# MODELOS DE ENTRADA
# =====================================================

class LoginRequest(BaseModel):
    """Datos para iniciar sesión"""
    username: str
    password: str


class CambioPasswordRequest(BaseModel):
    """Datos para cambiar contraseña"""
    password_actual: str
    password_nuevo: str


class TokenResponse(BaseModel):
    """Respuesta del login"""
    access_token: str
    token_type: str = "bearer"
    usuario: dict


# =====================================================
# ENDPOINTS
# =====================================================

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión",
    description="Autentica un usuario y devuelve un token JWT."
)
async def login(
    datos: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Inicia sesión con username y password.

    **Ejemplo de uso:**
    ```json
    {
        "username": "admin",
        "password": "tu_password"
    }
    ```

    **Respuesta:**
    ```json
    {
        "access_token": "eyJhbGciOiJIUzI1NiIs...",
        "token_type": "bearer",
        "usuario": {
            "id": 1,
            "username": "admin",
            "nombre": "Daniel Baltodano",
            "rol": "admin"
        }
    }
    ```
    """
    # Buscar el usuario
    result = await db.execute(select(Usuario).where(Usuario.username == datos.username))
    usuario = result.scalar_one_or_none()

    if not usuario:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    if not usuario.activo:
        raise HTTPException(status_code=403, detail="Usuario desactivado")

    # Verificar la contraseña
    if not verificar_password(datos.password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    # Crear el token JWT
    token_data = {
        "sub": str(usuario.id),
        "username": usuario.username,
        "rol": usuario.rol.value if hasattr(usuario.rol, 'value') else str(usuario.rol),
    }

    access_token = crear_token_acceso(data=token_data)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "usuario": {
            "id": usuario.id,
            "username": usuario.username,
            "nombre": usuario.nombre,
            "email": usuario.email,
            "rol": usuario.rol.value if hasattr(usuario.rol, 'value') else str(usuario.rol),
        }
    }


@router.get(
    "/me",
    summary="Obtener datos del usuario actual",
    description="Devuelve los datos del usuario autenticado mediante el token JWT."
)
async def obtener_usuario_actual(
    current_user: Usuario = Depends(get_current_user)
):
    """
    Devuelve los datos del usuario autenticado.

    El token se envía en el header:
    Authorization: Bearer <token>
    """
    return {
        "id": current_user.id,
        "username": current_user.username,
        "nombre": current_user.nombre,
        "email": current_user.email,
        "rol": current_user.rol.value if hasattr(current_user.rol, 'value') else str(current_user.rol),
        "activo": current_user.activo,
    }


@router.post(
    "/configurar-password",
    summary="Configurar contraseña de un usuario",
    description="Establece la contraseña de un usuario (para cuando el hash está pendiente)."
)
async def configurar_password(
    usuario_id: int,
    password_nuevo: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Configura la contraseña de un usuario.

    Se usa para establecer la contraseña inicial cuando está como 'hash_pendiente'.

    **Ejemplo:**
    ```
    POST /api/auth/configurar-password?usuario_id=1&password_nuevo=mi_password_seguro
    ```
    """
    result = await db.execute(select(Usuario).where(Usuario.id == usuario_id))
    usuario = result.scalar_one_or_none()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Hashear la nueva contraseña
    usuario.password_hash = hash_password(password_nuevo)

    await db.commit()

    return {"mensaje": f"Contraseña configurada para el usuario {usuario.username}"}
