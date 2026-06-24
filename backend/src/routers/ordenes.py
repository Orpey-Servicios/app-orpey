"""
Router de Órdenes de Servicio - Endpoints para gestionar órdenes.

Este es el router MÁS IMPORTANTE del sistema.
Gestiona el ciclo completo de una orden: desde que ingresa el equipo hasta que se entrega.

Endpoints disponibles:
- POST /api/ordenes          → Crear orden nueva
- GET /api/ordenes           → Listar todas las órdenes
- GET /api/ordenes/{id}      → Ver una orden específica
- PUT /api/ordenes/{id}      → Actualizar orden
- DELETE /api/ordenes/{id}   → Eliminar orden
- GET /api/ordenes/dashboard → Estadísticas del dashboard
"""

from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, text
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.models.models import (
    OrdenServicio, Cliente, Tecnico, EquipoOrden, Usuario,
    TipoEquipo, EstadoOrden, NotaOrden
)
from src.schemas.schemas import (
    OrdenCreate, OrdenUpdate, OrdenResponse, OrdenDetalleResponse,
    OrdenConCliente, DashboardStats,
    EquipoUpdate, EquipoResponse, EquipoDetalleResponse
)
from src.utils.auth import get_current_user, require_roles

router = APIRouter(
    prefix="/api/ordenes",
    tags=["Órdenes de Servicio"]
)


