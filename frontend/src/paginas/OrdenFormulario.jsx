/**
 * FORMULARIO DE ORDEN - Crear o editar una orden de servicio
 *
 * Cambios implementados:
 * 1. Al crear orden → Modal de éxito con botones PDF y WhatsApp
 * 2. Sección cliente con formulario para crear nuevo cliente inline
 */
import { useState, useEffect, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Save, ArrowLeft, Search, UserPlus, X, FileDown, MessageCircle, CheckCircle, Plus, Settings2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import {
  obtenerClientes, obtenerTecnicos, crearOrden, obtenerOrden, actualizarOrden,
  crearCliente, descargarPdfOrden, obtenerWhatsappOrden
} from '../api/orpey-api';
import './OrdenFormulario.css';

const TIPOS_EQUIPO = [
  { valor: 'pc_escritorio', etiqueta: 'PC Escritorio', emoji: '🖥️' },
  { valor: 'laptop', etiqueta: 'Laptop', emoji: '💻' },
  { valor: 'impresora', etiqueta: 'Impresora', emoji: '🖨️' },
  { valor: 'telefono', etiqueta: 'Teléfono', emoji: '📱' },
  { valor: 'otro', etiqueta: 'Otro', emoji: '🔧' },
];

const GARANTIAS = [
  { valor: 30, etiqueta: '30 días (mantenimiento estándar)' },
  { valor: 60, etiqueta: '60 días' },
  { valor: 90, etiqueta: '90 días' },
  { valor: 0, etiqueta: 'Sin garantía' },
];

const MARCAS_DEFECTO = {
  pc_escritorio: [
    "Dell", "HP", "Lenovo", "ASUS", "Acer", "Apple", "MSI", "Toshiba",
    "Samsung", "LG", "Huawei", "Xiaomi", "Razer", "Alienware", "Microsoft"
  ],
  laptop: [
    "Dell", "HP", "Lenovo", "ASUS", "Acer", "Apple", "MSI", "Toshiba",
    "Samsung", "LG", "Huawei", "Xiaomi", "Razer", "Alienware", "Microsoft"
  ],
  impresora: [
    "HP", "Canon", "Epson", "Brother", "Xerox", "Lexmark", "Samsung",
    "Kyocera", "Ricoh", "Konica Minolta", "OKI", "Panasonic", "Sharp", "Zebra"
  ],
  telefono: [
    "Apple", "Samsung", "Xiaomi", "Huawei", "OPPO", "Vivo", "Motorola",
    "Google", "OnePlus", "Realme", "Nokia", "Sony", "LG", "ZTE", "TCL",
    "iPhone", "Samsung Galaxy", "Redmi", "POCO", "Nothing"
  ],
  otro: []
};

const MODELOS_DEFECTO = {
  pc_escritorio: {}, laptop: {}, impresora: {}, telefono: {}, otro: {}
};

function getStoredData(key, defaults) {
  try {
    const stored = localStorage.getItem(key);
    const parsed = stored ? JSON.parse(stored) : null;
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      const result = { ...defaults };
      for (const tipo in parsed) {
        if (!result.hasOwnProperty(tipo)) continue;
        const defaultVal = defaults[tipo];
        const savedVal = parsed[tipo];
        if (savedVal == null) continue;

        if (Array.isArray(defaultVal)) {
          // Marcas: should be an array of strings
          if (Array.isArray(savedVal)) {
            result[tipo] = [...new Set([...defaultVal, ...savedVal])];
          } else if (typeof savedVal === 'object') {
            // Repair: corrupted array → object with numeric keys
            const values = Object.values(savedVal).filter(v => typeof v === 'string');
            result[tipo] = [...new Set([...defaultVal, ...values])];
          }
        } else if (typeof defaultVal === 'object' && defaultVal !== null) {
          // Modelos: nested object { brand: { model: true } }
          if (typeof savedVal === 'object' && !Array.isArray(savedVal)) {
            // Deep merge for nested brand→model structure
            result[tipo] = { ...defaultVal };
            for (const brand in savedVal) {
              if (typeof savedVal[brand] === 'object' && !Array.isArray(savedVal[brand])) {
                result[tipo][brand] = { ...(defaultVal[brand] || {}), ...savedVal[brand] };
              } else {
                result[tipo][brand] = savedVal[brand];
              }
            }
          }
        }
      }
      return result;
    }
    return defaults;
  } catch (e) {
    return defaults;
  }
}

function setStoredData(key, data) {
  localStorage.setItem(key, JSON.stringify(data));
}

// Función para formatear texto como Título
function formatearTexto(texto) {
  return texto.toLowerCase().replace(/(?:^|\s)\S/g, a => a.toUpperCase());
}

// Estado inicial para el formulario de nuevo cliente
const FORM_CLIENTE_INICIAL = {
  nombre: '', apellido: '', telefono: '', email: '', cedula_ruc: '', direccion: '',
};

export default function OrdenFormulario() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { usuario } = useAuth();
  const esEdicion = !!id;

  // ── Estado del formulario de orden ──────────────────────────────────
  const [form, setForm] = useState({
    cliente_id: '', tecnico_id: '', total_orden: '0.00',
    abono: '0.00', garantia_dias: 30, notas_internas: '',
    equipos: [{
      tipo_equipo: 'laptop', marca: '', modelo: '',
      cable: false, cargador: false, contrasena: '', descripcion_problema: '', diagnostico: '',
      trabajo_a_realizar: '', repuesto_a_instalar: '', costo: '0.00', abono_equipo: '0.00'
    }]
  });

  const [clientes, setClientes] = useState([]);
  const [tecnicos, setTecnicos] = useState([]);
  const [buscarCliente, setBuscarCliente] = useState('');
  const [mostrarClientes, setMostrarClientes] = useState(false);
  const [clienteSeleccionado, setClienteSeleccionado] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);

  // ── Estado: panel de nuevo cliente ──────────────────────────────────
  const [mostrarFormCliente, setMostrarFormCliente] = useState(false);
  const [formCliente, setFormCliente] = useState(FORM_CLIENTE_INICIAL);
  const [guardandoCliente, setGuardandoCliente] = useState(false);
  const [errorCliente, setErrorCliente] = useState(null);

  // ── Estado: modal de éxito al crear orden ───────────────────────────
  const [ordenCreada, setOrdenCreada] = useState(null); // guarda la orden recién creada

  // ── Estado: Listas dinámicas de marcas y modelos ────────────────────
  const [marcasPersonalizadas, setMarcasPersonalizadas] = useState(() => getStoredData('orpey_marcas', MARCAS_DEFECTO));
  const [modelosPersonalizados, setModelosPersonalizados] = useState(() => getStoredData('orpey_modelos', MODELOS_DEFECTO));
  const [modalConfig, setModalConfig] = useState({ abierto: false, tipo: 'marca', equipo: '', marca: '' });
  const [nuevoItemConfig, setNuevoItemConfig] = useState('');
  const [marcaEnModal, setMarcaEnModal] = useState('');

  useEffect(() => {
    setStoredData('orpey_marcas', marcasPersonalizadas);
  }, [marcasPersonalizadas]);

  useEffect(() => {
    setStoredData('orpey_modelos', modelosPersonalizados);
  }, [modelosPersonalizados]);

