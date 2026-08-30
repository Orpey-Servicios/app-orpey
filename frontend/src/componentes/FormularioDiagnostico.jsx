/**
 * ============================================================
 * FormularioDiagnostico.jsx — Panel del TÉCNICO dentro de la orden
 * ============================================================
 *
 * El técnico llena aquí el diagnóstico TÉCNICO del equipo:
 *   - ¿Enciende? (sí / no)
 *   - Disco (tipo + capacidad)
 *   - Memoria (tipo + capacidad)
 *   - Slot M2 / Caddy disponibles
 *   - Procesador
 *   - Resumen del diagnóstico
 *   - Repuestos necesarios (proveedor + repuesto + costo)
 *
 * Al guardar, el equipo pasa a estado "pendiente" de aprobación
 * del DUEÑO, que lo verá en la sección "Diagnósticos".
 * ============================================================
 */
import { useState } from 'react';
import { Save, Plus, Trash2, Stethoscope, ChevronDown, ChevronUp } from 'lucide-react';
import { guardarDiagnostico } from '../api/orpey-api';
import './FormularioDiagnostico.css';

// Opciones de los campos (para que sea rápido de llenar)
const OPCIONES_ENCIENDE = ['Sí', 'No', 'No enciende'];
const OPCIONES_DISCO = ['HDD', 'SSD', 'SSD M.2'];
const OPCIONES_MEMORIA = ['DDR3', 'DDR4', 'DDR5'];
const OPCIONES_SI_NO = ['Sí', 'No'];

