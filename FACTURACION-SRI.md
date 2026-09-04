# FACTURACIÓN ELECTRÓNICA SRI — Módulo de Orpey Servicios

> Documento maestro del módulo. Última actualización: 03/09/2026.

# ✅ VERIFICADO EN VIVO (03/09/2026) — ACTIVO PARA EMITIR FACTURAS ELECTRÓNICAS

**Resultado:** SÍ está autorizado como emisor electrónico (desde 30/11/2023). RUC ACTIVO. Régimen General (PERSONA NATURAL GENERAL) confirmado.

**⚠️ RESTRICCIÓN:** El permiso de facturación está **RESTRINGIDO a 3 MESES** (por obligaciones tributarias pendientes). Motivo: declaraciones de IVA pendientes.

**🔴 Qué lo limita (declaraciones IVA pendientes):**
1. ABRIL 2026 — ya declarado y pagado 03/09/2026 (en aprobación bancaria)
2. JUNIO 2026 — pendiente de declarar
3. JULIO 2026 — pendiente de declarar

**💡 Para ampliar permiso a 12 meses:** presentar las declaraciones pendientes. Mientras tanto puede emitir facturas con validez fiscal real respetando el período de 3 meses.

**Conclusión app-orpey:** El módulo de facturación SÍ puede pasar a producción ahora mismo con `ambiente=2`. Una vez presentadas las 3 declaraciones, el permiso se amplía a 12 meses automáticamente.

*Verificado por: @contador (agente SRI) — 03/09/2026. Detalle completo en registro Logseq.*
---
> Emisor: BALTODANO CATARINE DANIEL ABRAHAM — RUC **0964794234001** · **RÉGIMEN GENERAL** (verificado en SRI el 28/08/2026) · NO obligado a contabilidad.

---

## 🎯 Estado actual (28/08/2026)

### ✅ COMPLETADO Y VERIFICADO
- Generación de factura electrónica (XML + clave de acceso 49 dígitos + firma XAdES-BES con certificado ANFAC real).
- Validaciones de negocio: orden pagada 100% (abono ≥ total), estado `entregada` o `terminada`, anti-duplicado por orden/nota, tope consumidor final **$50.00** (régimen general).
- Transmisión SOAP al SRI (recepción + autorización) con firma WS-Security X509 usando el certificado real.
- Recepción REAL en ambiente de certificación: **RECIBIDA ✅** (el SRI valida estructura y firma sin rechazos; el bug de la leyenda RIMPE vacía quedó resuelto).
- Frontend completo: sección Facturación con 5 estados, botón "Transmitir al SRI", modal de errores del SRI, número de autorización en tabla.
- **40 tests verdes** en `backend/tests/`.
- Factura de prueba **`001-001-000000001`** transmitida con éxito el 28/08/2026 (id 13, estado `recibida`) — **dejada en BD por decisión de Daniel** como evidencia.

### ⏳ PENDIENTE PARA PRODUCCIÓN REAL (AUTORIZADO)
- La autorización NO se materializa en ambiente de certificación con certificado de producción (queda `EN PROCESO` / `numeroComprobantes=0`) — comportamiento esperado del ambiente de pruebas.
- Para emitir con **validez fiscal real** (ambiente 2 = producción) hay que primero resolver en el SRI:
  1. **Declaraciones IVA pendientes** (ver `~/recordatorios-registro/sri-declaracion-iva-2025-2026.md`): Abril, Junio y Julio 2026 (Abril/Junio/Julio según verificación del contador 28/08/2026).
  2. **Clave del portal SRI expirada** — hay que restablecerla (SRI Móvil / sitio).
  3. **Permiso de facturación** vigente solo ~3 meses — renovar/verificar.
- Una vez regularizado: transmitir una factura real de prueba en ambiente 2 → esperar `AUTORIZADO` con número de autorización real de 49 dígitos.

---

## 🏗️ Arquitectura

```
app-orpey/
├── backend/
│   ├── src/
│   │   ├── services/
│   │   │   ├── facturacion_sri.py      # Generación XML + clave acceso + firma XAdES-BES
│   │   │   └── transmision_sri.py      # SOAP al SRI: WS-Security X509, recepción + autorización
│   │   ├── routers/facturacion.py      # Endpoints REST de facturación + transmisión
│   │   ├── models/models.py            # FacturaElectronica (+ numero_autorizacion, fecha_autorizacion)
│   │   └── schemas/schemas.py          # FacturaElectronicaResponse
│   ├── migraciones/2026_08_28_autorizacion_sri.sql   # ALTER TABLE idempotente (columnas autorización)
│   └── tests/                          # test_facturacion_sri.py, test_facturacion_validaciones.py, test_transmision_sri.py
└── frontend/
    └── src/
        ├── paginas/Facturas.jsx + .css # Sección Facturación (tabla, modal, errores, filtros)
        ├── paginas/OrdenDetalle.jsx    # Botón "Factura SRI" + estado "Facturada · estado"
        ├── api/orpey-api.js            # obtenerFacturas, generarFactura, descargarXmlFactura, transmitirFactura
        ├── App.jsx                     # Ruta /facturacion
        └── componentes/BarraLateral.jsx# Item "Facturación" (icono FileCheck2)
```

