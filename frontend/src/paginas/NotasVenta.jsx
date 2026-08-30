/**
 * NOTAS DE VENTA - Listado de notas de venta generadas
 */
import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Receipt, FileDown, ClipboardList, CircleCheck, X } from 'lucide-react';
import { obtenerNotasVenta, descargarPdfNota } from '../api/orpey-api';
import './NotasVenta.css';

export default function NotasVenta() {
  const [notas, setNotas] = useState([]);
  const [cargando, setCargando] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  // Feedback si se llegó recién creada (vía location.state.notaCreada o ?creada=XXX)
  const [aviso, setAviso] = useState(() => {
    const porParametro = new URLSearchParams(location.search).get('creada');
    const porEstado = location.state?.notaCreada;
    if (porParametro) return `Nota de venta ${porParametro} creada correctamente`;
    if (porEstado) {
      const numero = typeof porEstado === 'string' ? porEstado : porEstado.numero_nota;
      return numero ? `Nota de venta ${numero} creada correctamente` : 'Nota de venta creada correctamente';
    }
    return null;
  });

  useEffect(() => {
    async function cargar() {
      try { setCargando(true); setNotas(await obtenerNotasVenta()); }
      catch (err) { console.error(err); }
      finally { setCargando(false); }
    }
    cargar();
  }, []);

  return (
    <div className="notas-pagina">
      {aviso && (
        <div className="notas-aviso-exito animar-entrada">
          <CircleCheck size={18} />
          <span>{aviso}</span>
          <button className="boton-icono" onClick={() => setAviso(null)} title="Cerrar"><X size={16} /></button>
        </div>
      )}
      <div className="ordenes-pagina__tabla animar-entrada">
        {cargando ? (
          <div className="dashboard__cargando"><div className="spinner" /></div>
        ) : notas.length === 0 ? (
          <div className="dashboard__vacio">
            <Receipt size={44} strokeWidth={1.5} />
            <p>No hay notas de venta. Se crean desde el detalle de una orden.</p>
            <button className="boton-primario" onClick={() => navigate('/ordenes')}>
              <ClipboardList size={16} /> Ir a Órdenes
            </button>
          </div>
        ) : (
          <table className="tabla">
            <thead>
              <tr><th>N° Nota</th><th>Subtotal</th><th>IVA (15%)</th><th>Total</th><th>Fecha</th><th>PDF</th></tr>
            </thead>
            <tbody>
              {notas.map(n => (
                <tr key={n.id}>
                  <td><strong>{n.numero_nota}</strong></td>
                  <td>${Number(n.subtotal ?? 0).toFixed(2)}</td>
                  <td>${Number(n.iva ?? 0).toFixed(2)}</td>
                  <td><strong>${Number(n.total ?? 0).toFixed(2)}</strong></td>
                  <td>{n.fecha_emision ? new Date(n.fecha_emision).toLocaleDateString('es-EC') : ''}</td>
                  <td><button className="boton-icono" onClick={() => descargarPdfNota(n.id)} title="Descargar PDF"><FileDown size={18} /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}