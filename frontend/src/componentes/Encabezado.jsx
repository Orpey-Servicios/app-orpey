/**
 * ENCABEZADO (Header) - Barra superior
 */
import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Bell, Search, User } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import './Encabezado.css';

const titulosPagina = {
  '/': 'Dashboard',
  '/ordenes': 'Ordenes de Servicio',
  '/clientes': 'Gestión de Clientes',
  '/tecnicos': 'Técnicos',
  '/cotizaciones': 'Cotizaciones',
  '/notas-venta': 'Notas de Venta',
  '/usuarios': 'Usuarios',
  '/configuracion': 'Configuración',
  '/caja': 'Caja',
};

const subtitulosPagina = {
  '/': 'Resumen general del servicio técnico',
  '/ordenes': 'Gestiona las ordenes de reparación',
  '/clientes': 'Administra la información de tus clientes',
  '/tecnicos': 'Gestiona tu equipo de técnicos',
  '/cotizaciones': 'Presupuestos y cotizaciones',
  '/notas-venta': 'Facturación y notas de venta',
  '/usuarios': 'Administra los usuarios del sistema',
  '/configuracion': 'Datos del negocio y preferencias',
  '/caja': 'Apertura, arqueo y cierre diario de caja',
};

export default function Encabezado() {
  const location = useLocation();
  const { usuario } = useAuth();
  const rutaBase = '/' + (location.pathname.split('/')[1] || '');
  const titulo = titulosPagina[rutaBase] || 'Orpey Servicios';
  const subtitulo = subtitulosPagina[rutaBase] || '';
  const [isVisible, setIsVisible] = useState(true);
  const [prevScrollY, setPrevScrollY] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY;

      if (currentScrollY > prevScrollY && currentScrollY > 100) {
        setIsVisible(false);
      } else {
        setIsVisible(true);
      }
      setPrevScrollY(currentScrollY);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [prevScrollY]);

  return (
    <header className="encabezado" id="header-principal" data-visible={isVisible}>
      <div className="encabezado__info">
        <h1 className="encabezado__titulo">{titulo}</h1>
        {subtitulo && <p className="encabezado__subtitulo">{subtitulo}</p>}
      </div>
      <div className="encabezado__acciones">
        <div className="encabezado__buscador">
          <Search size={18} className="encabezado__buscador-icono" />
          <input type="text" placeholder="Buscar ordenes, clientes..." className="encabezado__buscador-input" id="buscador-global" />
        </div>
        <button className="boton-icono" id="btn-notificaciones" title="Notificaciones">
          <Bell size={20} />
        </button>
        <div className="encabezado__usuario" id="usuario-info">
          <div className="encabezado__avatar">
            {usuario?.nombre ? usuario.nombre.charAt(0).toUpperCase() : <User size={18} />}
          </div>
          <span className="encabezado__usuario-nombre">{usuario?.nombre || 'Usuario'}</span>
        </div>
      </div>
    </header>
  );
}
