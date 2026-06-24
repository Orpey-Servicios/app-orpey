/**
 * GESTIÓN DE CLIENTES - Listado y CRUD
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, Users, X, Save } from 'lucide-react';
import { obtenerClientes, crearCliente, actualizarCliente, eliminarCliente } from '../api/orpey-api';
import './Clientes.css';

export default function Clientes() {
  const [clientes, setClientes] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [busqueda, setBusqueda] = useState('');
  const [modal, setModal] = useState(null); // null = cerrado, 'nuevo' o {cliente}
  const navigate = useNavigate();

  useEffect(() => { cargarClientes(); }, []);

  async function cargarClientes() {
    try { setCargando(true); const data = await obtenerClientes(); setClientes(data); }
    catch (err) { console.error(err); }
    finally { setCargando(false); }
  }

  // Filtrar clientes por búsqueda
  const clientesFiltrados = clientes.filter(c => {
    if (!busqueda) return true;
    const texto = busqueda.toLowerCase();
    return `${c.nombre} ${c.apellido}`.toLowerCase().includes(texto) ||
      (c.telefono || '').includes(texto) || (c.cedula_ruc || '').includes(texto);
  });

  // Eliminar cliente
  async function borrarCliente(id) {
    if (!confirm('¿Desactivar este cliente?')) return;
    try { await eliminarCliente(id); cargarClientes(); }
    catch (err) { alert(err.message); }
  }

  return (
    <div className="clientes-pagina">
      {/* Acciones */}
      <div className="ordenes-pagina__acciones animar-entrada">
        <div className="ordenes-pagina__filtros">
          <div className="filtro-buscador">
            <Search size={16} className="filtro-buscador__icono" />
            <input type="text" placeholder="Buscar por nombre, teléfono, cédula..." value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)} className="campo-texto filtro-buscador__input" id="buscar-clientes" />
          </div>
        </div>
        <button className="boton-primario" onClick={() => setModal('nuevo')} id="btn-nuevo-cliente">
          <Plus size={18} /> Nuevo Cliente
        </button>
      </div>

      {/* Tabla */}
      <div className="ordenes-pagina__tabla animar-entrada animar-retraso-1">
        {cargando ? (
          <div className="dashboard__cargando"><div className="spinner" /></div>
        ) : clientesFiltrados.length === 0 ? (
          <div className="dashboard__vacio">
            <Users size={44} strokeWidth={1.5} />
            <p>{clientes.length === 0 ? 'No hay clientes registrados' : 'No se encontraron resultados'}</p>
          </div>
        ) : (
          <table className="tabla">
            <thead>
              <tr><th>Nombre</th><th>Teléfono</th><th>Email</th><th>Cédula/RUC</th><th>Dirección</th><th>Acciones</th></tr>
            </thead>
            <tbody>
              {clientesFiltrados.map(c => (
                <tr key={c.id}>
                  <td><strong className="tabla__fila-click" onClick={() => navigate(`/clientes/${c.id}`)}>{c.nombre} {c.apellido}</strong></td>
                  <td>{c.telefono}</td>
                  <td>{c.email || '—'}</td>
                  <td>{c.cedula_ruc || '—'}</td>
                  <td>{c.direccion || '—'}</td>
                  <td>
                    <div className="tabla__acciones">
                      <button className="boton-icono" onClick={() => setModal(c)} title="Editar">✏️</button>
                      <button className="boton-icono" onClick={() => borrarCliente(c.id)} title="Desactivar">🗑️</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Modal para crear/editar cliente */}
      {modal && (
        <ModalCliente
          cliente={modal === 'nuevo' ? null : modal}
          onCerrar={() => setModal(null)}
          onGuardado={() => { setModal(null); cargarClientes(); }}
        />
      )}
    </div>
  );
}

/**
 * MODAL DE CLIENTE - Formulario para crear o editar
 */
function ModalCliente({ cliente, onCerrar, onGuardado }) {
  const esEdicion = !!cliente;
  const telOriginal = cliente?.telefono || '';
  const telParaForm = telOriginal.startsWith('+593') ? '0' + telOriginal.substring(4) : telOriginal;

  const [form, setForm] = useState({
    nombre: cliente?.nombre || '', apellido: cliente?.apellido || '',
    telefono: telParaForm, email: cliente?.email || '',
    direccion: cliente?.direccion || '', cedula_ruc: cliente?.cedula_ruc || '',
    tipo_persona: cliente?.tipo_persona || 'natural',
  });
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);

  // Función para formatear texto como Título
  const formatearTexto = (texto) => {
    return texto.toLowerCase().replace(/(?:^|\s)\S/g, a => a.toUpperCase());
  };

  async function guardar(e) {
    e.preventDefault();
    if (!form.nombre.trim() || !form.apellido.trim() || !form.telefono.trim()) {
      setError('Nombre, apellido y teléfono son obligatorios'); return;
    }
    if (!form.cedula_ruc.trim()) {
      setError('La Cédula/RUC es obligatoria'); return;
    }
    if (form.email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
      setError('El formato del correo electrónico es inválido'); return;
    }
    let telefonoDb = form.telefono.trim();
    if (telefonoDb.startsWith('0') && telefonoDb.length === 10) {
      telefonoDb = '+593' + telefonoDb.substring(1);
    }
    const dataGuardar = { ...form, telefono: telefonoDb };

    try {
      setGuardando(true); setError(null);
      if (esEdicion) { await actualizarCliente(cliente.id, dataGuardar); }
      else { await crearCliente(dataGuardar); }
      onGuardado();
    } catch (err) { setError(err.message); }
    finally { setGuardando(false); }
  }

  return (
    <div className="modal-overlay" onClick={onCerrar}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h3>{esEdicion ? 'Editar Cliente' : 'Nuevo Cliente'}</h3>
          <button className="boton-icono" onClick={onCerrar}><X size={20} /></button>
        </div>
        {error && <div className="dashboard__error" style={{margin: '0 0 16px'}}><p>{error}</p></div>}
        <form onSubmit={guardar}>
          <div className="orden-form__grid-2">
            <div className="campo-grupo">
              <label className="campo-label">Nombre *</label>
              <input type="text" className="campo-texto" placeholder="Gerardo" value={form.nombre} onChange={(e) => setForm(p => ({...p, nombre: formatearTexto(e.target.value)}))} />
            </div>
            <div className="campo-grupo">
              <label className="campo-label">Apellido *</label>
              <input type="text" className="campo-texto" placeholder="Zumba" value={form.apellido} onChange={(e) => setForm(p => ({...p, apellido: formatearTexto(e.target.value)}))} />
            </div>
          </div>
          <div className="orden-form__grid-2">
            <div className="campo-grupo">
              <label className="campo-label">Teléfono * (+593)</label>
              <input type="text" className="campo-texto" placeholder="0985983416" value={form.telefono} onChange={(e) => setForm(p => ({...p, telefono: e.target.value.replace(/\D/g, '').slice(0, 10)}))} />
            </div>
            <div className="campo-grupo">
              <label className="campo-label">Cédula / RUC *</label>
              <input type="text" className="campo-texto" placeholder="0903803575" value={form.cedula_ruc} onChange={(e) => setForm(p => ({...p, cedula_ruc: e.target.value}))} />
            </div>
          </div>
          <div className="campo-grupo">
            <label className="campo-label">Email</label>
            <input type="email" className="campo-texto" placeholder="correo@ejemplo.com" value={form.email} onChange={(e) => setForm(p => ({...p, email: e.target.value}))} />
          </div>
          <div className="campo-grupo">
            <label className="campo-label">Dirección</label>
            <input type="text" className="campo-texto" placeholder="Guayaquil, sector..." value={form.direccion} onChange={(e) => setForm(p => ({...p, direccion: e.target.value.toUpperCase()}))} />
          </div>
          <div className="campo-grupo">
            <label className="campo-label">Tipo</label>
            <select className="campo-texto" value={form.tipo_persona} onChange={(e) => setForm(p => ({...p, tipo_persona: e.target.value}))}>
              <option value="natural">Persona Natural</option>
              <option value="juridica">Empresa (Persona Jurídica)</option>
            </select>
          </div>
          <div className="modal__botones">
            <button type="button" className="boton-secundario" onClick={onCerrar}>Cancelar</button>
            <button type="submit" className="boton-primario" disabled={guardando}>
              <Save size={16} /> {guardando ? 'Guardando...' : 'Guardar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
