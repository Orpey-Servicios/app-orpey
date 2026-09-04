"""
app-orpey — Sistema de gestión de taller para Orpey Servicios
Copyright (C) 2026 Orpey Servicios

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

main.py - Punto de entrada de la aplicación FastAPI.

Este archivo es el CORAZÓN de tu backend:
1. Crea la aplicación FastAPI
2. Registra todos los routers (clientes, ordenes, tecnicos, cotizaciones, reportes, auth)
3. Configura la documentación automática (Swagger UI)
4. Define el endpoint raíz (/)

Para ejecutar:
    cd backend
    ./run.sh

Luego abrís en el navegador:
    http://127.0.0.1:8000/docs       → Swagger UI (interactivo)
    http://127.0.0.1:8000/redoc      → ReDoc (más elegante)
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import Request

from src.config.database import engine
from src.models.models import Base, Cliente, Tecnico, OrdenServicio, Cotizacion
from src.routers import (
    clientes_router, ordenes_router, tecnicos_router,
    cotizaciones_router, reportes_router, notas_venta_router, auth_router,
    pagos_router, notas_router, usuarios_router, diagnosticos_router,
    facturacion_router, caja_router, servicios
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle de la aplicación.
    Se ejecuta al iniciar y al cerrar el servidor.
    """
    # Al iniciar: verificar conexión a la BD
    print("=" * 50)
    print("  Orpey Servicios - Backend API")
    print("=" * 50)
    print("Conectando a la base de datos...")
    print("Documentación: http://127.0.0.1:8000/docs")
    print("=" * 50)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Base de datos conectada correctamente!")

    yield  # La app se ejecuta acá

    # Al cerrar: limpiar conexiones
    print("Cerrando conexión a la base de datos...")
    await engine.dispose()


# Crear la aplicación FastAPI
app = FastAPI(
    title="Orpey Servicios API",
    description="""
    API para el Sistema de Gestión de Servicio Técnico de Orpey Servicios.

    ## Funcionalidades disponibles:

    * **Clientes**: Registro y gestión de clientes
    * **Órdenes de Servicio**: Gestión completa del ciclo de vida de órdenes
    * **Técnicos**: Registro de técnicos y asignación de órdenes
    * **Cotizaciones**: Presupuestos para clientes
    * **Notas de Venta**: Facturación simple (SRI Ecuador)
    * **Reportes**: Generación de PDFs y links de WhatsApp
    * **Usuarios**: Gestión de usuarios del sistema (solo admin)
    * **Autenticación**: Login con JWT tokens
    """,
    version="0.2.0",
    lifespan=lifespan,
)

# Configurar CORS (permite que el frontend se comunique con el backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, cambiar por el dominio del frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar los routers (agrupar endpoints por tema)
app.include_router(auth_router)
app.include_router(clientes_router)
app.include_router(ordenes_router)
app.include_router(tecnicos_router)
app.include_router(cotizaciones_router)
app.include_router(notas_venta_router)
app.include_router(reportes_router)
app.include_router(pagos_router)
app.include_router(notas_router)
app.include_router(usuarios_router)
app.include_router(diagnosticos_router)
app.include_router(facturacion_router)
app.include_router(caja_router)
app.include_router(servicios.router)

# Manejador global de excepciones para evitar errores falsos de CORS
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    print(f"\\n[ERROR 500] Fallo en la ruta: {request.url.path}")
    traceback.print_exc()
    
    # Al retornar con Access-Control-Allow-Origin: *, evitamos que
    # el navegador oculte el error real 500 detrás de un error de CORS
    return JSONResponse(
        status_code=500,
        content={"detail": f"Error interno del servidor: {str(exc)}"},
        headers={"Access-Control-Allow-Origin": "*"}
    )


# Endpoint raíz
@app.get("/", tags=["Raíz"])
async def raiz():
    """Endpoint de prueba para verificar que la API funciona."""
    return {
        "mensaje": "Bienvenido a Orpey Servicios API",
        "version": "0.2.0",
        "documentacion": "http://127.0.0.1:8000/docs",
        "endpoints": {
            "clientes": "/api/clientes",
            "ordenes": "/api/ordenes",
            "tecnicos": "/api/tecnicos",
            "cotizaciones": "/api/cotizaciones",
            "notas_venta": "/api/notas-venta",
            "reportes": "/api/reportes",
            "auth": "/api/auth",
            "pagos": "/api/ordenes/{id}/pagos",
            "notas": "/api/ordenes/{id}/notas",
            "usuarios": "/api/usuarios",
            "facturacion": "/api/facturacion",
        }
    }


# Endpoint de salud
@app.get("/health", tags=["Sistema"])
async def health_check():
    """Verifica que la API esté funcionando correctamente."""
    return {"status": "ok", "version": "0.2.0"}
