/**
 * ============================================================
 * App.jsx - Componente raíz de la aplicación
 * ============================================================
 *
 * Este es el componente PRINCIPAL que define:
 * 1. El layout general (sidebar + header + contenido)
 * 2. Las RUTAS de navegación (qué página mostrar según la URL)
 *
 * ¿Qué es React Router?
 * Es una librería que permite navegar entre "páginas" sin recargar
 * el navegador. Cada ruta (<Route>) mapea una URL a un componente.
 *
 * ¿Qué es <Outlet />?
 * Es un "hueco" donde React Router inserta el componente de la ruta actual.
 * Es como un marco de foto: el marco (layout) es fijo, pero la foto
 * (contenido) cambia según la ruta.
 * ============================================================
 */

import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Outlet } from 'react-router-dom';

// Importar los componentes de layout
import BarraLateral from './componentes/BarraLateral';
import Encabezado from './componentes/Encabezado';

// Importar ruta protegida
import RutaProtegida from './componentes/RutaProtegida';

// Importar el ErrorBoundary (protege contra páginas en blanco)
import ErrorBoundary from './componentes/ErrorBoundary';

// Importar las páginas
import Dashboard from './paginas/Dashboard';
import Ordenes from './paginas/Ordenes';
import OrdenFormulario from './paginas/OrdenFormulario';
import OrdenDetalle from './paginas/OrdenDetalle';
import Clientes from './paginas/Clientes';
import ClienteDetalle from './paginas/ClienteDetalle';
import Tecnicos from './paginas/Tecnicos';
import Cotizaciones from './paginas/Cotizaciones';
import NotasVenta from './paginas/NotasVenta';
import Facturas from './paginas/Facturas';
import Caja from './paginas/Caja';
import Login from './paginas/Login';
import Usuarios from './paginas/Usuarios';
import Diagnostico from './paginas/Diagnostico';
import Configuracion from './paginas/Configuracion';
import Resumen from './paginas/Resumen';

/**
 * Layout principal: Sidebar fijo + Header + Contenido dinámico
 * 
 * Estructura visual:
 * ┌──────────┬────────────────────────────┐
 * │          │       ENCABEZADO           │
 * │  BARRA   ├────────────────────────────┤
 * │ LATERAL  │                            │
 * │          │       CONTENIDO            │
 * │          │       (cambia según        │
 * │          │        la ruta)            │
 * └──────────┴────────────────────────────┘
 */
function LayoutPrincipal() {
  return (
    <div className="layout">
      {/* Sidebar siempre visible */}
      <BarraLateral />

      {/* Área de contenido (a la derecha del sidebar) */}
      <div className="layout__contenido">
        {/* Header siempre visible */}
        <Encabezado />

        {/* Outlet: aquí se renderiza la página actual (protegida por ErrorBoundary) */}
        <main className="layout__main">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
}

/**
 * Componente App: define todas las rutas de la aplicación
 */
export default function App() {
  // Aplicar configuraciones guardadas al iniciar la app
  useEffect(() => {
    const customColor = localStorage.getItem('orpey_custom_primary_color');
    if (customColor) {
      document.documentElement.style.setProperty('--color-primario', customColor);
    }
    
    const isDark = localStorage.getItem('orpey_dark_mode') === 'true';
    if (isDark) {
      document.body.classList.add('dark-theme');
    }
  }, []);

  return (
    // BrowserRouter: habilita el enrutamiento basado en la URL del navegador
    <BrowserRouter>
      <Routes>
        {/* Ruta de login (sin layout, sin sidebar) */}
        <Route path="/login" element={<Login />} />

        {/* Ruta protegida con layout principal */}
        <Route element={<RutaProtegida><LayoutPrincipal /></RutaProtegida>}>
          {/* index = ruta raíz "/" */}
          <Route index element={<Dashboard />} />

          {/* Rutas de Órdenes */}
          <Route path="/ordenes" element={<Ordenes />} />
          <Route path="/ordenes/nueva" element={<OrdenFormulario />} />
          <Route path="/ordenes/:id" element={<OrdenDetalle />} />
          <Route path="/ordenes/:id/editar" element={<OrdenFormulario />} />

          {/* Rutas de Clientes */}
          <Route path="/clientes" element={<Clientes />} />
          <Route path="/clientes/:id" element={<ClienteDetalle />} />

          {/* Rutas de Técnicos */}
          <Route path="/tecnicos" element={<Tecnicos />} />

          {/* Rutas de Cotizaciones */}
          <Route path="/cotizaciones" element={<Cotizaciones />} />

          {/* Rutas de Notas de Venta */}
          <Route path="/notas-venta" element={<NotasVenta />} />

          {/* Rutas de Facturación Electrónica SRI */}
          <Route path="/facturacion" element={<Facturas />} />

          {/* Rutas de Caja */}
          <Route path="/caja" element={<Caja />} />

          {/* Rutas de Usuarios (solo admin) */}
          <Route path="/usuarios" element={<Usuarios />} />

          {/* Rutas de Diagnósticos (revisión del dueño) */}
          <Route path="/diagnosticos" element={<Diagnostico />} />

          {/* Rutas de Configuración */}
          <Route path="/configuracion" element={<Configuracion />} />

          {/* Rutas de Resumen/Estadísticas */}
          <Route path="/resumen" element={<Resumen />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
