# Registro de Progreso - Orpey Servicios

## 📅 Sesión: 28 de Agosto 2026

### FASE 6: Facturación Electrónica SRI — MÓDULO COMPLETO ✅

**Fecha:** 28 de Agosto 2026

**Lo que se hizo** (detalle completo en `FACTURACION-SRI.md`):

1. **Régimen tributario verificado en vivo en el SRI** (por @contador): el emisor es **RÉGIMEN GENERAL** (no RIMPE). La sesión de julio decía RIMPE Negocios Populares — quedó desactualizada. Impacto: facturación 100% electrónica obligatoria, tope consumidor final **$50.00**, sin leyenda RIMPE.
2. **Generación + firma XAdES-BES** de facturas con el certificado ANFAC real (`.p12` de producción, password resuelto automáticamente desde `~/agente-contador/.firma_p12.pass`).
3. **Validaciones backend:** orden pagada 100%, estado entregada/terminada, anti-duplicado, tope $50 consumidor final.
4. **Transmisión SOAP al SRI** (`transmision_sri.py`): WS-Security X509 con la firma real, recepción + autorización, reintentos en EN PROCESO, guard de producción (`confirmar_produccion`).
5. **Recepción real verificada en SRI de certificación: RECIBIDA ✅** (estructura + firma válidas; el bug de leyenda RIMPE vacía se corrigió).
6. **Frontend:** sección Facturación (`/facturacion`) con 5 estados, botón "Transmitir al SRI", modal de errores SRI, columna de autorización; botón "Factura SRI" en OrdenDetalle.
7. **Migración:** `backend/migraciones/2026_08_28_autorizacion_sri.sql` (columnas `numero_autorizacion`, `fecha_autorizacion`).
8. **40 tests verdes** en `backend/tests/`.
9. **Factura de prueba `001-001-000000001` (id 13)** transmitida el 28/08/2026 → estado `recibida`. **Dejada en BD por decisión de Daniel** como evidencia.

**Pendiente para producción real (validez fiscal):**
- [ ] Pagar declaraciones IVA pendientes (Abr, Jun, Jul 2026) — ver `~/recordatorios-registro/sri-declaracion-iva-2025-2026.md`
- [ ] Restablecer clave del portal SRI (expirada)
- [ ] Verificar/renovar permiso de facturación (~3 meses de vigencia)
- [ ] Transmitir factura en ambiente 2 → verificar `AUTORIZADO` con número real

**Nota régimen:** el emisor es régimen general desde ~jul/2026 (recategorización SRI); IR 2026 volverá al Formulario 102.

---

## 📅 Sesión: 5 de Mayo 2026

### FASE 3.5: Configuración de Passwords ✅ COMPLETADA

**Fecha:** 5 de Mayo 2026

**Lo que se hizo:**
1. Verificamos que los usuarios `admin` y `asistente` tenían passwords pendientes (hash_pendiente)
2. Usamos el endpoint `POST /api/auth/configurar-password` para establecer las contraseñas:
   - Usuario `admin` (ID: 1) → password: `admin123`
   - Usuario `asistente` (ID: 2) → password: `asistente123`
3. Las contraseñas se hashearon con **bcrypt** (seguro,不可逆)
4. Verificamos el login exitoso con ambas cuentas

