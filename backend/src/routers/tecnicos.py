"""
Router de Técnicos - Endpoints para gestionar técnicos.

Endpoints:
- POST /api/tecnicos       → Crear técnico
- GET /api/tecnicos        → Listar técnicos
- GET /api/tecnicos/{id}   → Ver técnico
- PUT /api/tecnicos/{id}   → Actualizar técnico
- DELETE /api/tecnicos/{id} → Eliminar técnico
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.models.models import Tecnico
from src.schemas.schemas import TecnicoCreate, TecnicoUpdate, TecnicoResponse

router = APIRouter(
    prefix="/api/tecnicos",
    tags=["Técnicos"]
)


@router.post("/", response_model=TecnicoResponse, status_code=201)
async def crear_tecnico(
    tecnico: TecnicoCreate,
    db: AsyncSession = Depends(get_db)
):
    """Crea un técnico nuevo."""
    db_tecnico = Tecnico(**tecnico.model_dump())
    db.add(db_tecnico)
    await db.commit()
    await db.refresh(db_tecnico)
    return db_tecnico


@router.get("/", response_model=List[TecnicoResponse])
async def listar_tecnicos(
    db: AsyncSession = Depends(get_db)
):
    """Lista todos los técnicos activos."""
    result = await db.execute(select(Tecnico).where(Tecnico.activo == True))
    return result.scalars().all()


@router.get("/{tecnico_id}", response_model=TecnicoResponse)
async def obtener_tecnico(
    tecnico_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene un técnico por ID."""
    result = await db.execute(select(Tecnico).where(Tecnico.id == tecnico_id))
    tecnico = result.scalar_one_or_none()

    if not tecnico:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")

    return tecnico


@router.put("/{tecnico_id}", response_model=TecnicoResponse)
async def actualizar_tecnico(
    tecnico_id: int,
    datos: TecnicoUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Actualiza un técnico."""
    result = await db.execute(select(Tecnico).where(Tecnico.id == tecnico_id))
    tecnico = result.scalar_one_or_none()

    if not tecnico:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")

    datos_dict = datos.model_dump(exclude_unset=True)
    for campo, valor in datos_dict.items():
        setattr(tecnico, campo, valor)

    await db.commit()
    await db.refresh(tecnico)
    return tecnico


@router.delete("/{tecnico_id}", status_code=204)
async def eliminar_tecnico(
    tecnico_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Elimina un técnico (desactivación lógica)."""
    result = await db.execute(select(Tecnico).where(Tecnico.id == tecnico_id))
    tecnico = result.scalar_one_or_none()

    if not tecnico:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")

    tecnico.activo = False
    await db.commit()
    return None
