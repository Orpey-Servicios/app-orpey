"""
Schemas Pydantic - Validación de datos de entrada y salida de la API.

Pydantic valida que los datos que recibimos y enviamos sean correctos.
Ejemplo: si un endpoint espera un email, Pydantic verifica que sea un email válido.

Hay 3 tipos de schemas por modelo:
- CreateXxx: datos para CREAR un registro
- UpdateXxx: datos para ACTUALIZAR un registro (todos opcionales)
- XxxResponse: datos que DEVUELVE la API (incluye id, fechas, etc.)
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator
import re


# =====================================================
# SCHEMA: Cliente
# =====================================================

class ClienteCreate(BaseModel):
    """Datos necesarios para crear un cliente nuevo"""
    nombre: str = Field(..., min_length=1, max_length=100)
    apellido: str = Field(..., min_length=1, max_length=100)
    telefono: str = Field(..., min_length=1, max_length=20)
    email: Optional[str] = None
    direccion: Optional[str] = None
    cedula_ruc: Optional[str] = None
    tipo_persona: str = "natural"

    @field_validator("nombre", "apellido")
    @classmethod
    def capitalizar(cls, v: str) -> str:
        """
        Convierte: "gerardo" -> "Gerardo"
        Primera letra mayúscula, resto minúscula.
        """
        if v:
            return v.strip().title()
        return v

    @field_validator("telefono")
    @classmethod
    def validar_telefono(cls, v: str) -> str:
        """
        Valida formato de teléfono ecuatoriano.
        Acepta: 09XXXXXXXX, +5939XXXXXXXX
        """
        v = v.strip()
        # Eliminar espacios, guiones y slash
        v = re.sub(r'[\s\-\./]', '', v)
        return v


class ClienteUpdate(BaseModel):
    """Datos para actualizar un cliente (todos opcionales)"""
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    cedula_ruc: Optional[str] = None
    tipo_persona: Optional[str] = None
    activo: Optional[bool] = None

    @field_validator("nombre", "apellido")
    @classmethod
    def capitalizar(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return v.strip().title()
        return v


class ClienteResponse(BaseModel):
    """Datos que devuelve la API cuando pedimos un cliente"""
    id: int
    nombre: str
    apellido: str
    telefono: str
    email: Optional[str] = None
    direccion: Optional[str] = None
    cedula_ruc: Optional[str] = None
    tipo_persona: str
    activo: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}  # Permite convertir objetos SQLAlchemy


# =====================================================
# SCHEMA: Tecnico
# =====================================================

class TecnicoCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    apellido: str = Field(..., min_length=1, max_length=100)
    telefono: Optional[str] = None
    email: Optional[str] = None
    especialidad: Optional[str] = None

    @field_validator("nombre", "apellido")
    @classmethod
    def capitalizar(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return v.strip().title()
        return v


class TecnicoUpdate(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    especialidad: Optional[str] = None
    activo: Optional[bool] = None


class TecnicoResponse(BaseModel):
    id: int
    nombre: str
    apellido: str
    telefono: Optional[str]
    email: Optional[str]
    especialidad: Optional[str]
    activo: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# =====================================================
# SCHEMA: EquipoOrden
# =====================================================

class EquipoCreate(BaseModel):
    tipo_equipo: str
    marca: Optional[str] = None
    modelo: Optional[str] = None
    cable: bool = False
    cargador: bool = False
    contrasena: Optional[str] = None
    descripcion_problema: str = Field(..., min_length=1)
    diagnostico: Optional[str] = None
    servicio_id: Optional[int] = None
    trabajo_a_realizar: Optional[str] = None
    repuesto_a_instalar: Optional[str] = None
    costo: Decimal = Decimal("0.00")
    estado: str = "revision"


class EquipoUpdate(BaseModel):
    tipo_equipo: Optional[str] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    cable: Optional[bool] = None
    cargador: Optional[bool] = None
    contrasena: Optional[str] = None
    descripcion_problema: Optional[str] = None
    diagnostico: Optional[str] = None
    servicio_id: Optional[int] = None
    trabajo_a_realizar: Optional[str] = None
    repuesto_a_instalar: Optional[str] = None
    costo: Optional[Decimal] = None
    estado: Optional[str] = None


class EquipoOrdenUpdate(BaseModel):
    """Usado cuando se actualiza toda la orden incluyendo sus equipos"""
    id: Optional[int] = None
    tipo_equipo: str
    marca: Optional[str] = None
    modelo: Optional[str] = None
    cable: bool = False
    cargador: bool = False
    contrasena: Optional[str] = None
    descripcion_problema: str = Field(..., min_length=1)
    diagnostico: Optional[str] = None
    servicio_id: Optional[int] = None
    trabajo_a_realizar: Optional[str] = None
    repuesto_a_instalar: Optional[str] = None
    costo: Decimal = Decimal("0.00")
    estado: str = "revision"
    # Campos de diagnóstico técnico (V3)
    enciende: Optional[str] = None
    tipo_disco: Optional[str] = None
    capacidad_disco: Optional[str] = None
    tipo_memoria: Optional[str] = None
    capacidad_memoria: Optional[str] = None
    slot_m2: Optional[str] = None
    slot_caddy: Optional[str] = None
    procesador: Optional[str] = None
    # Campos extra (impresoras y teléfonos)
    toma_papel: Optional[str] = None
    nivel_tinta: Optional[str] = None
    calidad_impresion: Optional[str] = None
    pantalla_rota: Optional[str] = None
    pin_carga: Optional[str] = None


class DiagnosticoRepuestoSchema(BaseModel):
    """Un repuesto del desglose (proveedor + repuesto + costo)."""
    id: Optional[int] = None
    proveedor: Optional[str] = None
    repuesto: Optional[str] = None
    costo: Decimal = Decimal("0.00")

    model_config = {"from_attributes": True}


class EquipoResponse(BaseModel):
    id: int
    orden_id: int
    tipo_equipo: str
    marca: Optional[str]
    modelo: Optional[str]
    cable: bool
    cargador: bool
    contrasena: Optional[str]
    descripcion_problema: str
    diagnostico: Optional[str]
    servicio_id: Optional[int] = None
    trabajo_a_realizar: Optional[str]
    repuesto_a_instalar: Optional[str]
    costo: Decimal = Decimal("0.00")
    estado: str
    created_at: datetime
    updated_at: datetime
    # Campos de diagnóstico técnico (V3)
    enciende: Optional[str] = None
    tipo_disco: Optional[str] = None
    capacidad_disco: Optional[str] = None
    tipo_memoria: Optional[str] = None
    capacidad_memoria: Optional[str] = None
    slot_m2: Optional[str] = None
    slot_caddy: Optional[str] = None
    procesador: Optional[str] = None
    # Campos extra (impresoras y teléfonos)
    toma_papel: Optional[str] = None
    nivel_tinta: Optional[str] = None
    calidad_impresion: Optional[str] = None
    pantalla_rota: Optional[str] = None
    pin_carga: Optional[str] = None
    # Campos de aprobación del dueño (V3)
    estado_aprobacion: Optional[str] = "pendiente"
    comentario_dueño: Optional[str] = None
    instalacion_decision: Optional[str] = None
    precio_venta: Optional[Decimal] = None
    # Desglose de repuestos
    repuestos: List[DiagnosticoRepuestoSchema] = []

    model_config = {"from_attributes": True}


class EquipoDetalleResponse(EquipoResponse):
    """Extiende EquipoResponse con datos financieros por equipo"""
    total_pagado: Decimal = Decimal("0.00")


# =====================================================
# SCHEMA: OrdenServicio
# =====================================================

class OrdenCreate(BaseModel):
    """Datos para crear una orden de servicio"""
    cliente_id: int
    tecnico_id: Optional[int] = None
    equipos: list[EquipoCreate] = Field(..., min_length=1)
    estado: str = "revision"
    total_orden: Decimal = Decimal("0.00")
    abono: Decimal = Decimal("0.00")
    garantia_dias: int = 30
    notas_internas: Optional[str] = None
    fecha_estimada: Optional[datetime] = None


class OrdenUpdate(BaseModel):
    """Datos para actualizar una orden"""
    cliente_id: Optional[int] = None
    tecnico_id: Optional[int] = None
    estado: Optional[str] = None
    total_orden: Optional[Decimal] = None
    abono: Optional[Decimal] = None
    garantia_dias: Optional[int] = None
    notas_internas: Optional[str] = None
    fecha_estimada: Optional[datetime] = None
    fecha_cierre: Optional[datetime] = None
    equipos: Optional[list[EquipoOrdenUpdate]] = None


class OrdenResponse(BaseModel):
    """Datos que devuelve la API de una orden"""
    id: int
    numero_orden: str
    cliente_id: int
    tecnico_id: Optional[int] = None
    creado_por: Optional[str] = None
    estado: str
    total_orden: Decimal
    abono: Decimal
    garantia_dias: Optional[int]
    notas_internas: Optional[str]
    fecha_ingreso: datetime
    fecha_estimada: Optional[datetime]
    fecha_cierre: Optional[datetime]
    created_at: datetime
    equipos: list[EquipoResponse] = []

    model_config = {"from_attributes": True}


class OrdenDetalleResponse(BaseModel):
    """Respuesta del detalle de orden con desglose financiero por equipo"""
    id: int
    numero_orden: str
    cliente_id: int
    tecnico_id: Optional[int] = None
    creado_por: Optional[str] = None
    estado: str
    total_orden: Decimal
    abono: Decimal
    garantia_dias: Optional[int]
    notas_internas: Optional[str]
    fecha_ingreso: datetime
    fecha_estimada: Optional[datetime]
    fecha_cierre: Optional[datetime]
    created_at: datetime
    equipos: list[EquipoDetalleResponse] = []


class OrdenConCliente(BaseModel):
    """Orden con datos del cliente incluidos (para respuesta completa)"""
    id: int
    numero_orden: str
    estado: str
    creado_por: Optional[str] = None
    total_orden: Decimal
    abono: Decimal
    garantia_dias: Optional[int]
    fecha_ingreso: datetime
    cliente: ClienteResponse
    tecnico: Optional[TecnicoResponse] = None
    equipos: list[EquipoResponse] = []

    model_config = {"from_attributes": True}


# =====================================================
# SCHEMA: Cotizacion
# =====================================================

class CotizacionItemSchema(BaseModel):
    descripcion: str = Field(..., min_length=1)
    cantidad: int = 1
    precio_unitario: Decimal = Decimal("0.00")
    total_item: Decimal = Decimal("0.00")

    model_config = {"from_attributes": True}

class CotizacionItemResponse(CotizacionItemSchema):
    id: int
    cotizacion_id: int

class CotizacionCreate(BaseModel):
    cliente_id: int
    estado: str = "abierta"
    descripcion: str = "Cotización General"
    total: Decimal = Decimal("0.00")
    validez_dias: int = 7
    orden_servicio_id: Optional[int] = None
    incluye_iva: bool = False
    items: List[CotizacionItemSchema] = []


class CotizacionUpdate(BaseModel):
    estado: Optional[str] = None
    descripcion: Optional[str] = None
    total: Optional[Decimal] = None
    validez_dias: Optional[int] = None
    orden_servicio_id: Optional[int] = None
    incluye_iva: Optional[bool] = None
    items: Optional[List[CotizacionItemSchema]] = None


class CotizacionResponse(BaseModel):
    id: int
    numero_cotizacion: str
    cliente_id: int
    estado: str
    descripcion: str
    total: Decimal
    validez_dias: int
    incluye_iva: bool = False
    fecha_creacion: datetime
    fecha_aprobacion: Optional[datetime] = None
    orden_servicio_id: Optional[int] = None
    items: List[CotizacionItemResponse] = []

    model_config = {"from_attributes": True}


# =====================================================
# SCHEMA: NotaVenta
# =====================================================

class NotaVentaCreate(BaseModel):
    orden_servicio_id: int
    cliente_id: int


class NotaVentaResponse(BaseModel):
    id: int
    numero_nota: str
    orden_servicio_id: int
    cliente_id: int
    fecha_emision: datetime
    subtotal: Decimal
    iva: Decimal
    total: Decimal

    model_config = {"from_attributes": True}


# =====================================================
# SCHEMA: FacturaElectronica (SRI)
# =====================================================

class FacturaElectronicaCreate(BaseModel):
    """
    Datos para generar una factura electrónica.
    Se indica el origen: orden_servicio_id o nota_venta_id (uno de los dos).
    Ambiente siempre "1" (pruebas) por defecto; "2" solo con override de admin.
    """
    orden_servicio_id: Optional[int] = None
    nota_venta_id: Optional[int] = None
    ambiente: str = Field("1", pattern="^[12]$")


class NotaCreditoRequest(BaseModel):
    """
    Body del POST /api/facturacion/{factura_id}/anular (nota de crédito).

    - motivo: texto de la anulación (obligatorio, va en <motivo> del XML).
    - monto_anular: monto TOTAL (IVA incluido) a anular. Default = total de la
      factura (anulación total). Si es menor, la NC es parcial.
    - fecha_autorizada: fecha de emisión de la NC (fechaEmision). Default = hoy.
      Debe ser >= fecha de emisión de la factura original.
    """
    motivo: str = Field(..., min_length=1, max_length=500, description="Motivo de la anulación")
    monto_anular: Optional[Decimal] = Field(None, gt=0, description="Monto total a anular (IVA incluido); default = total de la factura")
    fecha_autorizada: Optional[date] = Field(None, description="Fecha de emisión de la NC; default = hoy")


class FacturaElectronicaResponse(BaseModel):
    """Comprobante electrónico generado (factura 01 o nota de crédito 04)."""
    id: int
    orden_servicio_id: Optional[int] = None
    nota_venta_id: Optional[int] = None
    cliente_id: int
    tipo_comprobante: str = "01"
    factura_referenciada_id: Optional[int] = None
    motivo_anulacion: Optional[str] = None
    valor_anulacion: Optional[Decimal] = None
    clave_acceso: str
    numero_documento: str
    ambiente: str
    estado_sri: str
    xml_respuesta_sri: Optional[str] = None
    numero_autorizacion: Optional[str] = None
    fecha_autorizacion: Optional[datetime] = None
    fecha_emision: datetime
    subtotal: Decimal
    iva: Decimal
    total: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


# =====================================================
# SCHEMA: Dashboard
# =====================================================

class DashboardStats(BaseModel):
    """Estadísticas del dashboard"""
    ordenes_activas: int
    pcs_en_reparacion: int
    laptops_en_reparacion: int
    impresoras_en_reparacion: int
    telefonos_en_reparacion: int
    cotizaciones_abiertas: int
    cotizaciones_cerradas: int
    ordenes_cerradas: int


# =====================================================
# SCHEMA: PagoOrden
# =====================================================

class PagoCreate(BaseModel):
    """Datos para registrar un pago/abono en una orden"""
    monto: Decimal = Field(..., gt=0, description="Monto del pago")
    metodo_pago: str = "efectivo"
    equipo_id: Optional[int] = Field(None, description="ID del equipo al que se asigna este pago (opcional)")


class PagoResponse(BaseModel):
    """Datos que devuelve la API de un pago registrado"""
    id: int
    orden_id: int
    equipo_id: Optional[int] = None
    monto: Decimal
    metodo_pago: str
    created_at: datetime
    equipo_marca: Optional[str] = Field(None, alias="equipo_marca")
    equipo_modelo: Optional[str] = Field(None, alias="equipo_modelo")

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_equipo(cls, pago):
        """Crea el response incluyendo datos del equipo asociado"""
        data = {
            "id": pago.id,
            "orden_id": pago.orden_id,
            "equipo_id": pago.equipo_id,
            "monto": pago.monto,
            "metodo_pago": pago.metodo_pago,
            "created_at": pago.created_at,
            "equipo_marca": pago.equipo.marca if pago.equipo else None,
            "equipo_modelo": pago.equipo.modelo if pago.equipo else None,
        }
        return cls(**data)


# =====================================================
# SCHEMA: NotaOrden
# =====================================================

class NotaCreate(BaseModel):
    """Datos para agregar una nota interna a una orden"""
    contenido: str = Field(..., min_length=1, max_length=2000)
    creado_por: str = Field(..., min_length=1, max_length=100)


class NotaResponse(BaseModel):
    """Datos que devuelve la API de una nota interna"""
    id: int
    orden_id: int
    contenido: str
    creado_por: str
    created_at: datetime

    model_config = {"from_attributes": True}


# =====================================================
# SCHEMA: Usuario
# =====================================================

class UsuarioCreate(BaseModel):
    """Datos para crear un usuario nuevo"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    rol: str = Field(...)
    nombre: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = None


