import { useState } from 'react';
import { 
  X, FileCheck2, Send, CheckCircle2, Download, Mail, AlertTriangle, 
  Building2, User, Phone, MapPin, Receipt, ShieldCheck, Copy, Check, ExternalLink, Loader2
} from 'lucide-react';
import { 
  generarFactura, descargarPdfFactura, descargarXmlFactura, 
  enviarFacturaEmail, actualizarCliente 
} from '../api/orpey-api';

const FORMAS_PAGO_SRI = [
  { codigo: '01', etiqueta: '01 - Sin utilización del sistema financiero (Efectivo / Caja)' },
  { codigo: '20', etiqueta: '20 - Otros con utilización del sistema financiero (Transferencia / Tarjeta / DeUna)' },
];

export default function ModalFacturarOrden({ orden, cliente: clienteProp, onCerrar, onFacturaCreada }) {
  const cliente = clienteProp || orden?.cliente || {};
  
  // Estados para datos editables rápidos antes de facturar
  const [email, setEmail] = useState(cliente.email || '');
  const [direccion, setDireccion] = useState(cliente.direccion || '');
  const [formaPago, setFormaPago] = useState('01');
  const [editandoCliente, setEditandoCliente] = useState(false);
  const [guardandoCliente, setGuardandoCliente] = useState(false);

  // Estados de proceso
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);
  const [facturaGenerada, setFacturaGenerada] = useState(null);
  const [copiado, setCopiado] = useState(false);
  const [enviandoEmail, setEnviandoEmail] = useState(false);
  const [mensajeEmail, setMensajeEmail] = useState(null);

  const totalOrden = Number(orden?.total_orden || 0);
  const abonoOrden = Number(orden?.abono || 0);
  const porCancelar = totalOrden - abonoOrden;
  const estaPagada = porCancelar <= 0;
  const esEstadoValido = ['entregada', 'terminada'].includes(orden?.estado);

  // Guardar cambios rápidos de cliente si los editó
  async function guardarCambiosCliente() {
    if (!cliente.id) return;
    try {
      setGuardandoCliente(true);
      await actualizarCliente(cliente.id, { email, direccion });
      cliente.email = email;
      cliente.direccion = direccion;
      setEditandoCliente(false);
    } catch (e) {
      setError(`No se pudo actualizar el cliente: ${e.message}`);
    } finally {
      setGuardandoCliente(false);
    }
  }

  // Confirmar y generar factura
  async function handleGenerar() {
    if (!estaPagada) {
      setError('La orden debe estar pagada al 100% para generar la factura.');
      return;
    }
    if (!esEstadoValido) {
      setError('La orden debe estar en estado terminada o entregada para ser facturada.');
      return;
    }

    try {
      setGuardando(true);
      setError(null);

      // Si el email o dirección cambiaron y no se guardaron
      if (cliente.id && (email !== cliente.email || direccion !== cliente.direccion)) {
        await actualizarCliente(cliente.id, { email, direccion });
        cliente.email = email;
        cliente.direccion = direccion;
      }

      const res = await generarFactura({
        orden_servicio_id: orden.id
      });

      setFacturaGenerada(res);
      if (onFacturaCreada) {
        onFacturaCreada(res);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setGuardando(false);
    }
  }

  // Copiar clave de acceso
  function copiarClave() {
    if (!facturaGenerada?.clave_acceso) return;
    navigator.clipboard.writeText(facturaGenerada.clave_acceso);
    setCopiado(true);
    setTimeout(() => setCopiado(false), 2000);
  }

  // Enviar email desde el modal
  async function handleEnviarEmail() {
    if (!facturaGenerada?.id) return;
    const destino = email || cliente.email;
    if (!destino) {
      setMensajeEmail({ tipo: 'error', texto: 'Ingrese un correo electrónico válido' });
      return;
    }
    try {
      setEnviandoEmail(true);
      setMensajeEmail(null);
      await enviarFacturaEmail(facturaGenerada.id, destino);
      setMensajeEmail({ tipo: 'exito', texto: `Factura enviada exitosamente a ${destino}` });
    } catch (err) {
      setMensajeEmail({ tipo: 'error', texto: err.message });
    } finally {
      setEnviandoEmail(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onCerrar} style={{ zIndex: 1100 }}>
      <div 
        className="modal modal--lg animar-entrada" 
        onClick={e => e.stopPropagation()}
        style={{ maxWidth: '640px', width: '95%', maxHeight: '90vh', overflowY: 'auto' }}
      >
        {/* Encabezado del Modal */}
        <div className="modal__header" style={{ borderBottom: '1px solid #e5e7eb', paddingBottom: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ 
              width: '40px', height: '40px', borderRadius: '10px', 
              background: '#EFF6FF', display: 'flex', alignItems: 'center', 
              justifyContent: 'center', color: '#2563EB' 
            }}>
              <FileCheck2 size={22} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '18px', fontWeight: '700', color: '#111827' }}>
                Factura Electrónica SRI
              </h3>
              <p style={{ margin: '2px 0 0', fontSize: '13px', color: '#6B7280' }}>
                Orden de Servicio: <strong style={{ color: '#1F2937' }}>{orden?.numero_orden}</strong>
              </p>
            </div>
          </div>
          <button className="boton-icono" onClick={onCerrar} title="Cerrar"><X size={20} /></button>
        </div>

        {/* CONTENIDO 1: Pantalla de Éxito si ya se generó */}
        {facturaGenerada ? (
          <div style={{ padding: '20px 0' }}>
            <div style={{ textAlign: 'center', padding: '16px 0 24px' }}>
              <CheckCircle2 size={54} color="#16A34A" style={{ margin: '0 auto 12px' }} />
              <h4 style={{ fontSize: '19px', fontWeight: '700', color: '#166534', margin: '0 0 6px' }}>
                ¡Factura Generada y Firmada!
              </h4>
              <p style={{ fontSize: '14px', color: '#4B5563', margin: 0 }}>
                Comprobante electrónico N° <strong style={{ color: '#111827', fontSize: '16px' }}>{facturaGenerada.numero_documento}</strong>
              </p>
            </div>

            {/* Clave de Acceso */}
            <div style={{ 
              background: '#F9FAFB', border: '1px solid #E5E7EB', borderRadius: '10px', 
              padding: '12px 16px', marginBottom: '20px' 
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span style={{ fontSize: '11px', textTransform: 'uppercase', color: '#6B7280', fontWeight: '700' }}>
                  Clave de Acceso SRI (49 dígitos)
                </span>
                <button 
                  type="button" 
                  onClick={copiarClave}
                  style={{ 
                    background: 'none', border: 'none', cursor: 'pointer', 
                    fontSize: '12px', color: '#2563EB', display: 'flex', alignItems: 'center', gap: '4px' 
                  }}
                >
                  {copiado ? <Check size={14} color="#16A34A" /> : <Copy size={14} />}
                  {copiado ? '¡Copiado!' : 'Copiar clave'}
                </button>
              </div>
              <div style={{ 
                fontFamily: 'monospace', fontSize: '12px', wordBreak: 'break-all', 
                color: '#374151', background: '#FFFFFF', padding: '8px 10px', 
                borderRadius: '6px', border: '1px solid #E5E7EB' 
              }}>
                {facturaGenerada.clave_acceso}
              </div>
            </div>

            {/* Resumen Total */}
            <div style={{ 
              display: 'flex', justifyContent: 'space-between', alignItems: 'center', 
              padding: '12px 16px', background: '#F0FDF4', borderRadius: '8px', 
              border: '1px solid #BBF7D0', marginBottom: '20px' 
            }}>
              <span style={{ fontWeight: '600', color: '#166534' }}>Total Factura:</span>
              <span style={{ fontSize: '20px', fontWeight: '800', color: '#15803D' }}>
                ${Number(facturaGenerada.total).toFixed(2)}
              </span>
            </div>

            {/* Enviar por correo */}
            <div style={{ 
              border: '1px solid #E5E7EB', borderRadius: '10px', 
              padding: '14px', marginBottom: '20px', background: '#FFFFFF' 
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <Mail size={16} color="#2563EB" />
                <strong style={{ fontSize: '13px', color: '#1F2937' }}>Enviar Comprobante por Correo (PDF + XML)</strong>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input 
                  type="email" 
                  className="campo-texto" 
                  placeholder="cliente@ejemplo.com"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  style={{ flex: 1, fontSize: '13px' }}
                />
                <button
                  type="button"
                  className="boton-primario"
                  onClick={handleEnviarEmail}
                  disabled={enviandoEmail || !email}
                  style={{ padding: '8px 14px', fontSize: '13px', whiteSpace: 'nowrap' }}
                >
                  {enviandoEmail ? <Loader2 size={14} className="animar-spin" /> : <Mail size={14} />}
                  {enviandoEmail ? 'Enviando...' : 'Enviar'}
                </button>
              </div>
              {mensajeEmail && (
                <p style={{ 
                  margin: '8px 0 0', fontSize: '12px', 
                  color: mensajeEmail.tipo === 'exito' ? '#15803D' : '#DC2626' 
                }}>
                  {mensajeEmail.texto}
                </p>
              )}
            </div>

            {/* Botones de acción post-facturación */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '16px' }}>
              <button
                type="button"
                className="boton-secundario"
                onClick={() => descargarPdfFactura(facturaGenerada.id, facturaGenerada.numero_documento)}
                style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', padding: '10px' }}
              >
                <Download size={16} /> Descargar RIDE (PDF)
              </button>
              <button
                type="button"
                className="boton-secundario"
                onClick={() => descargarXmlFactura(facturaGenerada.id, facturaGenerada.numero_documento)}
                style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', padding: '10px' }}
              >
                <Download size={16} /> Descargar XML Firmado
              </button>
            </div>

            <div className="modal__botones" style={{ marginTop: '20px', borderTop: '1px solid #E5E7EB', paddingTop: '14px' }}>
              <button type="button" className="boton-primario" onClick={onCerrar} style={{ width: '100%', padding: '11px' }}>
                Entendido / Finalizar
              </button>
            </div>
          </div>
        ) : (
          /* CONTENIDO 2: Formulario de Pre-facturación */
          <div style={{ padding: '16px 0 0' }}>
            {error && (
              <div className="dashboard__error" style={{ marginBottom: '16px' }}>
                <p>⚠️ {error}</p>
              </div>
            )}

            {!estaPagada && (
              <div style={{ 
                padding: '12px', background: '#FEF2F2', border: '1px solid #FCA5A5', 
                borderRadius: '8px', color: '#991B1B', fontSize: '13px', 
                marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' 
              }}>
                <AlertTriangle size={18} />
                <span>Esta orden tiene un saldo pendiente de <strong>${porCancelar.toFixed(2)}</strong>. Debe pagarse al 100% para poder facturarse.</span>
              </div>
            )}

            {!esEstadoValido && (
              <div style={{ 
                padding: '12px', background: '#FFFBEB', border: '1px solid #FCD34D', 
                borderRadius: '8px', color: '#92400E', fontSize: '13px', 
                marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' 
              }}>
                <AlertTriangle size={18} />
                <span>La orden está en estado <strong>{orden?.estado}</strong>. Debe estar terminada o entregada para ser facturada.</span>
              </div>
            )}

            {/* Tarjeta de Datos del Cliente */}
            <div style={{ 
              background: '#F9FAFB', border: '1px solid #E5E7EB', borderRadius: '10px', 
              padding: '14px 16px', marginBottom: '16px' 
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <span style={{ fontSize: '12px', textTransform: 'uppercase', color: '#4B5563', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <User size={14} color="#2563EB" /> Cliente (Receptor)
                </span>
                <button
                  type="button"
                  onClick={() => setEditandoCliente(!editandoCliente)}
                  style={{ background: 'none', border: 'none', color: '#2563EB', fontSize: '12px', fontWeight: '600', cursor: 'pointer' }}
                >
                  {editandoCliente ? 'Cancelar edición' : 'Editar datos'}
                </button>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '13px' }}>
                <div>
                  <span style={{ color: '#6B7280', fontSize: '11px', display: 'block' }}>Razón Social / Nombre:</span>
                  <strong style={{ color: '#111827' }}>{cliente.nombre} {cliente.apellido}</strong>
                </div>
                <div>
                  <span style={{ color: '#6B7280', fontSize: '11px', display: 'block' }}>Cédula / RUC:</span>
                  <strong style={{ color: '#111827' }}>{cliente.cedula_ruc || '9999999999999 (Consumidor Final)'}</strong>
                </div>
              </div>

              {editandoCliente ? (
                <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px dashed #D1D5DB' }}>
                  <div className="orden-form__grid-2" style={{ marginBottom: '8px' }}>
                    <div className="campo-grupo">
                      <label className="campo-label" style={{ fontSize: '11px' }}>Correo Electrónico *</label>
                      <input 
                        type="email" 
                        className="campo-texto" 
                        value={email} 
                        onChange={e => setEmail(e.target.value)} 
                        placeholder="correo@ejemplo.com"
                        style={{ fontSize: '12px', padding: '6px 10px' }}
                      />
                    </div>
                    <div className="campo-grupo">
                      <label className="campo-label" style={{ fontSize: '11px' }}>Dirección *</label>
                      <input 
                        type="text" 
                        className="campo-texto" 
                        value={direccion} 
                        onChange={e => setDireccion(e.target.value.toUpperCase())} 
                        placeholder="Dirección del cliente"
                        style={{ fontSize: '12px', padding: '6px 10px' }}
                      />
                    </div>
                  </div>
                  <button
                    type="button"
                    className="boton-primario"
                    onClick={guardarCambiosCliente}
                    disabled={guardandoCliente}
                    style={{ fontSize: '12px', padding: '5px 12px' }}
                  >
                    {guardandoCliente ? 'Guardando...' : 'Guardar datos de cliente'}
                  </button>
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '13px', marginTop: '8px' }}>
                  <div>
                    <span style={{ color: '#6B7280', fontSize: '11px', display: 'block' }}>Correo Electrónico:</span>
                    <span style={{ color: email ? '#111827' : '#DC2626' }}>
                      {email || '⚠️ Sin correo (Recomendado para SRI)'}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: '#6B7280', fontSize: '11px', display: 'block' }}>Dirección:</span>
                    <span style={{ color: '#111827' }}>{direccion || 'Guayaquil'}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Detalle de Equipos y Trabajos */}
            <div style={{ 
              background: '#FFFFFF', border: '1px solid #E5E7EB', borderRadius: '10px', 
              padding: '14px 16px', marginBottom: '16px' 
            }}>
              <span style={{ fontSize: '12px', textTransform: 'uppercase', color: '#4B5563', fontWeight: '700', display: 'block', marginBottom: '10px' }}>
                Rubros a Facturar
              </span>

              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #E5E7EB', color: '#6B7280', textAlign: 'left', fontSize: '11px' }}>
                    <th style={{ paddingBottom: '6px' }}>Descripción</th>
                    <th style={{ paddingBottom: '6px', textAlign: 'center', width: '50px' }}>Cant.</th>
                    <th style={{ paddingBottom: '6px', textAlign: 'right', width: '80px' }}>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {(orden?.equipos || []).map((eq, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #F3F4F6' }}>
                      <td style={{ padding: '8px 0' }}>
                        <div style={{ fontWeight: '600', color: '#1F2937' }}>
                          Servicio Técnico: {[eq.marca, eq.modelo].filter(Boolean).join(' ') || eq.tipo_equipo}
                        </div>
                        <div style={{ fontSize: '11px', color: '#6B7280' }}>
                          {eq.trabajo_a_realizar || eq.descripcion_problema || 'Mantenimiento y reparación'}
                        </div>
                      </td>
                      <td style={{ textAlign: 'center', color: '#4B5563' }}>1</td>
                      <td style={{ textAlign: 'right', fontWeight: '600', color: '#111827' }}>
                        ${Number(eq.costo || 0).toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Desglose de Totales */}
              <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid #E5E7EB' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', color: '#4B5563', marginBottom: '4px' }}>
                  <span>Subtotal:</span>
                  <span>${totalOrden.toFixed(2)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', color: '#4B5563', marginBottom: '6px' }}>
                  <span>IVA (15% incluido / según config):</span>
                  <span>$0.00</span>
                </div>
                <div style={{ 
                  display: 'flex', justifyContent: 'space-between', fontSize: '16px', 
                  fontWeight: '700', color: '#111827', borderTop: '1px dashed #D1D5DB', 
                  paddingTop: '6px' 
                }}>
                  <span>Total Factura SRI:</span>
                  <span style={{ color: '#15803D' }}>${totalOrden.toFixed(2)}</span>
                </div>
              </div>
            </div>

            {/* Forma de Pago SRI */}
            <div className="campo-grupo" style={{ marginBottom: '20px' }}>
              <label className="campo-label" style={{ fontSize: '12px', fontWeight: '600' }}>
                Forma de Pago (Catálogo SRI)
              </label>
              <select 
                className="campo-texto" 
                value={formaPago} 
                onChange={e => setFormaPago(e.target.value)}
                style={{ fontSize: '13px' }}
              >
                {FORMAS_PAGO_SRI.map(f => (
                  <option key={f.codigo} value={f.codigo}>{f.etiqueta}</option>
                ))}
              </select>
            </div>

            {/* Botones de acción */}
            <div className="modal__botones" style={{ borderTop: '1px solid #E5E7EB', paddingTop: '14px' }}>
              <button type="button" className="boton-secundario" onClick={onCerrar} disabled={guardando}>
                Cancelar
              </button>
              <button 
                type="button" 
                className="boton-primario" 
                onClick={handleGenerar} 
                disabled={guardando || !estaPagada || !esEstadoValido}
                style={{ 
                  backgroundColor: estaPagada && esEstadoValido ? '#2563EB' : '#9CA3AF', 
                  display: 'flex', alignItems: 'center', gap: '8px' 
                }}
              >
                {guardando ? <Loader2 size={16} className="animar-spin" /> : <ShieldCheck size={16} />}
                {guardando ? 'Generando y firmando...' : 'Confirmar y Emitir Factura SRI'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
