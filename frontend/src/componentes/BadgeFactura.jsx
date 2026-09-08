import './BadgeFactura.css';

/**
 * Badge para indicar si una orden de servicio ha sido facturada con el SRI,
 * si está lista para facturar (terminada y pagada), o si la factura fue anulada.
 */
export default function BadgeFactura({ orden, mostrarNumero = false, estiloExtra = {} }) {
  if (!orden) return null;
  const factura = orden.factura;
  const porCancelar = Number(orden.total_orden || 0) - Number(orden.abono || 0);
  const esTerminadaOPagada = ['terminada', 'entregada'].includes(orden.estado) && porCancelar <= 0;

  if (factura) {
    const esAnulada = factura.estado_sri === 'anulada' || factura.estado_sri === 'anulada_parcial';
    if (esAnulada) {
      return (
        <span
          className="badge-factura badge-factura--anulada"
          style={estiloExtra}
          title={`Factura ${factura.numero_documento || ''} anulada`}
        >
          🚫 Factura Anulada
        </span>
      );
    }
    return (
      <span
        className="badge-factura badge-factura--ok"
        style={estiloExtra}
        title={`Factura SRI: ${factura.numero_documento || 'Emitida'} (Estado: ${factura.estado_sri})`}
      >
        🧾 Facturada{mostrarNumero && factura.numero_documento ? ` · ${factura.numero_documento}` : ''}
      </span>
    );
  }

  if (esTerminadaOPagada && orden.estado !== 'cancelada') {
    return (
      <span
        className="badge-factura badge-factura--pendiente"
        style={estiloExtra}
        title="Orden con saldo $0.00 lista para facturar"
      >
        ⏳ Por facturar
      </span>
    );
  }

  return null;
}
