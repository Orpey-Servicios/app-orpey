import { useState, useEffect } from 'react';
import { Settings, Image as ImageIcon, Palette, Save, CheckCircle2, RotateCcw, ListPlus, Edit2, Trash2, Plus, X } from 'lucide-react';
import { obtenerServicios, crearServicio, actualizarServicio, eliminarServicio } from '../api/orpey-api';
import './Configuracion.css';

export default function Configuracion() {
  const [colorPrimario, setColorPrimario] = useState('#FBC305');
  const [temaOscuro, setTemaOscuro] = useState(false);
  const [logoBase64, setLogoBase64] = useState('');
  const [guardado, setGuardado] = useState(false);

  // Catálogo de Servicios
  const [servicios, setServicios] = useState([]);
  const [editandoServicio, setEditandoServicio] = useState(null);
  const [nuevoServicio, setNuevoServicio] = useState({ nombre: '', costo: 0 });
  const [cargandoServicios, setCargandoServicios] = useState(false);

  useEffect(() => {
    // Cargar configuraciones actuales
    const currentColor = localStorage.getItem('orpey_custom_primary_color') || '#FBC305';
    setColorPrimario(currentColor);

    const isDark = localStorage.getItem('orpey_dark_mode') === 'true';
    setTemaOscuro(isDark);

    const currentLogo = localStorage.getItem('orpey_custom_logo') || '';
    setLogoBase64(currentLogo);

    cargarServicios();
  }, []);

  const cargarServicios = async () => {
    setCargandoServicios(true);
    try {
      const data = await obtenerServicios();
      setServicios(data);
    } catch (error) {
      console.error('Error al cargar servicios:', error);
    } finally {
      setCargandoServicios(false);
    }
  };

  const handleColorChange = (e) => {
    setColorPrimario(e.target.value);
  };

  const handleThemeToggle = () => {
    setTemaOscuro(!temaOscuro);
  };

  const handleLogoUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setLogoBase64(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const resetLogo = () => {
    setLogoBase64('');
  };

  const guardarConfiguracion = () => {
    // Guardar en localStorage
    localStorage.setItem('orpey_custom_primary_color', colorPrimario);
    localStorage.setItem('orpey_dark_mode', temaOscuro);
    
    if (logoBase64) {
      localStorage.setItem('orpey_custom_logo', logoBase64);
    } else {
      localStorage.removeItem('orpey_custom_logo');
    }

    // Aplicar inmediatamente
    document.documentElement.style.setProperty('--color-primario', colorPrimario);
    
    if (temaOscuro) {
      document.body.classList.add('dark-theme');
    } else {
      document.body.classList.remove('dark-theme');
    }

    setGuardado(true);
    setTimeout(() => {
      setGuardado(false);
    }, 2000);
  };

  // Funciones de Servicios
  const guardarServicio = async () => {
    if (!nuevoServicio.nombre.trim()) return;
    try {
      if (editandoServicio) {
        await actualizarServicio(editandoServicio.id, nuevoServicio);
      } else {
        await crearServicio(nuevoServicio);
      }
      setNuevoServicio({ nombre: '', costo: 0 });
      setEditandoServicio(null);
      cargarServicios();
    } catch (error) {
      alert(`Error al guardar servicio: ${error.message}`);
    }
  };

  const iniciarEdicionServicio = (srv) => {
    setEditandoServicio(srv);
    setNuevoServicio({ nombre: srv.nombre, costo: parseFloat(srv.costo) });
  };

  const cancelarEdicionServicio = () => {
    setEditandoServicio(null);
    setNuevoServicio({ nombre: '', costo: 0 });
  };

  const borrarServicio = async (id) => {
    if (window.confirm('¿Eliminar este servicio del catálogo?')) {
      try {
        await eliminarServicio(id);
        cargarServicios();
      } catch (error) {
        alert('Error al eliminar servicio');
      }
    }
  };

  return (
    <div className="configuracion animar-entrada">
      <div className="configuracion__header">
        <h2><Settings size={28} /> Ajustes Generales</h2>
        <p>Personaliza la apariencia y el comportamiento del sistema Orpey.</p>
      </div>

      <div className="configuracion__grid">
        {/* ─── APARIENCIA ─── */}
        <div className="configuracion__card">
          <div className="configuracion__card-header">
            <h3><Palette size={20} /> Apariencia y Tema</h3>
          </div>
          <div className="configuracion__card-body">
            
            <div className="configuracion__item">
              <div className="configuracion__item-info">
                <h4>Color Primario</h4>
                <p>El color principal usado en botones y acentos.</p>
              </div>
              <div className="configuracion__item-accion">
                <input 
                  type="color" 
                  value={colorPrimario} 
                  onChange={handleColorChange}
                  className="color-picker"
                  title="Elegir color primario"
                />
              </div>
            </div>

            <div className="configuracion__item">
              <div className="configuracion__item-info">
                <h4>Modo Oscuro</h4>
                <p>Cambiar la interfaz a un esquema de colores oscuros para trabajar de noche.</p>
              </div>
              <div className="configuracion__item-accion">
                <label className="switch">
                  <input 
                    type="checkbox" 
                    checked={temaOscuro} 
                    onChange={handleThemeToggle} 
                  />
                  <span className="slider round"></span>
                </label>
              </div>
            </div>

            <div className="configuracion__acciones-card">
              <button 
                className={`boton-primario boton-guardar ${guardado ? 'guardado' : ''}`} 
                onClick={guardarConfiguracion}
              >
                {guardado ? (
                  <><CheckCircle2 size={18} /> Guardado</>
                ) : (
                  <><Save size={18} /> Guardar Tema</>
                )}
              </button>
            </div>

          </div>
        </div>

        {/* ─── LOGO DEL SISTEMA ─── */}
        <div className="configuracion__card">
          <div className="configuracion__card-header">
            <h3><ImageIcon size={20} /> Logo del Sistema</h3>
          </div>
          <div className="configuracion__card-body">
            
            <div className="configuracion__logo-preview">
              <img 
                src={logoBase64 || '/logo-orpey.png'} 
                alt="Logo actual" 
                className="logo-actual"
                style={{ backgroundColor: temaOscuro ? '#353534' : '#353534' }}
              />
            </div>
            
            <div className="configuracion__logo-upload">
              <p className="upload-recomendacion">
                <strong>Recomendado:</strong> 200x60 px (Formato PNG transparente).
              </p>
              <div className="upload-botones">
                <label className="boton-secundario upload-btn">
                  Seleccionar Imagen
                  <input 
                    type="file" 
                    accept="image/png, image/jpeg" 
                    onChange={handleLogoUpload} 
                    style={{ display: 'none' }}
                  />
                </label>
                {logoBase64 && (
                  <button className="boton-icono" onClick={resetLogo} title="Restaurar logo por defecto" style={{ color: 'var(--color-error)' }}>
                    <RotateCcw size={18} /> Restaurar
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ─── CATÁLOGO DE SERVICIOS ─── */}
      <div className="configuracion__seccion-servicios mt-4">
        <div className="configuracion__card">
          <div className="configuracion__card-header d-flex justify-content-between align-items-center">
            <h3><ListPlus size={20} /> Catálogo de Servicios Predefinidos</h3>
          </div>
          <div className="configuracion__card-body">
            <p className="texto-ayuda" style={{ marginBottom: '24px', lineHeight: '1.6' }}>
              Agrega servicios comunes con su costo predeterminado (ej: Mantenimiento Impresora, Formateo PC). 
              Estos aparecerán como opciones rápidas al crear una orden y servirán para medir qué servicios se facturan más.
            </p>

            <div className="form-servicio-grid">
              <div className="form-grupo" style={{ marginBottom: 0 }}>
                <input 
                  type="text" 
                  className="campo-texto" 
                  placeholder="Nombre del Servicio (ej: Mantenimiento Hardware)" 
                  value={nuevoServicio.nombre}
                  onChange={(e) => setNuevoServicio({...nuevoServicio, nombre: e.target.value})}
                  style={{ width: '100%', padding: '10px 12px' }}
                />
              </div>
              <div className="form-grupo" style={{ marginBottom: 0 }}>
                <div className="monto-control" style={{ width: '100%' }}>
                  <button type="button" className="monto-btn monto-btn--menos" onClick={() => {
                    const actual = Number(nuevoServicio.costo) || 0;
                    setNuevoServicio({...nuevoServicio, costo: Math.max(0, actual - 5).toFixed(2)});
                  }}>−</button>
                  <input type="text" className="monto-input"
                    value={nuevoServicio.costo}
                    onChange={e => {
                      const val = e.target.value.replace(/[^0-9.]/g, '');
                      setNuevoServicio({...nuevoServicio, costo: val});
                    }}
                    onBlur={() => {
                      setNuevoServicio({...nuevoServicio, costo: (Number(nuevoServicio.costo) || 0).toFixed(2)});
                    }}
                  />
                  <button type="button" className="monto-btn monto-btn--mas" onClick={() => {
                    const actual = Number(nuevoServicio.costo) || 0;
                    setNuevoServicio({...nuevoServicio, costo: (actual + 5).toFixed(2)});
                  }}>+</button>
                </div>
              </div>
              <button 
                className="boton-primario" 
                onClick={guardarServicio}
                disabled={!nuevoServicio.nombre.trim()}
                style={{ padding: '0 16px', height: '38px' }}
              >
                {editandoServicio ? <><Save size={18} /> Actualizar</> : <><Plus size={18} /> Agregar</>}
              </button>
              {editandoServicio && (
                <button className="boton-secundario boton-icono" onClick={cancelarEdicionServicio} style={{ height: '38px', width: '38px', padding: '0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <X size={18} />
                </button>
              )}
            </div>

            <div className="lista-servicios mt-4">
              {cargandoServicios ? (
                <p>Cargando servicios...</p>
              ) : servicios.length === 0 ? (
                <p className="texto-vacio">No hay servicios registrados. Agrega uno arriba.</p>
              ) : (
                <div className="tabla-responsive">
                  <table className="tabla-orpey" style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr>
                        <th style={{ textAlign: 'left', padding: '12px 16px', width: '60%' }}>Nombre del Servicio</th>
                        <th style={{ textAlign: 'left', padding: '12px 16px', width: '20%' }}>Costo Predeterminado</th>
                        <th className="texto-derecha" style={{ padding: '12px 16px', width: '20%' }}>Acciones</th>
                      </tr>
                    </thead>
                    <tbody>
                      {servicios.map(srv => (
                        <tr key={srv.id} style={{ borderBottom: '1px solid var(--borde-color)' }}>
                          <td style={{ padding: '12px 16px' }}>{srv.nombre}</td>
                          <td style={{ padding: '12px 16px' }}><strong>${parseFloat(srv.costo).toFixed(2)}</strong></td>
                          <td className="texto-derecha flex-acciones" style={{ padding: '12px 16px' }}>
                            <button 
                              className="boton-icono" 
                              onClick={() => iniciarEdicionServicio(srv)}
                              title="Editar servicio"
                            >
                              <Edit2 size={16} />
                            </button>
                            <button 
                              className="boton-icono eliminar" 
                              onClick={() => borrarServicio(srv.id)}
                              title="Eliminar servicio"
                            >
                              <Trash2 size={16} />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      
    </div>
  );
}
