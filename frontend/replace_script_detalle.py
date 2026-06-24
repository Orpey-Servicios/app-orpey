import sys

with open('/home/skorggamor/app-orpey/frontend/src/paginas/OrdenDetalle.jsx', 'r') as f:
    content = f.read()

# 1. Imports
content = content.replace("actualizarOrden,", "actualizarOrden, actualizarEquipo,")

# 2. Function cambiarEstadoEquipo
content = content.replace("""  // Cambiar estado de la orden
  async function cambiarEstado(nuevoEstado) {
    try {
      await actualizarOrden(Number(id), { estado: nuevoEstado });
      cargarDatos();
    } catch (err) { alert('Error: ' + err.message); }
  }""", """  // Cambiar estado de la orden
  async function cambiarEstado(nuevoEstado) {
    try {
      await actualizarOrden(Number(id), { estado: nuevoEstado });
      cargarDatos();
    } catch (err) { alert('Error: ' + err.message); }
  }

  // Cambiar estado de un equipo
  async function cambiarEstadoEquipo(equipoId, nuevoEstado) {
    try {
      await actualizarEquipo(Number(id), equipoId, { estado: nuevoEstado });
      cargarDatos();
    } catch (err) { alert('Error: ' + err.message); }
  }""")

# 3. Remove global states
content = content.replace("""      {/* Cambiar estado */}
      <div className="orden-detalle__estados animar-entrada animar-retraso-1">
        <span className="orden-detalle__estados-label">Cambiar estado:</span>
        {ESTADOS.map(est => (
          <button key={est} onClick={() => cambiarEstado(est)}
            className={`orden-detalle__estado-btn ${orden.estado === est ? 'orden-detalle__estado-btn--activo' : ''}`}>
            {est.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase())}
          </button>
        ))}
      </div>""", "")

# 4. Replace Equipo card with nothing (we move it down)
content = content.replace("""        {/* Equipo */}
        <div className="orden-detalle__card">
          <h3><Wrench size={18} /> Equipo</h3>
          <div className="orden-detalle__datos">
            <p><strong>{tipoEquipoTexto[orden.tipo_equipo] || orden.tipo_equipo}</strong></p>
            {orden.marca && <p>Marca: {orden.marca}</p>}
            {orden.modelo && <p>Modelo: {orden.modelo}</p>}
            {orden.serial && <p>Serial: {orden.serial}</p>}
          </div>
        </div>""", "")

# 5. Replace service block (problems) and insert equipos list
start_marker = "{/* Detalles del servicio */}"
idx_start = content.find(start_marker)

new_section = """      {/* Equipos */}
      <div className="orden-detalle__equipos animar-entrada animar-retraso-3" style={{marginTop: '30px'}}>
        <h3 style={{marginBottom: '16px', color: 'var(--color-primario)', display: 'flex', alignItems: 'center'}}><Wrench size={20} style={{marginRight: '8px'}} /> Equipos de la Orden ({orden.equipos?.length || 0})</h3>
        {orden.equipos?.map((equipo, idx) => (
          <div key={equipo.id} className="equipo-detalle-card" style={{border: '1px solid var(--borde-color)', padding: '24px', borderRadius: '12px', marginBottom: '24px', backgroundColor: 'var(--fondo-principal)', boxShadow: '0 2px 8px rgba(0,0,0,0.02)'}}>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '16px'}}>
              <h4 style={{margin: 0, fontSize: '18px'}}>{tipoEquipoTexto[equipo.tipo_equipo] || equipo.tipo_equipo} {equipo.marca} {equipo.modelo}</h4>
              <BadgeEstado estado={equipo.estado} />
            </div>
            
            <div className="orden-detalle__estados" style={{marginBottom: '20px'}}>
              <span className="orden-detalle__estados-label" style={{fontSize: '13px'}}>Cambiar estado del equipo:</span>
              <div style={{display: 'flex', gap: '8px', flexWrap: 'wrap'}}>
                {ESTADOS.map(est => (
                  <button key={est} onClick={() => cambiarEstadoEquipo(equipo.id, est)}
                    className={`orden-detalle__estado-btn ${equipo.estado === est ? 'orden-detalle__estado-btn--activo' : ''}`}
                    style={{padding: '6px 12px', fontSize: '12px'}}>
                    {est.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase())}
                  </button>
                ))}
              </div>
            </div>

            <div className="orden-detalle__datos" style={{display: 'flex', gap: '24px', marginBottom: '24px', flexWrap: 'wrap', fontSize: '14px', backgroundColor: 'var(--fondo-secundario)', padding: '12px', borderRadius: '8px'}}>
              {equipo.serial && <div><strong>Serial:</strong> <span style={{color: 'var(--texto-secundario)'}}>{equipo.serial}</span></div>}
              {equipo.contrasena && <div><strong>Contraseña:</strong> <span style={{color: 'var(--texto-secundario)'}}>{equipo.contrasena}</span></div>}
              {!equipo.serial && !equipo.contrasena && <div style={{color: 'var(--texto-secundario)'}}>No hay datos adicionales del equipo.</div>}
            </div>

            <div className="orden-detalle__servicio" style={{marginTop: 0}}>
              {equipo.descripcion_problema && <div className="servicio-bloque" style={{padding: '16px', backgroundColor: '#fff', border: '1px solid #eee'}}><h4>Problema Reportado</h4><p>{equipo.descripcion_problema}</p></div>}
              {equipo.diagnostico && <div className="servicio-bloque" style={{padding: '16px', backgroundColor: '#fff', border: '1px solid #eee'}}><h4>Diagnóstico Técnico</h4><p>{equipo.diagnostico}</p></div>}
              {equipo.trabajo_a_realizar && <div className="servicio-bloque" style={{padding: '16px', backgroundColor: '#fff', border: '1px solid #eee'}}><h4>Trabajo a Realizar</h4><p>{equipo.trabajo_a_realizar}</p></div>}
              {equipo.repuesto_a_instalar && <div className="servicio-bloque" style={{padding: '16px', backgroundColor: '#fff', border: '1px solid #eee'}}><h4>Repuestos</h4><p>{equipo.repuesto_a_instalar}</p></div>}
            </div>
          </div>
        ))}
      </div>

      {/* Detalles del servicio */}
      <div className="orden-detalle__servicio animar-entrada animar-retraso-3">
        {orden.notas_internas && <div className="servicio-bloque servicio-bloque--interno"><h4>🔒 Notas Internas (Orden)</h4><p>{orden.notas_internas}</p></div>}
      </div>
    </div>
  );
}
"""

content = content[:idx_start] + new_section

with open('/home/skorggamor/app-orpey/frontend/src/paginas/OrdenDetalle.jsx', 'w') as f:
    f.write(content)
print("OrdenDetalle.jsx updated successfully!")
