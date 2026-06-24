/**
 * app-orpey — Sistema de gestión de taller para Orpey Servicios
 * Copyright (C) 2026 Orpey Servicios
 * 
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 * 
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 * 
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 * 
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