### Datos del emisor (en `facturacion_sri.py`)
| Campo | Valor |
|---|---|
| RUC | 0964794234001 |
| Razón social | BALTODANO CATARINE DANIEL ABRAHAM |
| Régimen | **General** (sin leyenda RIMPE — corregido 28/08/2026) |
| Establecimiento / Punto | 001 / 001 |
| IVA | `codigo="2"`, `codigoPorcentaje="4"`, `tarifa="15"` (15% vigente) |
| Límite consumidor final | **$50.00** (`LIMITE_CONSUMIDOR_FINAL`) |

### Endpoints
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/facturacion/generar` | Genera y firma factura. Body: `{orden_servicio_id? | nota_venta_id?, ambiente?}`. Validaciones: pago 100%, estado entregada/terminada, anti-duplicado, tope $50 CF. |
| GET | `/api/facturacion/` | Lista facturas (⚠️ requiere el slash final; sin él → 307). |
| GET | `/api/facturacion/{id}/xml` | Descarga el XML firmado. |
| POST | `/api/facturacion/{id}/transmitir` | Transmite al SRI según `ambiente` de la factura. Body: `{forzar_ambiente?, confirmar_produccion?}` — **ambiente 2 exige `confirmar_produccion: true`** (guard de seguridad). |

### Estados de factura
`firmado` → (transmitir) → `recibida` → `autorizado` ✅ · o `devuelta` / `no_autorizado` ❌ (con errores del SRI en `xml_respuesta_sri`).

### Credenciales crítica (SRI)
| Dato | Valor | Dónde |
|---|---|---|
| Firma digital `.p12` | `/home/skorggamor/agente-contador/firmadigital.p12` | `configuracion_sistema.firma_p12_ruta` |
| Password firma | `Wmah7qga.` **(con punto final)** | `~/agente-contador/.firma_p12.pass` (perms 600) — NO versionar |
| Password portal SRI | `Wmah7qga8360047@` | `~/agente-contador/SESION-SRI.md` ✅ **actualizada 02/09/2026** |

---

## 🧪 Validación en vivo (28/08/2026) — RESUMEN

1. Transmisión en ambiente certificación (`celcer.sri.gob.ec`): recepción → **RECIBIDA**, mensajes vacíos ✅.
2. Autorización consultada con `claveAccesoComprobante` (campo correcto, se corrigió de `claveAcceso`): responde HTTP 200, estado `EN PROCESO`, `numeroComprobantes=0` — sin número en certificación (esperado con cert de producción).
3. Fix importante del backend: el SRI rechazaba por `campoAdicional` RIMPE vacío en `infoAdicional` → **eliminada la leyenda RIMPE** (régimen general no tiene leyenda de régimen obligatoria).
4. Bugs corregidos en `transmision_sri.py`: nombre del elemento SOAP de autorización (`claveAccesoComprobante`) y manejo de `numeroComprobantes=0` (antes crasheaba la orquestación).

---

## 🚀 Cómo retomar (checklist)

### Para continuar el desarrollo del módulo
```bash
# Backend (terminal 1)
cd ~/app-orpey/backend && ./run.sh          # uvicorn 127.0.0.1:8000 --reload

# Frontend (terminal 2)
cd ~/app-orpey/frontend && npm run dev       # http://localhost:5173

# DB
psql -U skorggamor -d orpey_db