export default function FormularioDiagnostico({ equipo }) {
  // Estado de cada campo diagnóstico (se inicializa con lo ya guardado si existe)
  const [form, setForm] = useState({
    enciende: equipo.enciende || '',
    tipo_disco: equipo.tipo_disco || '',
    capacidad_disco: equipo.capacidad_disco || '',
    tipo_memoria: equipo.tipo_memoria || '',
    capacidad_memoria: equipo.capacidad_memoria || '',
    slot_m2: equipo.slot_m2 || '',
    slot_caddy: equipo.slot_caddy || '',
    procesador: equipo.procesador || '',
    diagnostico: equipo.diagnostico || '',
    toma_papel: equipo.toma_papel || '',
    nivel_tinta: equipo.nivel_tinta || '',
    calidad_impresion: equipo.calidad_impresion || '',
    pantalla_rota: equipo.pantalla_rota || '',
    pin_carga: equipo.pin_carga || '',
  });

  const [abierto, setAbierto] = useState(false);

  const esImpresora = equipo.tipo_equipo === 'impresora';
  const esTelefono = equipo.tipo_equipo === 'telefono';
  const esPC = equipo.tipo_equipo === 'pc_escritorio' || equipo.tipo_equipo === 'laptop' || (!esImpresora && !esTelefono);

  // Lista de repuestos: { proveedor, repuesto, costo }
  const [repuestos, setRepuestos] = useState(
    (equipo.repuestos || []).length > 0
      ? equipo.repuestos.map(r => ({ proveedor: r.proveedor || '', repuesto: r.repuesto || '', costo: r.costo || '' }))
      : [{ proveedor: '', repuesto: '', costo: '' }]
  );

  const [guardando, setGuardando] = useState(false);
  const [mensaje, setMensaje] = useState(null);

  // Actualizar un campo del diagnóstico
  function actualizarCampo(campo, valor) {
    setForm(prev => ({ ...prev, [campo]: valor }));
  }

  // Actualizar un repuesto por índice
  function actualizarRepuesto(idx, campo, valor) {
    setRepuestos(prev => prev.map((r, i) => i === idx ? { ...r, [campo]: valor } : r));
  }

  // Agregar fila de repuesto
  function agregarRepuesto() {
    setRepuestos(prev => [...prev, { proveedor: '', repuesto: '', costo: '' }]);
  }

  // Quitar fila de repuesto
  function quitarRepuesto(idx) {
    setRepuestos(prev => prev.filter((_, i) => i !== idx));
  }

  // Convertir el estado a un "select" seguro
  function SelectOpciones({ opciones, valor, onChange, placeholder = 'Seleccionar...' }) {
    return (
      <select
        className="campo-texto"
        value={valor || ''}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">{placeholder}</option>
        {opciones.map(op => <option key={op} value={op}>{op}</option>)}
      </select>
    );
  }

  // Guardar el diagnóstico (llama al endpoint del técnico)
  async function guardar() {
    if (!form.diagnostico.trim() && repuestos.filter(r => r.repuesto.trim()).length === 0) {
      setMensaje({ tipo: 'error', texto: 'Agrega al menos un diagnóstico o un repuesto.' });
      return;
    }

    setGuardando(true);
    setMensaje(null);
    try {
      // Filtrar filas de repuestos vacías
      const repuestosLimpios = repuestos
        .filter(r => r.repuesto.trim())
        .map(r => ({
          proveedor: r.proveedor.trim() || null,
          repuesto: r.repuesto.trim(),
          costo: r.costo ? Number(r.costo) : 0,
        }));

      await guardarDiagnostico(equipo.id, {
        ...form,
        repuestos: repuestosLimpios,
      });

      setMensaje({ tipo: 'exito', texto: '✅ Diagnóstico guardado. Queda pendiente de aprobación del dueño.' });
      // Refrescar la página para que se vean los datos nuevos
      setTimeout(() => window.location.reload(), 1200);
    } catch (err) {
      setMensaje({ tipo: 'error', texto: err.message || 'Error al guardar el diagnóstico.' });
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div className="diag-tecnic-panel">
      {/* Encabezado del panel - Botón para colapsar/expandir */}
      <button 
        type="button"
        className="diag-tecnic-titulo" 
        onClick={() => setAbierto(!abierto)}
        style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'none', border: 'none', cursor: 'pointer', padding: '0', textAlign: 'left' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Stethoscope size={16} /> Diagnóstico del Técnico
          {equipo.estado_aprobacion && equipo.estado_aprobacion !== 'pendiente' && equipo.estado_aprobacion !== 'sin_diagnostico' && (
            <span className={`diag-tecnic-badge diag-tecnic-badge--${equipo.estado_aprobacion}`}>
              {equipo.estado_aprobacion === 'aprobado' ? 'Aprobado ✅' : 'Rechazado ❌'}
            </span>
          )}
        </div>
        {abierto ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
      </button>

      {abierto && (
        <div className="diag-tecnic-contenido" style={{ marginTop: '16px' }}>

      <div className="diag-tecnic-grid">
        {/* Enciende (PC y Teléfonos) */}
        {(esPC || esTelefono) && (
          <div className="diag-tecnic-campo">
            <label>¿Enciende?</label>
            <SelectOpciones opciones={OPCIONES_ENCIENDE} valor={form.enciende} onChange={(v) => actualizarCampo('enciende', v)} />
          </div>
        )}

        {/* ================= CAMPOS DE PC ================= */}
        {esPC && (
          <>
            <div className="diag-tecnic-campo">
              <label>Tipo de disco</label>
              <SelectOpciones opciones={OPCIONES_DISCO} valor={form.tipo_disco} onChange={(v) => actualizarCampo('tipo_disco', v)} />
            </div>
            <div className="diag-tecnic-campo">
              <label>Capacidad disco (GB)</label>
              <input
                className="campo-texto"
                placeholder="Ej: 500"
                value={form.capacidad_disco}
                onChange={(e) => actualizarCampo('capacidad_disco', e.target.value)}
              />
            </div>
            <div className="diag-tecnic-campo">
              <label>Tipo de memoria</label>
              <SelectOpciones opciones={OPCIONES_MEMORIA} valor={form.tipo_memoria} onChange={(v) => actualizarCampo('tipo_memoria', v)} />
            </div>
            <div className="diag-tecnic-campo">
              <label>Capacidad memoria (GB)</label>
              <input
                className="campo-texto"
                placeholder="Ej: 8"
                value={form.capacidad_memoria}
                onChange={(e) => actualizarCampo('capacidad_memoria', e.target.value)}
              />
            </div>
            <div className="diag-tecnic-campo">
              <label>Slot M.2 disponible</label>
              <SelectOpciones opciones={OPCIONES_SI_NO} valor={form.slot_m2} onChange={(v) => actualizarCampo('slot_m2', v)} />
            </div>
            <div className="diag-tecnic-campo">
              <label>Slot Caddy (bahía)</label>
              <SelectOpciones opciones={OPCIONES_SI_NO} valor={form.slot_caddy} onChange={(v) => actualizarCampo('slot_caddy', v)} />
            </div>
            <div className="diag-tecnic-campo">
              <label>Procesador</label>
              <input
                className="campo-texto"
                placeholder="Ej: i5-12450H"
                value={form.procesador}
                onChange={(e) => actualizarCampo('procesador', e.target.value)}
              />
            </div>
          </>
        )}

        {/* ================= CAMPOS DE IMPRESORA ================= */}
        {esImpresora && (
          <>
            <div className="diag-tecnic-campo">
              <label>¿Toma papel?</label>
              <SelectOpciones opciones={OPCIONES_SI_NO} valor={form.toma_papel} onChange={(v) => actualizarCampo('toma_papel', v)} />
            </div>
            <div className="diag-tecnic-campo">
              <label>Nivel de tinta / tóner</label>
              <SelectOpciones opciones={['Bajo', 'Medio', 'Alto', 'Vacío', 'No detecta']} valor={form.nivel_tinta} onChange={(v) => actualizarCampo('nivel_tinta', v)} />
            </div>
            <div className="diag-tecnic-campo">
              <label>Calidad de impresión</label>
              <SelectOpciones opciones={['Buena', 'Mala', 'Con rayas', 'En blanco']} valor={form.calidad_impresion} onChange={(v) => actualizarCampo('calidad_impresion', v)} />
            </div>
          </>
        )}

        {/* ================= CAMPOS DE TELÉFONO ================= */}
        {esTelefono && (
          <>
            <div className="diag-tecnic-campo">
              <label>Pantalla / Glass</label>
              <SelectOpciones opciones={['Intacta', 'Tizada/Rota', 'No da imagen', 'Manchas/Líneas']} valor={form.pantalla_rota} onChange={(v) => actualizarCampo('pantalla_rota', v)} />
            </div>
            <div className="diag-tecnic-campo">
              <label>Pin de carga</label>
              <SelectOpciones opciones={['Carga bien', 'Falso contacto', 'No carga', 'Dañado visiblemente']} valor={form.pin_carga} onChange={(v) => actualizarCampo('pin_carga', v)} />
            </div>
          </>
        )}
      </div>

      {/* Resumen del diagnóstico */}
      <div className="diag-tecnic-resumen">
        <label>Resumen del diagnóstico (causa del problema)</label>
        <textarea
          className="campo-texto"
          rows="3"
          placeholder="Ej: Se revisó la placa, no inicializa, falla del panel central..."
          value={form.diagnostico}
          onChange={(e) => actualizarCampo('diagnostico', e.target.value)}
        />
      </div>

      {/* Repuestos */}
      <div className="diag-tecnic-repuestos">
        <div className="diag-tecnic-repuestos-titulo">
          <label>Repuestos necesarios</label>
          <button type="button" className="boton-icono" onClick={agregarRepuesto} title="Agregar repuesto">
            <Plus size={16} />
          </button>
        </div>

        {repuestos.map((r, idx) => (
          <div key={idx} className="diag-tecnic-fila-repuesto">
            <input
              className="campo-texto"
              placeholder="Proveedor"
              value={r.proveedor}
              onChange={(e) => actualizarRepuesto(idx, 'proveedor', e.target.value)}
            />
            <input
              className="campo-texto"
              placeholder="Repuesto (ej: batería)"
              value={r.repuesto}
              onChange={(e) => actualizarRepuesto(idx, 'repuesto', e.target.value)}
            />
            <input
              className="campo-texto"
              type="number"
              placeholder="Costo $"
              value={r.costo}
              onChange={(e) => actualizarRepuesto(idx, 'costo', e.target.value)}
            />
            <button
              type="button"
              className="boton-icono"
              onClick={() => quitarRepuesto(idx)}
              title="Quitar repuesto"
              disabled={repuestos.length <= 1}
              style={{ color: 'var(--color-error)', opacity: repuestos.length <= 1 ? 0.3 : 1 }}
            >
              <Trash2 size={16} />
            </button>
          </div>
        ))}
      </div>

      {/* Mensaje y botón */}
      {mensaje && (
        <p className={`diag-tecnic-mensaje diag-tecnic-mensaje--${mensaje.tipo}`}>{mensaje.texto}</p>
      )}

      <button
        type="button"
        className="boton-primario"
        onClick={guardar}
        disabled={guardando}
      >
        <Save size={16} /> {guardando ? 'Guardando...' : 'Guardar diagnóstico'}
      </button>
      </div>
      )}
    </div>
  );
}
