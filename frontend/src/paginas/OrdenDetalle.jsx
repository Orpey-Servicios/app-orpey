/**
 * DETALLE DE ORDEN - Vista completa de una orden de servicio
 *
 * CAMBIOS IMPLEMENTADOS (26 Mayo 2026):
 * 1. ✏️ Editar datos del cliente desde el detalle (modal)
 * 2. 💰 Editar total + registrar pagos con historial
 * 3. 📝 Notas internas con historial (quién, cuándo, qué dijo)
 */
import { useState, useEffect } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import {
  ArrowLeft, Edit, FileDown, MessageCircle, Receipt,
  Trash2, User, Wrench, Calendar, Shield, Save, X, DollarSign,
  Plus, Clock, MessageSquare, UserCheck, CreditCard, ListChecks,
  Pencil, History, FileCheck2, Ban, RotateCcw
} from 'lucide-react';
import {
  obtenerOrden, obtenerCliente, obtenerTecnico, actualizarEquipo,
  eliminarOrden, descargarPdfOrden, obtenerWhatsappOrden, crearNotaVenta,
  actualizarCliente, actualizarOrden,
  registrarPago, obtenerPagos, agregarNota, obtenerNotas, obtenerTecnicos,
  obtenerFacturas, generarFactura
} from '../api/orpey-api';
import BadgeEstado from '../componentes/BadgeEstado';
import FormularioDiagnostico from '../componentes/FormularioDiagnostico';
import { useAuth } from '../context/AuthContext';
import './OrdenDetalle.css';
import './OrdenFormulario.css';

const tipoEquipoTexto = {
  pc_escritorio: '🖥️ PC Escritorio', laptop: '💻 Laptop',
  impresora: '🖨️ Impresora', telefono: '📱 Teléfono', otro: '🔧 Otro'
};

const ESTADOS_MAP = {
  'revision': 'Revisión',
  'en_reparacion': 'En Reparación',
  'esperando_repuesto': 'Esperando Repuesto',
  'terminada': 'Reparado',
  'entregada': 'Entregado',
  'no_hubo_solucion': 'No Hubo Solución'
};
const ESTADOS = Object.keys(ESTADOS_MAP);

const METODOS_PAGO = ['efectivo', 'transferencia', 'tarjeta', 'depósito', 'otro'];

/**
 * Calcula el total pagado para un equipo específico.
 * Usa la proporción del abono de la orden (fuente de verdad) distribuida
 * según el costo de cada equipo.
 */
function calcularPagadoEquipo(equipoId, equipos, ordenAbono) {
  const totalCostoEquipos = equipos.reduce((sum, eq) => sum + (Number(eq.costo) || 0), 0);
  if (totalCostoEquipos <= 0) return 0;
  const equipo = equipos.find(eq => eq.id === equipoId);
  const costoEquipo = Number(equipo?.costo) || 0;
  const proporcion = costoEquipo / totalCostoEquipos;
  return Number(ordenAbono) * proporcion;
}