**Comandos ejecutados:**
```bash
# Configurar password admin
curl -X POST "http://127.0.0.1:8000/api/auth/configurar-password?usuario_id=1&password_nuevo=admin123"

# Configurar password asistente
curl -X POST "http://127.0.0.1:8000/api/auth/configurar-password?usuario_id=2&password_nuevo=asistente123"

# Probar login
curl -X POST "http://127.0.0.1:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

**Estado:** Sistema listo para autenticación completa ✅

---

## 📅 Sesión: 4 de Mayo 2026

### FASE 1: Base de Datos ✅ COMPLETADA

**Archivo principal:** `schema_completo.sql`

**Lo que se hizo:**
- Diseñé el esquema completo de PostgreSQL con 7 tablas:
  1. `clientes` - Información de clientes (nombre, apellido, teléfono, email, cédula/RUC)
  2. `tecnicos` - Registro de técnicos
  3. `ordenes_servicio` - Tabla principal (con número auto-generado ORP-0001)
  4. `cotizaciones` - Presupuestos para clientes
  5. `notas_venta` - Facturación simple
  6. `usuarios` - Gestión de acceso
  7. `configuracion_sistema` - Datos del negocio, términos

- Se crearon 4 ENUMs: tipo_equipo, estado_orden, estado_cotizacion, rol_usuario
- Triggers para auto-generar números (ORP-0001, COT-0001, NV-0001)
- Trigger para actualizar `updated_at` automáticamente
- Columna calculada `por_cancelar` (total_orden - abono)
- Vista `vista_dashboard` para estadísticas
- 25 clientes importados del backup anterior
- Datos iniciales: 2 usuarios, 1 técnico, configuración del negocio

**Estado:** Ejecutado exitosamente en PostgreSQL

---

### FASE 2: Backend con FastAPI ✅ COMPLETADA

**Directorio:** `backend/`

**Lo que se hizo:**

1. **Estructura del proyecto:**
   ```
   backend/
   ├── .env                     # Variables de entorno
   ├── pyproject.toml           # Dependencias
   ├── run.sh                   # Script para ejecutar
   └── src/
       ├── main.py              # Punto de entrada
       ├── config/database.py   # Conexión a PostgreSQL
       ├── models/models.py     # Modelos SQLAlchemy (7 tablas)
       ├── schemas/schemas.py   # Schemas Pydantic (validación)
       └── routers/
           ├── clientes.py      # CRUD clientes
           ├── ordenes.py       # CRUD órdenes + dashboard
           ├── tecnicos.py      # CRUD técnicos
           └── cotizaciones.py  # CRUD cotizaciones
   ```

2. **Endpoints CRUD completos** para clientes, órdenes, técnicos y cotizaciones
3. **Características:** Documentación Swagger, validación Pydantic, búsqueda, filtros
4. **Dependencias:** fastapi, uvicorn, sqlalchemy, asyncpg, pydantic

**Estado:** Completado

---

### FASE 3: Features Avanzados ✅ COMPLETADA

**Fecha:** 4 de Mayo 2026

#### 1. Generación de PDFs 📄
**Archivo:** `src/services/pdf_generator.py`

- PDF profesional para órdenes de servicio con:
  - Logo de Orpey Servicios (estilizado con ReportLab)
  - Colores corporativos (azul oscuro, azul medio, azul claro)
  - Datos completos del cliente
  - Datos del equipo (tipo, marca, modelo)
  - Diagnóstico y trabajo a realizar
  - Tabla financiera (total, abono, por cancelar)
  - Términos y condiciones
  - Pie de página con fecha de generación

- PDF para notas de venta con:
  - Logo y datos del negocio
  - Datos del cliente
  - Detalle del servicio
  - Totales (subtotal, IVA 15%, total)

**Librería:** ReportLab 4.5.0

#### 2. Integración WhatsApp 💬
**Archivo:** `src/services/whatsapp.py`

- Genera links `wa.me` para enviar mensajes por WhatsApp
- No usa API de WhatsApp Business (no cuesta dinero)
- Mensajes prellenados con datos de la orden/cotización
- El usuario adjunta el PDF descargado manualmente
- Soporta teléfonos ecuatorianos (agrega +593 automáticamente)

**Flujo:**
1. Frontend pide link WhatsApp → `GET /api/reportes/orden/{id}/whatsapp`
2. Backend devuelve: `{"link": "https://wa.me/593...", "mensaje": "Hola..."}`
3. Frontend abre el link → WhatsApp Web se abre con mensaje prellenado
4. Usuario adjunta PDF descargado y envía

#### 3. Autenticación JWT 🔐
**Archivo:** `src/utils/auth.py`

- Login con username + password → token JWT
- Token válido por 24 horas
- Hashing de contraseñas con bcrypt
- Endpoint para verificar token (`/api/auth/me`)
- Endpoint para configurar passwords iniciales

**Librerías:** python-jose, passlib[bcrypt]

#### 4. Notas de Venta 🧾
**Archivo:** `src/routers/notas_venta.py`

- Crea nota de venta a partir de una orden
- Calcula automáticamente subtotal, IVA (15%) y total
- Genera PDF descargable
- Número auto-generado (NV-0001, NV-0002...)

#### 5. Router de Reportes 📊
**Archivo:** `src/routers/reportes.py`

- `GET /api/reportes/orden/{id}/pdf` → Descarga PDF de orden
- `GET /api/reportes/orden/{id}/whatsapp` → Link WhatsApp para orden
- `GET /api/reportes/cotizacion/{id}/whatsapp` → Link WhatsApp para cotización

#### Nuevos archivos creados en Fase 3:
| Archivo | Líneas | Descripción |
|---------|--------|-------------|
| `src/services/pdf_generator.py` | 529 | Generador de PDFs con ReportLab |
| `src/services/whatsapp.py` | 95 | Servicio de WhatsApp (wa.me links) |
| `src/utils/auth.py` | 95 | Autenticación JWT + bcrypt |
| `src/routers/reportes.py` | 180 | Router de reportes (PDF + WhatsApp) |
| `src/routers/notas_venta.py` | 150 | Router de notas de venta |
| `src/routers/auth.py` | 140 | Router de autenticación |

**Version:** 0.2.0

---

### FASE 4: Frontend con React + Vite ✅ COMPLETADA

**Fecha:** 5 de Mayo 2026
**Herramienta:** Antigravity (AI de Google DeepMind)
**Directorio:** `frontend/`

#### Lo que se hizo:

1. **Proyecto inicializado** con Vite + React (JavaScript, sin TypeScript)
2. **27 archivos** creados con código comentado en español
3. **Sistema de diseño completo** con paleta de colores de Orpey
4. **7 módulos funcionales** conectados a la API del backend
5. **Bug corregido** en el backend: orden de rutas en `ordenes.py`

#### Estructura del frontend:
```
frontend/
├── public/
│   └── logo-orpey.png              # Logo de la empresa
├── src/
│   ├── main.jsx                    # Punto de entrada de React
│   ├── App.jsx                     # Rutas y layout principal
│   ├── index.css                   # 🎨 Sistema de diseño completo
│   ├── api/
│   │   └── orpey-api.js            # 🔌 Todas las funciones de API
│   ├── componentes/
│   │   ├── BarraLateral.jsx/css    # Sidebar con navegación
│   │   ├── Encabezado.jsx/css      # Header con título y buscador
│   │   └── BadgeEstado.jsx/css     # Etiqueta de estado con colores
│   └── paginas/
│       ├── Dashboard.jsx/css       # Estadísticas generales
│       ├── Ordenes.jsx/css         # Listado con filtros
│       ├── OrdenFormulario.jsx/css # Crear/editar (autocomplete)
│       ├── OrdenDetalle.jsx/css    # Vista detallada + acciones
│       ├── Clientes.jsx/css        # Listado + modal CRUD
│       ├── ClienteDetalle.jsx/css  # Ficha + historial
│       ├── Tecnicos.jsx/css        # Cards + modal CRUD
│       ├── Cotizaciones.jsx/css    # Tabla + aprobar
│       └── NotasVenta.jsx/css      # Listado + descarga PDF
├── index.html                      # HTML con SEO
├── package.json                    # Dependencias
└── vite.config.js                  # Config de Vite
```

#### Tecnologías usadas:
| Librería | Versión | Para qué |
|----------|---------|----------|
| React | 18.x | Componentes de interfaz |
| React Router DOM | 7.x | Navegación SPA (sin recargar) |
| Lucide React | latest | Iconos modernos |
| Vite | 5.4.21 | Bundler y dev server |
| Google Fonts (Inter) | — | Tipografía profesional |
| Vanilla CSS | — | Estilos (sin frameworks) |

#### Diseño implementado:
| Elemento | Detalle |
|----------|---------|
| Color primario | `#FBC305` (Amarillo dorado de Orpey) |
| Color oscuro | `#353534` (Gris oscuro, sidebar) |
| Color claro | `#E5E4DE` (Gris claro, fondos) |
| Tipografía | Inter (Google Fonts) |
| Iconos | Lucide React |
| Animaciones | Entrada suave, hover, transiciones |
| Layout | Sidebar fijo + Header sticky + Contenido dinámico |

