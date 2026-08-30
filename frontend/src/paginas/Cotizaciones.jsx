/**
 * GESTIÓN DE COTIZACIONES
 */
import { useState, useEffect } from 'react';
import { Plus, FileText, MessageCircle, Search, X, Save, Trash2, Mail } from 'lucide-react';
import { obtenerCotizaciones, crearCotizacion, aprobarCotizacion, obtenerWhatsappCotizacion, obtenerClientes, descargarPdfCotizacion } from '../api/orpey-api';
import BadgeEstado from '../componentes/BadgeEstado';
import './Cotizaciones.css';

export default function Cotizaciones() {
  const [cotizaciones, setCotizaciones] = useState([]);
  const [clientes, setClientes] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [filtroEstado, setFiltroEstado] = useState('');
  const [mostrarModal, setMostrarModal] = useState(false);

  useEffect(() => { cargar(); }, [filtroEstado]);

  useEffect(() => {
    obtenerClientes().then(setClientes).catch(err => console.error('Error cargando clientes:', err));
  }, []);

  async function cargar() {
    try {
      setCargando(true);
      const filtros = {};
      if (filtroEstado) filtros.estado = filtroEstado;
      setCotizaciones(await obtenerCotizaciones(filtros));
    } catch (err) { console.error(err); }
    finally { setCargando(false); }
  }

  async function aprobar(id) {
    if (!confirm('¿Aprobar esta cotización?')) return;
    try { await aprobarCotizacion(id); cargar(); }
    catch (err) { alert(err.message); }
  }

  async function enviarWa(id) {
    try {
      const data = await obtenerWhatsappCotizacion(id);
      window.open(data.link, '_blank');
    } catch (err) { alert(err.message); }
  }

  function onCotizacionCreada(creada) {
    setMostrarModal(false);
    cargar();
    alert(`Cotización ${creada.numero_cotizacion || ''} creada correctamente`);
  }

  return (
    <div className="cotizaciones-pagina">
      <div className="ordenes-pagina__acciones animar-entrada">
        <div className="ordenes-pagina__filtros">
          <select value={filtroEstado} onChange={(e) => setFiltroEstado(e.target.value)} className="campo-texto filtro-select">
            <option value="">Todos los estados</option>
            <option value="abierta">Abierta</option>
            <option value="aprobada">Aprobada</option>
            <option value="cerrada">Cerrada</option>
            <option value="rechazada">Rechazada</option>
          </select>
        </div>
        <button className="boton-primario" onClick={() => setMostrarModal(true)} id="btn-nueva-cotizacion">
          <Plus size={18} /> Nueva Cotización
        </button>
      </div>

      <div className="ordenes-pagina__tabla animar-entrada animar-retraso-1">
        {cargando ? (
          <div className="dashboard__cargando"><div className="spinner" /></div>
        ) : cotizaciones.length === 0 ? (
          <div className="dashboard__vacio">
            <FileText size={44} strokeWidth={1.5} />
            <p>No hay cotizaciones registradas</p>
            <button className="boton-primario" onClick={() => setMostrarModal(true)}>
              <Plus size={16} /> Crear primera cotización
            </button>
          </div>
        ) : (
          <table className="tabla">
            <thead>
              <tr><th>N° Cotización</th><th>Estado</th><th>Descripción</th><th>Total</th><th>Validez</th><th>Fecha</th><th>Acciones</th></tr>
            </thead>
            <tbody>
              {cotizaciones.map(c => {
                const clienteC = clientes.find(cl => cl.id === c.cliente_id);
                return (
                <tr key={c.id}>
                  <td><strong>{c.numero_cotizacion}</strong></td>
                  <td><BadgeEstado estado={c.estado} /></td>
                  <td style={{maxWidth: '250px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'}}>
                    {c.descripcion === "Cotización General" && c.items && c.items.length > 0 
                      ? c.items[0].descripcion 
                      : c.descripcion}
                  </td>
                  <td>${Number(c.total ?? 0).toFixed(2)}</td>
                  <td>{c.validez_dias ?? ''}</td>
                  <td>{c.fecha_creacion ? new Date(c.fecha_creacion).toLocaleDateString('es-EC') : ''}</td>
                  <td>
                    <div className="tabla__acciones">
                      {c.estado === 'abierta' && (
                        <button className="boton-secundario" onClick={() => aprobar(c.id)} style={{padding:'6px 12px', fontSize:'12px'}}>✅ Aprobar</button>
                      )}
                      <button className="boton-icono" onClick={() => descargarPdfCotizacion(c.id)} title="Descargar PDF" style={{color:'#D32F2F'}}><FileText size={16} /></button>
                      <button className="boton-icono" onClick={() => enviarWa(c.id)} title="WhatsApp" style={{color:'#25D366'}}><MessageCircle size={16} /></button>
                      <button className="boton-icono" onClick={() => {
                        const email = clienteC?.email;
                        if (email) {
                          window.open(`mailto:${email}?subject=Cotización N° ${c.numero_cotizacion}&body=Hola, adjunto encontrará la cotización solicitada.`, '_blank');
                        } else {
                          alert("El cliente no tiene un correo electrónico registrado.");
                        }
                      }} title="Email" style={{color:'#1976D2'}}><Mail size={16} /></button>
                    </div>
                  </td>
                </tr>
              )})}
            </tbody>
          </table>
        )}
      </div>

      {mostrarModal && (
        <ModalCotizacion
          clientes={clientes}
          onCerrar={() => setMostrarModal(false)}
          onGuardado={onCotizacionCreada}
        />
      )}
    </div>
  );
}

