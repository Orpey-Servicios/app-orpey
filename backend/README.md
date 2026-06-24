# Orpey Servicios - Backend API

## 🚀 Inicio Rápido

### Ejecutar el servidor:
```bash
cd ~/app-orpey/backend
./run.sh
```

### Abrir documentación:
http://127.0.0.1:8000/docs

---

## 📁 Estructura

```
backend/
├── .env                     # Variables de entorno
├── pyproject.toml           # Dependencias
├── run.sh                   # Script para ejecutar
├── README.md                # Este archivo (referencia rápida)
├── Guia_Backend.md          # Guía detallada de componentes
└── src/
    ├── main.py              # 🚀 Punto de entrada
    ├── config/database.py   # 🔗 Conexión a PostgreSQL
    ├── models/models.py     # 📊 Tablas como clases Python
    ├── schemas/schemas.py   # ✅ Validación de datos
    ├── services/
    │   ├── pdf_generator.py # 📄 Generador de PDFs
    │   └── whatsapp.py      # 💬 Links de WhatsApp
    ├── utils/
    │   └── auth.py          # 🔐 JWT y hashing de passwords
    └── routers/
        ├── clientes.py      # 👤 CRUD clientes
        ├── ordenes.py       # 📋 CRUD órdenes + dashboard
        ├── tecnicos.py      # 🔧 CRUD técnicos
        ├── cotizaciones.py  # 💰 CRUD cotizaciones
        ├── notas_venta.py   # 🧾 Notas de venta
        ├── reportes.py      # 📊 PDFs + WhatsApp
        └── auth.py          # 🔐 Login + autenticación
```

---

## 🌐 Endpoints Completos

### Raíz
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Mensaje de bienvenida |
| GET | `/health` | Verificar que funciona |

### Autenticación
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/auth/login` | Iniciar sesión → token JWT |
| GET | `/api/auth/me?token=xxx` | Verificar token |
| POST | `/api/auth/configurar-password` | Configurar password |

### Clientes
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/clientes` | Crear cliente |
| GET | `/api/clientes?buscar=nombre` | Listar con búsqueda |
| GET | `/api/clientes/1` | Ver cliente |
| PUT | `/api/clientes/1` | Actualizar cliente |
| DELETE | `/api/clientes/1` | Eliminar cliente |

### Órdenes de Servicio
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/ordenes` | Crear orden (número auto: ORP-0001) |
| GET | `/api/ordenes?estado=revision` | Listar con filtros |
| GET | `/api/ordenes/1` | Ver orden |
| PUT | `/api/ordenes/1` | Actualizar orden |
| DELETE | `/api/ordenes/1` | Eliminar orden |
| GET | `/api/ordenes/dashboard` | Estadísticas |

### Técnicos
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/tecnicos` | Crear técnico |
| GET | `/api/tecnicos` | Listar técnicos |
| GET | `/api/tecnicos/1` | Ver técnico |
| PUT | `/api/tecnicos/1` | Actualizar técnico |
| DELETE | `/api/tecnicos/1` | Eliminar técnico |

### Cotizaciones
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/cotizaciones` | Crear cotización (número auto: COT-0001) |
| GET | `/api/cotizaciones` | Listar cotizaciones |
| GET | `/api/cotizaciones/1` | Ver cotización |
| PUT | `/api/cotizaciones/1` | Actualizar cotización |
| POST | `/api/cotizaciones/1/aprobar` | Aprobar cotización |

### Notas de Venta
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/notas-venta` | Crear nota de venta (número auto: NV-0001) |
| GET | `/api/notas-venta` | Listar notas de venta |
| GET | `/api/notas-venta/1` | Ver nota de venta |
| GET | `/api/notas-venta/1/pdf` | Descargar PDF de nota de venta |

### Reportes (PDF + WhatsApp)
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/reportes/orden/1/pdf` | Descargar PDF de orden |
| GET | `/api/reportes/orden/1/whatsapp` | Generar link WhatsApp para orden |
| GET | `/api/reportes/cotizacion/1/whatsapp` | Generar link WhatsApp para cotización |

---

## 📋 Ejemplos de uso

### Login:
```json
POST /api/auth/login
{
    "username": "admin",
    "password": "tu_password"
}
```
**Respuesta:**
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "usuario": {
        "id": 1,
        "username": "admin",
        "nombre": "Daniel Baltodano",
        "rol": "admin"
    }
}
```

