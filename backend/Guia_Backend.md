# Guía Completa del Backend - Orpey Servicios API

## 📁 Estructura del proyecto

```
backend/
├── .env                     # Variables de entorno (contraseñas, URLs)
├── pyproject.toml           # Dependencias del proyecto
├── run.sh                   # Script para ejecutar el servidor
├── README.md                # Referencia rápida de endpoints
├── Guia_Backend.md          # Esta guía
└── src/
    ├── __init__.py
    ├── main.py              # 🚀 Punto de entrada (la aplicación)
    ├── config/
    │   ├── __init__.py
    │   └── database.py      # 🔗 Conexión a PostgreSQL
    ├── models/
    │   ├── __init__.py
    │   └── models.py        # 📊 Tablas de la BD como clases Python
    ├── schemas/
    │   ├── __init__.py
    │   └── schemas.py       # ✅ Validación de datos
    └── routers/
        ├── __init__.py
        ├── clientes.py      # 👤 Endpoints para clientes
        ├── ordenes.py       # 📋 Endpoints para órdenes
        ├── tecnicos.py      # 🔧 Endpoints para técnicos
        └── cotizaciones.py  # 💰 Endpoints para cotizaciones
```

## 🔧 Cómo ejecutar

### Opción 1: Con el script (recomendado)
```bash
cd ~/app-orpey/backend
./run.sh
```

### Opción 2: Con uvicorn directamente
```bash
cd ~/app-orpey/backend
python3 -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```

### ¿Qué hace `--reload`?
Reinicia automáticamente el servidor cuando modificás un archivo. Ideal para desarrollo.

## 🌐 Endpoints disponibles

### Raíz
- `GET /` → Mensaje de bienvenida
- `GET /health` → Verificar que la API funciona

### Clientes
- `POST /api/clientes` → Crear cliente
- `GET /api/clientes` → Listar clientes (acepta `?buscar=nombre`)
- `GET /api/clientes/1` → Ver cliente con ID 1
- `PUT /api/clientes/1` → Actualizar cliente
- `DELETE /api/clientes/1` → Eliminar cliente (desactivación lógica)

### Órdenes de Servicio
- `POST /api/ordenes` → Crear orden (número auto: ORP-0001)
- `GET /api/ordenes` → Listar órdenes (acepta `?estado=revision&tipo_equipo=laptop`)
- `GET /api/ordenes/1` → Ver orden
- `PUT /api/ordenes/1` → Actualizar orden
- `DELETE /api/ordenes/1` → Eliminar orden
- `GET /api/ordenes/dashboard` → Estadísticas del dashboard

### Técnicos
- `POST /api/tecnicos` → Crear técnico
- `GET /api/tecnicos` → Listar técnicos
- `GET /api/tecnicos/1` → Ver técnico
- `PUT /api/tecnicos/1` → Actualizar técnico
- `DELETE /api/tecnicos/1` → Eliminar técnico (desactivación lógica)

### Cotizaciones
- `POST /api/cotizaciones` → Crear cotización (número auto: COT-0001)
- `GET /api/cotizaciones` → Listar cotizaciones
- `GET /api/cotizaciones/1` → Ver cotización
- `PUT /api/cotizaciones/1` → Actualizar cotización
- `POST /api/cotizaciones/1/aprobar` → Aprobar cotización

## 📖 Documentación automática (Swagger UI)

Una vez que el servidor está corriendo, abrís en el navegador:
- **http://127.0.0.1:8000/docs** → Swagger UI (interactivo, podés probar los endpoints)
- **http://127.0.0.1:8000/redoc** → ReDoc (más elegante)

### ¿Qué es Swagger?
Es una interfaz web que genera FastAPI automáticamente. Te permite:
- Ver TODOS los endpoints disponibles
- Probarlos directamente desde el navegador (botón "Try it out")
- Ver qué datos necesita cada endpoint
- Ver qué devuelve cada endpoint
- No necesitás Postman ni nada adicional

## 🧩 Explicación de cada componente

### 1. FastAPI (el framework web)
FastAPI es el "motor" de tu API. Recibe peticiones HTTP (GET, POST, PUT, DELETE) y devuelve respuestas JSON.

**¿Por qué FastAPI?**
- Muy rápido (uno de los frameworks Python más veloces)
- Genera documentación automática (Swagger + ReDoc)
- Valida datos automáticamente con Pydantic
- Soporta async/await para mejor rendimiento
- Fácil de usar y aprender

**Ejemplo de un endpoint simple:**
```python
@router.get("/api/clientes")
async def listar_clientes(db = Depends(get_db)):
    # Obtener clientes de la BD
    result = await db.execute(select(Cliente))
    return result.scalars().all()
```

### 2. SQLAlchemy (el ORM)
SQLAlchemy convierte tablas SQL en clases Python.

**Sin SQLAlchemy:**
```python
# Tenés que escribir SQL a mano
cursor.execute("SELECT * FROM clientes WHERE id = 1")
cliente = cursor.fetchone()
```

**Con SQLAlchemy:**
```python
# Python lo hace por vos
result = await db.execute(select(Cliente).where(Cliente.id == 1))
cliente = result.scalar_one_or_none()
```

