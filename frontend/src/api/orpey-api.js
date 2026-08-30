/**
 * ============================================================
 * API DE ORPEY SERVICIOS - Funciones de comunicación con el backend
 * ============================================================
 *
 * Este archivo contiene TODAS las funciones que el frontend usa
 * para comunicarse con el backend (FastAPI).
 *
 * ¿Qué es una API?
 * Es como un "mesero" entre el frontend y el backend:
 * - El frontend le pide datos (GET) o envía datos (POST, PUT, DELETE)
 * - La API los lleva al backend
 * - El backend responde con los datos procesados
 *
 * ¿Qué es fetch()?
 * Es la función nativa de JavaScript para hacer peticiones HTTP.
 * Devuelve una "promesa" (Promise), por eso usamos async/await.
 *
 * async/await:
 * - async: marca una función como "asíncrona" (no bloquea la ejecución)
 * - await: espera a que la promesa se resuelva antes de continuar
 * ============================================================
 */

// URL base del backend - donde está corriendo FastAPI
// En desarrollo usamos la ruta relativa '/api' que el proxy de Vite
// (configurado en vite.config.js) reenvía al backend en 127.0.0.1:8000.
// Esto hace que la app funcione igual desde localhost y desde la IP de red
// (y desde cualquier dispositivo), eliminando el "flash"/desconexión que
// ocurría al usar la URL hardcodeada http://127.0.0.1:8000.
const URL_BASE = '';

/**
 * Función auxiliar genérica para hacer peticiones al backend.
 * Centraliza la lógica de fetch para no repetirla en cada función.
 *
 * @param {string} endpoint - La ruta del endpoint (ej: '/api/clientes')
 * @param {object} opciones - Opciones adicionales (method, body, etc.)
 * @returns {Promise} - Los datos de la respuesta en formato JSON
 */
async function hacerPeticion(endpoint, opciones = {}) {
  try {
    // Construir las opciones de la petición
    const headers = {
      'Content-Type': 'application/json',
      ...opciones.headers,
    };

    // Incluir token JWT automáticamente si existe
    const token = localStorage.getItem('token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const config = {
      method: opciones.method || 'GET',
      headers,
    };

    // Si hay un cuerpo (body), convertirlo a texto JSON
    // body se usa en POST y PUT para enviar datos
    if (opciones.body) {
      config.body = JSON.stringify(opciones.body);
    }

    // Hacer la petición HTTP
    const respuesta = await fetch(`${URL_BASE}${endpoint}`, config);

    // Si el servidor devuelve 204 (No Content), no hay cuerpo que leer
    // Esto pasa cuando eliminamos algo exitosamente
    if (respuesta.status === 204) {
      return null;
    }

    // Si la respuesta NO es exitosa (código 4xx o 5xx), lanzar error
    if (!respuesta.ok) {
      const errorData = await respuesta.json().catch(() => ({}));
      // FastAPI puede devolver 'detail' como string o como array de objetos
      // (los errores de validación Pydantic son arrays)
      let mensajeError;
      if (typeof errorData.detail === 'string') {
        mensajeError = errorData.detail;
      } else if (Array.isArray(errorData.detail)) {
        // Extraer los mensajes de cada error de validación
        mensajeError = errorData.detail.map(e => e.msg || e.message || JSON.stringify(e)).join(', ');
      } else {
        mensajeError = `Error ${respuesta.status}: ${respuesta.statusText}`;
      }
      throw new Error(mensajeError);
    }

    // Convertir la respuesta a JSON y devolverla
    return await respuesta.json();
  } catch (error) {
    // Si el error es de red (backend no disponible), mostrar mensaje claro
    if (error.message === 'Failed to fetch') {
      throw new Error('No se pudo conectar con el servidor. ¿Está corriendo el backend?');
    }
    throw error;
  }
}

/* ============================================================
   CLIENTES - Funciones CRUD (Crear, Leer, Actualizar, Eliminar)
   ============================================================ */

/**
 * Obtener la lista de todos los clientes.
 * @param {string} buscar - Texto para buscar por nombre/apellido (opcional)
 * @returns {Promise<Array>} - Lista de clientes
 */
export async function obtenerClientes(buscar = '') {
  // Si hay texto de búsqueda, agregarlo como parámetro de consulta
  const parametros = buscar ? `?buscar=${encodeURIComponent(buscar)}` : '';
  return hacerPeticion(`/api/clientes/${parametros}`);
}