#### Funcionalidades completadas:

**Dashboard (`/`)**
- 7 tarjetas con estadísticas del backend (órdenes, PCs, laptops, etc.)
- Tabla de últimas 5 órdenes recientes
- Botón rápido "Nueva Orden de Servicio"
- Animaciones de entrada escalonadas

**Órdenes (`/ordenes`)**
- Tabla con todas las órdenes
- 3 filtros: estado, tipo de equipo, búsqueda de texto
- Badges de colores por estado
- Cálculo de "por cancelar" visible

**Nueva Orden (`/ordenes/nueva`)**
- Autocomplete de clientes (busca por nombre, teléfono, cédula)
- Selector visual de tipo de equipo con emojis
- Todos los campos: marca, modelo, serial, problema, diagnóstico
- Cálculo automático: Por Cancelar = Total - Abono
- Selector de técnico y garantía

**Detalle de Orden (`/ordenes/:id`)**
- Tarjetas: cliente, equipo, financiero, información
- Cambio de estado con botones interactivos
- Botones: Descargar PDF, WhatsApp, Nota de Venta, Editar, Eliminar

**Clientes (`/clientes`)**
- Tabla con búsqueda por nombre/teléfono/cédula
- Modal para crear/editar cliente
- Desactivación lógica (no se borran)

