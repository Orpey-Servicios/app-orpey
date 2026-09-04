"""
Modelos SQLAlchemy - Representan las tablas de la base de datos como clases Python.

SQLAlchemy es un ORM (Object-Relational Mapping):
- Convierte tablas SQL en clases Python
- Cada instancia de la clase = una fila de la tabla
- Cada atributo de la clase = una columna de la tabla

Ventaja: no escribimos SQL a mano, Python lo genera por nosotros.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime,
    ForeignKey, Enum, Numeric, Index, func, CheckConstraint
)
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


# Base: clase padre de todos los modelos
# Proporciona funcionalidad básica para mapear clases a tablas
class Base(DeclarativeBase):
    pass


# =====================================================
# ENUMS (Tipos personalizados)
# =====================================================

class TipoEquipo(str, enum.Enum):
    """Tipos de equipo que se reciben en el taller"""
    pc_escritorio = "pc_escritorio"
    laptop = "laptop"
    impresora = "impresora"
    telefono = "telefono"
    otro = "otro"


class EstadoOrden(str, enum.Enum):
    """Estados posibles de una orden de servicio"""
    revision = "revision"
    en_reparacion = "en_reparacion"
    esperando_repuesto = "esperando_repuesto"
    terminada = "terminada"
    entregada = "entregada"
    no_hubo_solucion = "no_hubo_solucion"
    cancelada = "cancelada"


class EstadoCotizacion(str, enum.Enum):
    """Estados de una cotización"""
    abierta = "abierta"
    cerrada = "cerrada"
    aprobada = "aprobada"
    rechazada = "rechazada"


class RolUsuario(str, enum.Enum):
    """Roles de usuarios del sistema"""
    admin = "admin"
    tecnico = "tecnico"
    asistente = "asistente"


# =====================================================
# MODELO: Cliente
# =====================================================

class Cliente(Base):
    """
    Tabla: clientes
    Almacena la información de los clientes del taller.
    """
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    telefono = Column(String(20), nullable=False)
    email = Column(String(255))
    direccion = Column(Text)
    cedula_ruc = Column(String(20), unique=True)
    tipo_persona = Column(String(20), default="natural")
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relación: un cliente puede tener muchas órdenes
    ordenes = relationship("OrdenServicio", back_populates="cliente")
    cotizaciones = relationship("Cotizacion", back_populates="cliente")


# =====================================================
# MODELO: Tecnico
# =====================================================

class Tecnico(Base):
    """
    Tabla: tecnicos
    Almacena la información de los técnicos que trabajan en el taller.
    """
    __tablename__ = "tecnicos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    telefono = Column(String(20))
    email = Column(String(255))
    especialidad = Column(String(100))
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relación: un técnico puede tener muchas órdenes asignadas
    ordenes = relationship("OrdenServicio", back_populates="tecnico")


# =====================================================
# MODELO: OrdenServicio
# =====================================================

class EquipoOrden(Base):
    """
    Tabla: equipos_orden
    Equipos asociados a una orden de servicio.
    """
    __tablename__ = "equipos_orden"

    id = Column(Integer, primary_key=True, autoincrement=True)
    orden_id = Column(Integer, ForeignKey("ordenes_servicio.id", ondelete="CASCADE"), nullable=False)
    tipo_equipo = Column(Enum(TipoEquipo, name="tipo_equipo"), nullable=False)
    marca = Column(String(100))
    modelo = Column(String(100))
    cable = Column(Boolean, default=False)
    cargador = Column(Boolean, default=False)
    contrasena = Column(String(255))
    descripcion_problema = Column(Text, nullable=False)
    diagnostico = Column(Text)
    trabajo_a_realizar = Column(Text)
    repuesto_a_instalar = Column(Text)
    costo = Column(Numeric(10, 2), default=0.00)
    estado = Column(Enum(EstadoOrden, name="estado_orden"), default=EstadoOrden.revision, nullable=False)
    servicio_id = Column(Integer, ForeignKey("catalogo_servicios.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ============================================
    # CAMPOS DE DIAGNÓSTICO TÉCNICO (V3)
    # Los llena el TÉCNICO cuando recibe el equipo.
    # El dueño los revisa y decide la venta.
    # ============================================
    # ¿El equipo enciende? (sí/no)
    enciende = Column(String(10))
    # Tipo de disco: mecánico / SSD / Híbrido
    tipo_disco = Column(String(30))
    # Capacidad del disco (ej: 500GB, 1TB)
    capacidad_disco = Column(String(30))
    # Tipo de memoria RAM (ej: DDR3, DDR4)
    tipo_memoria = Column(String(20))
    # Capacidad de memoria RAM (ej: 4GB, 8GB, 4GB+4GB)
    capacidad_memoria = Column(String(40))
    # ¿Tiene slot M2? (sí/no)
    slot_m2 = Column(String(10))
    # ¿Tiene slot Caddy? (sí/no)
    slot_caddy = Column(String(10))
    # Procesador (ej: AMD, Intel)
    procesador = Column(String(100))

    # Campos adicionales para impresoras y teléfonos
    toma_papel = Column(String(10))
    nivel_tinta = Column(String(50))
    calidad_impresion = Column(String(50))
    pantalla_rota = Column(String(10))
    pin_carga = Column(String(50))

    # ============================================
    # APROBACIÓN DEL DUEÑO (V3)
    # Estados: pendiente | aprobado | rechazado
    # ============================================
    estado_aprobacion = Column(String(20), default="pendiente")
    # Comentario que escribe el dueño al aprobar o rechazar
    comentario_dueño = Column(Text)
    # Decisión del dueño: qué repuesto/parte instalar
    instalacion_decision = Column(Text)
    # Cuánto va a cobrar el dueño por la reparación
    precio_venta = Column(Numeric(10, 2))

    # Relaciones
    orden = relationship("OrdenServicio", back_populates="equipos")
    # Repuestos asociados a este equipo (desglose por proveedor/costo)
    repuestos = relationship(
        "DiagnosticoRepuesto",
        back_populates="equipo",
        cascade="all, delete-orphan",
        order_by="DiagnosticoRepuesto.id"
    )
    servicio = relationship("CatalogoServicio")


class CatalogoServicio(Base):
    """
    Tabla: catalogo_servicios
    Catálogo de servicios predefinidos con costos estandarizados.
    """
    __tablename__ = "catalogo_servicios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(200), unique=True, nullable=False)
    costo = Column(Numeric(10, 2), default=0.00, nullable=False)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class OrdenServicio(Base):
    """
    Tabla: ordenes_servicio
    Tabla PRINCIPAL del sistema. Gestiona todas las órdenes de servicio.
    """
    __tablename__ = "ordenes_servicio"

    id = Column(Integer, primary_key=True, autoincrement=True)
    numero_orden = Column(String(20), unique=True, nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    tecnico_id = Column(Integer, ForeignKey("tecnicos.id"))
    estado = Column(Enum(EstadoOrden, name="estado_orden"), default=EstadoOrden.revision, nullable=False)
    total_orden = Column(Numeric(10, 2), default=0.00)
    abono = Column(Numeric(10, 2), default=0.00)
    garantia_dias = Column(Integer, default=30)
    notas_internas = Column(Text)
    creado_por = Column(String(100))
    fecha_ingreso = Column(DateTime, server_default=func.now())
    fecha_estimada = Column(DateTime)
    fecha_cierre = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones
    cliente = relationship("Cliente", back_populates="ordenes")
    tecnico = relationship("Tecnico", back_populates="ordenes")
    nota_venta = relationship("NotaVenta", back_populates="orden", uselist=False, cascade="all, delete-orphan")
    equipos = relationship("EquipoOrden", back_populates="orden", cascade="all, delete-orphan")
    pagos = relationship("PagoOrden", back_populates="orden", cascade="all, delete-orphan", order_by="PagoOrden.created_at.desc()")
    notas = relationship("NotaOrden", back_populates="orden", cascade="all, delete-orphan", order_by="NotaOrden.created_at.desc()")


# =====================================================
# MODELO: Cotizacion
# =====================================================

class Cotizacion(Base):
    """
    Tabla: cotizaciones
    Gestiona los presupuestos/cotizaciones para clientes.
    """
    __tablename__ = "cotizaciones"

    id = Column(Integer, primary_key=True, autoincrement=True)
    numero_cotizacion = Column(String(20), unique=True, nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    estado = Column(Enum(EstadoCotizacion, name="estado_cotizacion"), default=EstadoCotizacion.abierta, nullable=False)
    descripcion = Column(Text, nullable=False)
    total = Column(Numeric(10, 2), default=0.00, nullable=False)
    validez_dias = Column(Integer, default=7)
    incluye_iva = Column(Boolean, default=False)
    fecha_creacion = Column(DateTime, server_default=func.now())
    fecha_aprobacion = Column(DateTime)
    orden_servicio_id = Column(Integer, ForeignKey("ordenes_servicio.id"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones
    cliente = relationship("Cliente", back_populates="cotizaciones")
    items = relationship("CotizacionItem", back_populates="cotizacion", cascade="all, delete-orphan", order_by="CotizacionItem.id")


class CotizacionItem(Base):
    """
    Tabla: cotizacion_items
    Ítems/detalle de una cotización (servicios o repuestos).
    """
    __tablename__ = "cotizacion_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cotizacion_id = Column(Integer, ForeignKey("cotizaciones.id", ondelete="CASCADE"), nullable=False)
    descripcion = Column(String(255), nullable=False)
    cantidad = Column(Integer, default=1, nullable=False)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    total_item = Column(Numeric(10, 2), nullable=False)

    # Relaciones
    cotizacion = relationship("Cotizacion", back_populates="items")


# =====================================================
# MODELO: NotaVenta
# =====================================================

class NotaVenta(Base):
    """
    Tabla: notas_venta
    Notas de venta (facturación simple sin facturación electrónica).
    """
    __tablename__ = "notas_venta"

    id = Column(Integer, primary_key=True, autoincrement=True)
    numero_nota = Column(String(20), unique=True, nullable=False)
    orden_servicio_id = Column(Integer, ForeignKey("ordenes_servicio.id", ondelete="CASCADE"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    fecha_emision = Column(DateTime, server_default=func.now())
    subtotal = Column(Numeric(10, 2), nullable=False)
    iva = Column(Numeric(10, 2), nullable=False)
    total = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # Relación
    orden = relationship("OrdenServicio", back_populates="nota_venta")


# =====================================================
# MODELO: Usuario
# =====================================================

class Usuario(Base):
    """
    Tabla: usuarios
    Gestión de usuarios y acceso al sistema.
    """
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    rol = Column(Enum(RolUsuario, name="rol_usuario"), nullable=False)
    nombre = Column(String(100), nullable=False)
    email = Column(String(255))
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# =====================================================
# MODELO: ConfiguracionSistema
# =====================================================

class ConfiguracionSistema(Base):
    """
    Tabla: configuracion_sistema
    Datos del negocio, términos, plantillas, etc.
    """
    __tablename__ = "configuracion_sistema"

    id = Column(Integer, primary_key=True, autoincrement=True)
    clave = Column(String(100), unique=True, nullable=False)
    valor = Column(Text, nullable=False)
    descripcion = Column(String(255))


# =====================================================
# MODELO: PagoOrden
# =====================================================

class PagoOrden(Base):
    """
    Tabla: pagos_orden
    Historial de pagos/abonos realizados por el cliente para una orden.
    Cada registro es un pago individual que incrementa el campo abono
    de la orden correspondiente.
    """
    __tablename__ = "pagos_orden"

    id = Column(Integer, primary_key=True, autoincrement=True)
    orden_id = Column(Integer, ForeignKey("ordenes_servicio.id", ondelete="CASCADE"), nullable=False)
    equipo_id = Column(Integer, ForeignKey("equipos_orden.id"), nullable=True)
    monto = Column(Numeric(10, 2), nullable=False)
    metodo_pago = Column(String(50), default="efectivo")
    created_at = Column(DateTime, server_default=func.now())

    # Relaciones
    orden = relationship("OrdenServicio", back_populates="pagos")
    equipo = relationship("EquipoOrden", foreign_keys=[equipo_id])


# =====================================================
# MODELO: NotaOrden
# =====================================================

class NotaOrden(Base):
    """
    Tabla: notas_orden
    Historial de notas internas escritas por el equipo técnico
    para una orden. Cada nota guarda quién la escribió y cuándo.
    """
    __tablename__ = "notas_orden"

    id = Column(Integer, primary_key=True, autoincrement=True)
    orden_id = Column(Integer, ForeignKey("ordenes_servicio.id", ondelete="CASCADE"), nullable=False)
    contenido = Column(Text, nullable=False)
    creado_por = Column(String(100), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # Relación
    orden = relationship("OrdenServicio", back_populates="notas")


# =====================================================
# MODELO: FacturaElectronica (Facturación SRI)
# =====================================================

class FacturaElectronica(Base):
    """
    Tabla: facturas_electronicas
    Comprobantes electrónicos (factura 01) generados para el SRI.

    El flujo actual genera localmente el XML firmado (XAdES-BES) sin
    transmisión al SRI (ambiente "1" = pruebas). Los estados reflejan
    el ciclo de vida completo hasta la autorización.
    """
    __tablename__ = "facturas_electronicas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Origen del comprobante: uno de los dos (el otro queda NULL)
    orden_servicio_id = Column(Integer, ForeignKey("ordenes_servicio.id"), nullable=True)
    nota_venta_id = Column(Integer, ForeignKey("notas_venta.id"), nullable=True)
    # Tipo de comprobante SRI: "01" = factura (default), "04" = nota de crédito.
    # En una NC, orden_servicio_id/nota_venta_id quedan NULL y el origen real es
    # la factura anulada vía factura_referenciada_id.
    tipo_comprobante = Column(String(2), default="01", nullable=False)
    # Solo en notas de crédito: id de la factura que se anula (null en facturas)
    factura_referenciada_id = Column(
        Integer,
        ForeignKey(
            "facturas_electronicas.id",
            name="facturas_electronicas_factura_referenciada_fkey",
        ),
        nullable=True,
    )
    # Motivo de anulación (solo notas de crédito)
    motivo_anulacion = Column(Text, nullable=True)
    # Valor anulado = subtotal/valorModificacion de la NC (solo notas de crédito)
    valor_anulacion = Column(Numeric(10, 2), nullable=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    # Clave de acceso SRI de 49 dígitos (única)
    clave_acceso = Column(String(49), unique=True, nullable=False)
    # Número de documento: establecimiento-punto-secuencial (001-001-000000001)
    numero_documento = Column(String(20), nullable=False)
    # Ambiente SRI: "1" = pruebas (default), "2" = producción (solo admin override)
    ambiente = Column(String(1), default="1", nullable=False)
    # Ciclo de vida: generado → firmado → recibido → autorizado / rechazado / anulado
    # En facturas: "anulada" o "anulada_parcial" la marca la NC vigente asociada.
    estado_sri = Column(String(20), default="generado", nullable=False)
    # XML firmado (XAdES-BES) listo para transmisión
    xml_firmado = Column(Text, nullable=False)
    # Respuesta cruda del SRI (recepción/autorización) — se llenará en el envío
    xml_respuesta_sri = Column(Text, nullable=True)
    # Número de autorización (49 dígitos) otorgado por el SRI (solo si AUTORIZADO)
    numero_autorizacion = Column(String(49), nullable=True)
    # Fecha/hora de autorización otorgada por el SRI (solo si AUTORIZADO)
    fecha_autorizacion = Column(DateTime, nullable=True)
    fecha_emision = Column(DateTime, server_default=func.now())
    subtotal = Column(Numeric(10, 2), nullable=False)
    iva = Column(Numeric(10, 2), nullable=False)
    total = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # Relaciones
    orden = relationship("OrdenServicio", foreign_keys=[orden_servicio_id])
    nota_venta = relationship("NotaVenta", foreign_keys=[nota_venta_id])
    cliente = relationship("Cliente", foreign_keys=[cliente_id])


# =====================================================
# MODELO: DiagnosticoRepuesto (V3)
# =====================================================

class DiagnosticoRepuesto(Base):
    """
    Tabla: diagnostico_repuestos
    Desglose de repuestos para un equipo dentro de una orden.

    Ejemplo (proveedor + repuesto + costo):
        quevecompu → Batería $45
        quevecompu → Pantalla $60

    Cada equipo puede tener varios repuestos de distintos proveedores.
    """
    __tablename__ = "diagnostico_repuestos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    equipo_id = Column(Integer, ForeignKey("equipos_orden.id", ondelete="CASCADE"), nullable=False)
    proveedor = Column(String(100))
    repuesto = Column(String(150))
    costo = Column(Numeric(10, 2), default=0.00)
    created_at = Column(DateTime, server_default=func.now())

    # Relación inversa: el repuesto pertenece a un equipo
    equipo = relationship("EquipoOrden", back_populates="repuestos")


# =====================================================
# MODELO: Caja (módulo de caja / arqueo diario)
# =====================================================

class Caja(Base):
    """
    Tabla: cajas
    Apertura y cierre de la caja diaria del negocio.

    Solo puede existir UNA caja abierta a la vez. El cierre es un arqueo:
    - monto_esperado = monto_inicial + SUM(ingresos) - SUM(egresos)
    - diferencia = monto_contado (monto_cierre) - monto_esperado
      (positivo = sobrante, negativo = faltante)
    """
    __tablename__ = "cajas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    monto_inicial = Column(Numeric(10, 2), nullable=False, default=0)
    monto_cierre = Column(Numeric(10, 2), nullable=True)
    monto_esperado = Column(Numeric(10, 2), nullable=True)
    diferencia = Column(Numeric(10, 2), nullable=True)
    estado = Column(String(20), nullable=False, default="abierta")
    abierta_por = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    cerrada_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    abierta_en = Column(DateTime, server_default=func.now())
    cerrada_en = Column(DateTime, nullable=True)
    nota_cierre = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("estado IN ('abierta', 'cerrada')", name="ck_cajas_estado"),
    )

    # Relación: una caja tiene muchos movimientos (ordenados como libro de caja)
    movimientos = relationship(
        "MovimientoCaja",
        back_populates="caja",
        cascade="all, delete-orphan",
        order_by="MovimientoCaja.id",
    )


class MovimientoCaja(Base):
    """
    Tabla: movimientos_caja
    Cada ingreso/egreso registrado en una caja.

    REGLA UNIFICADA (bug de abasto corregido):
    - SOLO dos tipos: 'ingreso' | 'egreso'.
    - El monto SIEMPRE es positivo en BD; el signo lo da el tipo.
    - origen 'pago_orden' se crea desde el hook de pagos (atómico con el pago).
    - origen 'ingreso_manual' / 'egreso_manual' desde el endpoint de caja.
    """
    __tablename__ = "movimientos_caja"

    id = Column(Integer, primary_key=True, autoincrement=True)
    caja_id = Column(Integer, ForeignKey("cajas.id", ondelete="CASCADE"), nullable=False)
    tipo = Column(String(20), nullable=False)
    origen = Column(String(30), nullable=False)
    referencia_id = Column(Integer, nullable=True)
    monto = Column(Numeric(10, 2), nullable=False)
    descripcion = Column(String(200), nullable=True)
    metodo_pago = Column(String(20), nullable=True, default="")
    creado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    creado_en = Column(DateTime, server_default=func.now())

    __table_args__ = (
        CheckConstraint("tipo IN ('ingreso', 'egreso')", name="ck_movimientos_caja_tipo"),
        CheckConstraint(
            "origen IN ('pago_orden', 'ingreso_manual', 'egreso_manual')",
            name="ck_movimientos_caja_origen",
        ),
    )

    # Relación inversa: el movimiento pertenece a una caja
    caja = relationship("Caja", back_populates="movimientos")
