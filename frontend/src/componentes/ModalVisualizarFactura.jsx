import { useState } from 'react';
import { 
  X, Printer, Download, Mail, Copy, Check, FileCheck2, 
  ExternalLink, FileText, CheckCircle2, ShieldCheck, User, Calendar, DollarSign
} from 'lucide-react';
import { 
  descargarPdfFactura, descargarXmlFactura, enviarFacturaEmail, imprimirFactura 
} from '../api/orpey-api';
import './ModalVisualizarFactura.css';

export default function ModalVisualizarFactura({ factura, cliente, orden, onCerrar }) {
  const [tabActiva, setTabActiva] = useState('preview'); // 'preview' o 'detalles'
  const [copiado, setCopiado] = useState(false);
  const [enviandoEmail, setEnviandoEmail] = useState(false);
  const [mensajeEmail, setMensajeEmail] = useState(null);

  if (!factura) return null;

  function copiarClave() {
    if (!factura.clave_acceso) return;
    navigator.clipboard.writeText(factura.clave_acceso);
    setCopiado(true);
    setTimeout(() => setCopiado(false), 2000);
  }

  async function handleEnviarEmail() {
    const emailDestino = cliente?.email || orden?.cliente?.email;
    if (!emailDestino) {
      setMensajeEmail({ tipo: 'error', texto: 'El cliente no tiene un correo electrónico registrado.' });
      return;
    }
    try {
      setEnviandoEmail(true);
      setMensajeEmail(null);
      await enviarFacturaEmail(factura.id, { email: emailDestino });
      setMensajeEmail({ tipo: 'exito', texto: `Factura enviada con éxito a ${emailDestino}` });
      factura.email_enviado = true;
    } catch (err) {
      setMensajeEmail({ tipo: 'error', texto: err.message || 'Error al enviar por correo' });
    } finally {
      setEnviandoEmail(false);
    }
  }

  const esAutorizada = factura.estado_sri === 'autorizado';
  const esProduccion = factura.ambiente === '2';

  return (
    <div className="modal-overlay" onClick={onCerrar}>
      <div className="modal-contenido modal-visualizar-factura animar-entrada" onClick={e => e.stopPropagation()}>
        
        {/* Header del Modal */}
        <div className="modal-visualizar-factura__header">
          <div className="modal-visualizar-factura__titulo-area">
            <div className="modal-visualizar-factura__icono">
              <FileCheck2 size={24} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 700 }}>Factura Electrónica SRI</h3>
                <span className={`badge-sri-estado badge-sri-estado--${factura.estado_sri || 'generada'}`}>
                  {factura.estado_sri ? factura.estado_sri.toUpperCase() : 'EMITIDA'}
                </span>
                <span className="badge-ambiente">
                  {esProduccion ? 'PRODUCCIÓN' : 'PRUEBAS'}
                </span>
              </div>
              <p style={{ margin: '3px 0 0', fontSize: '13px', color: 'var(--texto-secundario)' }}>
                Comprobante N° <strong>{factura.numero_documento || 'Sin número'}</strong>
                {orden?.numero_orden ? ` · Orden ${orden.numero_orden}` : ''}
              </p>
            </div>
          </div>
          <button className="boton-icono" onClick={onCerrar} title="Cerrar ventana">
            <X size={20} />
          </button>
        </div>

        {/* Barra de Acciones Rápidas */}
        <div className="modal-visualizar-factura__acciones-bar">
          <div className="modal-visualizar-factura__tabs">
            <button 
              className={`tab-btn ${tabActiva === 'preview' ? 'tab-btn--activo' : ''}`}
              onClick={() => setTabActiva('preview')}
            >
              <FileText size={15} /> Vista Previa (RIDE)
            </button>
            <button 
              className={`tab-btn ${tabActiva === 'detalles' ? 'tab-btn--activo' : ''}`}
              onClick={() => setTabActiva('detalles')}
            >
              <ShieldCheck size={15} /> Datos Fiscales SRI
            </button>
          </div>

          <div className="modal-visualizar-factura__botones">
            <button 
              className="boton-primario"
              onClick={() => imprimirFactura(factura.id)}
              title="Abrir RIDE en pestaña para imprimir inmediatamente"
            >
              <Printer size={16} /> Imprimir
            </button>
            <button 
              className="boton-secundario"
              onClick={() => descargarPdfFactura(factura.id, false)}
              title="Descargar archivo PDF (RIDE)"
            >
              <Download size={16} /> PDF
            </button>
            <button 
              className="boton-secundario"
              onClick={() => descargarXmlFactura(factura.id)}
              title="Descargar archivo XML firmado"
            >
              <Download size={16} /> XML
            </button>
            <button 
              className="boton-secundario"
              onClick={handleEnviarEmail}
              disabled={enviandoEmail}
              title={factura.email_enviado ? 'Reenviar factura por correo' : 'Enviar factura por correo al cliente'}
            >
              <Mail size={16} /> {enviandoEmail ? 'Enviando...' : (factura.email_enviado ? 'Reenviar' : 'Enviar Correo')}
            </button>
          </div>
        </div>

        {mensajeEmail && (
          <div className={`modal-visualizar-factura__mensaje modal-visualizar-factura__mensaje--${mensajeEmail.tipo}`}>
            {mensajeEmail.tipo === 'exito' ? <CheckCircle2 size={16} /> : <X size={16} />}
            <span>{mensajeEmail.texto}</span>
          </div>
        )}

        {/* Cuerpo del Modal */}
        <div className="modal-visualizar-factura__cuerpo">
          {tabActiva === 'preview' ? (
            <div className="modal-visualizar-factura__iframe-contenedor">
              <iframe 
                src={`/api/facturacion/${factura.id}/pdf?inline=true`} 
                title={`Factura ${factura.numero_documento}`}
                className="modal-visualizar-factura__iframe"
              />
            </div>
          ) : (
            <div className="modal-visualizar-factura__detalles-grid animar-entrada">
              
              {/* Clave de Acceso y Autorización */}
              <div className="detalles-card">
                <h4><ShieldCheck size={16} /> Información Tributaria SRI</h4>
                <div className="detalles-fila">
                  <span className="detalles-label">Clave de Acceso (49 dígitos):</span>
                  <div className="detalles-clave-box">
                    <code className="detalles-clave">{factura.clave_acceso || 'Pendiente de generación'}</code>
                    {factura.clave_acceso && (
                      <button className="boton-icono" onClick={copiarClave} title="Copiar clave">
                        {copiado ? <Check size={14} color="#10B981" /> : <Copy size={14} />}
                      </button>
                    )}
                  </div>
                </div>

                <div className="detalles-fila">
                  <span className="detalles-label">N° Autorización:</span>
                  <span className="detalles-valor">{factura.numero_autorizacion || 'No autorizado aún'}</span>
                </div>

                <div className="detalles-grid-2">
                  <div className="detalles-fila">
                    <span className="detalles-label">Fecha de Emisión:</span>
                    <span className="detalles-valor">
                      {factura.fecha_emision ? new Date(factura.fecha_emision).toLocaleString('es-EC') : '—'}
                    </span>
                  </div>
                  <div className="detalles-fila">
                    <span className="detalles-label">Fecha de Autorización:</span>
                    <span className="detalles-valor">
                      {factura.fecha_autorizacion ? new Date(factura.fecha_autorizacion).toLocaleString('es-EC') : '—'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Datos del Cliente */}
              <div className="detalles-card">
                <h4><User size={16} /> Cliente / Receptor</h4>
                <div className="detalles-grid-2">
                  <div className="detalles-fila">
                    <span className="detalles-label">Razón Social / Nombre:</span>
                    <span className="detalles-valor"><strong>{cliente?.nombre} {cliente?.apellido}</strong></span>
                  </div>
                  <div className="detalles-fila">
                    <span className="detalles-label">Cédula / RUC:</span>
                    <span className="detalles-valor">{cliente?.cedula_ruc || '9999999999999 (Consumidor Final)'}</span>
                  </div>
                  <div className="detalles-fila">
                    <span className="detalles-label">Correo Electrónico:</span>
                    <span className="detalles-valor">{cliente?.email || 'Sin correo registrado'}</span>
                  </div>
                  <div className="detalles-fila">
                    <span className="detalles-label">Dirección:</span>
                    <span className="detalles-valor">{cliente?.direccion || 'Ecuador'}</span>
                  </div>
                </div>
              </div>

              {/* Totales */}
              <div className="detalles-card">
                <h4><DollarSign size={16} /> Valores de la Factura</h4>
                <div className="detalles-totales-caja">
                  <div className="totales-fila">
                    <span>Subtotal 15%:</span>
                    <strong>${Number(factura.subtotal || 0).toFixed(2)}</strong>
                  </div>
                  <div className="totales-fila">
                    <span>IVA (15%):</span>
                    <strong>${Number(factura.iva || 0).toFixed(2)}</strong>
                  </div>
                  <div className="totales-fila totales-fila--total">
                    <span>TOTAL FACTURADO:</span>
                    <span>${Number(factura.total || 0).toFixed(2)}</span>
                  </div>
                </div>
              </div>

            </div>
          )}
        </div>

        {/* Footer */}
        <div className="modal-visualizar-factura__footer">
          <a 
            href="/facturacion" 
            target="_blank" 
            rel="noopener noreferrer"
            className="link-modulo-facturacion"
          >
            <ExternalLink size={14} /> Ir al módulo de facturación
          </a>
          <button className="boton-secundario" onClick={onCerrar}>
            Cerrar
          </button>
        </div>

      </div>
    </div>
  );
}