**Ficha de Cliente (`/clientes/:id`)**
- Datos de contacto e identificación
- Historial completo de órdenes
- Botones: WhatsApp directo, Email, Nueva Orden

**Técnicos (`/tecnicos`)**
- Cards con avatar (iniciales), especialidad, contacto
- Modal para crear/editar

**Cotizaciones (`/cotizaciones`)**
- Tabla con filtro por estado
- Botón "Aprobar" para cotizaciones abiertas
- Enviar por WhatsApp

**Notas de Venta (`/notas-venta`)**
- Listado con subtotal, IVA (15%), total
- Descarga de PDF por cada nota

#### API Client (`orpey-api.js`):
Cubre TODOS los 25+ endpoints del backend:
- Clientes: CRUD completo + búsqueda
- Órdenes: CRUD + dashboard + filtros
- Técnicos: CRUD completo
- Cotizaciones: CRUD + aprobar
- Notas de Venta: crear + listar
- Reportes: PDF download + WhatsApp links
- Auth: login + verificar token

#### Bug corregido en el backend:
**Archivo:** `backend/src/routers/ordenes.py`
- **Problema:** La ruta `/dashboard` estaba definida DESPUÉS de `/{orden_id}`
- **Efecto:** FastAPI interpretaba "dashboard" como un ID (error 422)
- **Solución:** Movimos `/dashboard` ANTES de `/{orden_id}`
- **Lección:** En FastAPI, las rutas específicas siempre van antes que las parametrizadas

