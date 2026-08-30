/**
 * ============================================================
 * CAJA - Apertura, arqueo y cierre diario de caja
 * ============================================================
 *
 * Muestra el estado de la caja del día (abierta/cerrada), permite
 * abrirla con un monto inicial, registrar ingresos/egresos manuales,
 * y al cerrar hacer el arqueo mostrando la diferencia en vivo.
 *
 * También lista los movimientos de la caja actual y el historial
 * de cierres anteriores.
 * ============================================================
 */
import { useState, useEffect } from 'react';
import {
  Wallet, Plus, Minus, Lock, Unlock, ArrowDownCircle, ArrowUpCircle,
  RefreshCw, History, CircleCheck, X, Calculator, AlertCircle,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import {
  obtenerCajaActual, abrirCaja, cerrarCaja,
  registrarMovimientoCaja, obtenerMovimientosCaja, obtenerHistorialCaja,
} from '../api/orpey-api';
import './Caja.css';

// Formato de moneda local (misma fórmula inline que el resto del proyecto)
const moneda = (v) => '$' + Number(v || 0).toFixed(2);

// Fecha + hora corta (es-EC)
const formatearFechaHora = (iso) => {
  if (!iso) return '—';
  const fecha = new Date(iso);
  return fecha.toLocaleDateString('es-EC') + ' ' + fecha.toLocaleTimeString('es-EC', { hour: '2-digit', minute: '2-digit' });
};

const METODOS_PAGO = ['efectivo', 'transferencia', 'tarjeta', 'otro'];

export default function Caja() {
  const { usuario } = useAuth();
  const esOperadorCaja = usuario?.rol === 'admin' || usuario?.rol === 'asistente';

  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [caja, setCaja] = useState(null);        // CajaResponse | null
  const [movimientos, setMovimientos] = useState([]);
  const [historial, setHistorial] = useState([]);
  const [aviso, setAviso] = useState(null);       // Feedback de éxito
  const [modal, setModal] = useState(null);       // null | 'abrir' | 'cerrar' | 'ingreso' | 'egreso'
  const [filtroTipo, setFiltroTipo] = useState(''); // '' | 'ingreso' | 'egreso'

  // ── Carga de datos (defensiva: si un endpoint falla no tumba la página) ──
  async function cargarDatos() {
    setCargando(true);
    setError(null);
    try {
      const res = await obtenerCajaActual();
      // El contrato devuelve { caja: CajaResponse|null }; toleramos respuesta directa.
      setCaja(res?.caja ?? res ?? null);
    } catch (err) {
      setError(err.message || 'No se pudo consultar el estado de la caja.');
      setCaja(null);
    }
    try {
      const movs = await obtenerMovimientosCaja();
      setMovimientos(Array.isArray(movs) ? movs : []);
    } catch (e) { setMovimientos([]); }
    try {
      const hist = await obtenerHistorialCaja();
      setHistorial(Array.isArray(hist) ? hist : []);
    } catch (e) { setHistorial([]); }
    setCargando(false);
  }

  useEffect(() => { cargarDatos(); }, []);

  const cajaAbierta = !!caja && caja.estado === 'abierta';

  // Monto esperado según el backend (con respaldo calculado)
  const esperado = cajaAbierta
    ? Number(caja.monto_en_caja ?? Number(caja.monto_inicial) + Number(caja.ingresos || 0) - Number(caja.egresos || 0))
    : 0;

  // ── Movimientos filtrados por tipo ──
  const movimientosFiltrados = movimientos.filter(m =>
    !filtroTipo || m.tipo === filtroTipo
  );

  // ── Al cerrar el modal, limpiar el aviso anterior ──
  function abrirModal(tipo) {
    setError(null);
    setModal(tipo);
  }

  function cerrarAviso() { setAviso(null); }

  return (
    <div className="caja-pagina">
      {/* Header tipo Facturas */}
      <div className="caja__header animar-entrada">
        <div>
          <h2><Wallet size={24} /> Caja</h2>
          <p>Apertura, arqueo y cierre diario de caja</p>
        </div>
        <button className="boton-secundario" onClick={cargarDatos} title="Recargar datos" id="btn-recargar-caja">
          <RefreshCw size={16} /> Recargar
        </button>
      </div>

      {aviso && (
        <div className="caja__aviso-exito animar-entrada">
          <CircleCheck size={18} />
          <span>{aviso}</span>
          <button className="boton-icono" onClick={cerrarAviso} title="Cerrar"><X size={16} /></button>
        </div>
      )}

      {error && (
        <div className="dashboard__error animar-entrada">
          <AlertCircle size={20} />
          <div>
            <strong>No se pudo cargar el módulo de caja</strong>
            <p>{error}</p>
          </div>
        </div>
      )}

      {cargando ? (
        <div className="dashboard__cargando"><div className="spinner" /><p>Cargando caja...</p></div>
      ) : (
        <>
          {/* ═══════════════════════════════════════════ */}
          {/* ESTADO PRINCIPAL DE LA CAJA               */}
          {/* ═══════════════════════════════════════════ */}
          {!cajaAbierta ? (
            <div className="caja__estado caja__estado--cerrada animar-entrada">
              <div className="caja__estado-icono"><Wallet size={44} strokeWidth={1.4} /></div>
              <h3>La caja está cerrada</h3>
              <p>Para registrar pagos y movimientos primero debes abrir la caja del día.</p>
              <p className="caja__hora-actual">
                {new Date().toLocaleDateString('es-EC', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
              </p>
              {esOperadorCaja && (
                <button className="boton-primario" onClick={() => abrirModal('abrir')} id="btn-abrir-caja">
                  <Unlock size={18} /> Abrir Caja
                </button>
              )}
            </div>
          ) : (
            <div className="caja__estado caja__estado--abierta animar-entrada">
              <div className="caja__estado-badge">
                <span className="caja__badge caja__badge--abierta"><span className="caja__badge-punto" /> Caja abierta</span>
              </div>

              <div className="caja__estado-grid">
                <div className="caja__dato">
                  <span className="caja__dato-nombre">Monto inicial</span>
                  <strong>{moneda(caja.monto_inicial)}</strong>
                </div>
                <div className="caja__dato">
                  <span className="caja__dato-nombre">Ingresos del día</span>
                  <strong className="caja__dato--ingreso">+{moneda(caja.ingresos)}</strong>
                </div>
                <div className="caja__dato">
                  <span className="caja__dato-nombre">Egresos del día</span>
                  <strong className="caja__dato--egreso">−{moneda(caja.egresos)}</strong>
                </div>
                <div className="caja__dato caja__dato--esperado">
                  <span className="caja__dato-nombre">Monto en caja (esperado)</span>
                  <strong className="caja__monto-grande">{moneda(esperado)}</strong>
                </div>
              </div>

              <div className="caja__estado-meta">
                <span>Apertura: <strong>{caja.abierta_por || '—'}</strong> · {formatearFechaHora(caja.abierta_en)}</span>
              </div>

              {esOperadorCaja && (
                <div className="caja__acciones">
                  <button className="boton-secundario" onClick={() => abrirModal('ingreso')} id="btn-nuevo-ingreso">
                    <ArrowDownCircle size={18} /> Nuevo Ingreso
                  </button>
                  <button className="boton-secundario" onClick={() => abrirModal('egreso')} id="btn-nuevo-egreso">
                    <ArrowUpCircle size={18} /> Nuevo Egreso
                  </button>
                  <button className="boton-peligro" onClick={() => abrirModal('cerrar')} id="btn-cerrar-caja">
                    <Lock size={18} /> Cerrar Caja
                  </button>
                </div>
              )}
            </div>
          )}

          {/* ═══════════════════════════════════════════ */}
          {/* MOVIMIENTOS DE LA CAJA                     */}
          {/* ═══════════════════════════════════════════ */}
          <div className="caja__seccion animar-entrada animar-retraso-1">
            <div className="caja__seccion-header">
              <h3><History size={18} /> Movimientos {cajaAbierta ? 'de hoy' : ''}</h3>
              <select
                className="campo-texto filtro-select"
                value={filtroTipo}
                onChange={(e) => setFiltroTipo(e.target.value)}
                id="filtro-movimientos"
              >
                <option value="">Todos los tipos</option>
                <option value="ingreso">Solo ingresos</option>
                <option value="egreso">Solo egresos</option>
              </select>
            </div>

            {movimientosFiltrados.length === 0 ? (
              <div className="dashboard__vacio">
                <Wallet size={44} strokeWidth={1.5} />
                <p>{cajaAbierta ? 'Aún no hay movimientos en la caja de hoy' : 'No hay movimientos registrados'}</p>
              </div>
            ) : (
              <div className="ordenes-pagina__tabla">
                <table className="tabla">
                  <thead>
                    <tr>
                      <th>Fecha / Hora</th>
                      <th>Tipo</th>
                      <th>Origen</th>
                      <th>Referencia</th>
                      <th>Método</th>
                      <th>Monto</th>
                      <th>Usuario</th>
                    </tr>
                  </thead>
                  <tbody>
                    {movimientosFiltrados.map(m => (
                      <tr key={m.id}>
                        <td>{formatearFechaHora(m.creado_en || m.fecha)}</td>
                        <td>
                          {m.tipo === 'egreso'
                            ? <span className="caja__badge caja__badge--egreso"><ArrowUpCircle size={13} /> Egreso</span>
                            : <span className="caja__badge caja__badge--ingreso"><ArrowDownCircle size={13} /> Ingreso</span>}
                        </td>
                        <td>{m.origen || (m.descripcion ? 'Movimiento manual' : '—')}</td>
                        <td>{m.referencia || m.descripcion || '—'}</td>
                        <td>{m.metodo_pago ? m.metodo_pago.charAt(0).toUpperCase() + m.metodo_pago.slice(1) : '—'}</td>
                        <td className={m.tipo === 'egreso' ? 'caja__tabla-monto caja__tabla-monto--egreso' : 'caja__tabla-monto caja__tabla-monto--ingreso'}>
                          {m.tipo === 'egreso' ? '−' : '+'}{moneda(m.monto)}
                        </td>
                        <td>{m.usuario || m.creado_por || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* ═══════════════════════════════════════════ */}
          {/* HISTORIAL DE CIERRES                        */}
          {/* ═══════════════════════════════════════════ */}
          <div className="caja__seccion animar-entrada animar-retraso-2">
            <div className="caja__seccion-header">
              <h3><Calculator size={18} /> Historial de cierres</h3>
            </div>

            {historial.length === 0 ? (
              <div className="dashboard__vacio">
                <History size={44} strokeWidth={1.5} />
                <p>No hay cierres registrados todavía</p>
              </div>
            ) : (
              <div className="ordenes-pagina__tabla">
                <table className="tabla">
                  <thead>
                    <tr>
                      <th>Apertura</th>
                      <th>Cierre</th>
                      <th>Inicial</th>
                      <th>Esperado</th>
                      <th>Contado</th>
                      <th>Diferencia</th>
                    </tr>
                  </thead>
                  <tbody>
                    {historial.map(h => {
                      const dif = Number(h.diferencia);
                      return (
                        <tr key={h.id}>
                          <td>{formatearFechaHora(h.abierta_en)}</td>
                          <td>{formatearFechaHora(h.cerrada_en)}</td>
                          <td>{moneda(h.monto_inicial)}</td>
                          <td>{moneda(h.monto_esperado)}</td>
                          <td>{moneda(h.monto_cierre ?? h.monto_contado)}</td>
                          <td>
                            <span className={`caja__diferencia ${dif === 0 ? 'caja__diferencia--cuadrada' : dif > 0 ? 'caja__diferencia--sobra' : 'caja__diferencia--falta'}`}>
                              {dif === 0 ? 'Cuadrada' : (dif > 0 ? '+' : '') + moneda(dif)}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {/* ═══════════════════════════════════════════ */}
      {/* MODAL: ABRIR CAJA                          */}
      {/* ═══════════════════════════════════════════ */}
      {modal === 'abrir' && (
        <ModalAbrirCaja
          onCerrar={() => setModal(null)}
          onExito={(cajaNueva) => {
            setModal(null);
            setAviso(`Caja abierta con un monto inicial de ${moneda(cajaNueva?.monto_inicial)}`);
            cargarDatos();
          }}
        />
      )}

      {/* MODAL: NUEVO INGRESO / EGRESO */}
      {(modal === 'ingreso' || modal === 'egreso') && (
        <ModalMovimiento
          tipo={modal}
          onCerrar={() => setModal(null)}
          onExito={(mov) => {
            setModal(null);
            setAviso(`${modal === 'ingreso' ? 'Ingreso' : 'Egreso'} de ${moneda(mov?.monto)} registrado correctamente`);
            cargarDatos();
          }}
        />
      )}

      {/* MODAL: CERRAR CAJA (ARQUEO) */}
      {modal === 'cerrar' && caja && (
        <ModalCerrarCaja
          caja={caja}
          esperado={esperado}
          onCerrar={() => setModal(null)}
          onExito={(cajaCerrada) => {
            setModal(null);
            const dif = Number(cajaCerrada?.diferencia);
            setAviso(dif === 0
              ? 'Caja cerrada y cuadrada. ¡Perfecto!'
              : `Caja cerrada con diferencia de ${moneda(dif)} (${dif > 0 ? 'sobra' : 'falta'})`);
            // Recargar para volver al estado "cerrada"
            cargarDatos();
          }}
        />
      )}
    </div>
  );
}

/* ============================================================
   MODAL: ABRIR CAJA
   ============================================================ */
function ModalAbrirCaja({ onCerrar, onExito }) {
  const [monto, setMonto] = useState('0.00');
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);

  async function guardar() {
    const montoNum = Number(monto) || 0;
    if (montoNum < 0) { setError('El monto inicial no puede ser negativo'); return; }
    try {
      setGuardando(true); setError(null);
      const res = await abrirCaja({ monto_inicial: montoNum });
      onExito(res?.caja ?? res);
    } catch (err) { setError(err.message); }
    finally { setGuardando(false); }
  }

  return (
    <div className="modal-overlay" onClick={onCerrar}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h3><Unlock size={18} /> Abrir Caja</h3>
          <button className="boton-icono" onClick={onCerrar}><X size={20} /></button>
        </div>

        {error && <div className="dashboard__error" style={{ margin: '0 0 16px' }}><p>⚠️ {error}</p></div>}

        <div className="campo-grupo">
          <label className="campo-label" htmlFor="monto-inicial">Monto inicial ($)</label>
          <input
            id="monto-inicial"
            type="number"
            className="campo-texto"
            min="0"
            step="0.01"
            value={monto}
            onChange={(e) => { setMonto(e.target.value); setError(null); }}
          />
          <p className="caja__hint">Este monto queda como base de la caja antes de registrar movimientos.</p>
        </div>

        <div className="modal__botones">
          <button type="button" className="boton-secundario" onClick={onCerrar} disabled={guardando}>Cancelar</button>
          <button type="button" className="boton-primario" onClick={guardar} disabled={guardando}>
            <Unlock size={16} /> {guardando ? 'Abriendo...' : 'Abrir Caja'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   MODAL: NUEVO INGRESO / EGRESO
   ============================================================ */
function ModalMovimiento({ tipo, onCerrar, onExito }) {
  const esIngreso = tipo === 'ingreso';
  const [monto, setMonto] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [metodo, setMetodo] = useState('efectivo');
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);

  async function guardar() {
    const montoNum = Number(monto);
    if (!monto || montoNum <= 0) { setError('El monto debe ser mayor a 0'); return; }
    if (!descripcion.trim()) { setError('La descripción es obligatoria'); return; }
    try {
      setGuardando(true); setError(null);
      const datos = { tipo, monto: montoNum, descripcion: descripcion.trim() };
      if (esIngreso) datos.metodo_pago = metodo;
      const res = await registrarMovimientoCaja(datos);
      onExito(res);
    } catch (err) { setError(err.message); }
    finally { setGuardando(false); }
  }

  return (
    <div className="modal-overlay" onClick={onCerrar}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h3>{esIngreso ? <ArrowDownCircle size={18} /> : <ArrowUpCircle size={18} />} {esIngreso ? 'Nuevo Ingreso' : 'Nuevo Egreso'}</h3>
          <button className="boton-icono" onClick={onCerrar}><X size={20} /></button>
        </div>

        {error && <div className="dashboard__error" style={{ margin: '0 0 16px' }}><p>⚠️ {error}</p></div>}

        <div className="campo-grupo">
          <label className="campo-label" htmlFor="monto-movimiento">Monto ($)</label>
          <input
            id="monto-movimiento"
            type="number"
            className="campo-texto"
            min="0.01"
            step="0.01"
            placeholder="0.00"
            value={monto}
            onChange={(e) => { setMonto(e.target.value); setError(null); }}
          />
        </div>

        {esIngreso && (
          <div className="campo-grupo">
            <label className="campo-label" htmlFor="metodo-movimiento">Método de pago</label>
            <select className="campo-texto" id="metodo-movimiento" value={metodo} onChange={(e) => setMetodo(e.target.value)}>
              {METODOS_PAGO.map(m => <option key={m} value={m}>{m.charAt(0).toUpperCase() + m.slice(1)}</option>)}
            </select>
          </div>
        )}

        <div className="campo-grupo">
          <label className="campo-label" htmlFor="descripcion-movimiento">Descripción</label>
          <textarea
            id="descripcion-movimiento"
            className="campo-texto"
            rows={2}
            placeholder={esIngreso ? 'Ej. Ingreso manual por venta de accesorios' : 'Ej. Compra de insumos de limpieza'}
            value={descripcion}
            onChange={(e) => { setDescripcion(e.target.value); setError(null); }}
          />
        </div>

        <div className="modal__botones">
          <button type="button" className="boton-secundario" onClick={onCerrar} disabled={guardando}>Cancelar</button>
          <button
            type="button"
            className={esIngreso ? 'boton-primario' : 'boton-peligro'}
            onClick={guardar}
            disabled={guardando}
          >
            {esIngreso ? <Plus size={16} /> : <Minus size={16} />} {guardando ? 'Guardando...' : (esIngreso ? 'Registrar Ingreso' : 'Registrar Egreso')}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   MODAL: CERRAR CAJA (ARQUEO)
   ============================================================ */
function ModalCerrarCaja({ caja, esperado, onCerrar, onExito }) {
  const [contado, setContado] = useState('');
  const [nota, setNota] = useState('');
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);

  const contadoNum = Number(contado) || 0;
  const esperadoNum = Number(esperado) || 0;
  const diferencia = (typeof contado === 'string' && contado !== '') ? contadoNum - esperadoNum : null;

  const claseDiferencia = diferencia === null ? '' :
    diferencia === 0 ? 'caja__diferencia caja__diferencia--cuadrada' :
    diferencia > 0 ? 'caja__diferencia caja__diferencia--sobra' : 'caja__diferencia caja__diferencia--falta';

  async function guardar() {
    if (contado === '' || contadoNum < 0) { setError('El monto contado es obligatorio y no puede ser negativo'); return; }
    try {
      setGuardando(true); setError(null);
      const res = await cerrarCaja({ monto_contado: contadoNum, nota_cierre: nota.trim() || undefined });
      const cajaCerrada = res?.caja ?? res;
      onExito(cajaCerrada);
    } catch (err) {
      setError(err.message);
    }
    finally { setGuardando(false); }
  }

  return (
    <div className="modal-overlay" onClick={onCerrar}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h3><Lock size={18} /> Cerrar Caja</h3>
          <button className="boton-icono" onClick={onCerrar}><X size={20} /></button>
        </div>

        {error && <div className="dashboard__error" style={{ margin: '0 0 16px' }}><p>⚠️ {error}</p></div>}

        {/* Desglose del arqueo */}
        <div className="caja__arqueo">
          <div className="caja__arqueo-fila">
            <span>Monto inicial</span>
            <span>{moneda(caja.monto_inicial)}</span>
          </div>
          <div className="caja__arqueo-fila caja__arqueo-fila--ingreso">
            <span>Ingresos del día</span>
            <span>+{moneda(caja.ingresos)}</span>
          </div>
          <div className="caja__arqueo-fila caja__arqueo-fila--egreso">
            <span>Egresos del día</span>
            <span>−{moneda(caja.egresos)}</span>
          </div>
          <div className="caja__arqueo-total">
            <span>Monto esperado</span>
            <strong>{moneda(esperadoNum)}</strong>
          </div>
        </div>

        <div className="campo-grupo">
          <label className="campo-label" htmlFor="monto-contado">Monto contado ($) *</label>
          <input
            id="monto-contado"
            type="number"
            className="campo-texto"
            min="0"
            step="0.01"
            placeholder="0.00"
            value={contado}
            onChange={(e) => { setContado(e.target.value); setError(null); }}
          />
        </div>

        {/* Diferencia calculada en vivo */}
        {diferencia !== null && (
          <div className="caja__diferencia-en-vivo animar-entrada">
            <div className={claseDiferencia}>
              {diferencia === 0
                ? `Cuadrada — no sobra ni falta`
                : `${diferencia > 0 ? 'Sobran' : 'Faltan'} ${moneda(Math.abs(diferencia))}`}
            </div>
          </div>
        )}

        <div className="campo-grupo">
          <label className="campo-label" htmlFor="nota-cierre">Nota de cierre (opcional)</label>
          <textarea
            id="nota-cierre"
            className="campo-texto"
            rows={2}
            placeholder="Ej. Caja cerrada sin novedades"
            value={nota}
            onChange={(e) => setNota(e.target.value)}
          />
        </div>

        <div className="modal__botones">
          <button type="button" className="boton-secundario" onClick={onCerrar} disabled={guardando}>Cancelar</button>
          <button type="button" className="boton-peligro" onClick={guardar} disabled={guardando}>
            <Lock size={16} /> {guardando ? 'Cerrando...' : 'Confirmar Cierre'}
          </button>
        </div>
      </div>
    </div>
  );
}