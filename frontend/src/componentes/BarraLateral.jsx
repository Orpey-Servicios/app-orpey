/**
 * ============================================================
 * BARRA LATERAL (Sidebar) - Navegación principal
 * ============================================================
 *
 * Este componente es el menú lateral izquierdo que siempre está visible.
 * Contiene:
 * - Logo de Orpey
 * - Links de navegación (Dashboard, Órdenes, Clientes, etc.)
 * - Indicador de página activa
 * - Submenú desplegable para Órdenes
 *
 * ¿Qué es un "componente" en React?
 * Es una pieza reutilizable de la interfaz. Como un bloque de LEGO.
 * Se escribe como una función que devuelve HTML (en realidad JSX).
 *
 * ¿Qué es JSX?
 * Es una mezcla de JavaScript + HTML que React entiende.
 * Se parece a HTML pero se escribe dentro de JavaScript.
 * ============================================================
 */

// Importar hooks de React Router para navegación
// useLocation: nos dice en qué página estamos actualmente
// Link: crea links de navegación SIN recargar la página
import { useState } from 'react';
import { useLocation, Link } from 'react-router-dom';

// Importar iconos de Lucide (librería de iconos modernos)
// Cada icono es un componente que se usa como: <LayoutDashboard />
import {
  LayoutDashboard,
  ClipboardList,
  Users,
  UserCog,
  Wrench,
  FileText,
  Receipt,
  FileCheck2,
  Wallet,
  Settings,
  LogOut,
  ChevronDown,
  Eye,
  FilePlus,
  Stethoscope,
  PieChart
} from 'lucide-react';

import { useAuth } from '../context/AuthContext';
import './BarraLateral.css';

/**
 * Definición de los items del menú de navegación.
 * Cada item tiene: ruta (URL), nombre, e icono.
 * Items con 'subItems' se renderizan como menús desplegables.
 */
const itemsMenu = [
  { ruta: '/',             nombre: 'Dashboard',       icono: LayoutDashboard },
  { ruta: '/resumen',      nombre: 'Reportes',        icono: PieChart },
  {
    nombre: 'Ordenes',
    icono: ClipboardList,
    subItems: [
      { ruta: '/ordenes',       nombre: 'Visualizar Ordenes', icono: Eye },
      { ruta: '/ordenes/nueva', nombre: 'Crear Orden',        icono: FilePlus },
    ],
  },
  { ruta: '/clientes',     nombre: 'Clientes',        icono: Users },
  { ruta: '/diagnosticos', nombre: 'Diagnósticos',    icono: Stethoscope },
  { ruta: '/cotizaciones', nombre: 'Cotizaciones',     icono: FileText },
  { ruta: '/notas-venta',  nombre: 'Notas de Venta',  icono: Receipt },
  { ruta: '/facturacion',  nombre: 'Facturación',     icono: FileCheck2 },
  { ruta: '/caja',         nombre: 'Caja',            icono: Wallet },
];

/**
 * Componente BarraLateral
 *
 * Es una función que devuelve JSX (HTML en JavaScript).
 * "export default" hace que se pueda importar desde otros archivos.
 */