/**
 * Obtener un cliente específico por su ID.
 * @param {number} id - El ID del cliente
 * @returns {Promise<Object>} - Datos del cliente
 */
export async function obtenerCliente(id) {
  return hacerPeticion(`/api/clientes/${id}`);
}

/**
 * Crear un cliente nuevo.
 * @param {Object} datos - Datos del cliente (nombre, apellido, teléfono, etc.)
 * @returns {Promise<Object>} - El cliente creado (con su ID asignado)
 */
export async function crearCliente(datos) {
  return hacerPeticion('/api/clientes/', {
    method: 'POST',
    body: datos,
  });
}

/**
 * Actualizar un cliente existente.
 * Solo se envían los campos que cambiaron.
 * @param {number} id - ID del cliente a actualizar
 * @param {Object} datos - Campos a actualizar
 * @returns {Promise<Object>} - El cliente actualizado
 */
export async function actualizarCliente(id, datos) {
  return hacerPeticion(`/api/clientes/${id}/`, {
    method: 'PUT',
    body: datos,
  });
}

/**
 * Eliminar un cliente (desactivación lógica).
 * No lo borra de la BD, solo lo marca como inactivo.
 * @param {number} id - ID del cliente a eliminar
 */
export async function eliminarCliente(id) {
  return hacerPeticion(`/api/clientes/${id}/`, {
    method: 'DELETE',
  });
}

/* ============================================================
   ÓRDENES DE SERVICIO
   ============================================================ */

/**
 * Obtener la lista de órdenes de servicio.
 * @param {Object} filtros - Filtros opcionales (estado, cliente_id, tipo_equipo)
 * @returns {Promise<Array>} - Lista de órdenes
 */
export async function obtenerOrdenes(filtros = {}) {
  // Construir los parámetros de consulta a partir de los filtros
  const parametros = new URLSearchParams();
  if (filtros.estado) parametros.append('estado', filtros.estado);
  if (filtros.cliente_id) parametros.append('cliente_id', filtros.cliente_id);
  if (filtros.tipo_equipo) parametros.append('tipo_equipo', filtros.tipo_equipo);

  const query = parametros.toString();
  return hacerPeticion(`/api/ordenes/${query ? '?' + query : ''}`);
}

/**
 * Obtener una orden específica por su ID.
 * @param {number} id - ID de la orden
 * @returns {Promise<Object>} - Datos de la orden
 */
export async function obtenerOrden(id) {
  return hacerPeticion(`/api/ordenes/${id}`);
}

/**
 * Crear una nueva orden de servicio.
 * El número de orden se genera automáticamente (ORP-0001).
 * @param {Object} datos - Datos de la orden
 * @returns {Promise<Object>} - La orden creada
 */
export async function crearOrden(datos) {
  return hacerPeticion('/api/ordenes/', {
    method: 'POST',
    body: datos,
  });
}

/**
 * Actualizar una orden existente.
 * @param {number} id - ID de la orden
 * @param {Object} datos - Campos a actualizar
 * @returns {Promise<Object>} - La orden actualizada
 */
export async function actualizarOrden(id, datos) {
  return hacerPeticion(`/api/ordenes/${id}`, {
    method: 'PUT',
    body: datos,
  });
}

/**
 * Actualizar un equipo específico de una orden.
 * @param {number} ordenId - ID de la orden
 * @param {number} equipoId - ID del equipo
 * @param {Object} datos - Campos a actualizar
 * @returns {Promise<Object>} - El equipo actualizado
 */
export async function actualizarEquipo(ordenId, equipoId, datos) {
  return hacerPeticion(`/api/ordenes/${ordenId}/equipos/${equipoId}`, {
    method: 'PUT',
    body: datos,
  });
}

/**
 * Eliminar una orden de servicio.
 * @param {number} id - ID de la orden
 */
export async function eliminarOrden(id) {
  return hacerPeticion(`/api/ordenes/${id}/`, {
    method: 'DELETE',
  });
}

/**
 * Obtener las estadísticas del dashboard.
 * Devuelve conteo de órdenes activas, equipos por tipo, etc.
 * @returns {Promise<Object>} - Estadísticas del dashboard
 */
export async function obtenerDashboard() {
  return hacerPeticion('/api/ordenes/dashboard');
}

/* ============================================================
   TÉCNICOS
   ============================================================ */

/** Obtener lista de técnicos activos */
export async function obtenerTecnicos() {
  return hacerPeticion('/api/tecnicos');
}

