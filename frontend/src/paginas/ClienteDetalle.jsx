/**
 * FICHA DE CLIENTE - Detalle completo con historial de órdenes
 */
import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Plus, MessageCircle, Mail, ClipboardList } from 'lucide-react';
import { obtenerCliente, obtenerOrdenes } from '../api/orpey-api';
import BadgeEstado from '../componentes/BadgeEstado';
import './ClienteDetalle.css';

const tipoEquipoTexto = { pc_escritorio: 'PC', laptop: 'Laptop', impresora: 'Impresora', telefono: 'Teléfono', otro: 'Otro' };

export default function ClienteDetalle() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [cliente, setCliente] = useState(null);
  const [ordenes, setOrdenes] = useState([]);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    async function cargar() {
      try {
        setCargando(true);
        const [c, o] = await Promise.all([
          obtenerCliente(Number(id)),
          obtenerOrdenes({ cliente_id: Number(id) })
        ]);
        setCliente(c);
        setOrdenes(o);
      } catch (err) { console.error(err); }
      finally { setCargando(false); }
    }
    cargar();
  }, [id]);

  if (cargando) return <div className="dashboard__cargando"><div className="spinner" /></div>;
  if (!cliente) return <div className="dashboard__vacio"><p>Cliente no encontrado</p></div>;

  // Generar link de WhatsApp directo
  const telLimpio = cliente.telefono.replace(/\D/g, '');
  const tel593 = telLimpio.startsWith('0') ? '593' + telLimpio.slice(1) : telLimpio;
  const waLink = `https://wa.me/${tel593}`;

  return (
    <div className="cliente-detalle">
      <div className="orden-detalle__header animar-entrada">
        <div className="orden-detalle__header-left">
          <button className="boton-secundario" onClick={() => navigate('/clientes')}><ArrowLeft size={18} /> Volver</button>
          <h2>{cliente.nombre} {cliente.apellido}</h2>
        </div>
        <div className="orden-detalle__header-acciones">
          <button className="boton-secundario" onClick={() => window.open(waLink, '_blank')} style={{color:'#25D366'}}>
            <MessageCircle size={18} /> WhatsApp
          </button>
          {cliente.email && (
            <button className="boton-secundario" onClick={() => window.open(`mailto:${cliente.email}`)}>
              <Mail size={18} /> Email
            </button>
          )}
          <button className="boton-primario" onClick={() => navigate('/ordenes/nueva')}>
            <Plus size={18} /> Nueva Orden
          </button>
        </div>
      </div>

      {/* Datos del cliente */}
      <div className="orden-detalle__grid animar-entrada animar-retraso-1">
        <div className="orden-detalle__card">
          <h3>📞 Contacto</h3>
          <div className="orden-detalle__datos">
            <p><strong>Teléfono:</strong> {cliente.telefono}</p>
            <p><strong>Email:</strong> {cliente.email || 'No registrado'}</p>
            <p><strong>Dirección:</strong> {cliente.direccion || 'No registrada'}</p>
          </div>
        </div>
        <div className="orden-detalle__card">
          <h3>🆔 Identificación</h3>
          <div className="orden-detalle__datos">
            <p><strong>Cédula/RUC:</strong> {cliente.cedula_ruc || 'No registrado'}</p>
            <p><strong>Tipo:</strong> {cliente.tipo_persona === 'natural' ? 'Persona Natural' : 'Empresa'}</p>
            <p><strong>Cliente desde:</strong> {new Date(cliente.created_at).toLocaleDateString('es-EC')}</p>
          </div>
        </div>
        <div className="orden-detalle__card">
          <h3>📊 Resumen</h3>
          <div className="orden-detalle__datos">
            <p><strong>Total de órdenes:</strong> {ordenes.length}</p>
            <p><strong>Activas:</strong> {ordenes.filter(o => !['entregada'].includes(o.estado)).length}</p>
          </div>
        </div>
      </div>

      {/* Historial de órdenes */}
      <div className="ordenes-pagina__tabla animar-entrada animar-retraso-2">
        <div className="dashboard__recientes-header">
          <h2><ClipboardList size={20} /> Historial de Órdenes</h2>
        </div>
        {ordenes.length === 0 ? (
          <div className="dashboard__vacio"><p>Este cliente no tiene órdenes aún</p></div>
        ) : (
          <table className="tabla">
            <thead><tr><th>N° Orden</th><th>Equipo</th><th>Estado</th><th>Total</th><th>Fecha</th></tr></thead>
            <tbody>
              {ordenes.map(o => (
                <tr key={o.id} onClick={() => navigate(`/ordenes/${o.id}`)} className="tabla__fila-click">
                  <td><strong>{o.numero_orden}</strong></td>
                  <td>{tipoEquipoTexto[o.tipo_equipo] || o.tipo_equipo} {o.marca || ''}</td>
                  <td><BadgeEstado estado={o.estado} /></td>
                  <td>${Number(o.total_orden).toFixed(2)}</td>
                  <td>{new Date(o.fecha_ingreso).toLocaleDateString('es-EC')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
