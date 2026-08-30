/**
 * FACTURACIÓN ELECTRÓNICA SRI
 * Listado de facturas electrónicas generadas + generación desde órdenes facturables.
 */
import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  FileText, FileDown, Plus, X, FileCheck2, Send, AlertTriangle,
  UploadCloud, Ban, Info, FileX2
} from 'lucide-react';
import {
  obtenerFacturas, obtenerOrdenes, obtenerClientes,
  generarFactura, descargarXmlFactura, transmitirFactura, anularFactura
} from '../api/orpey-api';
import './Facturas.css';

// Mapeo visual de estados SRI → clase de badge + etiqueta
const ESTADOS_SRI = {
  firmado:         { clase: 'badge--gris',          label: 'Firmado' },
  recibida:        { clase: 'badge--azul',          label: 'Recibida' },
  autorizado:      { clase: 'badge--verde',         label: 'Autorizado' },
  devuelta:        { clase: 'badge--rojo',          label: 'Devuelta' },
  no_autorizado:   { clase: 'badge--rojo',          label: 'No Autorizado' },
  anulada:         { clase: 'badge--anulada',       label: 'Anulada' },
  anulada_parcial: { clase: 'badge--anulada-parcial', label: 'Anulada Parcial' },
};

const ESTADOS_SRI_OPCIONES = [
  { value: 'firmado', label: 'Firmado' },
  { value: 'recibida', label: 'Recibida' },
  { value: 'autorizado', label: 'Autorizado' },
  { value: 'devuelta', label: 'Devuelta' },
  { value: 'no_autorizado', label: 'No Autorizado' },
  { value: 'anulada', label: 'Anulada' },
  { value: 'anulada_parcial', label: 'Anulada Parcial' },
];

// Estados en los que una factura (01) puede anularse emitiendo una NC
const ESTADOS_ANULABLES = ['autorizado', 'recibida'];

function esNotaCredito(comprobante) {
  return comprobante?.tipo_comprobante === '04';
}

function formatearFecha(fecha) {
  if (!fecha) return '';
  const d = new Date(fecha);
  if (isNaN(d.getTime())) return '';
  const dd = String(d.getDate()).padStart(2, '0');
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  return `${dd}/${mm}/${d.getFullYear()}`;
}

function formatearFechaHora(fecha) {
  if (!fecha) return '';
  const d = new Date(fecha);
  if (isNaN(d.getTime())) return '';
  return d.toLocaleString('es-EC', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  });
}

// Extrae mensajes legibles de errores SRI (de xml_respuesta_sri o del campo errores)
function extraerErroresSri(factura) {
  const errores = factura?.errores ?? [];
  if (Array.isArray(errores) && errores.length > 0) {
    return errores.map(e => ({
      identificador: e?.identificador || '',
      mensaje: e?.mensaje || '',
      info: e?.informacionAdicional || '',
    }));
  }
  const resp = factura?.xml_respuesta_sri;
  if (typeof resp === 'string' && resp.trim()) {
    return resp.split('\n').filter(Boolean).map(linea => ({
      identificador: '',
      mensaje: linea,
      info: '',
    }));
  }
  return [];
}

