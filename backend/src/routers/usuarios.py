"""
Router de Usuarios - CRUD y gestión de usuarios del sistema.
Requiere autenticación y rol de administrador.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.config.database import get_db
from src.models.models import Usuario, RolUsuario
from src.utils.auth import hash_password, get_current_user, require_roles, validar_password
from src.schemas.schemas import (
    UsuarioCreate, UsuarioUpdate, UsuarioResponse
)

router = APIRouter(
    prefix="/api/usuarios",
    tags=["Usuarios"]
)


@router.get("/", response_model=list[UsuarioResponse])
async def listar_usuarios(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["admin"]))
):
    """Lista todos los usuarios del sistema (solo admin)"""
    result = await db.execute(select(Usuario).order_by(Usuario.nombre))
    usuarios = result.scalars().all()
    return usuarios


@router.get("/{usuario_id}", response_model=UsuarioResponse)
async def obtener_usuario(
    usuario_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["admin"]))
):
    """Obtiene un usuario por ID (solo admin)"""
    result = await db.execute(select(Usuario).where(Usuario.id == usuario_id))
    usuario = result.scalar_one_or_none()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario


@router.post("/", response_model=UsuarioResponse, status_code=201)
async def crear_usuario(
    datos: UsuarioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["admin"]))
):
    """Crea un nuevo usuario (solo admin)"""
    roles_validos = [r.value for r in RolUsuario]
    if datos.rol not in roles_validos:
        raise HTTPException(
            status_code=400,
            detail=f"Rol inválido. Roles válidos: {', '.join(roles_validos)}"
        )

    result = await db.execute(select(Usuario).where(Usuario.username == datos.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="El username ya existe")

    # Validar la contraseña antes de hashearla (mensajes claros, evita el
    # error interno de bcrypt por contraseñas demasiado largas).
    validar_password(datos.password)

    nuevo_usuario = Usuario(
        username=datos.username,
        password_hash=hash_password(datos.password),
        rol=RolUsuario(datos.rol),
        nombre=datos.nombre,
        email=datos.email,
    )

    db.add(nuevo_usuario)
    await db.commit()
    await db.refresh(nuevo_usuario)
    return nuevo_usuario


@router.put("/{usuario_id}", response_model=UsuarioResponse)
async def actualizar_usuario(
    usuario_id: int,
    datos: UsuarioUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["admin"]))
):
    """Actualiza un usuario existente (solo admin)"""
    result = await db.execute(select(Usuario).where(Usuario.id == usuario_id))
    usuario = result.scalar_one_or_none()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if datos.username is not None:
        dup = await db.execute(
            select(Usuario).where(Usuario.username == datos.username, Usuario.id != usuario_id)
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="El username ya existe")
        usuario.username = datos.username

    if datos.password is not None:
        # Validar la nueva contraseña antes de hashearla.
        validar_password(datos.password)
        usuario.password_hash = hash_password(datos.password)

    if datos.rol is not None:
        roles_validos = [r.value for r in RolUsuario]
        if datos.rol not in roles_validos:
            raise HTTPException(
                status_code=400,
                detail=f"Rol inválido. Roles válidos: {', '.join(roles_validos)}"
            )
        usuario.rol = RolUsuario(datos.rol)

    if datos.nombre is not None:
        usuario.nombre = datos.nombre

    if datos.email is not None:
        usuario.email = datos.email

    if datos.activo is not None:
        usuario.activo = datos.activo

    await db.commit()
    await db.refresh(usuario)
    return usuario


@router.delete("/{usuario_id}")
async def desactivar_usuario(
    usuario_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_roles(["admin"]))
):
    """Desactiva un usuario (no lo borra, solo lo desactiva)"""
    if usuario_id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes desactivarte a ti mismo")

    result = await db.execute(select(Usuario).where(Usuario.id == usuario_id))
    usuario = result.scalar_one_or_none()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    usuario.activo = False
    await db.commit()
    return {"mensaje": f"Usuario {usuario.username} desactivado"}