class UsuarioUpdate(BaseModel):
    """Datos para actualizar un usuario (todos opcionales)"""
    username: Optional[str] = None
    password: Optional[str] = None
    rol: Optional[str] = None
    nombre: Optional[str] = None
    email: Optional[str] = None
    activo: Optional[bool] = None


class UsuarioResponse(BaseModel):
    """Datos que devuelve la API de un usuario"""
    id: int
    username: str
    rol: str
    nombre: str
    email: Optional[str] = None
    activo: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# =====================================================
# SCHEMA: Diagnóstico Técnico (V3)
# =====================================================

class DiagnosticoGuardar(BaseModel):
    """
    Cuerpo para GUARDAR el diagnóstico de un equipo.
    Lo llena el técnico dentro de la orden.
    """
    enciende: Optional[str] = None
    tipo_disco: Optional[str] = None
    capacidad_disco: Optional[str] = None
    tipo_memoria: Optional[str] = None
    capacidad_memoria: Optional[str] = None
    slot_m2: Optional[str] = None
    slot_caddy: Optional[str] = None
    procesador: Optional[str] = None
    diagnostico: Optional[str] = None
    # Campos extra (impresoras y teléfonos)
    toma_papel: Optional[str] = None
    nivel_tinta: Optional[str] = None
    calidad_impresion: Optional[str] = None
    pantalla_rota: Optional[str] = None
    pin_carga: Optional[str] = None
    # Desglose de repuestos (proveedor + repuesto + costo)
    repuestos: List[DiagnosticoRepuestoSchema] = []


