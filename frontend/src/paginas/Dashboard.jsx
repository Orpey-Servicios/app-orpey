/**
 * DASHBOARD - Pantalla principal con estadísticas
 * 
 * Muestra un resumen visual del estado del servicio técnico:
 * - Órdenes activas
 * - Equipos por tipo (PC, laptop, impresora, teléfono)
 * - Cotizaciones y órdenes cerradas
 * 
 * useEffect: ejecuta código cuando el componente se "monta" (aparece en pantalla)
 * useState: crea variables que cuando cambian, React re-renderiza el componente
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ClipboardList, Monitor, Laptop, Printer, Smartphone,
  FileText, CheckCircle, TrendingUp, AlertCircle, Plus,
  Wallet, FileCheck2, Receipt, ClipboardCheck,
} from 'lucide-react';
import { obtenerDashboard, obtenerOrdenes, obtenerResumenCaja } from '../api/orpey-api';
import BadgeEstado from '../componentes/BadgeEstado';
import './Dashboard.css';

export default function Dashboard() {
  // useState crea una variable de estado y su función para actualizarla
  // [valor, setValor] = useState(valorInicial)
  const [stats, setStats] = useState(null);       // Estadísticas del dashboard
  const [ordenes, setOrdenes] = useState([]);     // Últimas órdenes
  const [resumenCaja, setResumenCaja] = useState(null); // Resumen financiero del día
  const [cargando, setCargando] = useState(true); // ¿Está cargando?
  const [error, setError] = useState(null);       // Mensaje de error

  const navigate = useNavigate(); // Para navegar a otras páginas programáticamente

  // Carga datos al montar y cada vez que la pestaña recupera el foco
  useEffect(() => {
    cargarDatos();
    const onFocus = () => cargarDatos();
    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, []);

  // Función que carga los datos del backend
  async function cargarDatos() {
    try {
      setCargando(true);
      setError(null);
      // Promise.all ejecuta las peticiones AL MISMO TIEMPO (más rápido).
      // El resumen de caja es defensivo: si falla, no rompe el dashboard.
      const [dashData, ordenesData] = await Promise.all([
        obtenerDashboard(),
        obtenerOrdenes()
      ]);
      setStats(dashData);
      setOrdenes(ordenesData.slice(0, 5)); // Solo las 5 más recientes
      try {
        const resumen = await obtenerResumenCaja();
        setResumenCaja(resumen || null);
      } catch (e) {
        setResumenCaja(null);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setCargando(false);
    }
  }

  // Tarjetas de estadísticas con sus datos
  const tarjetas = stats ? [
    { titulo: 'Ordenes Activas',   valor: stats.ordenes_activas,        icono: ClipboardList, color: '#FBC305', fondo: '#FFF8DC' },
    { titulo: 'Ordenes Cerradas',  valor: stats.ordenes_cerradas,        icono: CheckCircle,   color: '#6B7280', fondo: '#F3F4F6' },
    { titulo: 'PCs',               valor: stats.pcs_en_reparacion,       icono: Monitor,       color: '#3B82F6', fondo: '#EFF6FF' },
    { titulo: 'Laptops',           valor: stats.laptops_en_reparacion,   icono: Laptop,        color: '#8B5CF6', fondo: '#F5F3FF' },
    { titulo: 'Impresoras',        valor: stats.impresoras_en_reparacion,icono: Printer,       color: '#F97316', fondo: '#FFF7ED' },
    { titulo: 'Telefonos',         valor: stats.telefonos_en_reparacion, icono: Smartphone,    color: '#22C55E', fondo: '#F0FDF4' },
    { titulo: 'Cotizaciones',      valor: stats.cotizaciones_abiertas,   icono: FileText,      color: '#06B6D4', fondo: '#ECFEFF' },
  ] : [];

  // TIPO_EQUIPO legible
  const tipoEquipoTexto = {
    pc_escritorio: 'PC', laptop: 'Laptop', impresora: 'Impresora', telefono: 'Teléfono', otro: 'Otro'
  };

  // ── Resumen financiero del día (defensivo: null → $0.00 / 0) ──
  const resumen = resumenCaja || {};
  const cajaAbiertaHoy = !!resumen.caja_abierta;
  const moneda = (v) => '$' + Number(v || 0).toFixed(2);

  const tarjetasFinancieras = [
    {
      titulo: 'Caja',
      valor: cajaAbiertaHoy ? moneda(resumen.esperado_hoy) : moneda(resumen.ingresos_hoy),
      icono: Wallet, color: '#22C55E', fondo: '#F0FDF4',
      subtexto: cajaAbiertaHoy
        ? `Caja abierta · Inicial ${moneda(resumen.caja_abierta?.monto_inicial)}`
        : (resumen.fecha ? 'Caja cerrada hoy' : 'Sin datos de caja hoy'),
    },
    {
      titulo: 'Facturado hoy',
      valor: moneda(resumen.facturado_hoy),
      icono: FileCheck2, color: '#3B82F6', fondo: '#EFF6FF',
      subtexto: 'Ventas facturadas del día',
    },
    {
      titulo: 'Notas de venta hoy',
      valor: moneda(resumen.notas_venta_hoy),
      icono: Receipt, color: '#F97316', fondo: '#FFF7ED',
      subtexto: 'S/I de ventas del día',
    },
    {
      titulo: 'Ingresos (caja) hoy',
      valor: moneda(resumen.ingresos_hoy),
      icono: TrendingUp, color: '#06B6D4', fondo: '#ECFEFF',
      subtexto: `Egresos: ${moneda(resumen.egresos_hoy)}`,
    },
    {
      titulo: 'Órdenes cerradas hoy',
      valor: Number(resumen.ordenes_cerradas_hoy || 0),
      icono: ClipboardCheck, color: '#6B7280', fondo: '#F3F4F6',
      subtexto: 'Servicios entregados',
    },
  ];

  // Pantalla de carga
  if (cargando) {
    return (
      <div className="dashboard__cargando">
        <div className="spinner" />
        <p>Cargando estadísticas...</p>
      </div>
    );
  }

  return (
    <div className="dashboard">
      {/* Mensaje de error si el backend no está disponible */}
      {error && (
        <div className="dashboard__error animar-entrada">
          <AlertCircle size={20} />
          <div>
            <strong>No se pudo conectar con el servidor</strong>
            <p>{error}</p>
          </div>
          <button className="boton-secundario" onClick={cargarDatos}>Reintentar</button>
        </div>
      )}

      {/* Botón rápido para crear orden */}
      <div className="dashboard__acciones animar-entrada">
        <button className="boton-primario" onClick={() => navigate('/ordenes/nueva')} id="btn-nueva-orden-rapida">
          <Plus size={18} /> Nueva Orden de Servicio
        </button>
      </div>

      {/* Tarjetas de estadísticas */}
      <div className="dashboard__tarjetas">
        {tarjetas.map((tarjeta, index) => {
          const Icono = tarjeta.icono;
          return (
            <div
              key={tarjeta.titulo}
              className={`tarjeta-stat animar-entrada animar-retraso-${index + 1}`}
            >
              <div className="tarjeta-stat__icono" style={{ background: tarjeta.fondo, color: tarjeta.color }}>
                <Icono size={22} />
              </div>
              <div className="tarjeta-stat__info">
                <span className="tarjeta-stat__valor">{tarjeta.valor}</span>
                <span className="tarjeta-stat__titulo">{tarjeta.titulo}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Resumen financiero del día */}
      <div className="dashboard__financiero-header animar-entrada">
        <h2><Wallet size={20} /> Resumen Financiero</h2>
      </div>
      <div className="dashboard__financiero">
        {tarjetasFinancieras.map((tarjeta, index) => {
          const Icono = tarjeta.icono;
          return (
            <div
              key={tarjeta.titulo}
              className={`tarjeta-stat animar-entrada animar-retraso-${index + 1}`}
            >
              <div className="tarjeta-stat__icono" style={{ background: tarjeta.fondo, color: tarjeta.color }}>
                <Icono size={22} />
              </div>
              <div className="tarjeta-stat__info">
                <span className="tarjeta-stat__valor">{tarjeta.valor}</span>
                <span className="tarjeta-stat__titulo">{tarjeta.titulo}</span>
                {tarjeta.subtexto && <span className="tarjeta-stat__subtexto">{tarjeta.subtexto}</span>}
              </div>
            </div>
          );
        })}
      </div>

      {/* Tabla de órdenes recientes */}
      <div className="dashboard__recientes animar-entrada animar-retraso-8">
        <div className="dashboard__recientes-header">
          <h2><TrendingUp size={20} /> Ordenes Recientes</h2>
          <button className="boton-secundario" onClick={() => navigate('/ordenes')}>Ver todas</button>
        </div>
        {ordenes.length === 0 ? (
          <div className="dashboard__vacio">
            <ClipboardList size={40} strokeWidth={1.5} />
            <p>No hay órdenes registradas todavía</p>
            <button className="boton-primario" onClick={() => navigate('/ordenes/nueva')}>
              <Plus size={16} /> Crear primera orden
            </button>
          </div>
        ) : (
          <table className="tabla">
            <thead>
              <tr>
                <th>N° Orden</th>
                <th>Cliente</th>
                <th>Equipo</th>
                <th>Marca / Modelo</th>
                <th>Estado</th>
                <th>Total</th>
                <th>Abono</th>
                <th>Por Cancelar</th>
                <th>Fecha</th>
              </tr>
            </thead>
            <tbody>
              {ordenes.map((orden) => {
                const porCancelar = Number(orden.total_orden) - Number(orden.abono || 0);
                return (
                  <tr key={orden.id} onClick={() => navigate(`/ordenes/${orden.id}`)} className="tabla__fila-click">
                    <td><strong>{orden.numero_orden}</strong></td>
                    <td>{orden.cliente ? `${orden.cliente.nombre} ${orden.cliente.apellido}` : '—'}</td>
                    <td>{orden.equipos?.map(e => tipoEquipoTexto[e.tipo_equipo] || e.tipo_equipo).join(', ') || '—'}</td>
                    <td>{orden.equipos?.map(e => [e.marca, e.modelo].filter(Boolean).join(' ')).filter(Boolean).join(', ') || '—'}</td>
                    <td>
                      <div style={{display: 'flex', flexDirection: 'column', gap: '4px'}}>
                        {orden.equipos?.length > 0 
                          ? orden.equipos.map((e, idx) => <BadgeEstado key={idx} estado={e.estado} />)
                          : <BadgeEstado estado={orden.estado} />
                        }
                      </div>
                    </td>
                    <td>${Number(orden.total_orden).toFixed(2)}</td>
                    <td>${Number(orden.abono || 0).toFixed(2)}</td>
                    <td className={porCancelar > 0 ? 'texto-pendiente' : ''}>${porCancelar.toFixed(2)}</td>
                    <td>{new Date(orden.fecha_ingreso).toLocaleDateString('es-EC')}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