export default function BarraLateral() {
  const location = useLocation();
  const { usuario, logout } = useAuth();
  const [menuAbierto, setMenuAbierto] = useState(null);

  const configSubItems = [
    { ruta: '/configuracion', nombre: 'Ajustes Generales', icono: Settings },
    { ruta: '/tecnicos',      nombre: 'Técnicos',          icono: Wrench },
  ];

  if (usuario?.rol === 'admin') {
    configSubItems.push({ ruta: '/usuarios', nombre: 'Usuarios', icono: UserCog });
  }

  const itemsExtra = [
    {
      nombre: 'Configuración',
      icono: Settings,
      subItems: configSubItems
    }
  ];

  // Caja es operativa (admin/asistente); los técnicos no la ven en el menú.
  const itemsMenuVisibles = usuario?.rol === 'tecnico'
    ? itemsMenu.filter(i => i.nombre !== 'Caja')
    : itemsMenu;

  const todosLosItems = [...itemsMenuVisibles, ...itemsExtra];

  // Verificar si alguna sub-ruta está activa (para marcar el padre)
  function esSubMenuActivo(subItems) {
    return subItems.some(sub => {
      if (sub.ruta === '/ordenes') return location.pathname === '/ordenes';
      return location.pathname.startsWith(sub.ruta);
    });
  }

  function toggleMenu(nombre) {
    setMenuAbierto(prev => prev === nombre ? null : nombre);
  }

  // Auto-abrir el submenu de Ordenes si estamos en una ruta de ordenes
  const ordenesActivas = location.pathname.startsWith('/ordenes');
  const menuOrdenesAbierto = menuAbierto === 'Ordenes' || (ordenesActivas && menuAbierto !== '__cerrado_ordenes');

  return (
    <aside className="barra-lateral" id="sidebar-principal">

      <div className="barra-lateral__logo">
        <img
          src={localStorage.getItem('orpey_custom_logo') || "/logo-orpey.png"}
          alt="Orpey Servicios"
          className="barra-lateral__logo-img"
        />
      </div>

      <nav className="barra-lateral__nav">
        {todosLosItems.map((item) => {
          // ── Item con submenú desplegable ──
          if (item.subItems) {
            const subActivo = esSubMenuActivo(item.subItems);
            const abierto = item.nombre === 'Ordenes' ? menuOrdenesAbierto : menuAbierto === item.nombre;
            const Icono = item.icono;

            return (
              <div key={item.nombre} className="barra-lateral__grupo">
                <button
                  type="button"
                  onClick={() => {
                    if (item.nombre === 'Ordenes') {
                      if (menuOrdenesAbierto) {
                        setMenuAbierto('__cerrado_ordenes');
                      } else {
                        setMenuAbierto('Ordenes');
                      }
                    } else {
                      toggleMenu(item.nombre);
                    }
                  }}
                  id={`nav-${item.nombre.toLowerCase().replace(/\s+/g, '-')}`}
                  className={`barra-lateral__link barra-lateral__link--padre ${subActivo ? 'barra-lateral__link--activo' : ''}`}
                >
                  <Icono size={20} />
                  <span>{item.nombre}</span>
                  <ChevronDown
                    size={16}
                    className={`barra-lateral__chevron ${abierto ? 'barra-lateral__chevron--abierto' : ''}`}
                  />
                  {subActivo && <div className="barra-lateral__indicador" />}
                </button>

                <div className={`barra-lateral__submenu ${abierto ? 'barra-lateral__submenu--abierto' : ''}`}>
                  {item.subItems.map((sub) => {
                    const subEstaActivo = sub.ruta === '/ordenes'
                      ? location.pathname === '/ordenes'
                      : location.pathname === sub.ruta;
                    const SubIcono = sub.icono;

                    return (
                      <Link
                        key={sub.ruta}
                        to={sub.ruta}
                        id={`nav-${sub.nombre.toLowerCase().replace(/\s+/g, '-')}`}
                        className={`barra-lateral__link barra-lateral__link--hijo ${subEstaActivo ? 'barra-lateral__link--sub-activo' : ''}`}
                      >
                        <SubIcono size={16} />
                        <span>{sub.nombre}</span>
                      </Link>
                    );
                  })}
                </div>
              </div>
            );
          }

          // ── Item simple (sin submenú) ──
          const estaActivo = item.ruta === '/'
            ? location.pathname === '/'
            : location.pathname.startsWith(item.ruta);

          const Icono = item.icono;

          return (
            <Link
              key={item.ruta}
              to={item.ruta}
              id={`nav-${item.nombre.toLowerCase().replace(/\s+/g, '-')}`}
              className={`barra-lateral__link ${estaActivo ? 'barra-lateral__link--activo' : ''}`}
            >
              <Icono size={20} />
              <span>{item.nombre}</span>
              {estaActivo && <div className="barra-lateral__indicador" />}
            </Link>
          );
        })}
      </nav>

      <div className="barra-lateral__footer">
        {usuario && (
          <div className="barra-lateral__usuario-info">
            <div className="barra-lateral__usuario-avatar">
              {usuario.nombre?.charAt(0)?.toUpperCase() || 'U'}
            </div>
            <div className="barra-lateral__usuario-detalle">
              <span className="barra-lateral__usuario-nombre">{usuario.nombre}</span>
              <span className="barra-lateral__usuario-rol">{usuario.rol}</span>
            </div>
          </div>
        )}

        <button onClick={logout} className="barra-lateral__link" id="btn-cerrar-sesion" style={{ width: '100%', textAlign: 'left' }}>
          <LogOut size={20} />
          <span>Cerrar Sesión</span>
        </button>
      </div>
    </aside>
  );
}