# Tests
cd ~/app-orpey/backend && python3 -m pytest tests/ -v   # → 40 passed
```
- Si la BD es nueva/otro entorno: ejecutar `backend/migraciones/2026_08_28_autorizacion_sri.sql` (agrega `numero_autorizacion` + `fecha_autorizacion`; el backend NO usa Alembic y `create_all` no altera tablas existentes).

### Para emitir una factura REAL (validez fiscal)
1. ⚠️ Resolver primero: IVA pendientes + clave expirada + permiso de facturación (ver recordatorios).
2. En la UI: Orden → botón "Factura SRI" (o sección Facturación → Generar Factura).
3. En Facturación → botón "Transmitir al SRI". Para ambiente producción el sistema pedirá confirmación extra.
4. Objetivo: estado `Autorizado` con número de autorización de 49 dígitos + fecha.

### Para replicar este módulo en otros proyectos
- Copiar: `facturacion_sri.py`, `transmision_sri.py`, router `facturacion.py`, modelos/schemas, migración SQL, y la UI (`Facturas.jsx/css`, `orpey-api.js`, rutas).
- Cambiar: datos del emisor en `FACTURACION_SRI_EMISOR` (o `configuracion_sistema`), ruta del `.p12` + password, validaciones según régimen.
- El módulo es agnóstico del frontend: la transmisión SOAP se puede llamar desde cualquier cliente vía el endpoint REST.

---

## 🐞 Notas / deudas técnicas
- `npm run lint` del frontend ya fallaba en TODO el proyecto antes de estos cambios (prop-types/unused en todas las páginas) — no es regresión.
- Si el SRI cambia WSDLs, los URLs están en `transmision_sri.py` (pruebas `celcer.*`, producción `cel.*`).
- El módulo de notas de venta (físicas) sigue existiendo — para este emisor (régimen general) la emisión debe ser electrónica; las notas de venta quedan para otros usos/productos.
- Ambiente default de generación: `"1"` (pruebas). Para producción real debe pasarse `"2"` (con confirmación).

*Creado por: CEO Lux — 28/08/2026. Colaboraron: @contador (verificación régimen), @backend-dev (SOAP), @frontend-designer (UI).*
---

# ✅ VERIFICADO EN VIVO (29/08/2026) — Anulación de facturas (Nota de Crédito)

El botón "Anular" de la sección Facturación **funciona end-to-end** contra el SRI de certificación:
`factura recibida → anular → NC creada/transmitida → factura original marcada "anulada" → NC "recibida"`.

## Reglas del SRI confirmadas en vivo (3 rechazos reales resueltos)

| # | Error del SRI | Causa | Fix |
|---|---|---|---|
| 1 | `cvc-pattern-valid ... 'numDocModificado'` — patrón `[0-9]{3}-[0-9]{3}-[0-9]{9}` | El XML de NC ponía la **clave de acceso** en `numDocModificado` | Usar el número de documento `001-001-000000001` (NO la clave de 49 dígitos) |
| 2 | `cvc-minInclusive-valid: Value '-47.83' ... minInclusive '0.0' for type 'totalSinImpuestos'` | Los montos de la NC iban **negativos** (decisión previa del backend) | El XSD/SRI exige montos **≥ 0** en `totalSinImpuestos`/`valorModificacion`/impuestos/detalle. El tipo 04 ya identifica la NC (constante `SIGNO_NOTA_CREDITO = Decimal("1")`) |
| 3 | `cvc-minLength-valid: Value '' ... minLength '1' for type 'direccionComprador'` | Cliente **sin dirección** → campo vacío rechazado | Fallback `DIRECCION_COMPRADOR_FALLBACK = "SIN DIRECCIÓN REGISTRADA"` en facturas y NCs |

## Comportamiento del SRI que hay que conocer
- **[70] CLAVE DE ACCESO EN PROCESAMIENTO**: NO es rechazo. El SRI aún procesa el comprobante (aparece al consultar autorización justo después de RECIBIDA o al reenviar una clave). El parser lo normaliza a `EN PROCESO` (autorización) / `RECIBIDA` (recepción) y reintenta. Verificado con la NC recién emitida.
- En certificación (ambiente 1), una NC/factura RECIBIDA suele quedarse en "recibida" o "en proceso" **sin número de autorización** — es esperado (la autorización real se materializa en producción).
- El SRI rechaza NCs sobre facturas no autorizadas en *producción* (no hay sustento); en certificación la acepta en recepción. Para pruebas E2E sirve igual.
- Anulación de facturas a consumidor final (`9999999999999`): **no permitida** por Resolución NAC-DGERCGC25-00000014/-17 desde ene/2026 (pedir cédula/RUC al cliente).

## Para regenerar una factura si cambian datos del cliente
- Si un comprobante quedó "devuelta"/"no_autorizado" por estructura y se corrigió el bug, **borrar el registro y generar de nuevo** (el XML firmado se persiste una sola vez; la re-transmisión reutiliza el XML viejo).
- Pendiente (opcional, futuro): endpoint "regenerar XML" que refirme con los datos actuales.

## Estado final del QA
- Suite backend: **64 tests verdes** (incluye reglas [70], montos positivos, numDocModificado, dirección fallback).
- BD limpia tras el QA: solo queda la factura 13 (evidencia de Daniel) en estado `recibida`, ambiente pruebas.
- UI: tabla de Facturación con badges Anulada/Anulada Parcial, columna "Factura Anulada", botón **Anular** + modal (motivo obligatorio, monto parcial editable), 0 errores de consola.

*Actualizado por: CEO Lux — 29/08/2026 (QA anulación E2E).*
