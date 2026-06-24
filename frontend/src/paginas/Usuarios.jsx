import { useState, useEffect } from 'react';
import { Plus, Search, Users, X, Save, Shield, UserX } from 'lucide-react';
import { obtenerUsuarios, crearUsuario, actualizarUsuario, desactivarUsuario } from '../api/orpey-api';
import { useAuth } from '../context/AuthContext';
import './Usuarios.css';

const roles = [
  { valor: 'admin', etiqueta: 'Administrador' },
  { valor: 'tecnico', etiqueta: 'Técnico' },
  { valor: 'asistente', etiqueta: 'Asistente' },
];

const badgeRolClass = {
  admin: 'badge-rol--admin',
  tecnico: 'badge-rol--tecnico',
  asistente: 'badge-rol--asistente',
};

export default function Usuarios() {
  const [usuarios, setUsuarios] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [busqueda, setBusqueda] = useState('');
  const [modal, setModal] = useState(null);
  const { usuario: usuarioActual } = useAuth();

  useEffect(() => { cargarUsuarios(); }, []);

  async function cargarUsuarios() {
    try { setCargando(true); setUsuarios(await obtenerUsuarios()); }
    catch (err) { console.error(err); }
    finally { setCargando(false); }
  }

  async function borrarUsuario(id) {
    if (!confirm('¿Desactivar este usuario? No podrá iniciar sesión.')) return;
    try { await desactivarUsuario(id); cargarUsuarios(); }
    catch (err) { alert(err.message); }
  }

  const filtrados = usuarios.filter(u => {
    if (!busqueda) return true;
    const q = busqueda.toLowerCase();
    return u.nombre?.toLowerCase().includes(q) ||
      u.username?.toLowerCase().includes(q) ||
      u.email?.toLowerCase().includes(q);
  });

  return (
    <div className="usuarios-pagina">
      <div className="ordenes-pagina__acciones animar-entrada">
        <div className="ordenes-pagina__filtros">
          <div className="filtro-buscador">
            <Search size={16} className="filtro-buscador__icono" />
            <input type="text" placeholder="Buscar usuarios..." value={busqueda}
              onChange={e => setBusqueda(e.target.value)} className="campo-texto filtro-buscador__input" />
          </div>
        </div>
        <button className="boton-primario" onClick={() => setModal('nuevo')}>
          <Plus size={18} /> Nuevo Usuario
        </button>
      </div>

      <div className="ordenes-pagina__tabla animar-entrada animar-retraso-1">
        {cargando ? (
          <div className="dashboard__cargando"><div className="spinner" /></div>
        ) : filtrados.length === 0 ? (
          <div className="dashboard__vacio">
            <Users size={44} strokeWidth={1.5} />
            <p>{usuarios.length === 0 ? 'No hay usuarios registrados' : 'No se encontraron resultados'}</p>
          </div>
        ) : (
          <table className="tabla">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Usuario</th>
                <th>Email</th>
                <th>Rol</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filtrados.map(u => (
                <tr key={u.id}>
                  <td><strong>{u.nombre}</strong></td>
                  <td style={{ color: 'var(--texto-secundario)' }}>@{u.username}</td>
                  <td>{u.email || '—'}</td>
                  <td>
                    <span className={`badge-rol ${badgeRolClass[u.rol] || ''}`}>
                      <Shield size={12} />
                      {roles.find(r => r.valor === u.rol)?.etiqueta || u.rol}
                    </span>
                  </td>
                  <td>
                    <span className={`badge-estado ${u.activo ? 'badge-estado--activo' : 'badge-estado--inactivo'}`}>
                      <span className="badge-estado__punto" />
                      {u.activo ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  <td>
                    <div className="tabla__acciones">
                      <button className="boton-icono" onClick={() => setModal(u)} title="Editar">✏️</button>
                      {u.id !== usuarioActual?.id && (
                        <button className="boton-icono" onClick={() => borrarUsuario(u.id)} title="Desactivar">
                          <UserX size={16} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {modal && (
        <ModalUsuario
          usuario={modal === 'nuevo' ? null : modal}
          onCerrar={() => setModal(null)}
          onGuardado={() => { setModal(null); cargarUsuarios(); }}
        />
      )}
    </div>
  );
}

function ModalUsuario({ usuario, onCerrar, onGuardado }) {
  const esEdicion = !!usuario;
  const [form, setForm] = useState({
    nombre: usuario?.nombre || '',
    username: usuario?.username || '',
    email: usuario?.email || '',
    rol: usuario?.rol || 'asistente',
    password: '',
  });
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);

  async function guardar(e) {
    e.preventDefault();
    if (!form.nombre.trim() || !form.username.trim()) {
      setError('Nombre y usuario son obligatorios'); return;
    }
    if (!esEdicion && !form.password.trim()) {
      setError('La contraseña es obligatoria para nuevos usuarios'); return;
    }
    if (form.email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
      setError('El formato del correo electrónico es inválido'); return;
    }
    try {
      setGuardando(true); setError(null);
      const datos = { ...form };
      if (!datos.password) delete datos.password;
      if (esEdicion) await actualizarUsuario(usuario.id, datos);
      else await crearUsuario(datos);
      onGuardado();
    } catch (err) { setError(err.message); }
    finally { setGuardando(false); }
  }

  return (
    <div className="modal-overlay" onClick={onCerrar}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal__header">
          <h3>{esEdicion ? 'Editar Usuario' : 'Nuevo Usuario'}</h3>
          <button className="boton-icono" onClick={onCerrar}><X size={20} /></button>
        </div>
        {error && <div className="dashboard__error" style={{ margin: '0 0 16px' }}><p>{error}</p></div>}
        <form onSubmit={guardar}>
          <div className="campo-grupo">
            <label className="campo-label">Nombre completo *</label>
            <input type="text" className="campo-texto" placeholder="Daniel Baltodano"
              value={form.nombre} onChange={e => setForm(p => ({ ...p, nombre: e.target.value }))} />
          </div>
          <div className="orden-form__grid-2">
            <div className="campo-grupo">
              <label className="campo-label">Usuario *</label>
              <input type="text" className="campo-texto" placeholder="dbaltodano"
                value={form.username} onChange={e => setForm(p => ({ ...p, username: e.target.value }))} />
            </div>
            <div className="campo-grupo">
              <label className="campo-label">Rol</label>
              <select className="campo-texto" value={form.rol}
                onChange={e => setForm(p => ({ ...p, rol: e.target.value }))}>
                {roles.map(r => <option key={r.valor} value={r.valor}>{r.etiqueta}</option>)}
              </select>
            </div>
          </div>
          <div className="campo-grupo">
            <label className="campo-label">Email</label>
            <input type="email" className="campo-texto" placeholder="correo@ejemplo.com"
              value={form.email} onChange={e => setForm(p => ({ ...p, email: e.target.value }))} />
          </div>
          <div className="campo-grupo">
            <label className="campo-label">{esEdicion ? 'Nueva contraseña (dejar vacío para mantener)' : 'Contraseña *'}</label>
            <input type="password" className="campo-texto" placeholder="••••••••"
              value={form.password} onChange={e => setForm(p => ({ ...p, password: e.target.value }))} />
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
