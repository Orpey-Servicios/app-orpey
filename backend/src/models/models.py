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
    ForeignKey, Enum, Numeric, Index, func
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
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones
    orden = relationship("OrdenServicio", back_populates="equipos")


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
    fecha_creacion = Column(DateTime, server_default=func.now())
    fecha_aprobacion = Column(DateTime)
    orden_servicio_id = Column(Integer, ForeignKey("ordenes_servicio.id"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones
    cliente = relationship("Cliente", back_populates="cotizaciones")


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
