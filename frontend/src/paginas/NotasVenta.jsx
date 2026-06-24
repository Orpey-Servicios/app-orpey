/**
 * NOTAS DE VENTA - Listado de notas de venta generadas
 */
import { useState, useEffect } from 'react';
import { Receipt, FileDown } from 'lucide-react';
import { obtenerNotasVenta, descargarPdfNota } from '../api/orpey-api';
import './NotasVenta.css';

export default function NotasVenta() {
  const [notas, setNotas] = useState([]);
  const [cargando, setCargando] = useState(true);

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
      <div className="ordenes-pagina__tabla animar-entrada">
        {cargando ? (
          <div className="dashboard__cargando"><div className="spinner" /></div>
        ) : notas.length === 0 ? (
          <div className="dashboard__vacio">
            <Receipt size={44} strokeWidth={1.5} />
            <p>No hay notas de venta. Se crean desde el detalle de una orden.</p>
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
                  <td>${Number(n.subtotal).toFixed(2)}</td>
                  <td>${Number(n.iva).toFixed(2)}</td>
                  <td><strong>${Number(n.total).toFixed(2)}</strong></td>
                  <td>{new Date(n.fecha_emision).toLocaleDateString('es-EC')}</td>
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
