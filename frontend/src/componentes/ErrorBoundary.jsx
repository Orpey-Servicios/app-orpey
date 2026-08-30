/**
 * ============================================================
 * ErrorBoundary.jsx - Protección contra páginas en blanco
 * ============================================================
 *
 * ¿Qué problema resuelve?
 * En React, si una página lanza un error (ej: un dato viene mal,
 * un campo es null, una fecha inválida...), TODO se rompe y la
 * pantalla queda EN BLANCO sin explicación.
 *
 * Un "Error Boundary" es un componente "muro" que atrapa esos
 * errores de las páginas hijas y muestra un mensaje claro en
 * lugar de dejar la pantalla en blanco.
 *
 * Así, si una página falla:
 * - Antes: pantalla en blanco total (parecía que todo estaba roto)
 * - Ahora: un mensaje "Algo salió mal" con botón para recargar
 *
 * Es la solución DEFINITIVA al problema de "página en blanco".
 * ============================================================
 */
import { Component } from 'react';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    // Estado que guarda si hubo error o no
    this.state = { tieneError: false };
  }

  // Se llama automáticamente cuando un hijo lanza un error
  static getDerivedStateFromError(error) {
    return { tieneError: true };
  }

  componentDidCatch(error, info) {
    // Registrar el error en la consola para poder depurarlo
    console.error('Error atrapado por ErrorBoundary:', error, info);
  }

  render() {
    // Si hubo error, mostrar un mensaje amigable en vez de pantalla en blanco
    if (this.state.tieneError) {
      return (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', minHeight: '50vh', textAlign: 'center',
          padding: '2rem'
        }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>⚠️</div>
          <h2 style={{ color: '#353534', margin: '0 0 0.5rem' }}>Algo salió mal en esta sección</h2>
          <p style={{ color: '#6b6b6b', margin: '0 0 1.5rem' }}>
            Ocurrió un error inesperado. Puede ser un dato que llegó corrupto.
          </p>
          <button
            onClick={() => window.location.reload()}
            style={{
              background: '#FBC305', color: '#353534', border: 'none',
              padding: '12px 24px', borderRadius: '8px', fontWeight: 'bold',
              cursor: 'pointer', fontSize: '16px'
            }}
          >
            🔄 Recargar página
          </button>
        </div>
      );
    }

    // Si no hay error, renderizar los hijos normalmente
    return this.props.children;
  }
}
