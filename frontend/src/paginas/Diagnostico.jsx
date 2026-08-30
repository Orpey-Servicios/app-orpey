/**
 * ============================================================
 * Diagnostico.jsx - Sección del DUEÑO para administrar diagnósticos
 * ============================================================
 *
 * Flujo de venta de Orpey:
 *   El TÉCNICO llena el diagnóstico dentro de la orden.
 *   El DUEÑO entra a esta sección y decide: APROBAR ✅ o RECHAZAR ❌
 *   con un comentario, e indica qué instalar al equipo.
 *
 * Aquí el dueño ve todos los equipos que el técnico ya revisó,
 * listos para que él (o ella) decida y cierre la venta llamando
 * al cliente por WhatsApp.
 * ============================================================
 */
import { useState, useEffect } from 'react';
import { ClipboardList, CheckCircle2, XCircle, MessageCircle, Search, User } from 'lucide-react';
import {
  obtenerDiagnosticos,
  aprobarDiagnostico,
  rechazarDiagnostico,
  obtenerWhatsappDiagnostico,
} from '../api/orpey-api';
import './Diagnostico.css';

// Colores según el estado de aprobación
const COLOR_ESTADO = {
  pendiente: { color: '#B8860B', bg: '#FFF8E1', label: 'Pendiente' },
  aprobado: { color: '#2E7D32', bg: '#E8F5E9', label: 'Aprobado' },
  rechazado: { color: '#C62828', bg: '#FFEBEE', label: 'Rechazado' },
};