/** Obtener un técnico por ID */
export async function obtenerTecnico(id) {
  return hacerPeticion(`/api/tecnicos/${id}`);
}

/** Crear un técnico nuevo */
export async function crearTecnico(datos) {
  return hacerPeticion('/api/tecnicos/', {
    method: 'POST',
    body: datos,
  });
}

/** Actualizar un técnico */
export async function actualizarTecnico(id, datos) {
  return hacerPeticion(`/api/tecnicos/${id}/`, {
    method: 'PUT',
    body: datos,
  });
}

/** Eliminar un técnico (desactivación lógica) */
export async function eliminarTecnico(id) {
  return hacerPeticion(`/api/tecnicos/${id}/`, {
    method: 'DELETE',
  });
}

/* ============================================================
   COTIZACIONES
   ============================================================ */

/** Obtener lista de cotizaciones */
export async function obtenerCotizaciones(filtros = {}) {
  const parametros = new URLSearchParams();
  if (filtros.estado) parametros.append('estado', filtros.estado);
  if (filtros.cliente_id) parametros.append('cliente_id', filtros.cliente_id);
  const query = parametros.toString();
  return hacerPeticion(`/api/cotizaciones/${query ? '?' + query : ''}`);
}

/** Obtener una cotización por ID */
export async function obtenerCotizacion(id) {
  return hacerPeticion(`/api/cotizaciones/${id}`);
}

/** Crear una cotización nueva */
export async function crearCotizacion(datos) {
  return hacerPeticion('/api/cotizaciones/', {
    method: 'POST',
    body: datos,
  });
}

/** Actualizar una cotización */
export async function actualizarCotizacion(id, datos) {
  return hacerPeticion(`/api/cotizaciones/${id}/`, {
    method: 'PUT',
    body: datos,
  });
}

/** Aprobar una cotización (cambia estado a 'aprobada') */
export async function aprobarCotizacion(id) {
  return hacerPeticion(`/api/cotizaciones/${id}/aprobar`, {
    method: 'POST',
  });
}

/* ============================================================
   NOTAS DE VENTA
   ============================================================ */

/** Obtener lista de notas de venta */
export async function obtenerNotasVenta() {
  return hacerPeticion('/api/notas-venta');
}

/** Crear una nota de venta a partir de una orden */
export async function crearNotaVenta(datos) {
  return hacerPeticion('/api/notas-venta/', {
    method: 'POST',
    body: datos,
  });
}

/* ============================================================
   REPORTES - PDFs y WhatsApp
   ============================================================ */

/**
 * Descargar el PDF de una orden de servicio.
 * Abre el PDF en una nueva pestaña del navegador.
 * @param {number} ordenId - ID de la orden
 */
export function descargarPdfOrden(ordenId) {
  // Abrimos directamente la URL del PDF en una nueva pestaña
  // El backend devuelve el archivo PDF como descarga
  window.open(`${URL_BASE}/api/reportes/orden/${ordenId}/pdf`, '_blank');
}

/**
 * Descargar el PDF de una nota de venta.
 * @param {number} notaId - ID de la nota de venta
 */
export function descargarPdfNota(notaId) {
  window.open(`${URL_BASE}/api/notas-venta/${notaId}/pdf`, '_blank');
}

/**
 * Descargar el PDF de una cotización.
 * @param {number} cotizacionId - ID de la cotización
 */
export function descargarPdfCotizacion(cotizacionId) {
  window.open(`${URL_BASE}/api/reportes/cotizacion/${cotizacionId}/pdf`, '_blank');
}

/**
 * Obtener link de WhatsApp para enviar una orden al cliente.
 * @param {number} ordenId - ID de la orden
 * @returns {Promise<Object>} - { link, telefono, mensaje }
 */
export async function obtenerWhatsappOrden(ordenId) {
  return hacerPeticion(`/api/reportes/orden/${ordenId}/whatsapp`);
}

/**
 * Obtener link de WhatsApp para enviar una cotización al cliente.
 * @param {number} cotizacionId - ID de la cotización
 * @returns {Promise<Object>} - { link, telefono, mensaje }
 */
export async function obtenerWhatsappCotizacion(cotizacionId) {
  return hacerPeticion(`/api/reportes/cotizacion/${cotizacionId}/whatsapp`);
}

/* ============================================================
   PAGOS - Historial de pagos/abonos por orden
   ============================================================ */