class AprobarDiagnostico(BaseModel):
    """
    Cuerpo para que el DUEÑO apruebe un diagnóstico.
    Incluye comentario y qué decide instalar.
    """
    comentario: Optional[str] = None
    instalacion_decision: Optional[str] = None
    precio_venta: Optional[Decimal] = None


class RechazarDiagnostico(BaseModel):
    """
    Cuerpo para que el DUEÑO rechace un diagnóstico.
    Debe indicar el motivo (comentario).
    """
    comentario: Optional[str] = None


class DiagnosticoActivoResponse(BaseModel):
    """
    Respuesta para la sección "Diagnósticos activos" (para el dueño).
    Incluye los datos del equipo + del cliente + de la orden,
    para que el dueño decida sin abrir la orden completa.
    """
    equipo: dict
    cliente: dict
    orden_id: int
    numero_orden: str


# =====================================================
# SCHEMA: Caja (módulo de caja / arqueo)
# =====================================================

class CajaAbrirRequest(BaseModel):
    """Datos para abrir la caja del día."""
    monto_inicial: Decimal = Field(Decimal("0.00"), ge=0, description="Dinero con el que se abre la caja")


class CajaCerrarRequest(BaseModel):
    """Datos para cerrar la caja (arqueo)."""
    monto_contado: Decimal = Field(..., ge=0, description="Dinero físico contado al cierre")
    nota_cierre: Optional[str] = None


