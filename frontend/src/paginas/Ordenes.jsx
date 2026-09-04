/**
 * ÓRDENES DE SERVICIO - Listado principal
 * 
 * Muestra todas las órdenes con:
 * - Filtros por estado y tipo de equipo
 * - Barra de búsqueda
 * - Tabla con datos de cada orden
 * - Botón para crear nueva orden
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Filter, Search, ClipboardList } from 'lucide-react';
import { obtenerOrdenes } from '../api/orpey-api';
import BadgeEstado from '../componentes/BadgeEstado';
import './Ordenes.css';

// Opciones de filtro de estado
const ESTADOS = [
  { valor: '', etiqueta: 'Todos los estados' },
  { valor: 'revision', etiqueta: 'Revisión' },
  { valor: 'en_reparacion', etiqueta: 'En Reparación' },
  { valor: 'esperando_repuesto', etiqueta: 'Esperando Repuesto' },
  { valor: 'terminada', etiqueta: 'Reparado' },
  { valor: 'entregada', etiqueta: 'Entregado' },
  { valor: 'no_hubo_solucion', etiqueta: 'No Hubo Solución' },
  { valor: 'cancelada', etiqueta: 'Cancelada' },
];

const TIPOS_EQUIPO = [
  { valor: '', etiqueta: 'Todos los equipos' },
  { valor: 'pc_escritorio', etiqueta: 'PC Escritorio' },
  { valor: 'laptop', etiqueta: 'Laptop' },
  { valor: 'impresora', etiqueta: 'Impresora' },
  { valor: 'telefono', etiqueta: 'Teléfono' },
  { valor: 'otro', etiqueta: 'Otro' },
];

const tipoEquipoTexto = {
  pc_escritorio: 'PC', laptop: 'Laptop', impresora: 'Impresora', telefono: 'Teléfono', otro: 'Otro'
};

export default function Ordenes() {
  const [ordenes, setOrdenes] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [filtroEstado, setFiltroEstado] = useState('');
  const [filtroTipo, setFiltroTipo] = useState('');
  const [busqueda, setBusqueda] = useState('');
  const navigate = useNavigate();

  // Cargar órdenes cada vez que cambien los filtros
  useEffect(() => {
    cargarOrdenes();
  }, [filtroEstado, filtroTipo]);

  async function cargarOrdenes() {
    try {
      setCargando(true);
      const filtros = {};
      if (filtroEstado) filtros.estado = filtroEstado;
      if (filtroTipo) filtros.tipo_equipo = filtroTipo;
      const data = await obtenerOrdenes(filtros);
      setOrdenes(data);
    } catch (err) {
      console.error('Error cargando órdenes:', err);
    } finally {
      setCargando(false);
    }
  }

  // Filtrar por búsqueda local (número de orden o marca)
  const ordenesFiltradas = ordenes.filter(o => {
    if (!busqueda) return true;
    const texto = busqueda.toLowerCase();
    return (
      (o.numero_orden || '').toLowerCase().includes(texto) ||
      (o.equipos?.some(e => (e.marca || '').toLowerCase().includes(texto) || (e.modelo || '').toLowerCase().includes(texto))) ||
      (o.cliente?.nombre || '').toLowerCase().includes(texto) ||
      (o.cliente?.apellido || '').toLowerCase().includes(texto)
    );
  });

  return (
    <div className="ordenes-pagina">
      {/* Barra de acciones superior */}
      <div className="ordenes-pagina__acciones animar-entrada">
        <div className="ordenes-pagina__filtros">
          {/* Buscador */}
          <div className="filtro-buscador">
            <Search size={16} className="filtro-buscador__icono" />
            <input
              type="text"
              placeholder="Buscar por N° orden, cliente, marca..."
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              className="campo-texto filtro-buscador__input"
              id="buscar-ordenes"
            />
          </div>
          {/* Filtro por estado */}
          <select value={filtroEstado} onChange={(e) => setFiltroEstado(e.target.value)} className="campo-texto filtro-select" id="filtro-estado">
            {ESTADOS.map(e => <option key={e.valor} value={e.valor}>{e.etiqueta}</option>)}
          </select>
          {/* Filtro por tipo de equipo */}
          <select value={filtroTipo} onChange={(e) => setFiltroTipo(e.target.value)} className="campo-texto filtro-select" id="filtro-tipo">
            {TIPOS_EQUIPO.map(t => <option key={t.valor} value={t.valor}>{t.etiqueta}</option>)}
          </select>
        </div>
        <button className="boton-primario" onClick={() => navigate('/ordenes/nueva')} id="btn-nueva-orden">
          <Plus size={18} /> Nueva Orden
        </button>
      </div>

      {/* Tabla de órdenes */}
      <div className="ordenes-pagina__tabla animar-entrada animar-retraso-1">
        {cargando ? (
          <div className="dashboard__cargando"><div className="spinner" /><p>Cargando ordenes...</p></div>
        ) : ordenesFiltradas.length === 0 ? (
          <div className="dashboard__vacio">
            <ClipboardList size={44} strokeWidth={1.5} />
            <p>{ordenes.length === 0 ? 'No hay ordenes registradas' : 'No se encontraron resultados'}</p>
            {ordenes.length === 0 && (
              <button className="boton-primario" onClick={() => navigate('/ordenes/nueva')}>
                <Plus size={16} /> Crear primera orden
              </button>
            )}
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
                <th>Técnico</th>
                <th>Creado por</th>
                <th>Fecha</th>
              </tr>
            </thead>
            <tbody>
              {ordenesFiltradas.map((orden) => {
                const porCancelar = Number(orden.total_orden) - Number(orden.abono);
                const esCancelada = orden.estado === 'cancelada' || orden.equipos?.some(e => e.estado === 'cancelada');
                return (
                  <tr key={orden.id} onClick={() => navigate(`/ordenes/${orden.id}`)} className={`tabla__fila-click ${esCancelada ? 'tabla__fila-cancelada' : ''}`}>
                    <td><strong>{orden.numero_orden}</strong></td>
                    <td>{orden.cliente ? `${orden.cliente.nombre} ${orden.cliente.apellido}` : '—'}</td>
                    <td>{orden.equipos?.map(e => tipoEquipoTexto[e.tipo_equipo] || e.tipo_equipo).join(', ') || '—'}</td>
                    <td>{orden.equipos?.map(e => [e.marca, e.modelo].filter(Boolean).join(' ')).filter(Boolean).join(', ') || '—'}</td>
                    <td>
                      <div style={{display: 'flex', flexDirection: 'column', gap: '4px'}}>
                        {orden.estado === 'cancelada' 
                          ? <BadgeEstado estado="cancelada" />
                          : (orden.equipos?.length > 0 
                              ? orden.equipos.map((e, idx) => <BadgeEstado key={idx} estado={e.estado} />)
                              : <BadgeEstado estado={orden.estado} />
                            )
                        }
                      </div>
                    </td>
                    <td>${Number(orden.total_orden).toFixed(2)}</td>
                    <td>${Number(orden.abono).toFixed(2)}</td>
                    <td className={porCancelar > 0 ? 'texto-pendiente' : ''}>${porCancelar.toFixed(2)}</td>
                    <td style={{fontSize: '13px'}}>
                      {orden.tecnico ? `${orden.tecnico.nombre} ${orden.tecnico.apellido}` : '—'}
                    </td>
                    <td style={{fontSize: '13px', color: 'var(--texto-secundario)'}}>
                      {orden.creado_por || '—'}
                    </td>
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