/**
 * Registrar un pago en una orden (suma al abono automáticamente).
 * @param {number} ordenId - ID de la orden
 * @param {Object} datos - { monto: number, metodo_pago: string }
 * @returns {Promise<Object>} - El pago registrado
 */
export async function registrarPago(ordenId, datos) {
  return hacerPeticion(`/api/ordenes/${ordenId}/pagos`, {
    method: 'POST',
    body: datos,
  });
}

/**
 * Obtener el historial de pagos de una orden.
 * @param {number} ordenId - ID de la orden
 * @returns {Promise<Array>} - Lista de pagos (más reciente primero)
 */
export async function obtenerPagos(ordenId) {
  return hacerPeticion(`/api/ordenes/${ordenId}/pagos`);
}

/* ============================================================
   NOTAS INTERNAS - Notas con historial por orden
   ============================================================ */

/**
 * Agregar una nota interna a una orden.
 * @param {number} ordenId - ID de la orden
 * @param {Object} datos - { contenido: string, creado_por: string }
 * @returns {Promise<Object>} - La nota creada
 */
export async function agregarNota(ordenId, datos) {
  return hacerPeticion(`/api/ordenes/${ordenId}/notas`, {
    method: 'POST',
    body: datos,
  });
}

/**
 * Obtener el historial de notas internas de una orden.
 * @param {number} ordenId - ID de la orden
 * @returns {Promise<Array>} - Lista de notas (más reciente primero)
 */
export async function obtenerNotas(ordenId) {
  return hacerPeticion(`/api/ordenes/${ordenId}/notas`);
}

/* ============================================================
   AUTENTICACIÓN
   ============================================================ */

/**
 * Iniciar sesión con usuario y contraseña.
 * @param {string} username - Nombre de usuario
 * @param {string} password - Contraseña
 * @returns {Promise<Object>} - { access_token, token_type, usuario }
 */
export async function iniciarSesion(username, password) {
  return hacerPeticion('/api/auth/login', {
    method: 'POST',
    body: { username, password },
  });
}

/**
 * Verificar si un token JWT es válido.
 * @param {string} token - El token JWT
 * @returns {Promise<Object>} - Datos del usuario
 */
export async function verificarToken(token) {
  return hacerPeticion('/api/auth/me', {
    headers: { 'Authorization': `Bearer ${token}` },
  });
}

/* ============================================================
   USUARIOS - CRUD (solo admin)
   ============================================================ */

/** Obtener lista de usuarios */
export async function obtenerUsuarios() {
  return hacerPeticion('/api/usuarios/');
}

/** Obtener un usuario por ID */
export async function obtenerUsuario(id) {
  return hacerPeticion(`/api/usuarios/${id}`);
}

/** Crear un usuario nuevo */
export async function crearUsuario(datos) {
  return hacerPeticion('/api/usuarios/', {
    method: 'POST',
    body: datos,
  });
}

/** Actualizar un usuario */
export async function actualizarUsuario(id, datos) {
  return hacerPeticion(`/api/usuarios/${id}`, {
    method: 'PUT',
    body: datos,
  });
}

/** Desactivar un usuario */
export async function desactivarUsuario(id) {
  return hacerPeticion(`/api/usuarios/${id}`, {
    method: 'DELETE',
  });
}

/* ============================================================
   CAJA - Apertura, movimientos, arqueo y cierre diario
   ============================================================ */

/**
 * Obtener el resumen financiero del día (para el Dashboard).
 * @returns {Promise<Object|null>} - { fecha, caja_abierta, ingresos_hoy,
 *   egresos_hoy, esperado_hoy, facturado_hoy, notas_venta_hoy,
 *   pagos_hoy, ordenes_cerradas_hoy }
 */
export async function obtenerResumenCaja() {
  return hacerPeticion('/api/caja/resumen-dia');
}

/**
 * Obtener la caja actual (abierta o null si está cerrada).
 * @returns {Promise<{caja: Object|null}>} - La caja vigente o null.
 */
export async function obtenerCajaActual() {
  return hacerPeticion('/api/caja/actual');
}

/**
 * Abrir la caja del día con un monto inicial.
 * @param {Object} datos - { monto_inicial: number }
 * @returns {Promise<Object>} - La caja creada
 */
export async function abrirCaja(datos) {
  return hacerPeticion('/api/caja/abrir', {
    method: 'POST',
    body: datos,
  });
}

