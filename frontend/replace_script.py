import sys

with open('/home/skorggamor/app-orpey/frontend/src/paginas/OrdenFormulario.jsx', 'r') as f:
    content = f.read()

# 1. setForm
content = content.replace("""  const [form, setForm] = useState({
    cliente_id: '', tecnico_id: '', tipo_equipo: 'laptop', marca: '', modelo: '',
    serial: '', contrasena: '', descripcion_problema: '', diagnostico: '',
    trabajo_a_realizar: '', repuesto_a_instalar: '', total_orden: '0.00',
    abono: '0.00', garantia_dias: 30, notas_internas: '',
  });""", """  const [form, setForm] = useState({
    cliente_id: '', tecnico_id: '', total_orden: '0.00',
    abono: '0.00', garantia_dias: 30, notas_internas: '',
    equipos: [{
      tipo_equipo: 'laptop', marca: '', modelo: '',
      serial: '', contrasena: '', descripcion_problema: '', diagnostico: '',
      trabajo_a_realizar: '', repuesto_a_instalar: ''
    }]
  });""")

# 2. cargarDatosIniciales
content = content.replace("""        setForm({
          cliente_id: orden.cliente_id, tecnico_id: orden.tecnico_id || '',
          tipo_equipo: orden.tipo_equipo, marca: orden.marca || '', modelo: orden.modelo || '',
          serial: orden.serial || '', contrasena: orden.contrasena || '',
          descripcion_problema: orden.descripcion_problema, diagnostico: orden.diagnostico || '',
          trabajo_a_realizar: orden.trabajo_a_realizar || '', repuesto_a_instalar: orden.repuesto_a_instalar || '',
          total_orden: orden.total_orden, abono: orden.abono,
          garantia_dias: orden.garantia_dias || 30, notas_internas: orden.notas_internas || '',
        });""", """        setForm({
          cliente_id: orden.cliente_id, tecnico_id: orden.tecnico_id || '',
          total_orden: orden.total_orden, abono: orden.abono,
          garantia_dias: orden.garantia_dias || 30, notas_internas: orden.notas_internas || '',
          equipos: orden.equipos && orden.equipos.length > 0 ? orden.equipos : [{
            tipo_equipo: 'laptop', marca: '', modelo: '',
            serial: '', contrasena: '', descripcion_problema: '', diagnostico: '',
            trabajo_a_realizar: '', repuesto_a_instalar: ''
          }]
        });""")

# 3. actualizarCampo etc
content = content.replace("""  function actualizarCampo(campo, valor) {
    setForm(prev => ({ ...prev, [campo]: valor }));
  }""", """  function actualizarCampo(campo, valor) {
    setForm(prev => ({ ...prev, [campo]: valor }));
  }

  function actualizarCampoEquipo(index, campo, valor) {
    setForm(prev => {
      const nuevosEquipos = [...prev.equipos];
      nuevosEquipos[index] = { ...nuevosEquipos[index], [campo]: valor };
      return { ...prev, equipos: nuevosEquipos };
    });
  }

  function agregarEquipo() {
    setForm(prev => ({
      ...prev,
      equipos: [...prev.equipos, {
        tipo_equipo: 'laptop', marca: '', modelo: '',
        serial: '', contrasena: '', descripcion_problema: '', diagnostico: '',
        trabajo_a_realizar: '', repuesto_a_instalar: ''
      }]
    }));
  }

  function eliminarEquipo(index) {
    setForm(prev => {
      const nuevosEquipos = prev.equipos.filter((_, i) => i !== index);
      return { ...prev, equipos: nuevosEquipos };
    });
  }""")

# 4. guardarOrden
content = content.replace("""  // ── Guardar la orden ─────────────────────────────────────────────────
  async function guardarOrden(e) {
    e.preventDefault();
    if (!form.cliente_id) { setError('Debes seleccionar un cliente'); return; }
    if (!form.descripcion_problema.trim()) { setError('La descripción del problema es obligatoria'); return; }""", """  // ── Guardar la orden ─────────────────────────────────────────────────
  async function guardarOrden(e) {
    e.preventDefault();
    if (!form.cliente_id) { setError('Debes seleccionar un cliente'); return; }
    for (let i = 0; i < form.equipos.length; i++) {
        if (!form.equipos[i].descripcion_problema.trim()) { setError(`La descripción del problema es obligatoria en el equipo ${i+1}`); return; }
    }""")