#### Archivos creados en Fase 4:
| Archivo | Líneas | Descripción |
|---------|--------|-------------|
| `src/index.css` | 395 | Sistema de diseño global (colores, tipografía, animaciones) |
| `src/api/orpey-api.js` | 389 | Cliente API completo (25+ funciones) |
| `src/App.jsx` | 101 | Rutas y layout principal |
| `src/main.jsx` | 26 | Punto de entrada |
| `src/componentes/BarraLateral.jsx` | 113 | Sidebar de navegación |
| `src/componentes/BarraLateral.css` | 107 | Estilos del sidebar |
| `src/componentes/Encabezado.jsx` | 54 | Header superior |
| `src/componentes/Encabezado.css` | 79 | Estilos del header |
| `src/componentes/BadgeEstado.jsx` | 33 | Etiquetas de estado |
| `src/componentes/BadgeEstado.css` | 24 | Estilos de badges |
| `src/paginas/Dashboard.jsx` | 119 | Pantalla principal |
| `src/paginas/Dashboard.css` | 65 | Estilos del dashboard |
| `src/paginas/Ordenes.jsx` | 112 | Listado de órdenes |
| `src/paginas/OrdenFormulario.jsx` | 195 | Formulario crear/editar orden |
| `src/paginas/OrdenDetalle.jsx` | 160 | Vista detallada de orden |
| `src/paginas/Clientes.jsx` | 157 | Gestión de clientes |
| `src/paginas/ClienteDetalle.jsx` | 98 | Ficha de cliente |
| `src/paginas/Tecnicos.jsx` | 104 | Gestión de técnicos |
| `src/paginas/Cotizaciones.jsx` | 82 | Gestión de cotizaciones |
| `src/paginas/NotasVenta.jsx` | 54 | Notas de venta |
| + 8 archivos CSS | — | Estilos de cada página |

**Versión Frontend:** 1.0.0

---

### PENDIENTE - FASE 4.5: Pulir Frontend

- [ ] Pantalla de Login (interfaz gráfica - la lógica JWT ya existe)
- [ ] Protección de rutas (redirigir a login si no hay token)
- [ ] Responsive design (optimizar para móvil/tablet)
- [ ] Buscador global funcional (del encabezado)
- [ ] Notificaciones en tiempo real
- [ ] Página de Configuración del sistema
- [ ] Mejorar la tabla de órdenes con paginación
- [ ] Agregar confirmaciones visuales (toasts) en vez de alert()

### PENDIENTE - FASE 5: Deploy

- [ ] Docker (frontend + backend)
- [ ] Nginx como proxy reverso
- [ ] Restringir CORS al dominio del frontend
- [ ] Backup automático de PostgreSQL
- [ ] SSL/HTTPS
- [ ] Producción

---

## 📝 Notas Importantes

1. **Base de datos:** Ya tiene datos reales (25 clientes del backup anterior)
2. **Usuarios iniciales:** Admin (Daniel) y Asistente (Sofía) - passwords configurados ✅
   - admin: `admin123`
   - asistente: `asistente123`
3. **Swagger UI:** Disponible en http://127.0.0.1:8000/docs cuando se ejecuta el backend
4. **Documentación completa del backend:** Ver `backend/Guia_Backend.md`
5. **Guía rápida:** Ver `backend/README.md`
6. **Python versión:** 3.12 (funciona perfecto)
7. **Node versión:** 18.19.1 (funciona con Vite 5)
8. **Conexión a BD:** Por socket Unix `/var/run/postgresql` (peer authentication)
9. **WhatsApp:** Se usa wa.me (gratis, sin API de Meta)
10. **PDFs:** Se generan con ReportLab, se descargan directamente
11. **Frontend comentado:** Todo el código tiene comentarios en español para aprendizaje

---

## 🔧 Comandos útiles

### Ejecutar el backend:
```bash
cd ~/app-orpey/backend
./run.sh
```

### Ejecutar el frontend:
```bash
cd ~/app-orpey/frontend
npm run dev
```

### URLs en desarrollo:
| Servicio | URL |
|----------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://127.0.0.1:8000 |
| Swagger (docs API) | http://127.0.0.1:8000/docs |

### Acceder a la documentación:
http://127.0.0.1:8000/docs

