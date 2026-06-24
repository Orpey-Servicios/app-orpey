/**
 * ============================================================
 * main.jsx - Punto de entrada de la aplicación React
 * ============================================================
 *
 * Este archivo es el PRIMERO que se ejecuta.
 * 1. Busca el elemento HTML con id="root" en index.html
 * 2. Crea una "raíz" de React dentro de ese elemento
 * 3. Renderiza (dibuja) el componente <App /> dentro
 *
 * StrictMode: modo estricto de React que ayuda a detectar
 * problemas potenciales durante el desarrollo. No afecta producción.
 * ============================================================
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

// Importar estilos globales (sistema de diseño)
import './index.css';

// Importar el AuthProvider para envolver la app
import { AuthProvider } from './context/AuthContext';

// Importar el componente principal
import App from './App';

// Renderizar la aplicación dentro del div#root de index.html
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </StrictMode>,
);