# 5. Modal Exito
content = content.replace("""            <div className="modal-exito__fila">
              <span>Equipo</span>
              <strong>{form.tipo_equipo.replace(/_/g, ' ')} {form.marca} {form.modelo}</strong>
            </div>""", """            <div className="modal-exito__fila">
              <span>Equipos</span>
              <strong>{form.equipos.length} equipo(s)</strong>
            </div>""")

# 6. Form rendering
# We need to replace the section starting with `<fieldset className="orden-form__seccion">` around line 512
# up to line 634 (`</fieldset>`) which is just before `💰 Datos Financieros`
start_marker = "{/* ── SECCIÓN: Equipo ───────────────────────────────────────── */}"
end_marker = "{/* ── SECCIÓN: Financiero y Asignación ─────────────────────── */}"

if start_marker in content and end_marker in content:
    idx_start = content.find(start_marker)
    idx_end = content.find(end_marker)
    
    new_section = """{/* ── SECCIÓN: Equipos ───────────────────────────────────────── */}
        {form.equipos.map((equipo, index) => (
          <div key={index} className="equipo-container" style={{ marginBottom: '24px', border: '1px solid var(--borde-color)', padding: '16px', borderRadius: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h4 style={{ margin: 0, color: 'var(--color-primario)' }}>Equipo {index + 1}</h4>
                {form.equipos.length > 1 && (
                    <button type="button" className="boton-texto" onClick={() => eliminarEquipo(index)} style={{ color: 'var(--color-error)' }}>
                        <X size={16} /> Eliminar
                    </button>
                )}
            </div>
            
            <fieldset className="orden-form__seccion" style={{ border: 'none', padding: 0, margin: 0 }}>
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
                    <button type="button" onClick={() => setModalConfig({ abierto: true, tipo: 'marca', equipo: equipo.tipo_equipo })} title="Configurar marcas" style={{ color: 'var(--texto-secundario)', fontSize: '11px', display: 'flex', gap: '4px', alignItems: 'center', background: 'none', border: 'none', cursor: 'pointer' }}>
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
                    <button type="button" onClick={() => setModalConfig({ abierto: true, tipo: 'modelo', equipo: equipo.tipo_equipo })} title="Configurar modelos" style={{ color: 'var(--texto-secundario)', fontSize: '11px', display: 'flex', gap: '4px', alignItems: 'center', background: 'none', border: 'none', cursor: 'pointer' }}>
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
                    {(modelosPersonalizados[equipo.tipo_equipo] || []).map(modelo => (
                      <option key={modelo} value={modelo} />
                    ))}
                  </datalist>
                  {(modelosPersonalizados[equipo.tipo_equipo] || []).length > 0 && (
                    <div className="sugerencias-marcas animar-entrada">
                      {(modelosPersonalizados[equipo.tipo_equipo] || []).map(modelo => (
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
                  <label className="campo-label">Serial</label>
                  <input type="text" className="campo-texto" placeholder="Número de serie" value={equipo.serial} onChange={(e) => actualizarCampoEquipo(index, 'serial', e.target.value)} />
                </div>
                <div className="campo-grupo">
                  <label className="campo-label">Contraseña del equipo</label>
                  <input type="text" className="campo-texto" placeholder="Si aplica" value={equipo.contrasena} onChange={(e) => actualizarCampoEquipo(index, 'contrasena', e.target.value)} />
                </div>
              </div>
            </fieldset>

            {/* ── SECCIÓN: Problema y Trabajo ───────────────────────────── */}
            <fieldset className="orden-form__seccion" style={{ border: 'none', padding: 0, margin: '20px 0 0 0' }}>
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
            </fieldset>
          </div>
        ))}

        <div style={{ marginBottom: '24px', textAlign: 'center' }}>
            <button type="button" className="boton-secundario" onClick={agregarEquipo} style={{ padding: '10px 20px', borderRadius: '20px' }}>
                <Plus size={16} /> Agregar otro equipo
            </button>
        </div>

        """
    content = content[:idx_start] + new_section + content[idx_end:]

with open('/home/skorggamor/app-orpey/frontend/src/paginas/OrdenFormulario.jsx', 'w') as f:
    f.write(content)
print("OrdenFormulario.jsx updated successfully!")