export default function Diagnostico() {
  const [diagnosticos, setDiagnosticos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [filtro, setFiltro] = useState('');
  const [buscar, setBuscar] = useState('');

  // Modal de aprobación
  const [modalAprobar, setModalAprobar] = useState(null); // { equipo, cliente, repuestos }
  const [comentario, setComentario] = useState('');
  const [decision, setDecision] = useState('');
  const [precio, setPrecio] = useState('');

  // Modal de rechazo
  const [modalRechazar, setModalRechazar] = useState(null);
  const [motivoRechazo, setMotivoRechazo] = useState('');

  // Cargar diagnósticos al iniciar
  useEffect(() => { cargar(); }, [filtro]);

  async function cargar() {
    try {
      setCargando(true);
      let datos = await obtenerDiagnosticos(filtro);
      // Filtrar por búsqueda local (cliente, equipo, nº orden)
      if (buscar.trim()) {
        const q = buscar.toLowerCase();
        datos = datos.filter(d =>
          (d.cliente?.nombre || '').toLowerCase().includes(q) ||
          (d.equipo?.marca || '').toLowerCase().includes(q) ||
          (d.numero_orden || '').toLowerCase().includes(q)
        );
      }
      setDiagnosticos(datos);
    } catch (err) {
      console.error(err);
      alert(err.message);
    } finally {
      setCargando(false);
    }
  }

  // Abrir modal de aprobación
  function abrirAprobar(d) {
    setModalAprobar(d);
    setComentario('');
    setDecision(d.equipo?.repuestos?.[0]?.repuesto || 'Instalar repuesto');
    setPrecio(d.equipo?.precio_venta || '');
  }

  // Confirmar aprobación
  async function confirmarAprobar() {
    try {
      await aprobarDiagnostico(modalAprobar.equipo.id, {
        comentario: comentario || null,
        instalacion_decision: decision || null,
        precio_venta: precio ? Number(precio) : null,
      });
      setModalAprobar(null);
      cargar();
    } catch (err) {
      alert(err.message);
    }
  }

  // Abrir modal de rechazo
  function abrirRechazar(d) {
    setModalRechazar(d);
    setMotivoRechazo('');
  }

  // Confirmar rechazo
  async function confirmarRechazar() {
    try {
      await rechazarDiagnostico(modalRechazar.equipo.id, {
        comentario: motivoRechazo || 'Sin motivo especificado',
      });
      setModalRechazar(null);
      cargar();
    } catch (err) {
      alert(err.message);
    }
  }

  // Enviar diagnóstico por WhatsApp
  async function enviarWhatsapp(equipoId) {
    try {
      const data = await obtenerWhatsappDiagnostico(equipoId);
      window.open(data.link, '_blank');
    } catch (err) {
      alert(err.message);
    }
  }

  return (
    <div className="diagnostico-pagina">
      {/* Encabezado de la sección */}
      <div className="diagnostico__acciones animar-entrada">
        <div className="diagnostico__filtros">
          <select value={filtro} onChange={(e) => setFiltro(e.target.value)} className="campo-texto filtro-select">
            <option value="">Todos los diagnósticos</option>
            <option value="pendiente">Pendientes de aprobación</option>
            <option value="aprobado">Aprobados</option>
            <option value="rechazado">Rechazados</option>
          </select>
          <div className="diagnostico__buscador">
            <Search size={16} style={{ marginRight: '6px', opacity: '.5' }} />
            <input
              className="campo-texto"
              placeholder="Buscar cliente, equipo u orden..."
              value={buscar}
              onChange={(e) => { setBuscar(e.target.value); cargar(); }}
            />
          </div>
        </div>
      </div>

      {/* Contenido */}
      {cargando ? (
        <div className="dashboard__cargando"><div className="spinner" /></div>
      ) : diagnosticos.length === 0 ? (
        <div className="dashboard__vacio">
          <ClipboardList size={44} strokeWidth={1.5} />
          <p>No hay diagnósticos para mostrar</p>
          <small>Cuando el técnico llene un diagnóstico en una orden, aparecerá aquí para que lo apruebes o rechaces.</small>
        </div>
      ) : (
        <div className="diagnostico__lista">
          {diagnosticos.map(d => {
            const estilo = COLOR_ESTADO[d.equipo?.estado_aprobacion] || COLOR_ESTADO.pendiente;
            return (
              <div key={d.equipo.id} className="diagnostico__tarjeta animar-entrada">
                {/* Encabezado de la tarjeta */}
                <div className="diagnostico__tarjeta-head">
                  <div className="diagnostico__cliente">
                    <div className="diagnostico__avatar">{(d.cliente?.nombre || '?').charAt(0)}</div>
                    <div>
                      <strong>{d.cliente?.nombre || 'Cliente'}</strong>
                      <span className="diagnostico__tlf">📞 {d.cliente?.telefono || '—'}</span>
                    </div>
                  </div>
                  <div className="diagnostico__orden">
                    <span className="diagnostico__badge-orden">{d.numero_orden}</span>
                    <span className="diagnostico__estado" style={{ color: estilo.color, background: estilo.bg }}>
                      {estilo.label}
                    </span>
                  </div>
                </div>

                {/* Datos del equipo */}
                <div className="diagnostico__equipo">
                  <div className="diagnostico__titulo-equipo">
                    🖥️ {d.equipo?.tipo_equipo} {d.equipo?.marca || ''} {d.equipo?.modelo || ''}
                  </div>
                  <div className="diagnostico__problema">
                    <strong>Motivo de ingreso:</strong> {d.equipo?.descripcion_problema || '—'}
                  </div>

                  {/* Especificaciones del diagnóstico */}
                  <div className="diagnostico__especificaciones">
                    <div className="diag-spec"><span>⚡ Enciende</span><strong>{d.equipo?.enciende || '—'}</strong></div>
                    <div className="diag-spec"><span>💾 Disco</span><strong>{[d.equipo?.tipo_disco, d.equipo?.capacidad_disco].filter(Boolean).join(' ') || '—'}</strong></div>
                    <div className="diag-spec"><span>🧠 Memoria</span><strong>{[d.equipo?.tipo_memoria, d.equipo?.capacidad_memoria].filter(Boolean).join(' ') || '—'}</strong></div>
                    <div className="diag-spec"><span>⬆️ M2</span><strong>{d.equipo?.slot_m2 || '—'}</strong></div>
                    <div className="diag-spec"><span>📀 Caddy</span><strong>{d.equipo?.slot_caddy || '—'}</strong></div>
                    <div className="diag-spec"><span>🔧 Procesador</span><strong>{d.equipo?.procesador || '—'}</strong></div>
                  </div>

                  {/* Diagnóstico del técnico */}
                  {d.equipo?.diagnostico && (
                    <div className="diagnostico__resumen">
                      <strong>🩺 Diagnóstico y resumen:</strong>
                      <p>{d.equipo.diagnostico}</p>
                    </div>
                  )}

                  {/* Repuestos por proveedor */}
                  {d.equipo?.repuestos?.length > 0 && (
                    <div className="diagnostico__repuestos">
                      <strong>💲 Repuestos ({d.equipo.repuestos.length}):</strong>
                      <div className="diagnostico__repuestos-lista">
                        {d.equipo.repuestos.map((r, i) => (
                          <span key={i} className="repuesto-chip">
                            {r.proveedor || '—'}: {r.repuesto || '—'} <em>(${Number(r.costo || 0).toFixed(2)})</em>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Decisión del dueño (si ya decidió) */}
                  {(d.equipo?.estado_aprobacion === 'aprobado' || d.equipo?.estado_aprobacion === 'rechazado') && (
                    <div className={`diagnostico__decision ${d.equipo.estado_aprobacion}`}>
                      {d.equipo.comentario_dueño && <div><strong>Comentario:</strong> {d.equipo.comentario_dueño}</div>}
                      {d.equipo.instalacion_decision && <div><strong>Se instala:</strong> {d.equipo.instalacion_decision}</div>}
                      {d.equipo.precio_venta && <div><strong>Precio de venta:</strong> ${Number(d.equipo.precio_venta).toFixed(2)}</div>}
                    </div>
                  )}
                </div>

                {/* Acciones */}
                <div className="diagnostico__acciones-tarjeta">
                  <button
                    className="boton-icono"
                    title="Enviar por WhatsApp"
                    onClick={() => enviarWhatsapp(d.equipo.id)}
                    style={{ color: '#25D366' }}
                  >
                    <MessageCircle size={18} />
                  </button>

                  {d.equipo?.estado_aprobacion === 'pendiente' ? (
                    <>
                      <button className="boton-exito" onClick={() => abrirAprobar(d)}>
                        <CheckCircle2 size={16} /> Aprobar
                      </button>
                      <button className="boton-peligro" onClick={() => abrirRechazar(d)}>
                        <XCircle size={16} /> Rechazar
                      </button>
                    </>
                  ) : (
                    <span className="diagnostico__sin-accion">
                      {d.equipo?.estado_aprobacion === 'aprobado' ? 'Decisiones tomadas ✅' : 'Decisiones tomadas ❌'}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ===== MODAL: Aprobar diagnóstico ===== */}
      {modalAprobar && (
        <div className="modal-overlay" onClick={() => setModalAprobar(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3 className="modal__titulo">✅ Aprobar diagnóstico</h3>
            <p className="modal__subtitulo">
              {modalAprobar.cliente?.nombre} — {modalAprobar.equipo?.tipo_equipo} {modalAprobar.equipo?.marca || ''} ({modalAprobar.numero_orden})
            </p>

            <label className="modal__label">¿Qué se va a instalar al equipo?</label>
            <input
              className="campo-texto"
              placeholder="Ej: Instalar batería nueva y pantalla"
              value={decision}
              onChange={(e) => setDecision(e.target.value)}
            />

            <label className="modal__label">Precio de venta ($)</label>
            <input
              className="campo-texto"
              type="number"
              placeholder="Ej: 120"
              value={precio}
              onChange={(e) => setPrecio(e.target.value)}
            />

            <label className="modal__label">Comentario (opcional)</label>
            <textarea
              className="campo-texto modal__textarea"
              placeholder="Comentario para el cliente/equipo..."
              value={comentario}
              onChange={(e) => setComentario(e.target.value)}
            />

            <div className="modal__acciones">
              <button className="boton-secundario" onClick={() => setModalAprobar(null)}>Cancelar</button>
              <button className="boton-exito" onClick={confirmarAprobar}>✅ Confirmar aprobación</button>
            </div>
          </div>
        </div>
      )}

      {/* ===== MODAL: Rechazar diagnóstico ===== */}
      {modalRechazar && (
        <div className="modal-overlay" onClick={() => setModalRechazar(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3 className="modal__titulo">❌ Rechazar diagnóstico</h3>
            <p className="modal__subtitulo">
              {modalRechazar.cliente?.nombre} — {modalRechazar.equipo?.tipo_equipo} {modalRechazar.equipo?.marca || ''} ({modalRechazar.numero_orden})
            </p>

            <label className="modal__label">Motivo del rechazo</label>
            <textarea
              className="campo-texto modal__textarea"
              placeholder="Ej: El costo del repuesto es muy alto, buscar otro proveedor..."
              value={motivoRechazo}
              onChange={(e) => setMotivoRechazo(e.target.value)}
            />

            <div className="modal__acciones">
              <button className="boton-secundario" onClick={() => setModalRechazar(null)}>Cancelar</button>
              <button className="boton-peligro" onClick={confirmarRechazar}>❌ Confirmar rechazo</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
