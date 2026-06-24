/**
 * BADGE DE ESTADO - Etiqueta colorida para mostrar estados
 * 
 * Cada estado de orden tiene su propio color:
 * - Revisión → Azul
 * - En reparación → Naranja
 * - Esperando repuesto → Púrpura
 * - Terminada → Verde
 * - Entregada → Gris
 */
import './BadgeEstado.css';

// Mapa de estados a colores y etiquetas legibles
const ESTADOS = {
  revision:            { etiqueta: 'Revisión',           clase: 'badge--azul' },
  en_reparacion:       { etiqueta: 'En Reparación',      clase: 'badge--naranja' },
  esperando_repuesto:  { etiqueta: 'Esperando Repuesto', clase: 'badge--purpura' },
  terminada:           { etiqueta: 'Reparado',           clase: 'badge--verde' },
  entregada:           { etiqueta: 'Entregado',          clase: 'badge--gris' },
  no_hubo_solucion:    { etiqueta: 'No Hubo Solución',   clase: 'badge--rojo' },
  // Estados de cotización
  abierta:             { etiqueta: 'Abierta',            clase: 'badge--azul' },
  cerrada:             { etiqueta: 'Cerrada',            clase: 'badge--gris' },
  aprobada:            { etiqueta: 'Aprobada',           clase: 'badge--verde' },
  rechazada:           { etiqueta: 'Rechazada',          clase: 'badge--rojo' },
};

export default function BadgeEstado({ estado }) {
  const config = ESTADOS[estado] || { etiqueta: estado, clase: 'badge--gris' };
  return (
    <span className={`badge-estado ${config.clase}`}>
      <span className="badge-estado__punto" />
      {config.etiqueta}
    </span>
  );
}
