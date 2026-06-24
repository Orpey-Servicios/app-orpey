/**
 * GESTIÓN DE COTIZACIONES
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, FileText, MessageCircle } from 'lucide-react';
import { obtenerCotizaciones, aprobarCotizacion, obtenerWhatsappCotizacion } from '../api/orpey-api';
import BadgeEstado from '../componentes/BadgeEstado';
import './Cotizaciones.css';

export default function Cotizaciones() {
  const [cotizaciones, setCotizaciones] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [filtroEstado, setFiltroEstado] = useState('');
  const navigate = useNavigate();

  useEffect(() => { cargar(); }, [filtroEstado]);

  async function cargar() {
    try {
      setCargando(true);
      const filtros = {};
      if (filtroEstado) filtros.estado = filtroEstado;
      setCotizaciones(await obtenerCotizaciones(filtros));
    } catch (err) { console.error(err); }
    finally { setCargando(false); }
  }

  async function aprobar(id) {
    if (!confirm('¿Aprobar esta cotización?')) return;
    try { await aprobarCotizacion(id); cargar(); }
    catch (err) { alert(err.message); }
  }

  async function enviarWa(id) {
    try {
      const data = await obtenerWhatsappCotizacion(id);
      window.open(data.link, '_blank');
    } catch (err) { alert(err.message); }
  }

  return (
    <div className="cotizaciones-pagina">
      <div className="ordenes-pagina__acciones animar-entrada">
        <div className="ordenes-pagina__filtros">
          <select value={filtroEstado} onChange={(e) => setFiltroEstado(e.target.value)} className="campo-texto filtro-select">
            <option value="">Todos los estados</option>
            <option value="abierta">Abierta</option>
            <option value="aprobada">Aprobada</option>
            <option value="cerrada">Cerrada</option>
            <option value="rechazada">Rechazada</option>
          </select>
        </div>
      </div>

      <div className="ordenes-pagina__tabla animar-entrada animar-retraso-1">
        {cargando ? (
          <div className="dashboard__cargando"><div className="spinner" /></div>
        ) : cotizaciones.length === 0 ? (
          <div className="dashboard__vacio">
            <FileText size={44} strokeWidth={1.5} />
            <p>No hay cotizaciones registradas</p>
          </div>
        ) : (
          <table className="tabla">
            <thead>
              <tr><th>N° Cotización</th><th>Estado</th><th>Descripción</th><th>Total</th><th>Validez</th><th>Fecha</th><th>Acciones</th></tr>
            </thead>
            <tbody>
              {cotizaciones.map(c => (
                <tr key={c.id}>
                  <td><strong>{c.numero_cotizacion}</strong></td>
                  <td><BadgeEstado estado={c.estado} /></td>
                  <td style={{maxWidth: '250px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'}}>{c.descripcion}</td>
                  <td>${Number(c.total).toFixed(2)}</td>
                  <td>{c.validez_dias} días</td>
                  <td>{new Date(c.fecha_creacion).toLocaleDateString('es-EC')}</td>
                  <td>
                    <div className="tabla__acciones">
                      {c.estado === 'abierta' && (
                        <button className="boton-secundario" onClick={() => aprobar(c.id)} style={{padding:'6px 12px', fontSize:'12px'}}>✅ Aprobar</button>
                      )}
                      <button className="boton-icono" onClick={() => enviarWa(c.id)} title="WhatsApp" style={{color:'#25D366'}}><MessageCircle size={16} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