@router.post(
    "/",
    response_model=OrdenResponse,
    status_code=201,
    summary="Crear una nueva orden de servicio",
    description="Registra una nueva orden. El número se genera automáticamente (ORP-0001)."
)
async def crear_orden(
    orden: OrdenCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Crea una orden de servicio nueva.
    El técnico se asigna automáticamente según el usuario autenticado
    si no se especifica uno manualmente.

    **Importante:**
    - El número de orden se genera automáticamente (ORP-0001, ORP-0002, etc.)
    - La fecha de ingreso se pone automáticamente (ahora)
    - total_orden se calcula automáticamente como suma de costos de equipos
    """
    # Verificar que el cliente existe
    result = await db.execute(select(Cliente).where(Cliente.id == orden.cliente_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # ── Resolver técnico según el rol del usuario ─────────────────────
    rol_usuario = current_user.rol.value if hasattr(current_user.rol, 'value') else str(current_user.rol)
    tecnico_id = orden.tecnico_id

    if rol_usuario == "tecnico":
        # El técnico SIEMPRE se auto-asigna — no puede asignar a otro
        tecnico_id = None  # Forzar búsqueda automática

    if not tecnico_id:
        # Buscar técnico cuyo nombre coincida con el usuario autenticado
        parts = current_user.nombre.split(" ", 1)
        nombre = parts[0]
        apellido = parts[1] if len(parts) > 1 else ""
        result_tec = await db.execute(
            select(Tecnico).where(
                Tecnico.nombre == nombre,
                Tecnico.apellido == apellido,
                Tecnico.activo == True
            )
        )
        tec_asignado = result_tec.scalar_one_or_none()
        if tec_asignado:
            tecnico_id = tec_asignado.id

    # Verificar que el técnico existe si se asigna uno
    if tecnico_id:
        result = await db.execute(select(Tecnico).where(Tecnico.id == tecnico_id))
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Técnico no encontrado")

    # Crear la orden (el número se genera con trigger en la BD)
    datos_orden = orden.model_dump(exclude={"equipos", "total_orden"})
    datos_orden["tecnico_id"] = tecnico_id  # Usar el técnico resuelto
    datos_orden["creado_por"] = current_user.nombre  # Registrar quién creó la orden
    db_orden = OrdenServicio(**datos_orden)
    db.add(db_orden)
    await db.flush()  # Para obtener el ID

    # Si hay notas internas, crear automáticamente un registro en notas_orden
    if orden.notas_internas:
        nombre_autor = current_user.nombre  # Usar el nombre del usuario autenticado
        if tecnico_id:
            result_tec = await db.execute(
                select(Tecnico).where(Tecnico.id == tecnico_id)
            )
            tec = result_tec.scalar_one_or_none()
            if tec:
                nombre_autor = f"{tec.nombre} {tec.apellido}"
        nota_auto = NotaOrden(
            orden_id=db_orden.id,
            contenido=orden.notas_internas,
            creado_por=nombre_autor,
        )
        db.add(nota_auto)

    # Crear equipos y calcular total_orden como suma de costos
    total_calculado = Decimal("0.00")
    for eq in orden.equipos:
        db_equipo = EquipoOrden(**eq.model_dump(), orden_id=db_orden.id)
        db.add(db_equipo)
        total_calculado += eq.costo or Decimal("0.00")

    # Auto-calcular total_orden basado en costo de equipos
    db_orden.total_orden = total_calculado

    await db.commit()
    
    # Cargar relaciones para la respuesta
    result = await db.execute(
        select(OrdenServicio)
        .options(joinedload(OrdenServicio.equipos))
        .where(OrdenServicio.id == db_orden.id)
    )
    db_orden_cargada = result.unique().scalar_one()
    
    return db_orden_cargada


@router.get(
    "/",
    response_model=List[OrdenConCliente],
    summary="Listar todas las órdenes",
    description="Lista todas las órdenes. Se pueden filtrar por estado, cliente o tipo de equipo."
)
async def listar_ordenes(
    estado: Optional[str] = Query(None, description="Filtrar por estado: revision, en_reparacion, esperando_repuesto, terminada, entregada, no_hubo_solucion"),
    cliente_id: Optional[int] = Query(None, description="Filtrar por cliente"),
    tipo_equipo: Optional[str] = Query(None, description="Filtrar por tipo: pc_escritorio, laptop, impresora, telefono"),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista todas las órdenes con filtros opcionales.

    **Ejemplos:**
    - /api/ordenes?estado=en_reparacion → Solo órdenes en reparación
    - /api/ordenes?cliente_id=1 → Solo órdenes del cliente 1
    - /api/ordenes?tipo_equipo=impresora → Solo impresoras
    """
    query = select(OrdenServicio).options(
        joinedload(OrdenServicio.cliente),
        joinedload(OrdenServicio.tecnico),
        joinedload(OrdenServicio.equipos)
    )

    if estado:
        query = query.where(OrdenServicio.estado == EstadoOrden(estado))
    if cliente_id:
        query = query.where(OrdenServicio.cliente_id == cliente_id)
    if tipo_equipo:
        query = query.join(EquipoOrden).where(EquipoOrden.tipo_equipo == TipoEquipo(tipo_equipo))

    query = query.order_by(OrdenServicio.id.desc())  # Más recientes primero
    result = await db.execute(query)
    return result.unique().scalars().all()


# IMPORTANTE: Esta ruta debe estar ANTES de /{orden_id}
# porque FastAPI evalúa las rutas en orden. Si /{orden_id} estuviera primero,
# "dashboard" se interpretaría como un ID y fallaría con error 422.
@router.get(
    "/dashboard",
    response_model=DashboardStats,
    summary="Estadísticas del dashboard",
    description="Devuelve las estadísticas generales para el dashboard."
)
async def obtener_dashboard(
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene las estadísticas del dashboard.
    Usa la vista 'vista_dashboard' que creamos en PostgreSQL.
    """
    result = await db.execute(text("SELECT * FROM vista_dashboard"))
    row = result.mappings().first()

    if not row:
        return DashboardStats(
            ordenes_activas=0,
            pcs_en_reparacion=0,
            laptops_en_reparacion=0,
            impresoras_en_reparacion=0,
            telefonos_en_reparacion=0,
            cotizaciones_abiertas=0,
            cotizaciones_cerradas=0,
            ordenes_cerradas=0
        )

    return DashboardStats(**dict(row))


@router.get(
    "/{orden_id}",
    response_model=OrdenDetalleResponse,
    summary="Obtener una orden por ID",
    description="Devuelve los datos completos con desglose financiero por equipo."
)
async def obtener_orden(
    orden_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene una orden con el desglose financiero por equipo."""
    result = await db.execute(
        select(OrdenServicio)
        .options(
            joinedload(OrdenServicio.equipos),
            joinedload(OrdenServicio.cliente),
            joinedload(OrdenServicio.tecnico)
        )
        .where(OrdenServicio.id == orden_id)
    )
    orden = result.unique().scalar_one_or_none()

    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    # Calcular total pagado por equipo usando el abono de la orden como fuente de verdad.
    # Se distribuye proporcionalmente según el costo de cada equipo.
    abono_orden = float(orden.abono or 0)
    total_costo_equipos = sum(float(eq.costo or 0) for eq in orden.equipos)

    def pagado_para_equipo(eq):
        """Distribuye el abono de la orden proporcionalmente al costo del equipo."""
        if total_costo_equipos <= 0:
            return 0
        costo_eq = float(eq.costo or 0)
        return abono_orden * (costo_eq / total_costo_equipos)

    # Construir respuesta con equipos enriquecidos
    equipos_detalle = [
        EquipoDetalleResponse(
            **{
                "id": eq.id,
                "orden_id": eq.orden_id,
                "tipo_equipo": eq.tipo_equipo.value if hasattr(eq.tipo_equipo, 'value') else str(eq.tipo_equipo),
                "marca": eq.marca,
                "modelo": eq.modelo,
                "cable": eq.cable,
                "cargador": eq.cargador,
                "contrasena": eq.contrasena,
                "descripcion_problema": eq.descripcion_problema,
                "diagnostico": eq.diagnostico,
                "trabajo_a_realizar": eq.trabajo_a_realizar,
                "repuesto_a_instalar": eq.repuesto_a_instalar,
                "costo": eq.costo or Decimal("0.00"),
                "estado": eq.estado.value if hasattr(eq.estado, 'value') else str(eq.estado),
                "created_at": eq.created_at,
                "updated_at": eq.updated_at,
                "total_pagado": Decimal(str(round(pagado_para_equipo(eq), 2))),
            }
        )
        for eq in orden.equipos
    ]

    return OrdenDetalleResponse(
        id=orden.id,
        numero_orden=orden.numero_orden,
        cliente_id=orden.cliente_id,
        tecnico_id=orden.tecnico_id,
        estado=orden.estado.value if hasattr(orden.estado, 'value') else str(orden.estado),
        total_orden=orden.total_orden or Decimal("0.00"),
        abono=orden.abono or Decimal("0.00"),
        garantia_dias=orden.garantia_dias,
        notas_internas=orden.notas_internas,
        fecha_ingreso=orden.fecha_ingreso,
        fecha_estimada=orden.fecha_estimada,
        fecha_cierre=orden.fecha_cierre,
        created_at=orden.created_at,
        equipos=equipos_detalle,
    )


@router.put(
    "/{orden_id}",
    response_model=OrdenResponse,
    summary="Actualizar una orden",
    description="Actualiza los datos de una orden existente."
)
async def actualizar_orden(
    orden_id: int,
    datos: OrdenUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Actualiza una orden.
    Si cambias el estado a 'entregada', se pone automáticamente la fecha de cierre.
    """
    result = await db.execute(
        select(OrdenServicio)
        .options(joinedload(OrdenServicio.equipos))
        .where(OrdenServicio.id == orden_id)
    )
    orden = result.unique().scalar_one_or_none()

    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    # Extraer equipos si vienen en el payload
    datos_dict = datos.model_dump(exclude_unset=True)
    equipos_data = datos_dict.pop("equipos", None)

    # Si cambia el estado de la orden, sincronizar con todos los equipos
    if datos_dict.get("estado"):
        for eq in orden.equipos:
            eq.estado = datos_dict["estado"]
        if datos_dict["estado"] in ("entregada", "terminada", "no_hubo_solucion"):
            datos_dict["fecha_cierre"] = datetime.now()
        else:
            datos_dict["fecha_cierre"] = None

    for campo, valor in datos_dict.items():
        setattr(orden, campo, valor)

    # Actualizar lista de equipos si se proporciona
    if equipos_data is not None:
        equipos_actuales_dict = {eq.id: eq for eq in orden.equipos}
        nuevos_equipos = []
        
        for eq_data in equipos_data:
            if eq_data.get("id") and eq_data["id"] in equipos_actuales_dict:
                # Actualizar existente
                eq_obj = equipos_actuales_dict[eq_data["id"]]
                for k, v in eq_data.items():
                    if k != "id":
                        setattr(eq_obj, k, v)
                nuevos_equipos.append(eq_obj)
            else:
                # Crear nuevo equipo
                nuevo_eq = EquipoOrden(
                    orden_id=orden.id,
                    tipo_equipo=eq_data["tipo_equipo"],
                    marca=eq_data.get("marca"),
                    modelo=eq_data.get("modelo"),
                    cable=eq_data.get("cable", False),
                    cargador=eq_data.get("cargador", False),
                    contrasena=eq_data.get("contrasena"),
                    descripcion_problema=eq_data["descripcion_problema"],
                    diagnostico=eq_data.get("diagnostico"),
                    trabajo_a_realizar=eq_data.get("trabajo_a_realizar"),
                    repuesto_a_instalar=eq_data.get("repuesto_a_instalar"),
                    estado=eq_data.get("estado", "revision")
                )
                nuevos_equipos.append(nuevo_eq)
                
        # Reemplazar la lista completa (SQLAlchemy maneja updates, inserts y deletes huérfanos)
        orden.equipos = nuevos_equipos

        # Recalcular total_orden como suma de costos de equipos
        orden.total_orden = sum(
            (eq.costo or Decimal("0.00"))
            for eq in nuevos_equipos
        )

    await db.commit()
    await db.refresh(orden)
    return orden


@router.put(
    "/{orden_id}/equipos/{equipo_id}",
    response_model=EquipoResponse,
    summary="Actualizar un equipo",
    description="Actualiza el estado u otros datos de un equipo específico."
)
async def actualizar_equipo(
    orden_id: int,
    equipo_id: int,
    datos: EquipoUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Actualiza un equipo específico. Cierra la orden si todos están entregados."""
    result = await db.execute(
        select(EquipoOrden).where(EquipoOrden.id == equipo_id, EquipoOrden.orden_id == orden_id)
    )
    equipo = result.scalar_one_or_none()

    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    datos_dict = datos.model_dump(exclude_unset=True)
    nuevo_estado = datos_dict.get("estado")

    # ── REGLA: "Entregado" requiere pago completo ──
    # Fuente de verdad: el campo abono de la orden vs total_orden.
    # Esto es lo que el usuario ve en la interfaz ("Por Cancelar: $0.00").
    if nuevo_estado == "entregada":
        # Obtener la orden para verificar el estado financiero global
        orden_result = await db.execute(
            select(OrdenServicio).where(OrdenServicio.id == orden_id)
        )
        orden_check = orden_result.scalar_one_or_none()

        if orden_check:
            total_orden = orden_check.total_orden or Decimal("0.00")
            abono_orden = orden_check.abono or Decimal("0.00")
            saldo_orden = total_orden - abono_orden

            if saldo_orden > Decimal("0.00"):
                raise HTTPException(
                    status_code=400,
                    detail=f"No se puede entregar el equipo. La orden tiene un saldo pendiente de ${saldo_orden:.2f}. "
                           f"Pagado: ${abono_orden:.2f} de ${total_orden:.2f}. "
                           f"Registra el pago completo antes de cambiar a 'Entregado'."
                )

    # ── REGLA: "No Hubo Solución" → ajustar costo al monto pagado (revisión técnica) ──
    if nuevo_estado == "no_hubo_solucion":
        # El costo del equipo se reduce a lo que ya se pagó (la revisión técnica)
        # Usar el abono de la orden distribuido proporcionalmente
        orden_nhs = await db.execute(
            select(OrdenServicio)
            .options(joinedload(OrdenServicio.equipos))
            .where(OrdenServicio.id == orden_id)
        )
        orden_nhs_data = orden_nhs.unique().scalar_one_or_none()
        if orden_nhs_data:
            abono_total = orden_nhs_data.abono or Decimal("0.00")
            total_costo = sum((eq.costo or Decimal("0.00")) for eq in orden_nhs_data.equipos)
            if total_costo > Decimal("0.00"):
                costo_actual = equipo.costo or Decimal("0.00")
                proporcion = costo_actual / total_costo
                equipo.costo = (abono_total * proporcion).quantize(Decimal("0.01"))
            else:
                equipo.costo = Decimal("0.00")

    for campo, valor in datos_dict.items():
        setattr(equipo, campo, valor)

    # Sincronizar el estado de la orden con el estado del equipo
    result = await db.execute(
        select(OrdenServicio)
        .options(joinedload(OrdenServicio.equipos))
        .where(OrdenServicio.id == orden_id)
    )
    orden = result.unique().scalar_one_or_none()
    if orden:
        orden.estado = equipo.estado
        if equipo.estado in (EstadoOrden.entregada, EstadoOrden.terminada, EstadoOrden.no_hubo_solucion):
            orden.fecha_cierre = datetime.now()
        else:
            orden.fecha_cierre = None

        # Recalcular total_orden como suma de costos de todos los equipos
        orden.total_orden = sum(
            (eq.costo or Decimal("0.00"))
            for eq in orden.equipos
        )

    await db.commit()
    await db.refresh(equipo)

    return equipo


@router.delete(
    "/{orden_id}",
    status_code=204,
    summary="Eliminar una orden",
    description="Elimina una orden del sistema. Solo permitido para administradores y asistentes.",
    dependencies=[Depends(require_roles(["admin", "asistente"]))]
)
async def eliminar_orden(
    orden_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Elimina una orden. Se usa solo si fue creada por error."""
    result = await db.execute(select(OrdenServicio).where(OrdenServicio.id == orden_id))
    orden = result.scalar_one_or_none()

    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    await db.delete(orden)
    await db.commit()
    return None