/**
 * MODAL DE COTIZACIÓN - Formulario para crear una cotización nueva
 */
function ModalCotizacion({ clientes, onCerrar, onGuardado }) {
  const [clienteSeleccionado, setClienteSeleccionado] = useState(null);
  const [buscarCliente, setBuscarCliente] = useState('');
  const [mostrarClientes, setMostrarClientes] = useState(false);
  const [form, setForm] = useState({ validez_dias: 7 });
  const [items, setItems] = useState([{ descripcion: '', cantidad: 1, precio_unitario: '' }]);
  const [incluyeIva, setIncluyeIva] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);

  const subtotal = items.reduce((acc, it) => acc + (Number(it.cantidad || 0) * Number(it.precio_unitario || 0)), 0);
  const totalCotizacion = incluyeIva ? subtotal * 1.15 : subtotal;

  const clientesFiltrados = clientes.filter(c => {
    const texto = buscarCliente.toLowerCase();
    return `${c.nombre} ${c.apellido}`.toLowerCase().includes(texto) ||
      (c.telefono || '').includes(texto) ||
      (c.cedula_ruc || '').includes(texto);
  });

  function seleccionarCliente(cliente) {
    setClienteSeleccionado(cliente);
    setBuscarCliente(`${cliente.nombre} ${cliente.apellido}`);
    setMostrarClientes(false);
    setError(null);
  }

  async function guardar(e) {
    e.preventDefault();
    if (!clienteSeleccionado) {
      setError('Selecciona un cliente para la cotización');
      return;
    }
    const itemsValidos = items.filter(it => it.descripcion.trim() !== '');
    if (itemsValidos.length === 0) {
      setError('Añade al menos un ítem con descripción');
      return;
    }

    const itemsAEnviar = itemsValidos.map(it => ({
      descripcion: it.descripcion.trim(),
      cantidad: Number(it.cantidad) || 1,
      precio_unitario: Number(it.precio_unitario) || 0,
      total_item: (Number(it.cantidad) || 1) * (Number(it.precio_unitario) || 0)
    }));

    const datos = {
      cliente_id: clienteSeleccionado.id,
      descripcion: "Cotización General",
      validez_dias: Number(form.validez_dias) || 7,
      total: totalCotizacion,
      incluye_iva: incluyeIva,
      items: itemsAEnviar
    };

    try {
      setGuardando(true); setError(null);
      const creada = await crearCotizacion(datos);
      onGuardado(creada);
    } catch (err) { setError(err.message); }
    finally { setGuardando(false); }
  }

  function agregarItem() {
    setItems([...items, { descripcion: '', cantidad: 1, precio_unitario: '' }]);
  }

  function eliminarItem(index) {
    if (items.length === 1) return;
    setItems(items.filter((_, i) => i !== index));
  }

  function updateItem(index, field, value) {
    const nuevosItems = [...items];
    nuevosItems[index][field] = value;
    setItems(nuevosItems);
  }

  return (
    <div className="modal-overlay" onClick={onCerrar}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h3>Nueva Cotización</h3>
          <button className="boton-icono" onClick={onCerrar}><X size={20} /></button>
        </div>
        {error && <div className="dashboard__error" style={{margin: '0 0 16px'}}><p>{error}</p></div>}
        <form onSubmit={guardar}>
          <div className="campo-grupo">
            <label className="campo-label">Cliente *</label>
            <div className="autocomplete">
              <div className="autocomplete__input-wrap">
                <Search size={16} className="autocomplete__icono" />
                <input
                  type="text"
                  className="campo-texto cot-autocomplete__input"
                  placeholder="Buscar por nombre, teléfono o cédula..."
                  value={buscarCliente}
                  onChange={(e) => { setBuscarCliente(e.target.value); setMostrarClientes(true); }}
                  onFocus={() => setMostrarClientes(true)}
                  id="buscar-cliente-cotizacion"
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
                  onClick={() => { setClienteSeleccionado(null); setBuscarCliente(''); }}
                >
                  <X size={14} />
                </button>
              </div>
            )}
          </div>

          <div className="campo-grupo">
            <label className="campo-label">Ítems de la Cotización</label>
            <div style={{display: 'flex', flexDirection: 'column', gap: '8px'}}>
              {items.map((item, i) => (
                <div key={i} style={{display: 'flex', gap: '8px', alignItems: 'center'}}>
                  <input type="text" className="campo-texto" placeholder="Descripción del trabajo o repuesto" value={item.descripcion} onChange={(e) => updateItem(i, 'descripcion', e.target.value)} style={{flex: '3'}} />
                  <input type="number" min="1" className="campo-texto" placeholder="Cant." value={item.cantidad} onChange={(e) => updateItem(i, 'cantidad', e.target.value)} style={{flex: '1'}} />
                  <input type="number" min="0" step="0.01" className="campo-texto" placeholder="P. Unit ($)" value={item.precio_unitario} onChange={(e) => updateItem(i, 'precio_unitario', e.target.value)} style={{flex: '1'}} />
                  <button type="button" className="boton-icono" onClick={() => eliminarItem(i)} style={{color: '#D32F2F'}} disabled={items.length === 1}><Trash2 size={18} /></button>
                </div>
              ))}
              <button type="button" className="boton-secundario" onClick={agregarItem} style={{alignSelf: 'flex-start', padding: '6px 12px', fontSize: '12px', marginTop: '4px'}}>
                <Plus size={14} /> Añadir Ítem
              </button>
            </div>
          </div>

          <div className="orden-form__grid-2" style={{alignItems: 'center'}}>
            <div className="campo-grupo" style={{marginBottom: 0}}>
              <label style={{display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontWeight: 'bold'}}>
                <input type="checkbox" checked={incluyeIva} onChange={(e) => setIncluyeIva(e.target.checked)} />
                Incluye IVA (15%)
              </label>
            </div>
            <div className="campo-grupo" style={{marginBottom: 0, textAlign: 'right'}}>
              <span style={{fontSize: '18px', fontWeight: 'bold', color: '#1F2937'}}>
                Total: ${totalCotizacion.toFixed(2)}
              </span>
            </div>
          </div>
          <br/>
          
          <div className="orden-form__grid-2">
            <div className="campo-grupo">
              <label className="campo-label">Validez (días)</label>
              <input
                type="number" min="1" step="1"
                className="campo-texto"
                placeholder="7"
                value={form.validez_dias}
                onChange={(e) => setForm(p => ({ ...p, validez_dias: e.target.value }))}
              />
            </div>
            <div></div>
          </div>

          <div className="modal__botones">
            <button type="button" className="boton-secundario" onClick={onCerrar}>Cancelar</button>
            <button type="submit" className="boton-primario" disabled={guardando}>
              <Save size={16} /> {guardando ? 'Guardando...' : 'Guardar cotización'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}