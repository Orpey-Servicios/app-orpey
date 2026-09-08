import { useState, useEffect } from 'react';
import {
  Settings, Image as ImageIcon, Palette, Save, CheckCircle2, RotateCcw,
  ListPlus, Edit2, Trash2, Plus, X, ShieldCheck, AlertCircle, UploadCloud,
  Eye, EyeOff, Mail, Send
} from 'lucide-react';
import {
  obtenerServicios, crearServicio, actualizarServicio, eliminarServicio,
  obtenerInfoFirma, subirFirmaP12,
  obtenerConfigSmtp, guardarConfigSmtp, probarConexionSmtp
} from '../api/orpey-api';
import { useAuth } from '../context/AuthContext';
import './Configuracion.css';

export default function Configuracion() {
  const { usuario } = useAuth();
  const [colorPrimario, setColorPrimario] = useState('#FBC305');
  const [temaOscuro, setTemaOscuro] = useState(false);
  const [logoBase64, setLogoBase64] = useState('');
  const [guardado, setGuardado] = useState(false);

  // Catálogo de Servicios
  const [servicios, setServicios] = useState([]);
  const [editandoServicio, setEditandoServicio] = useState(null);
  const [nuevoServicio, setNuevoServicio] = useState({ nombre: '', costo: 0 });
  const [cargandoServicios, setCargandoServicios] = useState(false);

  // Firma Electrónica SRI (.p12)
  const [infoFirma, setInfoFirma] = useState(null);
  const [cargandoFirma, setCargandoFirma] = useState(false);
  const [mostrarFormFirma, setMostrarFormFirma] = useState(false);
  const [archivoFirma, setArchivoFirma] = useState(null);
  const [passwordFirma, setPasswordFirma] = useState('');
  const [mostrarPasswordFirma, setMostrarPasswordFirma] = useState(false);
  const [subiendoFirma, setSubiendoFirma] = useState(false);
  const [errorFirma, setErrorFirma] = useState('');
  const [exitoFirma, setExitoFirma] = useState('');

  // Servidor SMTP (Correo Saliente)
  const [smtpConfig, setSmtpConfig] = useState({
    smtp_host: '',
    smtp_port: 587,
    smtp_usuario: '',
    smtp_password: '',
    smtp_from_email: '',
    smtp_from_nombre: 'Orpey Servicios',
    smtp_seguridad: 'tls',
    smtp_copia_oculta: '',
    smtp_password_configurada: false,
  });
  const [mostrarPasswordSmtp, setMostrarPasswordSmtp] = useState(false);
  const [cargandoSmtp, setCargandoSmtp] = useState(false);
  const [guardandoSmtp, setGuardandoSmtp] = useState(false);
  const [probandoSmtp, setProbandoSmtp] = useState(false);
  const [emailPrueba, setEmailPrueba] = useState('');
  const [errorSmtp, setErrorSmtp] = useState('');
  const [exitoSmtp, setExitoSmtp] = useState('');

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

  const cargarInfoFirma = async () => {
    if (usuario?.rol !== 'admin') return;
    setCargandoFirma(true);
    try {
      const data = await obtenerInfoFirma();
      setInfoFirma(data);
    } catch (err) {
      console.error('Error al cargar info de firma SRI:', err);
    } finally {
      setCargandoFirma(false);
    }
  };

  const cargarConfigSmtp = async () => {
    if (usuario?.rol !== 'admin') return;
    setCargandoSmtp(true);
    try {
      const data = await obtenerConfigSmtp();
      if (data) {
        setSmtpConfig({
          smtp_host: data.smtp_host || '',
          smtp_port: data.smtp_port || 587,
          smtp_usuario: data.smtp_usuario || '',
          smtp_password: '',
          smtp_from_email: data.smtp_from_email || '',
          smtp_from_nombre: data.smtp_from_nombre || 'Orpey Servicios',
          smtp_seguridad: data.smtp_seguridad || 'tls',
          smtp_copia_oculta: data.smtp_copia_oculta || '',
          smtp_password_configurada: !!data.smtp_password_configurada,
        });
      }
    } catch (err) {
      console.error('Error al cargar config SMTP:', err);
    } finally {
      setCargandoSmtp(false);
    }
  };

  useEffect(() => {
    if (usuario?.rol === 'admin') {
      cargarInfoFirma();
      cargarConfigSmtp();
    }
  }, [usuario]);

  const handleGuardarSmtp = async (e) => {
    e.preventDefault();
    setGuardandoSmtp(true);
    setErrorSmtp('');
    setExitoSmtp('');
    try {
      const payload = {
        smtp_host: smtpConfig.smtp_host,
        smtp_port: Number(smtpConfig.smtp_port) || 587,
        smtp_usuario: smtpConfig.smtp_usuario,
        smtp_from_email: smtpConfig.smtp_from_email || smtpConfig.smtp_usuario,
        smtp_from_nombre: smtpConfig.smtp_from_nombre || 'Orpey Servicios',
        smtp_seguridad: smtpConfig.smtp_seguridad,
        smtp_copia_oculta: smtpConfig.smtp_copia_oculta || null,
      };
      if (smtpConfig.smtp_password && smtpConfig.smtp_password.trim()) {
        payload.smtp_password = smtpConfig.smtp_password.trim();
      }
      const data = await guardarConfigSmtp(payload);
      setExitoSmtp('Configuración de correo saliente guardada con éxito.');
      setSmtpConfig(prev => ({
        ...prev,
        smtp_password: '',
        smtp_password_configurada: !!data.smtp_password_configurada,
      }));
    } catch (err) {
      setErrorSmtp(err?.message || 'Error al guardar la configuración SMTP');
    } finally {
      setGuardandoSmtp(false);
    }
  };

  const handleProbarSmtp = async (e) => {
    e?.preventDefault();
    if (!emailPrueba || !emailPrueba.includes('@')) {
      setErrorSmtp('Ingresa un correo electrónico de destino válido para la prueba.');
      return;
    }
    setProbandoSmtp(true);
    setErrorSmtp('');
    setExitoSmtp('');
    try {
      const payload = {
        destinatario: emailPrueba.trim(),
        smtp_host: smtpConfig.smtp_host || undefined,
        smtp_port: Number(smtpConfig.smtp_port) || undefined,
        smtp_usuario: smtpConfig.smtp_usuario || undefined,
        smtp_password: smtpConfig.smtp_password?.trim() || undefined,
        smtp_from_email: smtpConfig.smtp_from_email || undefined,
        smtp_from_nombre: smtpConfig.smtp_from_nombre || undefined,
        smtp_seguridad: smtpConfig.smtp_seguridad || undefined,
      };
      const res = await probarConexionSmtp(payload);
      setExitoSmtp(res?.mensaje || `Correo de prueba enviado con éxito a ${emailPrueba}`);
    } catch (err) {
      setErrorSmtp(err?.message || 'Error al enviar correo de prueba. Verifica las credenciales.');
    } finally {
      setProbandoSmtp(false);
    }
  };

  const handleSubirFirma = async (e) => {
    e.preventDefault();
    if (!archivoFirma) {
      setErrorFirma('Por favor selecciona un archivo .p12 o .pfx');
      return;
    }
    if (!passwordFirma.trim()) {
      setErrorFirma('Por favor ingresa la contraseña de la firma');
      return;
    }

    setSubiendoFirma(true);
    setErrorFirma('');
    setExitoFirma('');

    const formData = new FormData();
    formData.append('archivo', archivoFirma);
    formData.append('password', passwordFirma.trim());

    try {
      const resp = await subirFirmaP12(formData);
      setInfoFirma(resp);
      setExitoFirma(resp.mensaje || 'Firma electrónica instalada y validada exitosamente.');
      setArchivoFirma(null);
      setPasswordFirma('');
      setMostrarFormFirma(false);
    } catch (err) {
      setErrorFirma(err.message || 'Error al validar y subir la firma');
    } finally {
      setSubiendoFirma(false);
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
      
      {/* ─── FIRMA ELECTRÓNICA SRI (.P12) ─── */}
      {usuario?.rol === 'admin' && (
        <div className="configuracion__seccion-servicios mt-4" style={{ marginTop: '30px' }}>
          <div className="configuracion__card">
            <div className="configuracion__card-header d-flex justify-content-between align-items-center" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3><ShieldCheck size={20} /> Firma Electrónica SRI (.p12)</h3>
              {infoFirma && (
                <span className={`badge-firma ${infoFirma.activo ? 'badge-firma--vigente' : 'badge-firma--inactivo'}`}>
                  {infoFirma.activo ? `✓ VIGENTE (${infoFirma.dias_restantes} días)` : (infoFirma.configurada ? '⚠ EXPIRADO' : '✕ NO CONFIGURADA')}
                </span>
              )}
            </div>
            <div className="configuracion__card-body">
              <p className="texto-ayuda" style={{ marginBottom: '20px', lineHeight: '1.6' }}>
                Certificado digital PKCS#12 utilizado para emitir y autorizar facturas y notas de crédito ante el SRI con firma XAdES-BES.
              </p>

              {exitoFirma && (
                <div className="alerta alerta--exito mb-3" style={{ padding: '12px 16px', background: '#ecfdf5', color: '#065f46', borderRadius: '6px', border: '1px solid #a7f3d0', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <CheckCircle2 size={18} />
                  <span>{exitoFirma}</span>
                </div>
              )}

              {errorFirma && (
                <div className="alerta alerta--error mb-3" style={{ padding: '12px 16px', background: '#fef2f2', color: '#991b1b', borderRadius: '6px', border: '1px solid #fecaca', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <AlertCircle size={18} />
                  <span>{errorFirma}</span>
                </div>
              )}

              {cargandoFirma ? (
                <p>Cargando información del certificado...</p>
              ) : infoFirma && infoFirma.titular ? (
                <div className="firma-info-container">
                  <div className="firma-info-grid">
                    <div className="firma-info-item">
                      <span className="firma-info-label">Titular / Razón Social:</span>
                      <span className="firma-info-valor"><strong>{infoFirma.titular}</strong></span>
                    </div>
                    <div className="firma-info-item">
                      <span className="firma-info-label">RUC Asociado:</span>
                      <span className="firma-info-valor">{infoFirma.ruc || '—'}</span>
                    </div>
                    <div className="firma-info-item">
                      <span className="firma-info-label">Entidad Emisora:</span>
                      <span className="firma-info-valor">{infoFirma.emisor ? infoFirma.emisor.split(',')[0] : '—'}</span>
                    </div>
                    <div className="firma-info-item">
                      <span className="firma-info-label">Válido hasta:</span>
                      <span className="firma-info-valor">
                        {infoFirma.valido_hasta ? new Date(infoFirma.valido_hasta).toLocaleDateString('es-EC', { day: '2-digit', month: '2-digit', year: 'numeric' }) : '—'}
                        {' '}({infoFirma.dias_restantes} días restantes)
                      </span>
                    </div>
                    <div className="firma-info-item">
                      <span className="firma-info-label">Ubicación del archivo:</span>
                      <span className="firma-info-valor" style={{ fontFamily: 'monospace', fontSize: '12px' }}>{infoFirma.ruta}</span>
                    </div>
                  </div>

                  <div style={{ marginTop: '20px' }}>
                    <button
                      type="button"
                      className="boton-secundario"
                      onClick={() => setMostrarFormFirma(!mostrarFormFirma)}
                    >
                      <UploadCloud size={18} /> {mostrarFormFirma ? 'Cancelar Actualización' : 'Actualizar / Cargar Certificado .p12'}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="texto-vacio" style={{ marginBottom: '20px' }}>
                  <p>{infoFirma?.error || 'No se ha detectado ningún certificado digital válido en el servidor.'}</p>
                  <button
                    type="button"
                    className="boton-primario mt-3"
                    onClick={() => setMostrarFormFirma(true)}
                    style={{ marginTop: '12px' }}
                  >
                    <UploadCloud size={18} /> Cargar Certificado .p12
                  </button>
                </div>
              )}

              {mostrarFormFirma && (
                <form onSubmit={handleSubirFirma} className="firma-upload-form" style={{ marginTop: '24px', padding: '20px', background: 'var(--fondo-principal)', borderRadius: '8px', border: '1px solid var(--borde-color)' }}>
                  <h4 style={{ margin: '0 0 16px 0', fontSize: '15px' }}>Instalar o Reemplazar Firma Electrónica (.p12)</h4>
                  
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                    <div className="form-grupo" style={{ marginBottom: 0 }}>
                      <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: '500' }}>Archivo de Firma (.p12 / .pfx)</label>
                      <input
                        type="file"
                        accept=".p12,.pfx"
                        onChange={(e) => setArchivoFirma(e.target.files[0])}
                        className="campo-texto"
                        style={{ width: '100%', padding: '8px' }}
                        required
                      />
                    </div>
                    <div className="form-grupo" style={{ marginBottom: 0 }}>
                      <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: '500' }}>Contraseña del Certificado</label>
                      <div style={{ position: 'relative' }}>
                        <input
                          type={mostrarPasswordFirma ? 'text' : 'password'}
                          value={passwordFirma}
                          onChange={(e) => setPasswordFirma(e.target.value)}
                          placeholder="Contraseña de la firma"
                          className="campo-texto"
                          style={{ width: '100%', padding: '10px 38px 10px 12px' }}
                          required
                        />
                        <button
                          type="button"
                          onClick={() => setMostrarPasswordFirma(!mostrarPasswordFirma)}
                          style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--texto-secundario)' }}
                        >
                          {mostrarPasswordFirma ? <EyeOff size={16} /> : <Eye size={16} />}
                        </button>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                    <button
                      type="submit"
                      className="boton-primario"
                      disabled={subiendoFirma || !archivoFirma || !passwordFirma}
                      style={{ height: '38px', padding: '0 20px' }}
                    >
                      {subiendoFirma ? 'Validando e instalando...' : <><ShieldCheck size={18} /> Validar e Instalar</>}
                    </button>
                    <button
                      type="button"
                      className="boton-secundario"
                      onClick={() => setMostrarFormFirma(false)}
                      disabled={subiendoFirma}
                      style={{ height: '38px' }}
                    >
                      Cancelar
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 4. Servidor de Correo Saliente (SMTP / Envío de Facturas) */}
      {usuario?.rol === 'admin' && (
        <div className="configuracion-card">
          <div className="card-header">
            <Mail size={24} className="icono-header" />
            <div>
              <h3>Servidor de Correo Saliente (SMTP)</h3>
              <p>Configura la cuenta de correo para el envío automático de facturas electrónicas y RIDE (PDF + XML) a los clientes.</p>
            </div>
          </div>

          <div className="card-body">
            {/* Estado actual de SMTP */}
            <div className="smtp-status-banner" style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '12px 16px',
              borderRadius: '8px',
              marginBottom: '20px',
              background: smtpConfig.smtp_host && (smtpConfig.smtp_password_configurada || smtpConfig.smtp_password)
                ? 'rgba(16, 185, 129, 0.1)'
                : 'rgba(245, 158, 11, 0.1)',
              border: smtpConfig.smtp_host && (smtpConfig.smtp_password_configurada || smtpConfig.smtp_password)
                ? '1px solid rgba(16, 185, 129, 0.25)'
                : '1px solid rgba(245, 158, 11, 0.25)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                {smtpConfig.smtp_host && (smtpConfig.smtp_password_configurada || smtpConfig.smtp_password) ? (
                  <CheckCircle2 size={20} style={{ color: '#10B981' }} />
                ) : (
                  <AlertCircle size={20} style={{ color: '#F59E0B' }} />
                )}
                <div>
                  <div style={{ fontWeight: '600', fontSize: '14px', color: smtpConfig.smtp_host && (smtpConfig.smtp_password_configurada || smtpConfig.smtp_password) ? '#10B981' : '#F59E0B' }}>
                    {smtpConfig.smtp_host && (smtpConfig.smtp_password_configurada || smtpConfig.smtp_password)
                      ? 'Servidor SMTP Configurado'
                      : 'Servidor SMTP No Configurado'}
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--texto-secundario)' }}>
                    {smtpConfig.smtp_host
                      ? `Conectado a ${smtpConfig.smtp_host}:${smtpConfig.smtp_port} (${smtpConfig.smtp_seguridad.toUpperCase()})`
                      : 'Sin credenciales configuradas. Las facturas autorizadas no podrán ser despachadas por correo.'}
                  </div>
                </div>
              </div>
            </div>

            {errorSmtp && (
              <div className="alerta-error" style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 14px', borderRadius: '6px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.25)', color: '#EF4444', fontSize: '13px' }}>
                <AlertCircle size={16} />
                <span>{errorSmtp}</span>
              </div>
            )}

            {exitoSmtp && (
              <div className="alerta-exito" style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 14px', borderRadius: '6px', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.25)', color: '#10B981', fontSize: '13px' }}>
                <CheckCircle2 size={16} />
                <span>{exitoSmtp}</span>
              </div>
            )}

            <form onSubmit={handleGuardarSmtp}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px', marginBottom: '20px' }}>
                <div className="form-grupo" style={{ marginBottom: 0 }}>
                  <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: '500' }}>Servidor SMTP (Host)</label>
                  <input
                    type="text"
                    value={smtpConfig.smtp_host}
                    onChange={(e) => setSmtpConfig({ ...smtpConfig, smtp_host: e.target.value })}
                    placeholder="smtp.gmail.com o mail.orpey.com"
                    className="campo-texto"
                    style={{ width: '100%' }}
                    required
                  />
                </div>

                <div className="form-grupo" style={{ marginBottom: 0 }}>
                  <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: '500' }}>Puerto</label>
                  <input
                    type="number"
                    value={smtpConfig.smtp_port}
                    onChange={(e) => setSmtpConfig({ ...smtpConfig, smtp_port: e.target.value })}
                    placeholder="587 o 465"
                    className="campo-texto"
                    style={{ width: '100%' }}
                    required
                  />
                </div>

                <div className="form-grupo" style={{ marginBottom: 0 }}>
                  <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: '500' }}>Usuario / Correo Autenticación</label>
                  <input
                    type="text"
                    value={smtpConfig.smtp_usuario}
                    onChange={(e) => setSmtpConfig({ ...smtpConfig, smtp_usuario: e.target.value })}
                    placeholder="facturacion@orpey.com"
                    className="campo-texto"
                    style={{ width: '100%' }}
                    required
                  />
                </div>

                <div className="form-grupo" style={{ marginBottom: 0 }}>
                  <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: '500' }}>
                    Contraseña {smtpConfig.smtp_password_configurada && <span style={{ fontSize: '11px', color: '#10B981', fontWeight: 'normal' }}>(Configurada)</span>}
                  </label>
                  <div style={{ position: 'relative' }}>
                    <input
                      type={mostrarPasswordSmtp ? 'text' : 'password'}
                      value={smtpConfig.smtp_password}
                      onChange={(e) => setSmtpConfig({ ...smtpConfig, smtp_password: e.target.value })}
                      placeholder={smtpConfig.smtp_password_configurada ? 'Dejar vacío para no cambiar' : 'Contraseña o App Password'}
                      className="campo-texto"
                      style={{ width: '100%', paddingRight: '38px' }}
                      required={!smtpConfig.smtp_password_configurada}
                    />
                    <button
                      type="button"
                      onClick={() => setMostrarPasswordSmtp(!mostrarPasswordSmtp)}
                      style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--texto-secundario)' }}
                    >
                      {mostrarPasswordSmtp ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>

                <div className="form-grupo" style={{ marginBottom: 0 }}>
                  <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: '500' }}>Nombre del Remitente</label>
                  <input
                    type="text"
                    value={smtpConfig.smtp_from_nombre}
                    onChange={(e) => setSmtpConfig({ ...smtpConfig, smtp_from_nombre: e.target.value })}
                    placeholder="Orpey Servicios"
                    className="campo-texto"
                    style={{ width: '100%' }}
                  />
                </div>

                <div className="form-grupo" style={{ marginBottom: 0 }}>
                  <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: '500' }}>Correo Remitente (From)</label>
                  <input
                    type="email"
                    value={smtpConfig.smtp_from_email}
                    onChange={(e) => setSmtpConfig({ ...smtpConfig, smtp_from_email: e.target.value })}
                    placeholder="facturacion@orpey.com"
                    className="campo-texto"
                    style={{ width: '100%' }}
                    required
                  />
                </div>

                <div className="form-grupo" style={{ marginBottom: 0 }}>
                  <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: '500' }}>Seguridad de Conexión</label>
                  <select
                    value={smtpConfig.smtp_seguridad}
                    onChange={(e) => setSmtpConfig({ ...smtpConfig, smtp_seguridad: e.target.value })}
                    className="campo-texto"
                    style={{ width: '100%' }}
                  >
                    <option value="tls">STARTTLS (Recomendado para puerto 587)</option>
                    <option value="ssl">SSL / TLS Directo (Puerto 465)</option>
                    <option value="ninguna">Sin cifrado (No recomendado / Puerto 25)</option>
                  </select>
                </div>

                <div className="form-grupo" style={{ marginBottom: 0 }}>
                  <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: '500' }}>Copia Oculta (BCC - Opcional)</label>
                  <input
                    type="email"
                    value={smtpConfig.smtp_copia_oculta}
                    onChange={(e) => setSmtpConfig({ ...smtpConfig, smtp_copia_oculta: e.target.value })}
                    placeholder="gerencia@orpey.com"
                    className="campo-texto"
                    style={{ width: '100%' }}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginBottom: '24px' }}>
                <button
                  type="submit"
                  className="boton-primario"
                  disabled={guardandoSmtp || cargandoSmtp}
                  style={{ height: '38px', padding: '0 20px' }}
                >
                  <Save size={18} />
                  <span>{guardandoSmtp ? 'Guardando...' : 'Guardar Configuración'}</span>
                </button>
              </div>
            </form>

            {/* Subsección: Prueba de Conexión y Envío */}
            <div style={{
              background: 'var(--fondo-principal)',
              borderRadius: '8px',
              border: '1px solid var(--borde-color)',
              padding: '18px 20px',
            }}>
              <h4 style={{ margin: '0 0 8px 0', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Send size={16} />
                <span>Probar Conexión y Envío de Correo</span>
              </h4>
              <p style={{ margin: '0 0 14px 0', fontSize: '13px', color: 'var(--texto-secundario)' }}>
                Envía un correo de prueba instantáneo para comprobar que los datos SMTP ingresados funcionan sin errores.
              </p>
              <div style={{ display: 'flex', gap: '12px', alignItems: 'center', maxWidth: '500px' }}>
                <input
                  type="email"
                  value={emailPrueba}
                  onChange={(e) => setEmailPrueba(e.target.value)}
                  placeholder="ejemplo@correo.com"
                  className="campo-texto"
                  style={{ flex: 1 }}
                />
                <button
                  type="button"
                  onClick={handleProbarSmtp}
                  className="boton-secundario"
                  disabled={probandoSmtp || !emailPrueba}
                  style={{ height: '38px', whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: '8px' }}
                >
                  <Send size={16} />
                  <span>{probandoSmtp ? 'Enviando prueba...' : 'Probar Envío'}</span>
                </button>
              </div>
            </div>

          </div>
        </div>
      )}
      
    </div>
  );
}
