"""
Router de Servicios Predefinidos - CRUD del catálogo de servicios.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.models.models import CatalogoServicio
from src.schemas.schemas import ServicioCreate, ServicioUpdate, ServicioResponse

router = APIRouter(
    prefix="/api/servicios",
    tags=["Catálogo de Servicios"]
)


@router.get("/", response_model=List[ServicioResponse])
async def listar_servicios(db: AsyncSession = Depends(get_db)):
    """Lista todos los servicios activos del catálogo."""
    result = await db.execute(select(CatalogoServicio).where(CatalogoServicio.activo == True).order_by(CatalogoServicio.nombre))
    return result.scalars().all()


@router.post("/", response_model=ServicioResponse, status_code=201)
async def crear_servicio(
    servicio: ServicioCreate,
    db: AsyncSession = Depends(get_db)
):
    """Crea un nuevo servicio en el catálogo."""
    # Verificar si ya existe
    result = await db.execute(select(CatalogoServicio).where(CatalogoServicio.nombre == servicio.nombre))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Ya existe un servicio con ese nombre")

    nuevo_servicio = CatalogoServicio(**servicio.model_dump())
    db.add(nuevo_servicio)
    await db.commit()
    await db.refresh(nuevo_servicio)
    return nuevo_servicio


@router.put("/{servicio_id}", response_model=ServicioResponse)
async def actualizar_servicio(
    servicio_id: int,
    datos: ServicioUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Actualiza un servicio existente."""
    result = await db.execute(select(CatalogoServicio).where(CatalogoServicio.id == servicio_id))
    servicio = result.scalar_one_or_none()

    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")

    # Si cambia el nombre, verificar que no colisione
    if datos.nombre and datos.nombre != servicio.nombre:
        result_check = await db.execute(select(CatalogoServicio).where(CatalogoServicio.nombre == datos.nombre))
        if result_check.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Ya existe un servicio con ese nombre")

    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(servicio, campo, valor)

    await db.commit()
    await db.refresh(servicio)
    return servicio


@router.delete("/{servicio_id}", status_code=204)
async def eliminar_servicio(
    servicio_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Elimina (lógicamente) un servicio.
    Se marca como inactivo para no romper el historial.
    """
    result = await db.execute(select(CatalogoServicio).where(CatalogoServicio.id == servicio_id))
    servicio = result.scalar_one_or_none()

    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")

    servicio.activo = False
    await db.commit()
    return None