export default function Facturas() {
  const [facturas, setFacturas] = useState([]);
  const [ordenes, setOrdenes] = useState([]);
  const [clientes, setClientes] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [filtroEstado, setFiltroEstado] = useState('');
  const [mostrarModal, setMostrarModal] = useState(false);
  const [transmitiendo, setTransmitiendo] = useState(new Set());
  const [facturaDetalle, setFacturaDetalle] = useState(null);
  const [facturaAnular, setFacturaAnular] = useState(null);

  const idsOrdenesFacturadas = useMemo(
    () => new Set(facturas.map(f => f.orden_servicio_id).filter(Boolean)),
    [facturas]
  );

  // Una orden es facturable si está entregada/terminada, pagada 100% y sin factura
  const ordenesFacturables = useMemo(() => ordenes.filter(o => {
    const estadoOk = o.estado === 'entregada' || o.estado === 'terminada';
    const pagada = Number(o.abono ?? 0) >= Number(o.total_orden ?? 0);
    const sinFactura = !idsOrdenesFacturadas.has(o.id);
    return estadoOk && pagada && sinFactura;
  }), [ordenes, idsOrdenesFacturadas]);

  useEffect(() => { cargar(); }, []);

  async function cargar() {
    try {
      setCargando(true);
      const [f, o, c] = await Promise.all([obtenerFacturas(), obtenerOrdenes(), obtenerClientes()]);
      setFacturas(f);
      setOrdenes(o);
      setClientes(c);
    } catch (err) { console.error(err); }
    finally { setCargando(false); }
  }

  async function cargarFacturas() {
    try { setFacturas(await obtenerFacturas()); }
    catch (err) { console.error(err); }
  }

  function onFacturaGenerada(factura) {
    setMostrarModal(false);
    cargarFacturas();
    alert(`Factura ${factura.numero_documento} generada y firmada`);
  }

  // Transmitir una factura al SRI (recepción + autorización)
  async function transmitir(factura) {
    const esProduccion = factura?.ambiente === '2';

    if (!confirm('¿Enviar al SRI? Esta acción transmite el comprobante al SRI en el ambiente indicado.')) {
      return;
    }

    // GUARDA DE SEGURIDAD: producción exige confirmación explícita adicional
    let confirmarProduccion = false;
    if (esProduccion) {
      if (!confirm('⚠️ PRODUCCIÓN: Vas a transmitir una factura REAL al SRI en ambiente de producción.\nEsta acción NO se puede deshacer. ¿Continuar?')) {
        return;
      }
      confirmarProduccion = true;
    }

    setTransmitiendo(prev => new Set(prev).add(factura.id));
    try {
      const resultado = await transmitirFactura(factura.id, {
        confirmar_produccion: confirmarProduccion,
      });
      await cargarFacturas();

      if (resultado?.estado_sri === 'devuelta' || resultado?.estado_sri === 'no_autorizado') {
        const mensajes = extraerErroresSri({ errores: resultado.errores });
        const detalle = mensajes.length > 0
          ? mensajes.map(m => `${m.identificador ? '[' + m.identificador + '] ' : ''}${m.mensaje} ${m.info}`.trim()).join('\n')
          : '';
        setFacturaDetalle({
          numero_documento: factura.numero_documento,
          estado_sri: resultado.estado_sri,
          errores: mensajes.length > 0 ? mensajes : [{ mensaje: 'El SRI rechazó el comprobante. Revisa el detalle.' }],
          detalleCrudo: detalle,
        });
        alert(detalle ? `El SRI rechazó la factura:\n\n${detalle}` : 'El SRI rechazó la factura. Abre el detalle para ver los errores.');
      } else if (resultado?.estado_sri === 'autorizado') {
        alert('Factura transmitida y AUTORIZADA por el SRI ✓');
      } else {
        alert(`Factura transmitida. Estado: ${ESTADOS_SRI[resultado?.estado_sri]?.label || resultado?.estado_sri || 'recibida'}`);
      }
    } catch (err) {
      alert(err.message || 'No se pudo transmitir la factura al SRI.');
    } finally {
      setTransmitiendo(prev => {
        const copia = new Set(prev);
        copia.delete(factura.id);
        return copia;
      });
    }
  }

  // NCs vigentes agrupadas por factura que anularon (factura_referenciada_id)
  const ncPorFacturaAnulada = useMemo(() => {
    const mapa = new Map();
    facturas.forEach(f => {
      if (esNotaCredito(f) && f.factura_referenciada_id) {
        mapa.set(Number(f.factura_referenciada_id), f);
      }
    });
    return mapa;
  }, [facturas]);

  const facturasPorId = useMemo(() => {
    const mapa = new Map();
    facturas.forEach(f => mapa.set(Number(f.id), f));
    return mapa;
  }, [facturas]);

  // Retorno de la anulación (NC emitida) → cerrar modal, recargar y avisar
  function onAnulada(resultado) {
    setFacturaAnular(null);
    cargarFacturas();
    const nc = resultado?.nota_credito;
    const tx = resultado?.transmision;
    const mensajeNC = nc?.numero_documento
      ? `Nota de Crédito ${nc.numero_documento} emitida`
      : 'Nota de Crédito emitida';
    if (tx?.estado === 'fallo_red' || tx?.estado === 'fallo_interno') {
      alert(`${mensajeNC}, pero la transmisión al SRI falló (${tx.error || tx.estado}). La NC quedó firmada y puedes transmitirla después.`);
    } else {
      alert(`${mensajeNC} correctamente.`);
    }
  }

  const filtradas = filtroEstado
    ? facturas.filter(f => f.estado_sri === filtroEstado)
    : facturas;

  const clientesPorId = new Map(clientes.map(c => [c.id, c]));
  const ordenesPorId = new Map(ordenes.map(o => [o.id, o]));

  return (
    <div className="facturas-pagina">
      <div className="facturas__header animar-entrada">
        <div>
          <h2><FileText size={22} /> Facturación</h2>
          <p>Facturas y notas de crédito electrónicas SRI</p>
        </div>
      </div>

      <div className="ordenes-pagina__acciones animar-entrada animar-retraso-1">
        <div className="ordenes-pagina__filtros">
          <select value={filtroEstado} onChange={(e) => setFiltroEstado(e.target.value)} className="campo-texto filtro-select">
            <option value="">Todos los estados</option>
            {ESTADOS_SRI_OPCIONES.map(op => (
              <option key={op.value} value={op.value}>{op.label}</option>
            ))}
          </select>
        </div>
        <button className="boton-primario" onClick={() => setMostrarModal(true)} id="btn-generar-factura">
          <Plus size={18} /> Generar Factura
        </button>
      </div>

      <div className="ordenes-pagina__tabla animar-entrada animar-retraso-1">
        {cargando ? (
          <div className="dashboard__cargando"><div className="spinner" /></div>
        ) : facturas.length === 0 ? (
          <div className="dashboard__vacio">
            <FileText size={44} strokeWidth={1.5} />
            <p>No hay comprobantes electrónicos generados</p>
            <button className="boton-primario" onClick={() => setMostrarModal(true)}>
              <Plus size={16} /> Generar la primera factura
            </button>
          </div>
        ) : filtradas.length === 0 ? (
          <div className="dashboard__vacio">
            <FileText size={44} strokeWidth={1.5} />
            <p>No hay comprobantes con el estado seleccionado</p>
          </div>
        ) : (
          <table className="tabla">
            <thead>
              <tr>
                <th>N° Documento</th>
                <th>Clave de Acceso</th>
                <th>Cliente</th>
                <th>Origen</th>
                <th>Factura Anulada</th>
                <th>Estado</th>
                <th>Autorización</th>
                <th>Ambiente</th>
                <th>Total</th>
                <th>Fecha</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filtradas.map(f => {
                const esNC = esNotaCredito(f);
                const cliente = clientesPorId.get(f.cliente_id);
                const origenOrden = f.orden_servicio_id ? ordenesPorId.get(f.orden_servicio_id) : null;
                // NC → factura original que anula; factura anulada → NC que la anuló
                const facturaOriginal = !esNC ? null : facturasPorId.get(Number(f.factura_referenciada_id));
                const ncAnuladora = esNC ? null : ncPorFacturaAnulada.get(Number(f.id));
                const anulable = !esNC && ESTADOS_ANULABLES.includes(f.estado_sri);
                return (
                  <tr key={f.id}>
                    <td>
                      <div className="facturas__doc">
                        <strong>{f.numero_documento}</strong>
                        <span className={`facturas__tipo ${esNC ? 'facturas__tipo--nc' : 'facturas__tipo--fac'}`}>
                          {esNC ? <FileX2 size={10} /> : <FileText size={10} />}
                          {esNC ? 'Nota Crédito' : 'Factura'}
                        </span>
                      </div>
                    </td>
                    <td>
                      <span className="facturas__clave" title={f.clave_acceso}>{f.clave_acceso}</span>
                    </td>
                    <td>{cliente ? `${cliente.nombre} ${cliente.apellido}` : `Cliente #${f.cliente_id}`}</td>
                    <td>
                      {esNC ? (
                        <span className="facturas__origen-nc">Nota de crédito</span>
                      ) : f.orden_servicio_id ? (
                        <Link to={`/ordenes/${f.orden_servicio_id}`} className="facturas__link">
                          {origenOrden?.numero_orden || `Orden #${f.orden_servicio_id}`}
                        </Link>
                      ) : 'Nota de venta'}
                    </td>
                    <td>
                      {esNC ? (
                        <span
                          className="facturas__nc-ref"
                          title={facturaOriginal ? `Anula la factura ${facturaOriginal.numero_documento}` : 'Factura original'}
                        >
                          {facturaOriginal?.numero_documento || `#${f.factura_referenciada_id}`}
                        </span>
                      ) : ncAnuladora ? (
                        <span className="facturas__nc-ref" title={`Anulada por ${ncAnuladora.numero_documento}`}>
                          {ncAnuladora.numero_documento}
                        </span>
                      ) : (
                        <span className="facturas__aut--vacio">—</span>
                      )}
                    </td>
                    <td>
                      {(() => {
                        const info = ESTADOS_SRI[f.estado_sri];
                        if (!info) {
                          return (
                            <span className="badge-estado badge--gris">
                              <span className="badge-estado__punto" />{f.estado_sri || 'Generado'}
                            </span>
                          );
                        }
                        const esError = f.estado_sri === 'devuelta' || f.estado_sri === 'no_autorizado';
                        const clase = esError
                          ? `${info.clase} facturas__badge--error`
                          : info.clase;
                        return (
                          <span
                            className={`badge-estado ${clase}${esError ? ' facturas__badge--clickable' : ''}`}
                            onClick={esError ? () => setFacturaDetalle(f) : undefined}
                            title={esError ? 'Clic para ver los errores del SRI' : info.label}
                          >
                            <span className="badge-estado__punto" />{info.label}
                            {esError && <AlertTriangle size={13} className="facturas__badge-icono" />}
                          </span>
                        );
                      })()}
                    </td>
                    <td>
                      {f.numero_autorizacion ? (
                        <div className="facturas__aut">
                          <span className="facturas__aut-num" title={f.numero_autorizacion}>{f.numero_autorizacion}</span>
                          {f.fecha_autorizacion && (
                            <span className="facturas__aut-fecha">{formatearFechaHora(f.fecha_autorizacion)}</span>
                          )}
                        </div>
                      ) : (
                        <span className="facturas__aut--vacio">—</span>
                      )}
                    </td>
                    <td>
                      <span className={`facturas__ambiente ${f.ambiente === '2' ? 'facturas__ambiente--prod' : ''}`}>
                        {f.ambiente === '2' ? 'Producción' : 'Pruebas'}
                      </span>
                    </td>
                    <td><strong>${Number(f.total ?? 0).toFixed(2)}</strong></td>
                    <td>{formatearFecha(f.fecha_emision)}</td>
                    <td>
                      <div className="tabla__acciones">
                        {(f.estado_sri === 'firmado' || f.estado_sri === 'recibida') && (
                          <button
                            className="boton-secundario facturas__btn-transmitir"
                            onClick={() => transmitir(f)}
                            disabled={transmitiendo.has(f.id)}
                            title="Transmitir y autorizar al SRI"
                          >
                            <UploadCloud size={16} />
                            {transmitiendo.has(f.id) ? 'Transmitiendo...' : 'Transmitir'}
                          </button>
                        )}
                        {anulable && (
                          <button
                            className="boton-secundario facturas__btn-anular"
                            onClick={() => setFacturaAnular(f)}
                            title="Emitir una nota de crédito para anular esta factura"
                          >
                            <Ban size={16} /> Anular
                          </button>
                        )}
                        <button className="boton-icono" onClick={() => descargarXmlFactura(f.id)} title="Descargar XML"><FileDown size={18} /></button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {mostrarModal && (
        <ModalFacturacion
          ordenes={ordenesFacturables}
          clientes={clientes}
          onCerrar={() => setMostrarModal(false)}
          onGenerada={onFacturaGenerada}
        />
      )}

      {facturaDetalle && (
        <ModalErroresSri
          factura={facturaDetalle}
          onCerrar={() => setFacturaDetalle(null)}
        />
      )}

      {facturaAnular && (
        <ModalAnulacion
          factura={facturaAnular}
          nombreCliente={facturaAnular.cliente_id ? (() => {
            const c = clientesPorId.get(facturaAnular.cliente_id);
            return c ? `${c.nombre} ${c.apellido}` : '';
          })() : ''}
          onCerrar={() => setFacturaAnular(null)}
          onAnulada={onAnulada}
        />
      )}
    </div>
  );
}

/**
 * MODAL DE ANULACIÓN - Emite una nota de crédito (NC) que anula la factura.
 * Cambia el estado de la factura a 'anulada' (o 'anulada_parcial' si el monto
 * a anular es menor al total). Solo aplica a facturas (01) autorizadas/recibidas.
 */
function ModalAnulacion({ factura, nombreCliente, onCerrar, onAnulada }) {
  const total = Number(factura?.total ?? 0);
  const [motivo, setMotivo] = useState('');
  const [monto, setMonto] = useState(total ? total.toFixed(2) : '');
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);

  const montoNum = Number(monto);
  const esParcial = montoNum > 0 && montoNum < total;

  function anular() {
    const motivoLimpio = motivo.trim();
    if (!motivoLimpio) {
      setError('Indica el motivo de la anulación.');
      return;
    }
    if (!monto || isNaN(montoNum) || montoNum <= 0) {
      setError('Indica un monto a anular mayor a cero.');
      return;
    }
    if (montoNum > total) {
      setError(`El monto a anular no puede superar el total de la factura ($${total.toFixed(2)}).`);
      return;
    }
    setGuardando(true);
    setError(null);
    anularFactura(factura.id, {
      motivo: motivoLimpio,
      monto_anular: montoNum,
    })
      .then(onAnulada)
      .catch(err => {
        setError(err.message || 'No se pudo anular la factura.');
        setGuardando(false);
      });
  }

  return (
    <div className="modal-overlay" onClick={onCerrar}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h3><Ban size={18} /> Anular Factura</h3>
          <button className="boton-icono" onClick={onCerrar}><X size={20} /></button>
        </div>

        <div className="facturas__anular-resumen">
          <p><strong>{factura.numero_documento}</strong>{nombreCliente && <span> · {nombreCliente}</span>}</p>
          <p>Total: <strong>${total.toFixed(2)}</strong> · Estado: {ESTADOS_SRI[factura.estado_sri]?.label || factura.estado_sri}</p>
        </div>

        {error && <div className="dashboard__error" style={{ margin: '0 0 16px' }}><p>⚠️ {error}</p></div>}

        <div className="campo-grupo">
          <label className="campo-label" htmlFor="motivo-anulacion">Motivo de la anulación *</label>
          <textarea
            id="motivo-anulacion"
            className="campo-texto facturas__textarea-motivo"
            placeholder="Ej. Anulación de factura por devolución del servicio"
            value={motivo}
            onChange={(e) => { setMotivo(e.target.value); setError(null); }}
            maxLength={500}
            rows={3}
          />
        </div>

        <div className="campo-grupo">
          <label className="campo-label" htmlFor="monto-anulacion">Monto a anular (IVA incluido) *</label>
          <div className="facturas__monto-fila">
            <input
              id="monto-anulacion"
              type="number"
              className="campo-texto"
              min="0.01"
              max={total}
              step="0.01"
              value={monto}
              onChange={(e) => { setMonto(e.target.value); setError(null); }}
            />
            <button
              type="button"
              className="boton-secundario"
              onClick={() => setMonto(total.toFixed(2))}
              disabled={guardando}
              title="Restaurar el monto total"
            >
              ％ Anular todo
            </button>
          </div>
          {esParcial && (
            <p className="facturas__monto-hint">
              Anulación parcial: la factura quedará como <strong>Anulada Parcial</strong> y la NC por ${montoNum.toFixed(2)}.
            </p>
          )}
        </div>

        <div className="facturas__nc-aviso">
          <Info size={16} />
          <span>Se emitirá una Nota de Crédito electrónica ante el SRI.</span>
        </div>

        <div className="modal__botones">
          <button type="button" className="boton-secundario" onClick={onCerrar} disabled={guardando}>Cancelar</button>
          <button type="button" className="boton-primario facturas__btn-anular-confirmar" onClick={anular} disabled={guardando}>
            <Ban size={16} /> {guardando ? 'Anulando...' : 'Anular y emitir NC'}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * MODAL DE ERRORES SRI - Muestra el detalle de rechazo (devuelta / no autorizada).
 */
function ModalErroresSri({ factura, onCerrar }) {
  const errores = factura.errores && factura.errores.length > 0
    ? factura.errores
    : extraerErroresSri(factura);

  const esNoAutorizado = factura.estado_sri === 'no_autorizado';

  return (
    <div className="modal-overlay" onClick={onCerrar}>
      <div className="modal modal--md" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h3><AlertTriangle size={18} /> {esNoAutorizado ? 'Comprobante no autorizado' : 'Comprobante devuelto por el SRI'}</h3>
          <button className="boton-icono" onClick={onCerrar}><X size={20} /></button>
        </div>

        {factura.numero_documento && (
          <p className="facturas__detalle-num">Factura <strong>{factura.numero_documento}</strong></p>
        )}

        <p className="facturas__detalle-aviso">
          El SRI {esNoAutorizado ? 'no autorizó' : 'rechazó'} el comprobante. Revisa los errores, corrige la causa y transmítelo de nuevo.
        </p>

        {errores.length === 0 ? (
          <div className="dashboard__vacio">
            <AlertTriangle size={36} strokeWidth={1.5} />
            <p>{factura.detalleCrudo || 'No hay detalle de errores disponible.'}</p>
          </div>
        ) : (
          <div className="facturas__errores-lista">
            {errores.map((e, i) => (
              <div key={i} className="facturas__error-item">
                {e.identificador && <span className="facturas__error-codigo">[{e.identificador}]</span>}
                <span className="facturas__error-mensaje">{e.mensaje || e.message}</span>
                {e.info && <span className="facturas__error-info">{e.info}</span>}
              </div>
            ))}
          </div>
        )}

        <div className="modal__botones">
          <button type="button" className="boton-primario" onClick={onCerrar}>Cerrar</button>
        </div>
      </div>
    </div>
  );
}

/**
 * MODAL DE FACTURACIÓN - Selección de orden para generar la factura electrónica.
 * Solo muestra órdenes facturables (entregada/terminada, pagada 100%, sin factura).
 */
function ModalFacturacion({ ordenes, clientes, onCerrar, onGenerada }) {
  const [ordenId, setOrdenId] = useState('');
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);

  function nombreCliente(orden) {
    const clienteEmbebido = orden.cliente;
    if (clienteEmbebido && (clienteEmbebido.nombre || clienteEmbebido.apellido)) {
      return `${clienteEmbebido.nombre} ${clienteEmbebido.apellido}`.trim();
    }
    const clienteId = orden.cliente_id ?? clienteEmbebido?.id;
    const c = clientes.find(c => c.id === clienteId);
    return c ? `${c.nombre} ${c.apellido}` : `Cliente #${clienteId ?? ''}`;
  }

  async function generar() {
    if (!ordenId) {
      setError('Selecciona una orden para facturar');
      return;
    }
    try {
      setGuardando(true);
      setError(null);
      const factura = await generarFactura({ orden_servicio_id: Number(ordenId) });
      onGenerada(factura);
    } catch (err) { setError(err.message); }
    finally { setGuardando(false); }
  }

  return (
    <div className="modal-overlay" onClick={onCerrar}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h3><FileCheck2 size={18} /> Generar Factura Electrónica</h3>
          <button className="boton-icono" onClick={onCerrar}><X size={20} /></button>
        </div>

        {error && <div className="dashboard__error" style={{ margin: '0 0 16px' }}><p>{error}</p></div>}

        {ordenes.length === 0 ? (
          <div className="dashboard__vacio">
            <FileText size={40} strokeWidth={1.5} />
            <p>No hay órdenes listas para facturar. Deben estar entregadas, pagadas al 100% y sin factura previa.</p>
          </div>
        ) : (
          <>
            <div className="campo-grupo">
              <label className="campo-label">Orden de servicio *</label>
              <select
                className="campo-texto facturas__select-ordenes"
                value={ordenId}
                onChange={(e) => { setOrdenId(e.target.value); setError(null); }}
                id="select-orden-facturar"
              >
                <option value="">Selecciona una orden...</option>
                {ordenes.map(o => (
                  <option key={o.id} value={o.id}>
                    {o.numero_orden} — {nombreCliente(o)} — ${Number(o.total_orden ?? 0).toFixed(2)}
                  </option>
                ))}
              </select>
              <p className="facturas__hint">Se generará la factura electrónica en ambiente de pruebas y quedará firmada.</p>
            </div>

            <div className="modal__botones">
              <button type="button" className="boton-secundario" onClick={onCerrar}>Cancelar</button>
              <button type="button" className="boton-primario" onClick={generar} disabled={guardando}>
                <Send size={16} /> {guardando ? 'Generando...' : 'Generar factura'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}