**Ventajas:**
- No escribís SQL a mano
- Protege contra inyección SQL
- Fácil de mantener
- Funciona con cualquier base de datos

### 3. Pydantic (la validación)
Pydantic valida que los datos que recibís y envías sean correctos.

**Ejemplo:**
```python
class ClienteCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    telefono: str = Field(..., min_length=1, max_length=20)
```

Si alguien envía un nombre vacío, Pydantic devuelve un error automáticamente:
```json
{
    "detail": [
        {
            "type": "string_too_short",
            "loc": ["body", "nombre"],
            "msg": "String should have at least 1 character"
        }
    ]
}
```

**Validators personalizados:**
En `schemas.py` tenemos validators que:
- Capitalizan nombres automáticamente: "gerardo" → "Gerardo"
- Limpian teléfonos: "0985 983 416" → "0985983416"

### 4. Routers (organización de endpoints)
Los routers agrupan endpoints por tema. Cada router es un archivo:
- `clientes.py` → Todo lo relacionado con clientes
- `ordenes.py` → Todo lo relacionado con órdenes
- `tecnicos.py` → Todo lo relacionado con técnicos
- `cotizaciones.py` → Todo lo relacionado con cotizaciones

Se registran en `main.py`:
```python
app.include_router(clientes_router)
app.include_router(ordenes_router)
app.include_router(tecnicos_router)
app.include_router(cotizaciones_router)
```

### 5. Uvicorn (el servidor)
Uvicorn es el servidor que ejecuta tu API. FastAPI es el framework, Uvicorn es el que lo hace funcionar en la web.

## 🔄 Flujo de una petición

1. **El frontend/envía**: `POST /api/clientes` con datos JSON
2. **Uvicorn** recibe la petición
3. **FastAPI** la dirige al router correcto (`clientes.py`)
4. **Pydantic** valida los datos (si el nombre está vacío, devuelve error)
5. **SQLAlchemy** guarda en la base de datos
6. **Pydantic** formatea la respuesta
7. **FastAPI** devuelve JSON al frontend

## 📊 Base de Datos

### Conexión
Se conecta por socket Unix (peer authentication) sin necesidad de contraseña:
```
postgresql+asyncpg:///orpey_db?host=/var/run/postgresql
```

### Tablas existentes:
| Tabla | Registros | Descripción |
|-------|-----------|-------------|
| `clientes` | 25 | Datos de clientes importados del backup |
| `tecnicos` | 1 | Daniel Baltodano |
| `ordenes_servicio` | 0 | Lista para usar |
| `cotizaciones` | 0 | Lista para usar |
| `notas_venta` | 0 | Lista para usar |
| `usuarios` | 2 | Admin + Asistente |
| `configuracion_sistema` | 6 | Datos del negocio |

### Características especiales:
- **Números auto-generados:** ORP-0001, COT-0001, NV-0001 (triggers en la BD)
- **Por calcular:** `por_cancelar` = total_orden - abono (columna generada)
- **Fechas automáticas:** `created_at`, `updated_at` se actualizan solos
- **Vista dashboard:** `vista_dashboard` da estadísticas de un solo golpe

## 📝 Ejemplos de uso con curl

### Crear cliente:
```bash
curl -X POST http://127.0.0.1:8000/api/clientes \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "gerardo",
    "apellido": "zumba",
    "telefono": "0985983416",
    "cedula_ruc": "0903803575",
    "email": "gerardo@email.com",
    "direccion": "Guayaquil"
  }'
```

### Listar clientes:
```bash
curl http://127.0.0.1:8000/api/clientes
curl http://127.0.0.1:8000/api/clientes?buscar=gerardo
```

### Crear orden:
```bash
curl -X POST http://127.0.0.1:8000/api/ordenes \
  -H "Content-Type: application/json" \
  -d '{
    "cliente_id": 1,
    "tipo_equipo": "laptop",
    "marca": "HP",
    "modelo": "15DA2180NIA",
    "descripcion_problema": "No enciende, pantalla negra",
    "tecnico_id": 1,
    "total_orden": 50.00,
    "abono": 20.00,
    "garantia_dias": 30
  }'
```

### Dashboard:
```bash
curl http://127.0.0.1:8000/api/ordenes/dashboard
```

## 🚀 Próximos pasos

1. ✅ **Base de datos** (completado)
2. ✅ **Backend CRUD** (completado)
3. ⏳ **Features avanzados**: PDF, WhatsApp, autenticación
4. ⏳ **Frontend** (con Antigravity)
5. ⏳ **Deploy** (Docker)

## 📝 Notas importantes

- Los passwords de usuarios están como `'hash_pendiente'` - se deben hashear con bcrypt cuando implementemos autenticación
- CORS está configurado con `allow_origins=["*"]` - en producción hay que restringirlo al dominio del frontend
- El campo `por_cancelar` en órdenes se calcula automáticamente en PostgreSQL
- Los números de orden/cotización/nota se generan automáticamente con triggers en la BD
- Los clientes se desactivan (no se borran) para mantener historial de órdenes

---

*Orpey Servicios - Backend API v0.1.0*