### Probar la API:
```bash
# Crear cliente
curl -X POST http://127.0.0.1:8000/api/clientes \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Juan","apellido":"Perez","telefono":"0987654321","cedula_ruc":"0999999999"}'

# Descargar PDF de orden
curl -o orden.pdf http://127.0.0.1:8000/api/reportes/orden/1/pdf

# Generar link WhatsApp
curl http://127.0.0.1:8000/api/reportes/orden/1/whatsapp

# Login
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

### Conectar a PostgreSQL:
```bash
psql -U skorggamor -d orpey_db
```

---

*Última actualización: 28 de Agosto 2026 — Sesión Facturación Electrónica SRI (Fase 6)*


---

## Sesión 29/08/2026 — QA Anulación (Nota de Crédito) E2E ✅

### Ganado hoy
- **Botón "Anular" implementado y probado en vivo** (frontend: modal con motivo + monto parcial, badge Anulada/Anulada Parcial, columna "Factura Anulada").
- **3 bugs reales resueltos contra el SRI de certificación** (ver FACTURACION-SRI.md):
  1. `numDocModificado` debe ser `001-001-000000001` (no la clave de acceso).
  2. Montos de NC **positivos** (XSD minInclusive 0.0) — se invirtió la decisión previa.
  3. `direccionComprador` requires minLength 1 → fallback "SIN DIRECCIÓN REGISTRADA".
- **Regla [70]** CLAVE EN PROCESAMIENTO ≠ rechazo: normalizada a EN PROCESO/RECIBIDA (afecta reenvíos y consultas inmediatas).
- QA completo: factura nueva → RECIBIDA → anular → NC RECIBIDA → factura `anulada`. BD limpiada (solo queda factura 13).
- Suite: **64 tests verdes** (2 nuevos: [70] recepción y autorización).

### Pendientes (sin cambios de código)
- Regularizar SRI: IVA Abr/Jun/Jul 2026, clave portal, permiso de facturación (~3 meses vigencia).
- (Opcional futuro) Endpoint "regenerar XML" para re-firmar comprobantes devueltos por estructura.
- (Opcional futuro) Confirmar con el SRI el `codigoPorcentaje` vigente (13% vs 15%) antes de producción.

## 2026-09-03 — Facturación completa operativa
- Se implementó facturación electrónica de punta a punta (generar → transmitir → autorizar → descargar).
- Backend: descarga XML autorizado, generación de PDF con reportlab (formato SRI), endpoint consultar-autorización.
- Frontend: botones Descargar PDF/XML, Refrescar autorización, badges de estado (Facturas.jsx).
- Primera factura REAL emitida a producción (ORP-0002 → 001-001-000000002, $30.00). SRI la recibió, autorización en proceso.
- Monitor de autorización en background: `logs/monitor_autorizacion.py` (consulta cada 2 min).
- Ver ESPEC-FACTURACION.md para el contrato de API implementado.

---

## 2026-09-03 — ⚡ Sistema de Autorización Eficiente (ANEXO)

### Estado: Facturación de producción funcional end-to-end
✅ **Primera factura real autorizable:** id=21 (ORP-0002, $30.00), clave válida, ambiente 2 (producción).
⚠️ SRI la tiene "EN PROCESO" — el worker la monitorea en background hasta autorizar.

### Mejoras de eficiencia implementadas (como sistemas certificados comerciales)
1. **Retry agresivo síncrono** (`transmision_sri.py:transmitir_y_autorizar`):
   - `modo_agresivo=True` con backoff variable (2s→10s), ~30s de retry.
   - Captura la autorización típica sin bloquear la UI.
2. **Worker de fondo persistente** (`worker_autorizacion.py` + systemd):
   - Servicio `orpey-worker-autorizacion.service`, reinicia auto, sobrevive reboot.
   - Escanea BD cada 45s por `firmado/recibida/en_proceso`, consulta SRI, actualiza estado.
   - Garantiza que NINGUNA factura quede sin autorizar.

### Verificación
- Worker corre como servicio systemd (1 instancia, active running).
- Pasada de prueba: consultó correctamente las 2 facturas pendientes (13 pruebas + 21 producción) contra sus respectivos ambientes.
- Backend (`--reload`) ya tiene el nuevo retry agresivo.

### Próximo
- Cuando SRI autorice id=21 → confirmar estado "autorizado" + N° en UI/PDF/XML.
- Luego deploy a VPS (pendiente green light de Daniel).
- IVA Mayo 2026: reintentar tras aprobación (04-05/09/2026).

---

## 2026-09-03 → 09-04 — 🚀 DESPLIEGUE A PRODUCCIÓN EN VPS CONTABO (COMPLETADO)

### Estado: ✅ app-orpey EN PRODUCCIÓN (VPS 5.189.165.55, puerto 8001)

**Sistema de facturación SRI funcionando end-to-end + deploy en servidor.**

### Deploy completado
- **3 containers** en red `orpey_net` (aislada de `abasto_net`):
  - `orpey-db-1` (Postgres 16, 5432 interno solo)
  - `orpey-backend-1` (FastAPI, 8000 interno)
  - `orpey-nginx-1` (frontend + proxy, **puerto 8001 expuesto**)
- **Datos reales migrados:** 41 clientes, 21 órdenes, 4 usuarios, facturas electrónicas.
  - Usado el DUMP FRESCO con `--no-owner` (evita error de rol `skorggamor` en container).
  - Corregida la ruta del `.p12` en el dump → `/app/firma/firmadigital.p12`.
- **Firma digital montada:** `/app/firma/firmadigital.p12` (read-only), verificada OK: el backend la carga (cert RUC GUAYAQUIL).
- **Firewall:** puerto 8001 abierto (UFW allow, aditivo — Abasto 8000 intacto).
- **Acceso externo:** `http://5.189.165.55:8001` responde 200.
- **Backup automático:** cron 3am → `/opt/backups/orpey_YYYYMMDD.sql.gz` (rotación 7 días).
- **AbastoAPP NO afectado** — ambos containers siguen corriendo.