// ══════════════════════════════════════════════════
// COMPONENTE PRINCIPAL
// ══════════════════════════════════════════════════
export default function OrdenDetalle() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { usuario } = useAuth();
  const [orden, setOrden] = useState(null);
  const [cliente, setCliente] = useState(null);
  const [tecnico, setTecnico] = useState(null);
  const [pagos, setPagos] = useState([]);
  const [notas, setNotas] = useState([]);
  const [tecnicos, setTecnicos] = useState([]);
  const [facturas, setFacturas] = useState([]);
  const [cargando, setCargando] = useState(true);

  // ── Estados de modales ──────────────────────────
  const [modalCliente, setModalCliente] = useState(false);
  const [modalTotal, setModalTotal] = useState(false);
  const [modalPago, setModalPago] = useState(false);
  const [notaTexto, setNotaTexto] = useState('');
  const [notaAutor, setNotaAutor] = useState('');

  // ── Estados de formularios ──────────────────────
  const [formCliente, setFormCliente] = useState({
    nombre: '', apellido: '', telefono: '', email: '',
    direccion: '', cedula_ruc: ''
  });
  const [formTotal, setFormTotal] = useState('0.00');
  const [formTotalEquipos, setFormTotalEquipos] = useState(null);
  const [formPago, setFormPago] = useState({ monto: '', metodo_pago: 'efectivo', equipo_id: '' });
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => { cargarDatos(); }, [id]);

  async function cargarDatos() {
    try {
      setCargando(true);
      const [ordenData, tecnicosData] = await Promise.all([
        obtenerOrden(Number(id)),
        obtenerTecnicos()
      ]);
      setOrden(ordenData);
      setTecnicos(tecnicosData);
      try {
        setFacturas(await obtenerFacturas());
      } catch (err) { console.error('Error cargando facturas:', err); setFacturas([]); }

      // Nombre del técnico actual como autor por defecto
      const daniel = tecnicosData.find(t =>
        t.nombre === 'Daniel' && t.apellido === 'Baltodano'
      );
      setNotaAutor(daniel ? `${daniel.nombre} ${daniel.apellido}` : '');

      const [clienteData, pagosData, notasData] = await Promise.all([
        obtenerCliente(ordenData.cliente_id),
        obtenerPagos(Number(id)),
        obtenerNotas(Number(id))
      ]);
      setCliente(clienteData);
      setPagos(pagosData);
      setNotas(notasData);

      if (ordenData.tecnico_id) {
        const tecData = await obtenerTecnico(ordenData.tecnico_id);
        setTecnico(tecData);
      }
    } catch (err) { console.error(err); }
    finally { setCargando(false); }
  }

  // Cambiar estado de un equipo
  async function cambiarEstadoEquipo(equipoId, nuevoEstado) {
    // REGLA: "Entregado" requiere pago completo de la ORDEN
    // Fuente de verdad: abono vs total_orden (lo que muestra "Por Cancelar")
    if (nuevoEstado === 'entregada') {
      const totalOrden = Number(orden.total_orden) || 0;
      const abonoOrden = Number(orden.abono) || 0;
      const saldo = totalOrden - abonoOrden;
      if (saldo > 0) {
        setError(`No se puede entregar. La orden tiene un saldo pendiente de $${saldo.toFixed(2)}. Pagado: $${abonoOrden.toFixed(2)} de $${totalOrden.toFixed(2)}. Registra el pago completo primero.`);
        return;
      }
    }
    try {
      setError(null);
      await actualizarEquipo(Number(id), equipoId, { estado: nuevoEstado });
      cargarDatos();
    } catch (err) {
      // Mostrar error del backend de forma más amigable
      const mensaje = err.message || 'Error al cambiar el estado';
      setError(mensaje);
    }
  }

  // Enviar por WhatsApp
  async function enviarWhatsapp() {
    try {
      const data = await obtenerWhatsappOrden(Number(id));
      window.open(data.link, '_blank');
    } catch (err) { alert('Error: ' + err.message); }
  }

  // Convertir a nota de venta
  async function convertirNotaVenta() {
    if (!confirm('¿Crear nota de venta para esta orden?')) return;
    try {
      await crearNotaVenta({ orden_servicio_id: Number(id), cliente_id: orden.cliente_id });
      alert('Nota de venta creada exitosamente');
    } catch (err) { alert('Error: ' + err.message); }
  }

  // Generar factura electrónica SRI
  async function generarFacturaSRI() {
    if (!confirm('¿Generar factura electrónica SRI para esta orden?')) return;
    try {
      setError(null);
      const factura = await generarFactura({ orden_servicio_id: Number(id) });
      alert(`Factura ${factura.numero_documento} generada y firmada correctamente`);
      navigate('/facturacion');
    } catch (err) { setError(err.message); }
  }

  // Cancelar orden (soft delete — mantiene el correlativo)
  async function borrarOrden() {
    if (!confirm('¿Cancelar esta orden? Quedará registrada como CANCELADA para no alterar el correlativo de órdenes.')) return;
    try {
      await eliminarOrden(Number(id));
      navigate('/ordenes');
    } catch (err) { alert('Error: ' + err.message); }
  }

  // ── ✏️ EDITAR CLIENTE ───────────────────────────
  function abrirModalCliente() {
    setFormCliente({
      nombre: cliente?.nombre || '',
      apellido: cliente?.apellido || '',
      telefono: cliente?.telefono || '',
      email: cliente?.email || '',
      direccion: cliente?.direccion || '',
      cedula_ruc: cliente?.cedula_ruc || '',
    });
    setModalCliente(true);
  }

  async function guardarCliente() {
    try {
      setGuardando(true);
      setError(null);
      const datos = {};
      for (const [key, val] of Object.entries(formCliente)) {
        if (val !== cliente[key]) datos[key] = val;
      }
      if (Object.keys(datos).length === 0) { setModalCliente(false); return; }
      const actualizado = await actualizarCliente(cliente.id, datos);
      setCliente(actualizado);
      setModalCliente(false);
    } catch (err) { setError(err.message); }
    finally { setGuardando(false); }
  }

  // ── 💰 EDITAR TOTAL ─────────────────────────────
  function abrirModalTotal() {
    setFormTotal(orden.total_orden.toString());
    setFormTotalEquipos(orden.equipos?.map(eq => ({
      id: eq.id, marca: eq.marca, modelo: eq.modelo,
      tipo_equipo: eq.tipo_equipo, costo: eq.costo?.toString() || '0.00'
    })) || []);
    setModalTotal(true);
  }

  async function guardarTotal() {
    try {
      setGuardando(true);
      setError(null);
      // Validar que el nuevo total no sea menor al abono actual
      const nuevoTotal = formTotalEquipos?.reduce((s, e) => s + (Number(e.costo) || 0), 0) || 0;
      const abonoActual = Number(orden.abono) || 0;
      if (nuevoTotal < abonoActual) {
        setError(`El nuevo total ($${nuevoTotal.toFixed(2)}) no puede ser menor al abono actual ($${abonoActual.toFixed(2)}). Ya se han registrado pagos por esa cantidad.`);
        setGuardando(false);
        return;
      }

      // Enviar equipos completos al backend (con todos los campos requeridos)
      const equiposActualizados = formTotalEquipos.map(eq => {
        const original = orden.equipos.find(o => o.id === eq.id);
        return {
          ...(original ? {
            id: original.id, tipo_equipo: original.tipo_equipo, marca: original.marca,
            modelo: original.modelo, cable: original.cable, cargador: original.cargador,
            contrasena: original.contrasena, descripcion_problema: original.descripcion_problema,
            diagnostico: original.diagnostico, trabajo_a_realizar: original.trabajo_a_realizar,
            repuesto_a_instalar: original.repuesto_a_instalar, estado: original.estado,
          } : { tipo_equipo: 'otro', descripcion_problema: '---' }),
          costo: Number(eq.costo) || 0,
        };
      });
      await actualizarOrden(Number(id), { equipos: equiposActualizados });
      setModalTotal(false);
      const [ordenActualizada, pagosActualizados] = await Promise.all([
        obtenerOrden(Number(id)),
        obtenerPagos(Number(id))
      ]);
      setOrden(ordenActualizada);
      setPagos(pagosActualizados);
    } catch (err) { setError(err.message); }
    finally { setGuardando(false); }
  }

  // ── 💵 REGISTRAR PAGO ────────────────────────────
  // Calcular saldo pendiente (lo que aún se puede abonar)
  const saldoPendiente = orden ? Math.max(0, Number(orden.total_orden) - Number(orden.abono)) : 0;

  async function guardarPago() {
    if (!formPago.monto || Number(formPago.monto) <= 0) {
      setError('El monto del pago debe ser mayor a 0');
      return;
    }
    const montoNum = Number(formPago.monto);
    if (montoNum > saldoPendiente) {
      setError(`El pago ($${montoNum.toFixed(2)}) excede el saldo pendiente ($${saldoPendiente.toFixed(2)}). Para agregar un abono mayor, primero edita el monto total de la orden.`);
      return;
    }
    try {
      setGuardando(true);
      setError(null);
      // Registrar el pago (el backend suma al abono automáticamente)
      await registrarPago(Number(id), {
        monto: montoNum,
        metodo_pago: formPago.metodo_pago,
        equipo_id: formPago.equipo_id ? Number(formPago.equipo_id) : null,
      });
      setFormPago({ monto: '', metodo_pago: 'efectivo', equipo_id: '' });
      setModalPago(false);
      // Recargar datos para ver el abono actualizado + el historial
      const [ordenActualizada, pagosActualizados] = await Promise.all([
        obtenerOrden(Number(id)),
        obtenerPagos(Number(id))
      ]);
      setOrden(ordenActualizada);
      setPagos(pagosActualizados);
    } catch (err) { setError(err.message); }
    finally { setGuardando(false); }
  }

  // ── 📝 AGREGAR NOTA ─────────────────────────────
  async function guardarNota() {
    if (!notaTexto.trim()) return;
    if (!notaAutor.trim()) {
      setError('Selecciona o escribe tu nombre para la nota');
      return;
    }
    try {
      setGuardando(true);
      setError(null);
      await agregarNota(Number(id), {
        contenido: notaTexto.trim(),
        creado_por: notaAutor.trim(),
      });
      setNotaTexto('');
      // Recargar notas
      const notasActualizadas = await obtenerNotas(Number(id));
      setNotas(notasActualizadas);
    } catch (err) { setError(err.message); }
    finally { setGuardando(false); }
  }

  // ── RENDER ──────────────────────────────────────
  if (cargando) return <div className="dashboard__cargando"><div className="spinner" /><p>Cargando orden...</p></div>;
  if (!orden) return <div className="dashboard__vacio"><p>Orden no encontrada</p></div>;

  const porCancelar = Number(orden.total_orden) - Number(orden.abono);
  const esCancelada = orden.estado === 'cancelada' || orden.equipos?.some(e => e.estado === 'cancelada');
  const facturaOrden = facturas.find(f => Number(f.orden_servicio_id) === Number(id));
  const tieneFactura = Boolean(facturaOrden);
  const facturaAutorizada = Boolean(facturaOrden?.estado_sri === 'autorizado' && facturaOrden?.numero_autorizacion);
  const facturaAnulada = Boolean(facturaOrden && (facturaOrden.estado_sri === 'anulada' || facturaOrden.estado_sri === 'anulada_parcial'));
  const esFacturable = (orden.estado === 'entregada' || orden.estado === 'terminada') &&
    Number(orden.abono) >= Number(orden.total_orden) &&
    !tieneFactura;

  return (
    <div className="orden-detalle">
      {/* ═══ HEADER ═══ */}
      <div className="orden-detalle__header animar-entrada">
        <div className="orden-detalle__header-left">
          <button className="boton-secundario" onClick={() => navigate('/ordenes')}><ArrowLeft size={18} /> Volver</button>
          <div>
            <h2>{orden.numero_orden}</h2>
            <BadgeEstado estado={orden.equipos?.[0]?.estado || orden.estado} />
          </div>
        </div>
        <div className="orden-detalle__header-acciones">
          <button className="boton-secundario" onClick={() => descargarPdfOrden(Number(id))} title="Descargar PDF"><FileDown size={18} /> PDF</button>
          <button className="boton-secundario" onClick={enviarWhatsapp} title="Enviar por WhatsApp" style={{ color: '#25D366' }}><MessageCircle size={18} /> WhatsApp</button>
          <button className="boton-secundario" onClick={convertirNotaVenta} title="Nota de Venta" disabled={esCancelada} style={esCancelada ? {opacity: 0.5, cursor: 'not-allowed'} : {}}><Receipt size={18} /> Nota Venta</button>
          
{facturaAnulada ? (
              <Link to="/facturacion" className="btn-card-accion" title={facturaOrden.estado_sri === 'anulada_parcial'
                ? 'La factura fue anulada parcialmente con una nota de crédito'
                : 'La factura fue anulada con una nota de crédito'}
                style={{ color: '#7C3AED', borderColor: '#C4B5FD', backgroundColor: '#F5F3FF' }}>
                <Ban size={14} /> {facturaOrden.estado_sri === 'anulada_parcial' ? 'Facturada · Anulada Parcial' : 'Facturada · Anulada'}
              </Link>
            ) : facturaAutorizada ? (
              <Link to="/facturacion" className="btn-card-accion" title={`Autorización SRI: ${facturaOrden.numero_autorizacion}`} style={{ color: 'var(--color-exito)', borderColor: 'var(--color-exito)' }}>
                <FileCheck2 size={14} /> Facturada ✓
              </Link>
            ) : tieneFactura ? (
            <Link to="/facturacion" className="boton-secundario" style={{ color: 'var(--texto-secundario)' }}>
              <FileCheck2 size={18} /> Estado Factura
            </Link>
          ) : (
            <button
              className="boton-secundario"
              onClick={() => {
                if (porCancelar <= 0) generarFacturaSRI();
              }}
              title={porCancelar > 0 ? `Falta pagar $${porCancelar.toFixed(2)} para facturar` : 'Generar factura electrónica SRI'}
              style={{
                opacity: porCancelar > 0 ? 0.6 : 1,
                cursor: porCancelar > 0 ? 'not-allowed' : 'pointer',
                color: porCancelar <= 0 ? '#1976d2' : undefined,
                borderColor: porCancelar <= 0 ? '#90caf9' : undefined,
                backgroundColor: porCancelar <= 0 ? '#e3f2fd' : undefined
              }}
              disabled={porCancelar > 0}
            >
              <FileCheck2 size={18} /> Facturar
            </button>
          )}

          <button className="boton-primario" onClick={() => navigate(`/ordenes/${id}/editar`)} disabled={esCancelada} style={esCancelada ? {opacity: 0.5, cursor: 'not-allowed'} : {}}><Edit size={18} /> Editar</button>
          {(usuario?.rol === 'admin' || usuario?.rol === 'asistente') && !esCancelada && (
            <button className="boton-icono" onClick={borrarOrden} style={{ color: 'var(--color-error)' }} title="Cancelar orden (mantiene el correlativo)"><Ban size={18} /> Cancelar</button>
          )}
          {esCancelada && (
            <span className="boton-secundario" style={{ color: 'var(--texto-secundario)', borderStyle: 'dashed' }} disabled>
              <Ban size={18} /> Orden CANCELADA
            </span>
          )}
        </div>
      </div>

      {/* ═══ ERROR ═══ */}
      {error && <div className="dashboard__error animar-entrada"><p>⚠️ {error}</p></div>}

      {/* ═══ GRID DE TARJETAS ═══ */}
      <div className="orden-detalle__grid animar-entrada animar-retraso-2">

        {/* ─── TARJETA: CLIENTE (EDITABLE) ─── */}
        <div className="orden-detalle__card">
          <div className="orden-detalle__card-header">
            <h3><User size={18} /> Cliente</h3>
            <button className="btn-card-accion" onClick={abrirModalCliente} title="Editar cliente">
              <Pencil size={14} /> Editar
            </button>
          </div>
          {cliente && (
            <div className="orden-detalle__datos">
              <p><strong>{cliente.nombre} {cliente.apellido}</strong></p>
              <p>📞 {cliente.telefono}</p>
              {cliente.email && <p>📧 {cliente.email}</p>}
              {cliente.direccion && <p>📍 {cliente.direccion}</p>}
              {cliente.cedula_ruc && <p>🆔 {cliente.cedula_ruc}</p>}
            </div>
          )}
        </div>

        {/* ─── TARJETA: INFORMACIÓN ─── */}
        <div className="orden-detalle__card">
          <h3><Calendar size={18} /> Información</h3>
          <div className="orden-detalle__datos">
            <p>📅 Ingreso: {new Date(orden.fecha_ingreso).toLocaleDateString('es-EC')}</p>
            {orden.creado_por && <p>✍️ Creado por: <strong>{orden.creado_por}</strong></p>}
            {tecnico && <p>👨‍🔧 Técnico asignado: <strong>{tecnico.nombre} {tecnico.apellido}</strong></p>}
            <p><Shield size={14} /> Garantía: {orden.garantia_dias ? `${orden.garantia_dias} días` : 'Sin garantía'}</p>
          </div>
        </div>
      </div>

      {/* ═══ SECCIÓN FINANCIERA (ANCHO COMPLETO) ═══ */}
      <div className="orden-detalle__card--financiero animar-entrada animar-retraso-2">
        <div className="orden-detalle__card-header">
          <h3><DollarSign size={18} /> Datos Financieros</h3>
          <div className="orden-detalle__card-acciones">
            {/* ─── Botón de Facturar (SRI) ─── */}
{facturaAnulada ? (
            <Link to="/facturacion" className="boton-secundario" title={facturaOrden.estado_sri === 'anulada_parcial'
              ? 'La factura de esta orden fue anulada parcialmente con una nota de crédito'
              : 'La factura de esta orden fue anulada con una nota de crédito'}
              style={{ color: '#7C3AED', borderColor: '#C4B5FD', backgroundColor: '#F5F3FF' }}>
              <Ban size={18} /> {facturaOrden.estado_sri === 'anulada_parcial' ? 'Facturada · Anulada Parcial' : 'Facturada · Anulada'}
            </Link>
          ) : facturaAutorizada ? (
              <Link to="/facturacion" className="btn-card-accion" title={`Autorización SRI: ${facturaOrden.numero_autorizacion}`} style={{ color: 'var(--color-exito)', borderColor: 'var(--color-exito)' }}>
                <FileCheck2 size={14} /> Facturada ✓
              </Link>
            ) : tieneFactura ? (
              <Link to="/facturacion" className="btn-card-accion" style={{ color: 'var(--texto-secundario)' }}>
                <FileCheck2 size={14} /> Estado Factura
              </Link>
            ) : (
              <button
                className={`btn-card-accion ${porCancelar > 0 ? 'btn-card-accion--bloqueado' : 'btn-card-accion--facturar'}`}
                onClick={() => {
                  if (porCancelar <= 0) generarFacturaSRI();
                }}
                title={porCancelar > 0 ? `Falta pagar $${porCancelar.toFixed(2)} para facturar` : 'Generar factura electrónica SRI'}
                disabled={porCancelar > 0}
              >
                <FileCheck2 size={14} /> Facturar
              </button>
            )}

            <button className="btn-card-accion" onClick={abrirModalTotal} title="Editar total">
              <Pencil size={14} /> Total
            </button>
            <button className="btn-card-accion btn-card-accion--pago" onClick={() => {
              const autoEquipoId = orden.equipos?.length === 1 ? String(orden.equipos[0].id) : '';
              setFormPago({ monto: '', metodo_pago: 'efectivo', equipo_id: autoEquipoId });
              setModalPago(true);
            }} title="Registrar pago">
              <Plus size={14} /> Pago
            </button>
          </div>
        </div>

        {/* Barra de resumen */}
        <div className="financiero-resumen-bar">
          <div className="financiero-resumen-item">
            <span>Total de la Orden</span>
            <strong>${Number(orden.total_orden).toFixed(2)}</strong>
          </div>
          <div className="financiero-resumen-item financiero-resumen-item--pagado">
            <span>Total Abonado</span>
            <strong style={{ color: '#2e7d32' }}>${Number(orden.abono).toFixed(2)}</strong>
          </div>
          <div className={`financiero-resumen-item ${porCancelar > 0 ? 'financiero-resumen-item--saldo' : 'financiero-resumen-item--pagado'}`}>
            <span>Por Cancelar</span>
            <strong style={{ color: porCancelar > 0 ? 'var(--color-error)' : '#2e7d32' }}>
              ${porCancelar.toFixed(2)}
            </strong>
          </div>
        </div>

        {/* Grid: Equipos + Historial de Pagos */}
        <div className="financiero-contenido-grid">
          {/* Columna: Costo por equipo */}
          {orden.equipos?.length > 0 && (
            <div className="financiero-columna">
              <h4><ListChecks size={14} /> Costo por Equipo</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {orden.equipos.map((eq, idx) => {
                  const eqCosto = Number(eq.costo) || 0;
                  const pagado = calcularPagadoEquipo(eq.id, orden.equipos, orden.abono);
                  const saldo = eqCosto - pagado;
                  return (
                    <div key={eq.id || idx} className="desglose-equipo-item">
                      <span className="desglose-equipo-item__nombre">
                        #{idx + 1} {eq.marca} {eq.modelo}
                        <span className="tipo">
                          ({tipoEquipoTexto[eq.tipo_equipo]?.split(' ')[1] || eq.tipo_equipo})
                        </span>
                      </span>
                      <span className="desglose-equipo-item__costo">${eqCosto.toFixed(2)}</span>
                      <span className="desglose-equipo-item__pagado" style={{ color: pagado > 0 ? 'var(--color-exito)' : 'var(--texto-secundario)' }}>
                        Pagado: ${pagado.toFixed(2)}
                      </span>
                      <span className="desglose-equipo-item__saldo" style={{ color: saldo > 0 ? 'var(--color-error)' : 'var(--color-exito)' }}>
                        {saldo > 0 ? `Saldo: $${saldo.toFixed(2)}` : '✓ Pagado'}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Columna: Historial de pagos */}
          <div className="financiero-columna">
            <h4><History size={14} /> Historial de Pagos</h4>
            {pagos.length === 0 ? (
              <p style={{ fontSize: '13px', color: 'var(--texto-secundario)', margin: 0 }}>
                No hay pagos registrados aún.
              </p>
            ) : (
              <div className="historial-pagos-lista">
                {pagos.map(pago => (
                  <div key={pago.id} className="historial-pago-item">
                    <div className="historial-pago-left">
                      <span className="historial-pago-monto">+${Number(pago.monto).toFixed(2)}</span>
                      <span className="historial-pago-metodo">{pago.metodo_pago}</span>
                      {pago.equipo_marca && (
                        <span className="historial-pago-equipo" style={{ fontSize: '11px', color: 'var(--texto-secundario)' }}>
                          → {pago.equipo_marca} {pago.equipo_modelo || ''}
                        </span>
                      )}
                    </div>
                    <span className="historial-pago-fecha">
                      {new Date(pago.created_at).toLocaleDateString('es-EC', {
                        day: 'numeric', month: 'short',
                        hour: '2-digit', minute: '2-digit'
                      })}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ═══ EQUIPOS ═══ */}
      <div className="orden-detalle__equipos animar-entrada animar-retraso-3" style={{ marginTop: '30px' }}>
        <h3 style={{ marginBottom: '16px', color: 'var(--color-primario)', display: 'flex', alignItems: 'center' }}>
          <Wrench size={20} style={{ marginRight: '8px' }} /> Equipos ({orden.equipos?.length || 0})
        </h3>
        {orden.equipos?.map((equipo, idx) => (
          <div key={equipo.id} className="equipo-detalle-card" style={{
            border: '1px solid var(--borde-color)', padding: '24px',
            borderRadius: '12px', marginBottom: '24px',
            backgroundColor: 'var(--fondo-principal)', boxShadow: '0 2px 8px rgba(0,0,0,0.02)'
          }}>
            <div style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              marginBottom: '16px', flexWrap: 'wrap', gap: '16px'
            }}>
              <h4 style={{ margin: 0, fontSize: '18px' }}>
                {tipoEquipoTexto[equipo.tipo_equipo] || equipo.tipo_equipo} {equipo.marca} {equipo.modelo}
              </h4>
              <BadgeEstado estado={equipo.estado} />
            </div>

            <div className="orden-detalle__estados" style={{ marginBottom: '20px' }}>
              {esCancelada ? (
                <span className="orden-detalle__estados-label" style={{ color: 'var(--texto-secundario)', fontWeight: 600 }}>
                  ⛔ Esta orden fue CANCELADA. No se pueden cambiar los estados.
                </span>
              ) : (
              <span className="orden-detalle__estados-label">Cambiar estado del equipo:</span>
              )}
              {(() => {
                // Verificar si la ORDEN está completamente pagada
                // Fuente de verdad: abono vs total_orden
                const totalOrden = Number(orden.total_orden) || 0;
                const abonoOrden = Number(orden.abono) || 0;
                const ordenPagada = totalOrden <= 0 || abonoOrden >= totalOrden;
                const saldoOrden = Math.max(0, totalOrden - abonoOrden);

                return (
                  <>
                    {!esCancelada && (
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      {ESTADOS.map(est => {
                        const esEntregado = est === 'entregada';
                        // Solo "Entregado" se bloquea cuando no está pagado
                        const bloqueado = esEntregado && !ordenPagada;
                        const tooltip = bloqueado
                          ? `Falta pagar $${saldoOrden.toFixed(2)} para entregar`
                          : ESTADOS_MAP[est];
                        return (
                          <button key={est}
                            onClick={() => !bloqueado && cambiarEstadoEquipo(equipo.id, est)}
                            disabled={bloqueado}
                            className={`orden-detalle__estado-btn ${equipo.estado === est ? 'orden-detalle__estado-btn--activo' : ''} ${bloqueado ? 'orden-detalle__estado-btn--bloqueado' : ''}`}
                            style={{ padding: '6px 12px', fontSize: '12px' }}
                            title={tooltip}
                          >
                            {bloqueado && '🔒 '}{ESTADOS_MAP[est]}
                          </button>
                        );
                      })}
                    </div>
                    )}
                    {!esCancelada && !ordenPagada && (
                      <p style={{ fontSize: '11px', color: 'var(--color-error)', marginTop: '8px', marginBottom: 0 }}>
                        ⚠️ Para entregar los equipos falta pagar <strong>${saldoOrden.toFixed(2)}</strong> (Pagado: ${abonoOrden.toFixed(2)} de ${totalOrden.toFixed(2)})
                      </p>
                    )}
                  </>
                );
              })()}
            </div>

            <div className="orden-detalle__datos" style={{
              display: 'flex', gap: '24px', marginBottom: '24px', flexWrap: 'wrap',
              fontSize: '14px', backgroundColor: 'var(--fondo-secundario)',
              padding: '12px', borderRadius: '8px'
            }}>
              <div>
                <strong>Accesorios recibidos:</strong>
                <span style={{ color: 'var(--texto-secundario)' }}>
                  {[equipo.cable && 'Cable', equipo.cargador && 'Cargador'].filter(Boolean).join(', ') || 'Ninguno'}
                </span>
              </div>
              {equipo.contrasena &&
                <div><strong>Contraseña:</strong>
                  <span style={{ color: 'var(--texto-secundario)' }}>{equipo.contrasena}</span>
                </div>}
            </div>

            <div className="orden-detalle__servicio" style={{ marginTop: 0 }}>
              {equipo.descripcion_problema && (
                <div className="servicio-bloque" style={{ padding: '16px', backgroundColor: '#fff', border: '1px solid #eee' }}>
                  <h4>Problema Reportado</h4><p>{equipo.descripcion_problema}</p>
                </div>
              )}
              {equipo.diagnostico && (
                <div className="servicio-bloque" style={{ padding: '16px', backgroundColor: '#fff', border: '1px solid #eee' }}>
                  <h4>Diagnóstico Técnico</h4><p>{equipo.diagnostico}</p>
                </div>
              )}
              {equipo.trabajo_a_realizar && (
                <div className="servicio-bloque" style={{ padding: '16px', backgroundColor: '#fff', border: '1px solid #eee' }}>
                  <h4>Trabajo a Realizar</h4><p>{equipo.trabajo_a_realizar}</p>
                </div>
              )}
              {equipo.repuesto_a_instalar && (
                <div className="servicio-bloque" style={{ padding: '16px', backgroundColor: '#fff', border: '1px solid #eee' }}>
                  <h4>Repuestos</h4><p>{equipo.repuesto_a_instalar}</p>
                </div>
              )}
            </div>

            {/* ═══ FORMULARIO DE DIAGNÓSTICO DEL TÉCNICO ═══ */}
            <FormularioDiagnostico equipo={equipo} />
          </div>
        ))}
      </div>

      {/* ═══ SECCIÓN: NOTAS INTERNAS CON HISTORIAL ═══ */}
      <div className="orden-detalle__notas-seccion animar-entrada animar-retraso-3">
        <h3 style={{
          marginBottom: '16px', color: 'var(--color-primario)',
          display: 'flex', alignItems: 'center'
        }}>
          <MessageSquare size={20} style={{ marginRight: '8px' }} /> Notas Internas
          {notas.length > 0 && <span className="notas-contador">{notas.length}</span>}
        </h3>

        {/* Formulario para agregar nota */}
        <div className="notas-formulario">
          <div className="notas-form-row">
            <div className="notas-input-group">
              <label className="campo-label">Agregar nota:</label>
              <textarea
                className="campo-texto"
                rows={2}
                placeholder="Escribe una nota interna sobre esta orden..."
                value={notaTexto}
                onChange={e => setNotaTexto(e.target.value)}
              />
            </div>
          </div>
          <div className="notas-form-row notas-form-row--bottom">
            <div className="notas-autor-group">
              <label className="campo-label">Escrito por:</label>
              <select
                className="campo-texto"
                value={notaAutor}
                onChange={e => setNotaAutor(e.target.value)}
              >
                <option value="">Seleccionar...</option>
                {tecnicos.map(t => (
                  <option key={t.id} value={`${t.nombre} ${t.apellido}`}>
                    {t.nombre} {t.apellido}
                  </option>
                ))}
              </select>
            </div>
            <button
              className="boton-primario"
              onClick={guardarNota}
              disabled={guardando || !notaTexto.trim() || !notaAutor.trim()}
            >
              <Plus size={16} /> Agregar Nota
            </button>
          </div>
        </div>

        {/* Timeline de notas */}
        {notas.length === 0 ? (
          <div className="notas-vacio">
            <MessageSquare size={24} />
            <p>No hay notas internas aún. Agrega la primera nota arriba.</p>
          </div>
        ) : (
          <div className="notas-timeline">
            {notas.map(nota => (
              <div key={nota.id} className="nota-item animar-entrada">
                <div className="nota-avatar">
                  <span>{nota.creado_por.charAt(0).toUpperCase()}</span>
                </div>
                <div className="nota-contenido">
                  <div className="nota-header">
                    <strong className="nota-autor">{nota.creado_por}</strong>
                    <span className="nota-fecha">
                      {new Date(nota.created_at).toLocaleDateString('es-EC', {
                        day: 'numeric', month: 'long', year: 'numeric',
                        hour: '2-digit', minute: '2-digit'
                      })}
                    </span>
                  </div>
                  <p className="nota-texto">{nota.contenido}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ════════════════════════════════════════════ */}
      {/* MODAL: Editar Cliente */}
      {/* ════════════════════════════════════════════ */}
      {modalCliente && (
        <div className="modal-overlay" onClick={() => setModalCliente(false)}>
          <div className="modal-contenido animar-entrada" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3><User size={20} /> Editar Cliente</h3>
              <button className="boton-icono" onClick={() => setModalCliente(false)}><X size={20} /></button>
            </div>
            <div className="modal-cuerpo">
              <div className="orden-form__grid-2">
                <div className="campo-grupo">
                  <label className="campo-label">Nombre</label>
                  <input type="text" className="campo-texto"
                    value={formCliente.nombre}
                    onChange={e => setFormCliente(p => ({ ...p, nombre: e.target.value }))} />
                </div>
                <div className="campo-grupo">
                  <label className="campo-label">Apellido</label>
                  <input type="text" className="campo-texto"
                    value={formCliente.apellido}
                    onChange={e => setFormCliente(p => ({ ...p, apellido: e.target.value }))} />
                </div>
              </div>
              <div className="campo-grupo">
                <label className="campo-label">Teléfono</label>
                <input type="text" className="campo-texto"
                  value={formCliente.telefono}
                  onChange={e => setFormCliente(p => ({ ...p, telefono: e.target.value }))} />
              </div>
              <div className="campo-grupo">
                <label className="campo-label">Email</label>
                <input type="email" className="campo-texto"
                  value={formCliente.email}
                  onChange={e => setFormCliente(p => ({ ...p, email: e.target.value }))} />
              </div>
              <div className="campo-grupo">
                <label className="campo-label">Dirección</label>
                <input type="text" className="campo-texto"
                  value={formCliente.direccion}
                  onChange={e => setFormCliente(p => ({ ...p, direccion: e.target.value }))} />
              </div>
              <div className="campo-grupo">
                <label className="campo-label">Cédula / RUC</label>
                <input type="text" className="campo-texto"
                  value={formCliente.cedula_ruc}
                  onChange={e => setFormCliente(p => ({ ...p, cedula_ruc: e.target.value }))} />
              </div>
            </div>
            <div className="modal-footer">
              <button className="boton-secundario" onClick={() => setModalCliente(false)}>Cancelar</button>
              <button className="boton-primario" onClick={guardarCliente} disabled={guardando}>
                <Save size={16} /> {guardando ? 'Guardando...' : 'Guardar Cambios'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ════════════════════════════════════════════ */}
      {/* MODAL: Editar Total / Costos por Equipo */}
      {/* ════════════════════════════════════════════ */}
      {modalTotal && (
        <div className="modal-overlay" onClick={() => setModalTotal(false)}>
          <div className="modal-contenido modal-contenido--md animar-entrada" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3><DollarSign size={20} /> Costos por Equipo</h3>
              <button className="boton-icono" onClick={() => setModalTotal(false)}><X size={20} /></button>
            </div>
            <div className="modal-cuerpo">
              <p className="modal-ayuda" style={{ marginBottom: '16px' }}>
                💡 Ajusta el costo de cada equipo. El total se calcula automáticamente.
              </p>
              {formTotalEquipos?.map((eq, idx) => (
                <div key={eq.id || idx} style={{
                  display: 'flex', gap: '12px', alignItems: 'center',
                  padding: '10px 12px', marginBottom: '8px',
                  backgroundColor: 'var(--fondo-secundario)', borderRadius: '8px'
                }}>
                  <span style={{ fontWeight: 600, minWidth: '40px', fontSize: '14px' }}>
                    #{idx + 1}
                  </span>
                  <span style={{ flex: 1, fontSize: '13px', color: 'var(--texto-secundario)' }}>
                    {eq.marca} {eq.modelo || ''}
                  </span>
                  <div className="monto-control" style={{ width: '180px', flexShrink: 0 }}>
                    <button type="button" className="monto-btn monto-btn--menos" onClick={() => {
                      const nuevos = [...formTotalEquipos];
                      const actual = Number(nuevos[idx].costo) || 0;
                      nuevos[idx] = { ...nuevos[idx], costo: Math.max(0, actual - 5).toFixed(2) };
                      setFormTotalEquipos(nuevos);
                    }}>−</button>
                    <input type="text" className="monto-input"
                      value={eq.costo || '0.00'}
                      onChange={e => {
                        const val = e.target.value.replace(/[^0-9.]/g, '');
                        const nuevos = [...formTotalEquipos];
                        nuevos[idx] = { ...nuevos[idx], costo: val };
                        setFormTotalEquipos(nuevos);
                      }}
                      onBlur={() => {
                        const nuevos = [...formTotalEquipos];
                        nuevos[idx] = { ...nuevos[idx], costo: (Number(nuevos[idx].costo) || 0).toFixed(2) };
                        setFormTotalEquipos(nuevos);
                      }}
                    />
                    <button type="button" className="monto-btn monto-btn--mas" onClick={() => {
                      const nuevos = [...formTotalEquipos];
                      const actual = Number(nuevos[idx].costo) || 0;
                      nuevos[idx] = { ...nuevos[idx], costo: (actual + 5).toFixed(2) };
                      setFormTotalEquipos(nuevos);
                    }}>+</button>
                  </div>
                </div>
              ))}
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '12px 16px', marginTop: '8px',
                backgroundColor: 'var(--color-primario-claro)', borderRadius: '8px',
                fontWeight: 800, fontSize: '16px'
              }}>
                <span>Total calculado:</span>
                <span style={{ color: 'var(--color-primario)' }}>
                  ${formTotalEquipos?.reduce((s, e) => s + (Number(e.costo) || 0), 0).toFixed(2) || '0.00'}
                </span>
              </div>
              <p className="modal-ayuda" style={{ marginTop: '16px' }}>
                💡 El abono actual de <strong>${Number(orden.abono).toFixed(2)}</strong> no se modifica.
                Para registrar nuevos pagos usa "Registrar Pago".
              </p>
            </div>
            <div className="modal-footer">
              <button className="boton-secundario" onClick={() => setModalTotal(false)}>Cancelar</button>
              <button className="boton-primario" onClick={guardarTotal} disabled={guardando}>
                <Save size={16} /> {guardando ? 'Guardando...' : 'Actualizar Costos'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ════════════════════════════════════════════ */}
      {/* MODAL: Registrar Pago */}
      {/* ════════════════════════════════════════════ */}
      {modalPago && (
        <div className="modal-overlay" onClick={() => setModalPago(false)}>
          <div className="modal-contenido modal-contenido--sm animar-entrada" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3><CreditCard size={20} /> Registrar Pago</h3>
              <button className="boton-icono" onClick={() => setModalPago(false)}><X size={20} /></button>
            </div>
            <div className="modal-cuerpo">
              <div className="campo-grupo">
                <label className="campo-label">Monto del pago ($)</label>
                <div className="monto-control">
                  <button type="button" className="monto-btn monto-btn--menos" onClick={() => {
                    const actual = Number(formPago.monto) || 0;
                    setFormPago(p => ({ ...p, monto: Math.max(0, actual - 5).toFixed(2) }));
                  }}>−</button>
                  <input type="text" className="monto-input"
                    value={formPago.monto || '0.00'}
                    onChange={e => {
                      const val = e.target.value.replace(/[^0-9.]/g, '');
                      setFormPago(p => ({ ...p, monto: val }));
                    }}
                    onBlur={() => {
                      let val = Number(formPago.monto) || 0;
                      // No permitir que el monto exceda el saldo pendiente
                      if (val > saldoPendiente) val = saldoPendiente;
                      setFormPago(p => ({ ...p, monto: val.toFixed(2) }));
                    }}
                  />
                  <button type="button" className="monto-btn monto-btn--mas" onClick={() => {
                    const actual = Number(formPago.monto) || 0;
                    // No permitir que el monto exceda el saldo pendiente
                    const nuevoMonto = Math.min(actual + 5, saldoPendiente);
                    setFormPago(p => ({ ...p, monto: nuevoMonto.toFixed(2) }));
                  }}>+</button>
                </div>
                {saldoPendiente <= 0 && (
                  <p style={{ color: 'var(--color-exito)', fontSize: '12px', marginTop: '6px', fontWeight: 600 }}>
                    ✅ Esta orden ya está completamente pagada.
                  </p>
                )}
              </div>
              <div className="campo-grupo">
                <label className="campo-label">Método de pago</label>
                <select className="campo-texto"
                  value={formPago.metodo_pago}
                  onChange={e => setFormPago(p => ({ ...p, metodo_pago: e.target.value }))}>
                  {METODOS_PAGO.map(m => <option key={m} value={m}>{m.charAt(0).toUpperCase() + m.slice(1)}</option>)}
                </select>
              </div>
              <div className="campo-grupo">
                <label className="campo-label">Asignar a equipo (opcional)</label>
                <select className="campo-texto"
                  value={formPago.equipo_id}
                  onChange={e => setFormPago(p => ({ ...p, equipo_id: e.target.value }))}>
                  <option value="">— Pago general (sin asignar) —</option>
                  {orden.equipos?.map((eq, idx) => (
                    <option key={eq.id} value={eq.id}>
                      #{idx + 1} {eq.marca} {eq.modelo || ''} — ${Number(eq.costo || 0).toFixed(2)}
                    </option>
                  ))}
                </select>
              </div>
              <div className="modal-resumen-pago">
                <div className="resumen-pago-item">
                  <span>Total de la orden:</span>
                  <strong>${Number(orden.total_orden).toFixed(2)}</strong>
                </div>
                <div className="resumen-pago-item">
                  <span>Abono actual:</span>
                  <strong>${Number(orden.abono).toFixed(2)}</strong>
                </div>
                <div className="resumen-pago-item" style={{ color: saldoPendiente > 0 ? 'var(--color-error)' : 'var(--color-exito)', fontWeight: 700 }}>
                  <span>Saldo pendiente:</span>
                  <strong>${saldoPendiente.toFixed(2)}</strong>
                </div>
                {formPago.monto && Number(formPago.monto) > 0 && (
                  <div className="resumen-pago-item resumen-pago-item--nuevo">
                    <span>Nuevo abono:</span>
                    <strong>${(Number(orden.abono) + Number(formPago.monto)).toFixed(2)}</strong>
                  </div>
                )}
                {formPago.monto && Number(formPago.monto) > saldoPendiente && (
                  <p style={{ color: 'var(--color-error)', fontSize: '12px', marginTop: '8px', lineHeight: 1.4 }}>
                    ⚠️ El monto excede el saldo pendiente. Para agregar un abono mayor, primero edita el monto total de la orden.
                  </p>
                )}
              </div>
            </div>
            <div className="modal-footer">
              <button className="boton-secundario" onClick={() => setModalPago(false)}>Cancelar</button>
              <button className="boton-primario" onClick={guardarPago}
                disabled={guardando || !formPago.monto || Number(formPago.monto) <= 0 || Number(formPago.monto) > saldoPendiente}>
                <Plus size={16} /> {guardando ? 'Registrando...' : 'Registrar Pago'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