/**
 * Cerrar la caja con el arqueo (monto contado + nota opcional).
 * Devuelve la diferencia (monto_contado − monto_esperado).
 * @param {Object} datos - { monto_contado: number, nota_cierre?: string }
 * @returns {Promise<Object>} - La caja cerrada con su diferencia
 */
export async function cerrarCaja(datos) {
  return hacerPeticion('/api/caja/cerrar', {
    method: 'POST',
    body: datos,
  });
}

/**
 * Registrar un movimiento manual en la caja actual.
 * @param {Object} datos - { tipo: 'ingreso'|'egreso', monto: number,
 *   descripcion?: string, metodo_pago?: string }
 * @returns {Promise<Object>} - El movimiento creado
 */
export async function registrarMovimientoCaja(datos) {
  return hacerPeticion('/api/caja/movimientos', {
    method: 'POST',
    body: datos,
  });
}

/**
 * Obtener los movimientos de la caja actual (si está cerrada → []).
 * @returns {Promise<Array>} - Lista de movimientos
 */
export async function obtenerMovimientosCaja() {
  return hacerPeticion('/api/caja/movimientos');
}

/**
 * Obtener el historial de cierres de caja.
 * @returns {Promise<Array>} - Lista de cajas cerradas con sus sumas
 */
export async function obtenerHistorialCaja() {
  return hacerPeticion('/api/caja/historial');
}

/* ============================================================
   DIAGNÓSTICOS TÉCNICOS (V3)
   Flujo: técnico llena diagnóstico → dueño aprueba/rechaza
   ============================================================ */

/**
 * Guardar el diagnóstico técnico de un equipo (lo llena el técnico).
 * Además del diagnóstico, incluye el desglose de repuestos por proveedor.
 * @param {number} equipoId - ID del equipo
 * @param {object} datos - { enciende, tipo_disco, capacidad_disco, tipo_memoria,
 *   capacidad_memoria, slot_m2, slot_caddy, procesador, diagnostico, repuestos[] }
 * @returns {Promise<Object>} Equipo actualizado
 */
export async function guardarDiagnostico(equipoId, datos) {
  return hacerPeticion(`/api/equipos/${equipoId}/diagnostico`, {
    method: 'PUT',
    body: datos,
  });
}

/**
 * Aprobar el diagnóstico de un equipo (lo hace el dueño).
 * @param {number} equipoId - ID del equipo
 * @param {object} datos - { comentario, instalacion_decision, precio_venta }
 * @returns {Promise<Object>} Equipo actualizado
 */
export async function aprobarDiagnostico(equipoId, datos) {
  return hacerPeticion(`/api/equipos/${equipoId}/aprobar`, {
    method: 'POST',
    body: datos,
  });
}

/**
 * Rechazar el diagnóstico de un equipo (lo hace el dueño).
 * @param {number} equipoId - ID del equipo
 * @param {object} datos - { comentario }
 * @returns {Promise<Object>} Equipo actualizado
 */
export async function rechazarDiagnostico(equipoId, datos) {
  return hacerPeticion(`/api/equipos/${equipoId}/rechazar`, {
    method: 'POST',
    body: datos,
  });
}

/**
 * Listar diagnósticos.
 * @param {string} [estado] - pendiente | aprobado | rechazado (opcional)
 * @returns {Promise<Array>} Lista de diagnósticos con equipo + cliente + orden
 */
export async function obtenerDiagnosticos(estado = '') {
  const q = estado ? `?estado=${estado}` : '';
  return hacerPeticion(`/api/diagnosticos${q}`);
}

/**
 * Obtener el link de WhatsApp de un diagnóstico.
 * @param {number} equipoId - ID del equipo
 * @returns {Promise<Object>} { link, mensaje }
 */
export async function obtenerWhatsappDiagnostico(equipoId) {
  return hacerPeticion(`/api/diagnosticos/${equipoId}/whatsapp`);
}

/* ============================================================
   FACTURACIÓN ELECTRÓNICA SRI
   ============================================================ */

/**
 * Obtener la lista de facturas electrónicas generadas.
 * @returns {Promise<Array>} - Lista de facturas
 */
