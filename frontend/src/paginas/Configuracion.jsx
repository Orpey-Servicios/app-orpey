import { useState, useEffect } from 'react';
import { Settings, Image as ImageIcon, Palette, Save, CheckCircle2, RotateCcw } from 'lucide-react';
import './Configuracion.css';

export default function Configuracion() {
  const [colorPrimario, setColorPrimario] = useState('#FBC305');
  const [temaOscuro, setTemaOscuro] = useState(false);
  const [logoBase64, setLogoBase64] = useState('');
  const [guardado, setGuardado] = useState(false);

  useEffect(() => {
    // Cargar configuraciones actuales
    const currentColor = localStorage.getItem('orpey_custom_primary_color') || '#FBC305';
    setColorPrimario(currentColor);

    const isDark = localStorage.getItem('orpey_dark_mode') === 'true';
    setTemaOscuro(isDark);

    const currentLogo = localStorage.getItem('orpey_custom_logo') || '';
    setLogoBase64(currentLogo);
  }, []);

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
      // Opcional: recargar la página para que los componentes que leen directamente actualicen el logo
      window.location.reload();
    }, 1000);
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

      <div className="configuracion__acciones">
        <button 
          className={`boton-primario boton-guardar ${guardado ? 'guardado' : ''}`} 
          onClick={guardarConfiguracion}
        >
          {guardado ? (
            <><CheckCircle2 size={20} /> Guardado</>
          ) : (
            <><Save size={20} /> Guardar Cambios</>
          )}
        </button>
      </div>
    </div>
  );
}