### Crear cliente:
```json
POST /api/clientes
{
    "nombre": "gerardo",
    "apellido": "zumba",
    "telefono": "0985983416",
    "cedula_ruc": "0903803575"
}
```
**Nota:** El nombre se capitaliza automáticamente → "Gerardo Zumba"

### Crear orden:
```json
POST /api/ordenes
{
    "cliente_id": 1,
    "tipo_equipo": "laptop",
    "marca": "HP",
    "modelo": "15DA2180NIA",
    "descripcion_problema": "No enciende, pantalla negra",
    "tecnico_id": 1,
    "total_orden": 50.00,
    "abono": 20.00,
    "garantia_dias": 30
}
```
**Nota:** El número se genera automáticamente → "ORP-0001"

### Descargar PDF de orden:
```
GET /api/reportes/orden/1/pdf
```
**Resultado:** Descarga archivo `orden_ORP-0001.pdf`

### Generar link WhatsApp para orden:
```
GET /api/reportes/orden/1/whatsapp
```
**Respuesta:**
```json
{
    "link": "https://wa.me/593985983416?text=Hola+Gerardo...",
    "telefono": "0985983416",
    "mensaje": "Hola Gerardo, te saludo de Orpey Servicios..."
}
```
**Uso:** Abrir el link en el navegador → WhatsApp Web/App se abre con el mensaje prellenado. El usuario adjunta el PDF descargado y envía.

### Crear nota de venta:
```json
POST /api/notas-venta
{
    "orden_servicio_id": 1,
    "cliente_id": 1
}
```
**Cálculos automáticos:**
- Si la orden tiene total de $115.00
- Subtotal: $100.00
- IVA (15%): $15.00
- Total: $115.00

---

## 🧩 Componentes

| Componente | Librería | Para qué sirve |
|-----------|----------|----------------|
| **FastAPI** | `fastapi` | Framework web, crea las rutas de la API |
| **SQLAlchemy** | `sqlalchemy` | ORM, convierte tablas SQL en clases Python |
| **Pydantic** | `pydantic` | Valida datos de entrada y salida |
| **asyncpg** | `asyncpg` | Driver asíncrono para PostgreSQL |
| **Uvicorn** | `uvicorn` | Servidor que ejecuta la API |
| **ReportLab** | `reportlab` | Genera PDFs profesionales |
| **python-jose** | `python-jose` | JWT para autenticación |
| **passlib** | `passlib` | Hashing de contraseñas (bcrypt) |

---

## 📊 Base de Datos

### Tablas creadas:
- `clientes` - Datos de clientes
- `tecnicos` - Datos de técnicos
- `ordenes_servicio` - Órdenes de servicio
- `cotizaciones` - Presupuestos
- `notas_venta` - Facturación simple
- `usuarios` - Acceso al sistema
- `configuracion_sistema` - Datos del negocio

### Datos iniciales:
- 25 clientes importados del backup anterior
- 2 usuarios: admin (Daniel) y asistente (Sofía)
- 1 técnico: Daniel Baltodano
- Configuración del negocio con términos y condiciones

---

## 🔐 Autenticación

La autenticación usa JWT (JSON Web Tokens):

1. Enviar `POST /api/auth/login` con username + password
2. Recibir token JWT válido por 24 horas
3. Enviar token en cada request: `Authorization: Bearer <token>`

**Configurar passwords iniciales:**
```
POST /api/auth/configurar-password?usuario_id=1&password_nuevo=tu_password
```

---

## 📄 PDFs

Los PDFs se generan con ReportLab e incluyen:
- Logo de Orpey Servicios (estilizado)
- Colores corporativos
- Datos completos del cliente y equipo
- Información financiera
- Términos y condiciones

**Tipos de PDF:**
- Orden de servicio: `/api/reportes/orden/{id}/pdf`
- Nota de venta: `/api/notas-venta/{id}/pdf`

---

## 💬 WhatsApp

Se usa el protocolo `wa.me` (gratuito, no requiere API de Meta):

1. Generar link: `GET /api/reportes/orden/{id}/whatsapp`
2. Abrir link en navegador
3. WhatsApp Web/App se abre con mensaje prellenado
4. Usuario adjunta PDF descargado y envía

**Ventaja:** No requiere WhatsApp Business API, no cuesta dinero, funciona inmediatamente.

---

## 📖 Para más detalle

Ver `Guia_Backend.md` para explicación detallada de cada componente.

---

*Orpey Servicios - Backend API v0.2.0*