### Fixes de seguridad aplicados (pre-deploy)
- JWT secret desde env var (`JWT_SECRET_KEY`).
- CORS configurable (`ALLOWED_ORIGINS`, ya no `*`).
- Ruta `.p12` configurable (`FIRMA_P12_RUTA` → `/app/firma/`).
- Password firma: env var + fallback `/app/firma/.firma_p12.pass`.
- deps XML (lxml, signxml, cryptography, httpx) agregadas a pyproject.

### Comandos útiles en VPS
```bash
docker compose -f /opt/app-orpey/docker-compose.yml ps        # estado
docker logs orpey-backend-1 --tail=50                          # logs
/opt/backups/backup_orpey.sh                                   # backup manual
```

### Pendiente
- Emitir una factura real desde la interfaz en producción (verificar flujo completo desde el container).
- Confirmar autorización de factura 21 (worker local la monitorea) y que la factura en el VPS refleje autorización.
- IVA Mayo 2026 (reintentar tras aprobación).

---

## 2026-09-04 — 🔑 FIX BUG: "password cannot be longer than 72 bytes" (CAUSA RAÍZ)

### Síntoma
Al intentar login/configurar contraseña salía: `Error interno del servidor: password cannot be longer than 72 bytes` — incluso con contraseñas cortas.

### Causa raíz (importante)
**NO era la longitud de la contraseña.** Era una **incompatibilidad de versiones** en el container de producción:
- `docker` instaló `bcrypt 5.0.0` (la más nueva)
- `passlib 1.7.4` es **incompatible con `bcrypt >= 4.1`** (bcrypt eliminó el atributo `__about__`)
- passlib fallaba internamente y ese error se manifestaba como el error de 72 bytes
- Local funcionaba porque usaba `bcrypt 4.0.1` (compatible)

### Solución aplicada (desplegada)
- Fijado en `backend/pyproject.toml`: `"bcrypt>=3.2,<4.1"` (junto a `passlib>=1.7.4`)
- Rebuild `--no-cache` del backend en el VPS → `bcrypt 4.0.1` + `passlib 1.7.4` ✅
- Verificado: configurar-password → 200, login admin → 200 con token

### Mejoras de seguridad/UX que también se implementaron
- `validar_password()`: política de contraseñas (mín 6, máx 64 bytes) con mensajes claros en vez de error de servidor.
- `hash_password`/`verificar_password` robustos: nunca revientan (login con error de bcrypt → credenciales inválidas, no 500).
- Endpoint faltante `POST /api/auth/cambiar-password` creado (estaba documentado pero no existía).
- Validación de contraseña en crear/actualizar usuario.

### Acceso admin (producción)
- Usuario: `admin` | Contraseña: `Wmah7qga.` (con punto, = password de la firma SRI)
- Verificado login 200 OK ✅