const agregarItemConfig = () => {
  const valor = nuevoItemConfig.trim();
  if (!valor) return;
  const { tipo, equipo } = modalConfig;
  if (tipo === 'marca') {
    setMarcasPersonalizadas(prev => ({
      ...prev,
      [equipo]: [...(prev[equipo] || []), valor]
    }));
  } else {
    const brand = marcaEnModal.trim();
    if (!brand) return; // Se necesita seleccionar una marca
    setModelosPersonalizados(prev => ({
      ...prev,
      [equipo]: {
        ...(prev[equipo] || {}),
        [brand]: {
          ...((prev[equipo] || {})[brand] || {}),
          [valor]: true
        }
      }
    }));
    setMarcaEnModal('');
  }
  setNuevoItemConfig('');
};

const eliminarItemConfig = (itemStr) => {
  const { tipo, equipo } = modalConfig;
  if (tipo === 'marca') {
    setMarcasPersonalizadas(prev => ({ ...prev, [equipo]: prev[equipo].filter(i => i !== itemStr) }));
  } else {
    // itemStr format: "Brand||Model"
    const sepIdx = itemStr.indexOf('||');
    const itemBrand = itemStr.slice(0, sepIdx);
    const itemModel = itemStr.slice(sepIdx + 2);
    setModelosPersonalizados(prev => {
      const tipoModels = { ...(prev[equipo] || {}) };
      if (tipoModels[itemBrand]) {
        const brandModels = { ...tipoModels[itemBrand] };
        delete brandModels[itemModel];
        if (Object.keys(brandModels).length === 0) {
          delete tipoModels[itemBrand]; // Eliminar marca si no quedan modelos
        } else {
          tipoModels[itemBrand] = brandModels;
        }
      }
      return { ...prev, [equipo]: tipoModels };
    });
  }
};

  useEffect(() => { cargarDatosIniciales(); }, []);

  async function cargarDatosIniciales() {
    try {
      const [clientesData, tecnicosData] = await Promise.all([
        obtenerClientes(), obtenerTecnicos()
      ]);
      setClientes(clientesData);
      setTecnicos(tecnicosData);

      if (esEdicion) {
        const orden = await obtenerOrden(Number(id));
        setForm({
          cliente_id: orden.cliente_id, tecnico_id: orden.tecnico_id || '',
          total_orden: orden.total_orden, abono: orden.abono,
          garantia_dias: orden.garantia_dias || 30, notas_internas: orden.notas_internas || '',
          equipos: orden.equipos && orden.equipos.length > 0
            ? orden.equipos.map(eq => ({ ...eq, costo: eq.costo || '0.00', abono_equipo: eq.abono_equipo || '0.00' }))
            : [{
              tipo_equipo: 'laptop', marca: '', modelo: '',
              cable: false, cargador: false, contrasena: '', descripcion_problema: '', diagnostico: '',
              trabajo_a_realizar: '', repuesto_a_instalar: '', costo: '0.00', abono_equipo: '0.00'
            }]
        });
        const cliente = clientesData.find(c => c.id === orden.cliente_id);
        if (cliente) {
          setClienteSeleccionado(cliente);
          setBuscarCliente(`${cliente.nombre} ${cliente.apellido}`);
        }
      } else {
        // Asignar técnico automáticamente según el usuario autenticado
        if (usuario?.nombre) {
          const partes = usuario.nombre.split(' ');
          const nombre = partes[0];
          const apellido = partes.slice(1).join(' ');
          const tecAutomatico = tecnicosData.find(
            t => t.nombre === nombre && t.apellido === apellido
          );
          if (tecAutomatico) {
            setForm(prev => ({ ...prev, tecnico_id: tecAutomatico.id }));
          }
        }
      }
    } catch (err) { setError(err.message); }
  }


  function actualizarCampo(campo, valor) {
    setForm(prev => ({ ...prev, [campo]: valor }));
  }

  function actualizarCampoEquipo(index, campo, valor) {
    setForm(prev => {
      const nuevosEquipos = [...prev.equipos];
      nuevosEquipos[index] = { ...nuevosEquipos[index], [campo]: valor };

      // Si se cambia el abono_equipo, no permitir que exceda el costo del equipo
      if (campo === 'abono_equipo') {
        const costoEquipo = Number(nuevosEquipos[index].costo) || 0;
        const abonoEquipo = Number(nuevosEquipos[index].abono_equipo) || 0;
        if (abonoEquipo > costoEquipo) {
          nuevosEquipos[index] = { ...nuevosEquipos[index], abono_equipo: costoEquipo.toFixed(2) };
        }
      }

      // Si se cambia el costo, ajustar el abono_equipo si excede el nuevo costo
      if (campo === 'costo') {
        const nuevoCosto = Number(nuevosEquipos[index].costo) || 0;
        const abonoActual = Number(nuevosEquipos[index].abono_equipo) || 0;
        if (abonoActual > nuevoCosto) {
          nuevosEquipos[index] = { ...nuevosEquipos[index], abono_equipo: nuevoCosto.toFixed(2) };
        }
      }

      // Auto-calcular total_orden como suma de costos de equipos
      const totalEquipos = nuevosEquipos.reduce(
        (sum, eq) => sum + (Number(eq.costo) || 0), 0
      );
      // Auto-calcular abono como suma de abonos de equipos
      const totalAbono = nuevosEquipos.reduce(
        (sum, eq) => sum + (Number(eq.abono_equipo) || 0), 0
      );
      return { ...prev, equipos: nuevosEquipos, total_orden: totalEquipos.toFixed(2), abono: totalAbono.toFixed(2) };
    });
  }

  function agregarEquipo() {
    setForm(prev => ({
      ...prev,
      equipos: [...prev.equipos, {
        tipo_equipo: 'laptop', marca: '', modelo: '',
        cable: false, cargador: false, contrasena: '', descripcion_problema: '', diagnostico: '',
        trabajo_a_realizar: '', repuesto_a_instalar: '', costo: '0.00', abono_equipo: '0.00'
      }]
    }));
  }

  function eliminarEquipo(index) {
    setForm(prev => {
      const nuevosEquipos = prev.equipos.filter((_, i) => i !== index);
      return { ...prev, equipos: nuevosEquipos };
    });
  }

  // Filtrar clientes por búsqueda
  const clientesFiltrados = clientes.filter(c => {
    const texto = buscarCliente.toLowerCase();
    return `${c.nombre} ${c.apellido}`.toLowerCase().includes(texto) ||
      (c.telefono || '').includes(texto) ||
      (c.cedula_ruc || '').includes(texto);
  });

  function seleccionarCliente(cliente) {
    setClienteSeleccionado(cliente);
    setForm(prev => ({ ...prev, cliente_id: cliente.id }));
    setBuscarCliente(`${cliente.nombre} ${cliente.apellido}`);
    setMostrarClientes(false);
  }

  // ── Crear nuevo cliente inline ───────────────────────────────────────
  async function guardarNuevoCliente() {
    if (!formCliente.nombre.trim()) { setErrorCliente('El nombre es obligatorio'); return; }
    if (!formCliente.apellido.trim()) { setErrorCliente('El apellido es obligatorio'); return; }
    if (!formCliente.telefono.trim()) { setErrorCliente('El teléfono es obligatorio'); return; }
    if (!formCliente.cedula_ruc.trim()) { setErrorCliente('La Cédula/RUC es obligatoria'); return; }
    
    if (formCliente.email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formCliente.email.trim())) {
      setErrorCliente('El formato del correo electrónico es inválido'); return;
    }

    let telefonoDb = formCliente.telefono.trim();
    if (telefonoDb.startsWith('0') && telefonoDb.length === 10) {
      telefonoDb = '+593' + telefonoDb.substring(1);
    }
    const clienteParaGuardar = { ...formCliente, telefono: telefonoDb };

    try {
      setGuardandoCliente(true);
      setErrorCliente(null);
      const nuevoCliente = await crearCliente(clienteParaGuardar);
      // Agregar a la lista local y seleccionarlo
      setClientes(prev => [...prev, nuevoCliente]);
      seleccionarCliente(nuevoCliente);
      setFormCliente(FORM_CLIENTE_INICIAL);
      setMostrarFormCliente(false);
    } catch (err) {
      setErrorCliente(err.message);
    } finally {
      setGuardandoCliente(false);
    }
  }

  const porCancelar = (Number(form.total_orden) || 0) - (Number(form.abono) || 0);

  // ── Guardar la orden ─────────────────────────────────────────────────
  async function guardarOrden(e) {
    e.preventDefault();
    if (!form.cliente_id) { setError('Debes seleccionar un cliente'); return; }
    for (let i = 0; i < form.equipos.length; i++) {
        if (!form.equipos[i].descripcion_problema.trim()) { setError(`La descripción del problema es obligatoria en el equipo ${i+1}`); return; }
        const costoEq = Number(form.equipos[i].costo) || 0;
        const abonoEq = Number(form.equipos[i].abono_equipo) || 0;
        if (abonoEq > costoEq) { setError(`El abono del equipo ${i+1} ($${abonoEq.toFixed(2)}) no puede ser mayor al costo ($${costoEq.toFixed(2)})`); return; }
    }
    if ((Number(form.abono) || 0) > (Number(form.total_orden) || 0)) {
      setError('El abono total no puede ser mayor al total de la orden');
      return;
    }

    try {
      setGuardando(true);
      setError(null);
      const datos = {
        ...form,
        cliente_id: Number(form.cliente_id),
        tecnico_id: form.tecnico_id ? Number(form.tecnico_id) : null,
        total_orden: Number(form.total_orden),
        abono: Number(form.abono),
        garantia_dias: Number(form.garantia_dias),
      };

      if (esEdicion) {
        await actualizarOrden(Number(id), datos);
        navigate('/ordenes');
      } else {
        // Al crear: mostrar modal de éxito con la orden recién creada
        const ordenNueva = await crearOrden(datos);
        setOrdenCreada(ordenNueva);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setGuardando(false);
    }
  }

  // ── Acciones del modal de éxito ──────────────────────────────────────
  function irAOrden() {
    navigate(`/ordenes/${ordenCreada.id}`);
  }

  function irAOrdenes() {
    navigate('/ordenes');
  }

  async function enviarWhatsapp() {
    try {
      const data = await obtenerWhatsappOrden(ordenCreada.id);
      window.open(data.link, '_blank');
    } catch (err) {
      alert('Error al generar el enlace de WhatsApp: ' + err.message);
    }
  }

  // ════════════════════════════════════════════════════════════════════
  // MODAL DE ÉXITO
  // ════════════════════════════════════════════════════════════════════
  if (ordenCreada) {
    return (
      <div className="modal-exito-overlay">
        <div className="modal-exito animar-entrada">
          {/* Ícono de éxito */}
          <div className="modal-exito__icono">
            <CheckCircle size={56} color="var(--color-exito)" />
          </div>

          <h2 className="modal-exito__titulo">¡Orden Creada Exitosamente!</h2>
          <p className="modal-exito__numero">{ordenCreada.numero_orden}</p>

          {/* Resumen de la orden */}
          <div className="modal-exito__resumen">
            <div className="modal-exito__fila">
              <span>Cliente</span>
              <strong>{clienteSeleccionado?.nombre} {clienteSeleccionado?.apellido}</strong>
            </div>
            <div className="modal-exito__fila">
              <span>Equipos</span>
              <strong>{form.equipos.length} equipo(s)</strong>
            </div>
            <div className="modal-exito__fila">
              <span>Total</span>
              <strong>${Number(ordenCreada.total_orden).toFixed(2)}</strong>
            </div>
            <div className="modal-exito__fila">
              <span>Abono</span>
              <strong>${Number(ordenCreada.abono).toFixed(2)}</strong>
            </div>
            <div className="modal-exito__fila">
              <span>Estado</span>
              <strong>Revisión</strong>
            </div>
          </div>

          {/* Botones de acción */}
          <div className="modal-exito__acciones">
            <button
              className="boton-primario"
              onClick={() => descargarPdfOrden(ordenCreada.id)}
              id="btn-descargar-pdf"
            >
              <FileDown size={18} /> Descargar PDF
            </button>
            <button
              className="boton-secundario modal-exito__btn-whatsapp"
              onClick={enviarWhatsapp}
              id="btn-enviar-whatsapp"
            >
              <MessageCircle size={18} /> Enviar por WhatsApp
            </button>
          </div>

          <div className="modal-exito__navegacion">
            <button className="boton-secundario" onClick={irAOrden} id="btn-ver-orden">
              Ver detalle de la orden
            </button>
            <button className="boton-texto" onClick={irAOrdenes} id="btn-volver-ordenes">
              Volver a la lista de órdenes
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ════════════════════════════════════════════════════════════════════
  // FORMULARIO PRINCIPAL
  // ════════════════════════════════════════════════════════════════════
  return (
    <div className="orden-form-pagina">
      <div className="orden-form-pagina__header animar-entrada" style={{ display: 'flex', alignItems: 'center', gap: '20px', marginBottom: '24px', flexWrap: 'wrap' }}>
        <button className="boton-secundario" onClick={() => navigate('/ordenes')}>
          <ArrowLeft size={18} /> Volver
        </button>
        <h2 style={{ margin: 0 }}>{esEdicion ? 'Editar Orden' : 'Nueva Orden de Servicio'}</h2>
        
        <div className="tecnico-header-select" style={{ display: 'flex', alignItems: 'center', gap: '10px', background: 'var(--color-primario-sutil)', padding: '6px 14px', borderRadius: '12px', border: '1px solid var(--color-primario-claro)', marginLeft: '10px' }}>
          <label htmlFor="tecnico-asignado" style={{ fontSize: '13px', fontWeight: '700', color: 'var(--color-oscuro)', whiteSpace: 'nowrap' }}>Técnico:</label>
          {usuario?.rol === 'tecnico' ? (
            // ── Técnico: auto-asignado, no puede cambiar ──
            <>
              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-exito)', padding: '4px 8px' }}>
                {tecnicos.find(t => t.id === Number(form.tecnico_id))?.nombre || 'Tú mismo'} {tecnicos.find(t => t.id === Number(form.tecnico_id))?.apellido || ''}
              </span>
              <span style={{ fontSize: '11px', color: 'var(--color-exito)', fontWeight: 600, background: 'rgba(34,197,94,0.1)', padding: '2px 8px', borderRadius: '6px' }}>
                🔒 Auto-asignado
              </span>
            </>
          ) : (
            // ── Admin / Asistente: pueden elegir ──
            <>
              <select 
                className="campo-texto" 
                style={{ padding: '4px 8px', fontSize: '13px', minWidth: '180px', height: 'auto', border: 'none', background: 'white' }}
                value={form.tecnico_id} 
                onChange={(e) => actualizarCampo('tecnico_id', e.target.value)}
                id="tecnico-asignado"
              >
                <option value="">Seleccionar técnico...</option>
                {tecnicos.map(t => (
                  <option key={t.id} value={t.id}>
                    {t.nombre} {t.apellido}
                  </option>
                ))}
              </select>
              {usuario?.rol === 'admin' && form.tecnico_id && tecnicos.find(t => t.id === Number(form.tecnico_id))?.nombre === usuario?.nombre?.split(' ')[0] && (
                <span style={{ fontSize: '11px', color: 'var(--color-exito)', fontWeight: 600, whiteSpace: 'nowrap' }}>
                  ✅ Auto-asignado
                </span>
              )}
            </>
          )}
        </div>
      </div>

      {error && <div className="dashboard__error animar-entrada"><p>⚠️ {error}</p></div>}

      <form onSubmit={guardarOrden} className="orden-form animar-entrada animar-retraso-1">
        <div className="orden-form__layout">
          {/* ── COLUMNA PRINCIPAL (Izquierda) ── */}
          <div className="orden-form__columna-principal">
            {/* ── SECCIÓN: Cliente ─────────────────────────────────────── */}
        <fieldset className="orden-form__seccion">
          <legend>👤 Datos del Cliente</legend>

          {/* Buscador de cliente existente */}
          {!mostrarFormCliente && (
            <div className="campo-grupo">
              <label className="campo-label">Buscar cliente existente *</label>
              <div className="autocomplete">
                <div className="autocomplete__input-wrap">
                  <Search size={16} className="autocomplete__icono" />
                  <input
                    type="text"
                    className="campo-texto"
                    style={{ paddingLeft: '36px' }}
                    placeholder="Buscar por nombre, teléfono o cédula..."
                    value={buscarCliente}
                    onChange={(e) => { setBuscarCliente(e.target.value); setMostrarClientes(true); }}
                    onFocus={() => setMostrarClientes(true)}
                    id="buscar-cliente-orden"
                  />
                </div>
                {mostrarClientes && buscarCliente && (
                  <div className="autocomplete__lista">
                    {clientesFiltrados.length === 0 ? (
                      <div className="autocomplete__vacio">No se encontraron clientes</div>
                    ) : clientesFiltrados.slice(0, 8).map(c => (
                      <div key={c.id} className="autocomplete__item" onClick={() => seleccionarCliente(c)}>
                        <strong>{c.nombre} {c.apellido}</strong>
                        <span>{c.telefono} {c.cedula_ruc ? `• ${c.cedula_ruc}` : ''}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              {clienteSeleccionado && (
                <div className="cliente-seleccionado">
                  ✅ {clienteSeleccionado.nombre} {clienteSeleccionado.apellido} — {clienteSeleccionado.telefono}
                  <button
                    type="button"
                    className="cliente-seleccionado__limpiar"
                    onClick={() => { setClienteSeleccionado(null); setForm(p => ({ ...p, cliente_id: '' })); setBuscarCliente(''); }}
                  >
                    <X size={14} />
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Botón para alternar entre buscar y crear cliente */}
          <button
            type="button"
            className={`boton-toggle-cliente ${mostrarFormCliente ? 'boton-toggle-cliente--activo' : ''}`}
            onClick={() => {
              setMostrarFormCliente(p => !p);
              setErrorCliente(null);
            }}
            style={{
              width: '100%',
              padding: '12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '10px',
              background: mostrarFormCliente ? 'var(--color-error-fondo)' : 'white',
              border: `2px dashed ${mostrarFormCliente ? 'var(--color-error)' : 'var(--color-primario)'}`,
              borderRadius: '12px',
              color: mostrarFormCliente ? 'var(--color-error)' : 'var(--color-oscuro)',
              fontWeight: '600',
              fontSize: '14px',
              transition: 'all var(--transicion-normal)',
              cursor: 'pointer',
              marginTop: '16px',
              boxShadow: 'var(--sombra-sm)'
            }}
            onMouseEnter={(e) => {
              if (!mostrarFormCliente) e.currentTarget.style.background = 'var(--color-primario-claro)';
              e.currentTarget.style.transform = 'translateY(-1px)';
            }}
            onMouseLeave={(e) => {
              if (!mostrarFormCliente) e.currentTarget.style.background = 'white';
              e.currentTarget.style.transform = 'translateY(0)';
            }}
            id="btn-toggle-nuevo-cliente"
          >
            {mostrarFormCliente ? (
              <><X size={18} /> Cancelar registro de nuevo cliente</>
            ) : (
              <><UserPlus size={18} /> Registrar un nuevo cliente</>
            )}
          </button>

          {/* ── Panel: Formulario de nuevo cliente ───────────────── */}
          {mostrarFormCliente && (
            <div className="nuevo-cliente-panel animar-entrada">
              <h4 className="nuevo-cliente-panel__titulo">✏️ Registrar Nuevo Cliente</h4>

              {errorCliente && (
                <div className="dashboard__error" style={{ marginBottom: '16px' }}>
                  <p>⚠️ {errorCliente}</p>
                </div>
              )}

              <div className="nuevo-cliente-form">
                <div className="orden-form__grid-2">
                  <div className="campo-grupo">
                    <label className="campo-label">Nombre *</label>
                    <input
                      type="text" className="campo-texto" placeholder="Nombre del cliente"
                      value={formCliente.nombre}
                      onChange={e => setFormCliente(p => ({ ...p, nombre: formatearTexto(e.target.value) }))}
                      id="nc-nombre"
                    />
                  </div>
                  <div className="campo-grupo">
                    <label className="campo-label">Apellido *</label>
                    <input
                      type="text" className="campo-texto" placeholder="Apellido del cliente"
                      value={formCliente.apellido}
                      onChange={e => setFormCliente(p => ({ ...p, apellido: formatearTexto(e.target.value) }))}
                      id="nc-apellido"
                    />
                  </div>
                </div>
                <div className="orden-form__grid-2">
                  <div className="campo-grupo">
                    <label className="campo-label">Teléfono *</label>
                    <input
                      type="tel" className="campo-texto" placeholder="Ej: 0985983416"
                      value={formCliente.telefono}
                      onChange={e => setFormCliente(p => ({ ...p, telefono: e.target.value.replace(/\D/g, '').slice(0, 10) }))}
                      id="nc-telefono"
                    />
                  </div>
                  <div className="campo-grupo">
                    <label className="campo-label">Cédula / RUC *</label>
                    <input
                      type="text" className="campo-texto" placeholder="Ej: 0903803575"
                      value={formCliente.cedula_ruc}
                      onChange={e => setFormCliente(p => ({ ...p, cedula_ruc: e.target.value }))}
                      id="nc-cedula"
                    />
                  </div>
                </div>
                <div className="orden-form__grid-2">
                  <div className="campo-grupo">
                    <label className="campo-label">Correo Electrónico</label>
                    <input
                      type="email" className="campo-texto" placeholder="correo@ejemplo.com"
                      value={formCliente.email}
                      onChange={e => setFormCliente(p => ({ ...p, email: e.target.value }))}
                      id="nc-email"
                    />
                  </div>
                  <div className="campo-grupo">
                    <label className="campo-label">Dirección</label>
                    <input
                      type="text" className="campo-texto" placeholder="Dirección del cliente"
                      value={formCliente.direccion}
                      onChange={e => setFormCliente(p => ({ ...p, direccion: e.target.value.toUpperCase() }))}
                      id="nc-direccion"
                    />
                  </div>
                </div>

                <div className="nuevo-cliente-panel__botones">
                  <button
                    type="button"
                    className="boton-secundario"
                    onClick={() => { setMostrarFormCliente(false); setFormCliente(FORM_CLIENTE_INICIAL); }}
                  >
                    Cancelar
                  </button>
                  <button
                    type="button"
                    className="boton-primario"
                    disabled={guardandoCliente}
                    onClick={guardarNuevoCliente}
                    id="btn-guardar-nuevo-cliente"
                  >
                    <UserPlus size={16} />
                    {guardandoCliente ? 'Guardando...' : 'Guardar Cliente'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </fieldset>

        {/* ── SECCIÓN: Equipos ───────────────────────────────────────── */}
        {form.equipos.map((equipo, index) => (
          <div key={index} className="equipo-container orden-form__seccion" style={{ marginBottom: '24px', position: 'relative' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h4 style={{ margin: 0, color: 'var(--color-primario)' }}>Equipo {index + 1}</h4>
                {form.equipos.length > 1 && (
                    <button type="button" className="boton-texto" onClick={() => eliminarEquipo(index)} style={{ color: 'var(--color-error)' }}>
                        <X size={16} /> Eliminar
                    </button>
                )}
            </div>
            
            <fieldset style={{ border: 'none', padding: 0, margin: 0 }}>
              <div className="campo-grupo">
                <label className="campo-label">Tipo de Equipo *</label>
                <div className="tipo-equipo-grid">
                  {TIPOS_EQUIPO.map(tipo => (
                    <button
                      key={tipo.valor} type="button"
                      className={`tipo-equipo-btn ${equipo.tipo_equipo === tipo.valor ? 'tipo-equipo-btn--activo' : ''}`}
                      onClick={() => actualizarCampoEquipo(index, 'tipo_equipo', tipo.valor)}
                    >
                      <span className="tipo-equipo-btn__emoji">{tipo.emoji}</span>
                      <span>{tipo.etiqueta}</span>
                    </button>
                  ))}
                </div>
              </div>
              <div className="orden-form__grid-2">
                <div className="campo-grupo">
                  <label className="campo-label" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>Marca</span>
                    <button type="button" onClick={() => { setMarcaEnModal(''); setModalConfig({ abierto: true, tipo: 'marca', equipo: equipo.tipo_equipo, marca: '' }); }} title="Configurar marcas" style={{ color: 'var(--texto-secundario)', fontSize: '11px', display: 'flex', gap: '4px', alignItems: 'center', background: 'none', border: 'none', cursor: 'pointer' }}>
                      <Settings2 size={13} /> Agregar Marca
                    </button>
                  </label>
                  <input
                    type="text"
                    className="campo-texto"
                    placeholder="Ej: HP, Epson, Samsung"
                    value={equipo.marca}
                    onChange={(e) => actualizarCampoEquipo(index, 'marca', e.target.value)}
                    list={`lista-marcas-${index}`}
                    autoComplete="off"
                  />
                  <datalist id={`lista-marcas-${index}`}>
                    {(marcasPersonalizadas[equipo.tipo_equipo] || []).map(marca => (
                      <option key={marca} value={marca} />
                    ))}
                  </datalist>
                  {(marcasPersonalizadas[equipo.tipo_equipo] || []).length > 0 && (
                    <div className="sugerencias-marcas animar-entrada">
                      {(marcasPersonalizadas[equipo.tipo_equipo] || []).map(marca => (
                        <button
                          key={marca}
                          type="button"
                          className={`chip-marca ${equipo.marca === marca ? 'chip-marca--activo' : ''}`}
                          onClick={() => actualizarCampoEquipo(index, 'marca', marca)}
                        >
                          {marca}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                <div className="campo-grupo">
                  <label className="campo-label" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>Modelo</span>
                    <button type="button" onClick={() => { setMarcaEnModal(equipo.marca || ''); setModalConfig({ abierto: true, tipo: 'modelo', equipo: equipo.tipo_equipo, marca: equipo.marca }); }} title="Configurar modelos" style={{ color: 'var(--texto-secundario)', fontSize: '11px', display: 'flex', gap: '4px', alignItems: 'center', background: 'none', border: 'none', cursor: 'pointer' }}>
                      <Settings2 size={13} /> Agregar Modelo
                    </button>
                  </label>
                  <input
                    type="text"
                    className="campo-texto"
                    placeholder="Ej: 15DA2180NIA"
                    value={equipo.modelo}
                    onChange={(e) => actualizarCampoEquipo(index, 'modelo', e.target.value)}
                    list={`lista-modelos-${index}`}
                    autoComplete="off"
                  />
                <datalist id={`lista-modelos-${index}`}>
                  {Object.keys(modelosPersonalizados[equipo.tipo_equipo]?.[equipo.marca] || {}).map(modelo => (
                    <option key={modelo} value={modelo} />
                  ))}
                </datalist>
                  {Object.keys(modelosPersonalizados[equipo.tipo_equipo]?.[equipo.marca] || {}).length > 0 && (
                    <div className="sugerencias-marcas animar-entrada">
                      {Object.keys(modelosPersonalizados[equipo.tipo_equipo]?.[equipo.marca] || {}).map(modelo => (
                        <button
                          key={modelo}
                          type="button"
                          className={`chip-marca ${equipo.modelo === modelo ? 'chip-marca--activo' : ''}`}
                          onClick={() => actualizarCampoEquipo(index, 'modelo', modelo)}
                        >
                          {modelo}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              <div className="orden-form__grid-2">
                <div className="campo-grupo">
                  <label className="campo-label">Accesorios Recibidos</label>
                  <div style={{ display: 'flex', gap: '16px', marginTop: '8px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '14px', cursor: 'pointer' }}>
                      <input 
                        type="checkbox" 
                        checked={equipo.cable} 
                        onChange={(e) => {
                          actualizarCampoEquipo(index, 'cable', e.target.checked);
                        }} 
                      /> Cable
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '14px', cursor: 'pointer' }}>
                      <input 
                        type="checkbox" 
                        checked={equipo.cargador} 
                        onChange={(e) => {
                          actualizarCampoEquipo(index, 'cargador', e.target.checked);
                        }} 
                      /> Cargador
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '14px', cursor: 'pointer' }}>
                      <input 
                        type="checkbox" 
                        checked={!equipo.cable && !equipo.cargador} 
                        onChange={(e) => {
                          if (e.target.checked) {
                            actualizarCampoEquipo(index, 'cable', false);
                            actualizarCampoEquipo(index, 'cargador', false);
                          }
                        }} 
                      /> No se recibe
                    </label>
                  </div>
                </div>
                <div className="campo-grupo">
                  <label className="campo-label">Contraseña del equipo</label>
                  <input type="text" className="campo-texto" placeholder="Si aplica" value={equipo.contrasena || ''} onChange={(e) => actualizarCampoEquipo(index, 'contrasena', e.target.value)} />
                </div>
              </div>
            </fieldset>

            {/* ── SECCIÓN: Problema y Trabajo ───────────────────────────── */}
            <fieldset style={{ border: 'none', padding: 0, margin: '20px 0 0 0' }}>
              <div className="campo-grupo">
                <label className="campo-label">Descripción del Problema *</label>
                <textarea className="campo-texto" rows={3} placeholder="¿Qué le pasa al equipo?" value={equipo.descripcion_problema} onChange={(e) => actualizarCampoEquipo(index, 'descripcion_problema', e.target.value)} />
              </div>
              <div className="campo-grupo">
                <label className="campo-label">Diagnóstico</label>
                <textarea className="campo-texto" rows={2} placeholder="Resultado de la revisión técnica" value={equipo.diagnostico} onChange={(e) => actualizarCampoEquipo(index, 'diagnostico', e.target.value)} />
              </div>
              <div className="campo-grupo">
                <label className="campo-label">Trabajo a Realizar</label>
                <textarea className="campo-texto" rows={2} placeholder="¿Qué se va a hacer?" value={equipo.trabajo_a_realizar} onChange={(e) => actualizarCampoEquipo(index, 'trabajo_a_realizar', e.target.value)} />
              </div>
              <div className="campo-grupo">
                <label className="campo-label">Repuesto a Instalar</label>
                <input type="text" className="campo-texto" placeholder="Ej: SSD 480GB, Teclado, etc." value={equipo.repuesto_a_instalar} onChange={(e) => actualizarCampoEquipo(index, 'repuesto_a_instalar', e.target.value)} />
              </div>
              <div className="orden-form__grid-2" style={{ marginTop: '20px' }}>
                <div className="campo-grupo">
                  <label className="campo-label">Costo del Servicio ($)</label>
                  <div className="monto-control">
                    <button type="button" className="monto-btn monto-btn--menos" onClick={() => {
                      const actual = Number(equipo.costo) || 0;
                      actualizarCampoEquipo(index, 'costo', Math.max(0, actual - 5).toFixed(2));
                    }}>−</button>
                    <input type="text" className="monto-input"
                      value={equipo.costo}
                      onChange={e => {
                        const val = e.target.value.replace(/[^0-9.]/g, '');
                        actualizarCampoEquipo(index, 'costo', val);
                      }}
                      onBlur={() => {
                        actualizarCampoEquipo(index, 'costo', (Number(equipo.costo) || 0).toFixed(2));
                      }}
                    />
                    <button type="button" className="monto-btn monto-btn--mas" onClick={() => {
                      const actual = Number(equipo.costo) || 0;
                      actualizarCampoEquipo(index, 'costo', (actual + 5).toFixed(2));
                    }}>+</button>
                  </div>
                </div>
                <div className="campo-grupo">
                  <label className="campo-label">Abono del Equipo ($)</label>
                  <div className="monto-control">
                    <button type="button" className="monto-btn monto-btn--menos" onClick={() => {
                      const actual = Number(equipo.abono_equipo) || 0;
                      actualizarCampoEquipo(index, 'abono_equipo', Math.max(0, actual - 5).toFixed(2));
                    }}>−</button>
                    <input type="text" className="monto-input"
                      value={equipo.abono_equipo || '0.00'}
                      onChange={e => {
                        const val = e.target.value.replace(/[^0-9.]/g, '');
                        actualizarCampoEquipo(index, 'abono_equipo', val);
                      }}
                      onBlur={() => {
                        let val = Number(equipo.abono_equipo) || 0;
                        const costoMax = Number(equipo.costo) || 0;
                        if (val > costoMax) val = costoMax;
                        actualizarCampoEquipo(index, 'abono_equipo', val.toFixed(2));
                      }}
                    />
                    <button type="button" className="monto-btn monto-btn--mas" onClick={() => {
                      const actual = Number(equipo.abono_equipo) || 0;
                      const costoMax = Number(equipo.costo) || 0;
                      // No permitir que el abono exceda el costo del equipo
                      const nuevoAbono = Math.min(actual + 5, costoMax);
                      actualizarCampoEquipo(index, 'abono_equipo', nuevoAbono.toFixed(2));
                    }}>+</button>
                  </div>
                </div>
              </div>
            </fieldset>
          </div>
        ))}

        <div style={{ marginBottom: '32px' }}>
          <button 
            type="button" 
            onClick={agregarEquipo}
            style={{
              width: '100%',
              padding: '18px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '12px',
              background: 'white',
              border: '2px dashed var(--color-primario)',
              borderRadius: '16px',
              color: 'var(--color-oscuro)',
              fontWeight: '700',
              fontSize: '16px',
              transition: 'all var(--transicion-normal)',
              cursor: 'pointer',
              boxShadow: 'var(--sombra-sm)'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--color-primario-claro)';
              e.currentTarget.style.borderColor = 'var(--color-primario-hover)';
              e.currentTarget.style.boxShadow = 'var(--sombra-md)';
              e.currentTarget.style.transform = 'translateY(-2px)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'white';
              e.currentTarget.style.borderColor = 'var(--color-primario)';
              e.currentTarget.style.boxShadow = 'var(--sombra-sm)';
              e.currentTarget.style.transform = 'translateY(0)';
            }}
          >
            <div style={{ 
              background: 'var(--color-primario)', 
              borderRadius: '50%', 
              width: '32px', 
              height: '32px', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              color: 'var(--texto-sobre-primario)'
            }}>
              <Plus size={20} strokeWidth={3} />
            </div>
            <span>Añadir otro equipo al servicio</span>
          </button>
        </div>
          </div> {/* Fin Columna Principal */}

          {/* ── COLUMNA LATERAL (Derecha) ── */}
          <div className="orden-form__columna-lateral">
            {/* ── SECCIÓN: Financiero y Asignación ─────────────────────── */}
        <fieldset className="orden-form__seccion">
          <legend>💰 Datos Financieros y Asignación</legend>

          <div className="flex-columna" style={{ gap: '12px' }}>

            <div className="campo-grupo">
              <label className="campo-label">Total Orden ($) <span style={{ fontSize: '11px', color: 'var(--texto-secundario)' }}>(auto-calculado)</span></label>
              <div className="monto-control">
                <input type="text" className="monto-input" value={form.total_orden} readOnly style={{ fontWeight: 800, fontSize: '16px', color: 'var(--color-primario)' }} />
              </div>
            </div>
            <div className="campo-grupo">
              <label className="campo-label">Abono ($) <span style={{ fontSize: '11px', color: 'var(--texto-secundario)' }}>(auto-calculado)</span></label>
              <div className="monto-control">
                <input type="text" className="monto-input" value={form.abono} readOnly style={{ fontWeight: 700, fontSize: '16px', color: 'var(--color-exito)' }} />
              </div>
            </div>
            <div className="campo-grupo" style={{
              background: porCancelar > 0 ? 'var(--color-error-fondo)' : 'var(--color-exito-fondo)',
              borderRadius: 'var(--borde-radio-sm)',
              padding: '8px 12px',
              marginTop: '4px'
            }}>
              <label className="campo-label" style={{ fontSize: '12px', marginBottom: '2px', display: 'block' }}>Por Cancelar</label>
              <span style={{ fontWeight: 800, fontSize: '20px', color: porCancelar > 0 ? 'var(--color-error)' : 'var(--color-exito)' }}>
                ${porCancelar.toFixed(2)}
              </span>
            </div>
          </div>

          <div className="campo-grupo">
            <label className="campo-label">Garantía</label>
            <select className="campo-texto" value={form.garantia_dias} onChange={(e) => actualizarCampo('garantia_dias', e.target.value)}>
              {GARANTIAS.map(g => <option key={g.valor} value={g.valor}>{g.etiqueta}</option>)}
            </select>
          </div>
          <div className="campo-grupo">
            <label className="campo-label">Notas Internas (solo visibles para el equipo)</label>
            <textarea className="campo-texto" rows={2} placeholder="Notas privadas sobre esta orden..." value={form.notas_internas} onChange={(e) => actualizarCampo('notas_internas', e.target.value)} />
          </div>
        </fieldset>

        {/* ── Botones de acción ─────────────────────────────────────── */}
        <div className="orden-form__botones" style={{ flexDirection: 'column', width: '100%' }}>
          <button type="submit" className="boton-primario" disabled={guardando} id="btn-guardar-orden" style={{ width: '100%', justifyContent: 'center', padding: '14px' }}>
            <Save size={18} /> {guardando ? 'Guardando...' : (esEdicion ? 'Actualizar Orden' : 'Crear Orden')}
          </button>
          <button type="button" className="boton-secundario" onClick={() => navigate('/ordenes')} style={{ width: '100%', justifyContent: 'center' }}>Cancelar</button>
        </div>
          </div> {/* Fin Columna Lateral */}
        </div> {/* Fin Layout Grid */}
      </form>

      {/* Modal de Configuración de Marcas/Modelos */}
      {modalConfig.abierto && (
        <div className="modal-exito-overlay animar-entrada">
          <div className="modal-exito" style={{ maxWidth: '400px', width: '90%' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 className="modal-exito__titulo" style={{ fontSize: '18px', textAlign: 'left' }}>
                Configurar {modalConfig.tipo === 'marca' ? 'Marcas' : 'Modelos'}
              </h3>
              <button type="button" className="boton-texto" onClick={() => { setMarcaEnModal(''); setModalConfig({ abierto: false, tipo: '', equipo: '', marca: '' }); }} style={{ padding: 0 }}><X size={20} /></button>
            </div>
            <p className="texto-secundario" style={{ marginBottom: '16px', fontSize: '13px', textAlign: 'left' }}>
              Categoría: <strong>{TIPOS_EQUIPO.find(t => t.valor === modalConfig.equipo)?.etiqueta}</strong>
              {modalConfig.tipo === 'modelo' && modalConfig.marca && (
                <> · Marca actual: <strong>{modalConfig.marca}</strong></>
              )}
            </p>

            {modalConfig.tipo === 'modelo' && (
              <div className="campo-grupo" style={{ marginBottom: '8px' }}>
                <label className="campo-label" style={{ fontSize: '12px' }}>Marca *</label>
                <input
                  type="text"
                  className="campo-texto"
                  placeholder="Ej: Epson, HP, Dell..."
                  value={marcaEnModal}
                  onChange={e => setMarcaEnModal(e.target.value)}
                  list={`lista-marcas-modal`}
                  autoComplete="off"
                />
                <datalist id={`lista-marcas-modal`}>
                  {(marcasPersonalizadas[modalConfig.equipo] || []).map(m => (
                    <option key={m} value={m} />
                  ))}
                </datalist>
              </div>
            )}

            <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
              <input
                type="text"
                className="campo-texto"
                placeholder={modalConfig.tipo === 'marca' ? 'Agregar marca...' : 'Agregar modelo...'}
                value={nuevoItemConfig}
                onChange={e => setNuevoItemConfig(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); agregarItemConfig(); } }}
              />
              <button
                type="button"
                className="boton-primario"
                onClick={agregarItemConfig}
                style={{ padding: '0 16px' }}
              >
                <Plus size={16} />
              </button>
            </div>

            <div className="config-items-lista" style={{ maxHeight: '200px', overflowY: 'auto', border: '1px solid var(--borde-color)', borderRadius: 'var(--borde-radio-sm)', padding: '8px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {(() => {
                if (modalConfig.tipo === 'marca') {
                  const items = marcasPersonalizadas[modalConfig.equipo] || [];
                  if (items.length === 0) {
                    return <p style={{ fontSize: '13px', color: 'var(--texto-secundario)', textAlign: 'center', padding: '20px 0' }}>No hay elementos guardados.</p>;
                  }
                  return items.map((item, idx) => (
                    <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 12px', background: 'var(--fondo-principal)', borderRadius: 'var(--borde-radio-sm)' }}>
                      <span style={{ fontSize: '14px' }}>{item}</span>
                      <button type="button" onClick={() => eliminarItemConfig(item)} style={{ background: 'none', border: 'none', color: 'var(--color-error)', cursor: 'pointer', display: 'flex', alignItems: 'center', padding: '4px' }} title="Eliminar">
                        <X size={14} />
                      </button>
                    </div>
                  ));
                } else {
                  // Modelos: mostrar agrupados por marca
                  const modelos = modelosPersonalizados[modalConfig.equipo] || {};
                  const entradas = Object.entries(modelos);
                  if (entradas.length === 0) {
                    return <p style={{ fontSize: '13px', color: 'var(--texto-secundario)', textAlign: 'center', padding: '20px 0' }}>No hay elementos guardados.</p>;
                  }
                  return entradas.flatMap(([brand, models]) => [
                    <div key={brand} style={{ fontWeight: 700, fontSize: '13px', padding: '8px 8px 2px 8px', color: 'var(--texto-secundario)', borderBottom: '1px solid var(--borde-color)', marginBottom: '4px' }}>
                      {brand}
                    </div>,
                    ...Object.keys(models).map(modelo => (
                      <div key={`${brand}||${modelo}`} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 12px 4px 24px', background: 'var(--fondo-principal)', borderRadius: 'var(--borde-radio-sm)' }}>
                        <span style={{ fontSize: '14px' }}>{modelo}</span>
                        <button type="button" onClick={() => eliminarItemConfig(`${brand}||${modelo}`)} style={{ background: 'none', border: 'none', color: 'var(--color-error)', cursor: 'pointer', display: 'flex', alignItems: 'center', padding: '4px' }} title="Eliminar">
                          <X size={14} />
                        </button>
                      </div>
                    ))
                  ]);
                }
              })()}
            </div>

            <div className="modal-exito__acciones" style={{ marginTop: '20px' }}>
              <button
                type="button"
                className="boton-primario"
                onClick={() => { setMarcaEnModal(''); setModalConfig({ abierto: false, tipo: '', equipo: '', marca: '' }); }}
              >
                Listo
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