class MovimientoCajaCreate(BaseModel):
    """
    Datos para registrar un movimiento MANUAL en la caja.
    El signo lo da el tipo: 'ingreso' suma, 'egreso' resta.
    El monto siempre es positivo.
    """
    tipo: Literal["ingreso", "egreso"]
    monto: Decimal = Field(..., gt=0)
    descripcion: Optional[str] = None
    metodo_pago: Optional[str] = None


class CajaResponse(BaseModel):
    """Caja con montos calculados del período (ingresos, egresos, monto en caja)."""
    id: int
    monto_inicial: Decimal
    monto_cierre: Optional[Decimal] = None
    monto_esperado: Optional[Decimal] = None
    diferencia: Optional[Decimal] = None
    estado: str
    abierta_por: int
    abierta_en: datetime
    cerrada_por: Optional[int] = None
    cerrada_en: Optional[datetime] = None
    nota_cierre: Optional[str] = None
    monto_en_caja: Optional[Decimal] = None
    ingresos: Decimal = Decimal("0.00")
    egresos: Decimal = Decimal("0.00")


class MovimientoCajaResponse(BaseModel):
    """Movimiento de caja (ingreso o egreso)."""
    id: int
    caja_id: int
    tipo: str
    origen: str
    referencia_id: Optional[int] = None
    monto: Decimal
    descripcion: Optional[str] = None
    metodo_pago: Optional[str] = None
    creado_por: int
    creado_en: datetime

    model_config = {"from_attributes": True}


class ResumenDiaResponse(BaseModel):
    """Resumen financiero del día para el Dashboard."""
    fecha: date
    caja_abierta: Optional[CajaResponse] = None
    ingresos_hoy: Decimal = Decimal("0.00")
    egresos_hoy: Decimal = Decimal("0.00")
    esperado_hoy: Decimal = Decimal("0.00")
    facturado_hoy: Decimal = Decimal("0.00")
    notas_venta_hoy: Decimal = Decimal("0.00")
    pagos_hoy: Decimal = Decimal("0.00")
    ordenes_cerradas_hoy: int = 0


# =====================================================
# SCHEMA: CatalogoServicio
# =====================================================

class ServicioCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    costo: Decimal = Decimal("0.00")
    activo: bool = True

class ServicioUpdate(BaseModel):
    nombre: Optional[str] = None
    costo: Optional[Decimal] = None
    activo: Optional[bool] = None

class ServicioResponse(BaseModel):
    id: int
    nombre: str
    costo: Decimal
    activo: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