export async function obtenerFacturas() {
  const facturas = await hacerPeticion('/api/facturacion') || [];
  // Defensivo: si el backend no devuelve array, devolver lista vacía.
  if (!Array.isArray(facturas)) return [];
  return facturas.map(f => ({
    ...f,
    estado_sri: f?.estado_sri,
    // Campos nuevos del listado (facturas 01 + notas de crédito 04):
    // tipo_comprobante default '01' para datos previos sin el campo.
    tipo_comprobante: f?.tipo_comprobante ?? '01',
    factura_referenciada_id: f?.factura_referenciada_id,
    motivo_anulacion: f?.motivo_anulacion,
    valor_anulacion: f?.valor_anulacion,
    numero_autorizacion: f?.numero_autorizacion,
    fecha_autorizacion: f?.fecha_autorizacion,
    xml_respuesta_sri: f?.xml_respuesta_sri,
  }));
}

/**
 * Generar una factura electrónica a partir de una orden de servicio.
 * @param {Object} datos - { orden_servicio_id: number, ambiente?: "1"|"2" }
 * @returns {Promise<Object>} - La factura creada
 */
export async function generarFactura(datos) {
  return hacerPeticion('/api/facturacion/generar', {
    method: 'POST',
    body: datos,
  });
}

/**
 * Descargar el XML firmado de una factura electrónica.
 * Abre el XML en una nueva pestaña del navegador (descarga attachment).
 * @param {number} facturaId - ID de la factura
 */
export function descargarXmlFactura(facturaId) {
  window.open(`${URL_BASE}/api/facturacion/${facturaId}/xml`, '_blank');
}

/**
 * Transmitir y autorizar una factura al SRI (SOAP: recepción + autorización).
 * @param {number} facturaId - ID de la factura
 * @param {Object} datos - { forzar_ambiente?: "1"|"2", confirmar_produccion?: boolean }
 * @returns {Promise<Object>} - { id, clave_acceso, estado_sri, numero_autorizacion,
 *   fecha_autorizacion, errores }
 */
export async function transmitirFactura(facturaId, datos = {}) {
  try {
    return await hacerPeticion(`/api/facturacion/${facturaId}/transmitir`, {
      method: 'POST',
      body: datos,
    });
  } catch (err) {
    // Traducir errores comunes del backend a mensajes amigables
    const msg = (err.message || '').toLowerCase();
    if (msg.includes('no tiene xml firmado')) {
      throw new Error('La factura no está firmada. Crea la factura nuevamente.');
    }
    if (msg.includes('confirmación explícita') || msg.includes('confirmar_produccion')) {
      throw new Error('Para transmitir a producción debes confirmar la acción explícitamente.');
    }
    if (msg.includes('no se pudo transmitir al sri')) {
      throw new Error('No se pudo contactar al SRI. Revisa la conexión e inténtalo de nuevo.');
    }
    if (msg.includes('no encontrada')) {
      throw new Error('La factura no existe o ya fue eliminada.');
    }
    if (err.message && !err.message.startsWith('Error 4')) {
      throw new Error(`No se pudo transmitir al SRI: ${err.message}`);
    }
    throw err;
  }
}

/**
 * Anular una factura emitiendo una NOTA DE CRÉDITO electrónica (SRI).
 * La NC se firma, persiste y transmite automáticamente al SRI. Si la NC queda
 * 'autorizado'/'recibida', la factura original se marca 'anulada' (o
 * 'anulada_parcial' si monto_anular < total).
 * @param {number} facturaId - ID de la factura a anular (tipo 01)
 * @param {Object} datos - { motivo: string, monto_anular?: number }
 *   motivo: obligatorio (va en <motivo> del XML).
 *   monto_anular: monto TOTAL (IVA incluido) a anular; si se omite anula el 100%.
 * @returns {Promise<Object>} - { nota_credito, factura_original, transmision }
 */
export async function anularFactura(facturaId, datos) {
  try {
    return await hacerPeticion(`/api/facturacion/${facturaId}/anular`, {
      method: 'POST',
      body: datos,
    });
  } catch (err) {
    // Los errores 400/404 del backend llegan con 'detail' legible; se conserva
    // y se agrega contexto donde conviene.
    const msg = (err.message || '').toLowerCase();
    if (msg.includes('ya tiene una nota de crédito asociada')) {
      throw new Error('La factura ya tiene una nota de crédito asociada. Recarga la lista para ver el estado actual.');
    }
    if (msg.includes('solo se pueden anular') || msg.includes('solo se anulan facturas')) {
      throw new Error(`No se puede anular esta factura: ${err.message}`);
    }
    if (msg.includes('no encontrada')) {
      throw new Error('La factura no existe o ya fue eliminada.');
    }
    throw err;
  }
}
