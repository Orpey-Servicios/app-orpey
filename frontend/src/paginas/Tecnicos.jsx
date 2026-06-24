/**
 * GESTIÓN DE TÉCNICOS
 */
import { useState, useEffect } from 'react';
import { Plus, Search, Wrench, X, Save } from 'lucide-react';
import { obtenerTecnicos, crearTecnico, actualizarTecnico, eliminarTecnico } from '../api/orpey-api';
import './Tecnicos.css';

export default function Tecnicos() {
  const [tecnicos, setTecnicos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [modal, setModal] = useState(null);

  useEffect(() => { cargar(); }, []);
  async function cargar() {
    try { setCargando(true); setTecnicos(await obtenerTecnicos()); }
    catch (err) { console.error(err); } finally { setCargando(false); }
  }

  async function borrar(id) {
    if (!confirm('¿Desactivar este técnico?')) return;
    try { await eliminarTecnico(id); cargar(); } catch (err) { alert(err.message); }
  }

  return (
    <div className="tecnicos-pagina">
      <div className="ordenes-pagina__acciones animar-entrada">
        <h3 style={{fontSize: 'var(--fuente-tamano-md)', fontWeight: 600}}>
          <Wrench size={20} /> {tecnicos.length} técnico(s) activo(s)
        </h3>
        <button className="boton-primario" onClick={() => setModal('nuevo')} id="btn-nuevo-tecnico">
          <Plus size={18} /> Nuevo Técnico
        </button>
      </div>

      <div className="tecnicos-grid animar-entrada animar-retraso-1">
        {cargando ? <div className="dashboard__cargando"><div className="spinner" /></div> :
          tecnicos.length === 0 ? <div className="dashboard__vacio"><Wrench size={44} strokeWidth={1.5} /><p>No hay técnicos</p></div> :
          tecnicos.map(t => (
            <div key={t.id} className="tecnico-card">
              <div className="tecnico-card__avatar">{t.nombre[0]}{t.apellido[0]}</div>
              <h4>{t.nombre} {t.apellido}</h4>
              {t.especialidad && <p className="tecnico-card__esp">{t.especialidad}</p>}
              {t.telefono && <p>📞 {t.telefono}</p>}
              {t.email && <p>📧 {t.email}</p>}
              <div className="tecnico-card__acciones">
                <button className="boton-secundario" onClick={() => setModal(t)}>Editar</button>
                <button className="boton-icono" onClick={() => borrar(t.id)} title="Desactivar">🗑️</button>
              </div>
            </div>
          ))
        }
      </div>

      {modal && <ModalTecnico tecnico={modal === 'nuevo' ? null : modal} onCerrar={() => setModal(null)} onGuardado={() => { setModal(null); cargar(); }} />}
    </div>
  );
}

function ModalTecnico({ tecnico, onCerrar, onGuardado }) {
  const esEdicion = !!tecnico;
  const [form, setForm] = useState({
    nombre: tecnico?.nombre || '', apellido: tecnico?.apellido || '',
    telefono: tecnico?.telefono || '', email: tecnico?.email || '',
    especialidad: tecnico?.especialidad || '',
  });
  const [guardando, setGuardando] = useState(false);

  async function guardar(e) {
    e.preventDefault();
    if (!form.nombre.trim() || !form.apellido.trim()) { alert('Nombre y apellido requeridos'); return; }
    try {
      setGuardando(true);
      if (esEdicion) await actualizarTecnico(tecnico.id, form);
      else await crearTecnico(form);
      onGuardado();
    } catch (err) { alert(err.message); } finally { setGuardando(false); }
  }

  return (
    <div className="modal-overlay" onClick={onCerrar}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h3>{esEdicion ? 'Editar Técnico' : 'Nuevo Técnico'}</h3>
          <button className="boton-icono" onClick={onCerrar}><X size={20} /></button>
        </div>
        <form onSubmit={guardar}>
          <div className="orden-form__grid-2">
            <div className="campo-grupo"><label className="campo-label">Nombre *</label>
              <input type="text" className="campo-texto" value={form.nombre} onChange={(e) => setForm(p => ({...p, nombre: e.target.value}))} /></div>
            <div className="campo-grupo"><label className="campo-label">Apellido *</label>
              <input type="text" className="campo-texto" value={form.apellido} onChange={(e) => setForm(p => ({...p, apellido: e.target.value}))} /></div>
          </div>
          <div className="campo-grupo"><label className="campo-label">Teléfono</label>
            <input type="text" className="campo-texto" value={form.telefono} onChange={(e) => setForm(p => ({...p, telefono: e.target.value}))} /></div>
          <div className="campo-grupo"><label className="campo-label">Email</label>
            <input type="email" className="campo-texto" value={form.email} onChange={(e) => setForm(p => ({...p, email: e.target.value}))} /></div>
          <div className="campo-grupo"><label className="campo-label">Especialidad</label>
            <input type="text" className="campo-texto" placeholder="Ej: Impresoras, Laptops" value={form.especialidad} onChange={(e) => setForm(p => ({...p, especialidad: e.target.value}))} /></div>
          <div className="modal__botones">
            <button type="button" className="boton-secundario" onClick={onCerrar}>Cancelar</button>
            <button type="submit" className="boton-primario" disabled={guardando}><Save size={16} /> {guardando ? 'Guardando...' : 'Guardar'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}
