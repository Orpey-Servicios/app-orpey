# 📐 ESPECIFICACIÓN — Facturación Electrónica Completa (app-orpey)

> **Objetivo:** poner el sistema de facturación 100% operativo para que Daniel facture desde la interfaz:
> generar → transmitir → autorizar → descargar PDF/XML autorizado.
> Fecha: 2026-09-03 | CEO Lux, con @backend-dev y @frontend-designer

---

## 🎯 CONTEXTO

App-orpey ya genera XML firmado (XAdES-BES) y transmite al SRI (ambiente 1 pruebas / 2 producción).
La factura **id=21 (ORP-0002, $30.00)** fue transmitida a **producción** y el SRI respondió **"RECIBIDA"** → estado bd `recibida`. El SRI aún procesa la autorización (puede tardar minutos-horas).

**LO QUE FALTA para que el sistema esté completo:**

1. **Descargar XML AUTORIZADO** (con número de autorización), no solo el firmado
2. **Generar PDF** de la factura (legible, formato SRI: logo, datos emisor/cliente, detalle, IVA, total, número autorización)
3. **Botón "Refrescar autorización"** en la lista de facturas (consultar estado sin retransmitir)
4. **Flujo completo en la UI**: transmitir → esperar → ver estado → descargar PDF/XML

El objetivo final es que cuando Daniel entre a la app, pueda emitir facturas reales de punta a punta.

---

## 📦 CONTRATO DE API A IMPLEMENTAR

### 1. `GET /api/facturacion/{id}/xml` — MEJORAR
**Actual:** sirve siempre `xml_firmado`.
**Nuevo:** servir el XML **autorizado** si existe (`xml_respuesta_sri` si es el XML autorizado), si no el firmado.
Filename: `<clave_acceso>.xml`.
- Si `factura.estado_sri == "autorizado"` y `xml_respuesta_sri` contiene un XML (con rastro `<comprobante>` y `numeroAutorizacion`), servir ese.
- Si no, servir `xml_firmado`.

### 2. `GET /api/facturacion/{id}/pdf` — NUEVO
Genera y devuelve el **PDF** de la factura mediante `reportlab` (ya instalado, patrón en `reportes.py`).
Response: `application/pdf`, `Content-Disposition: attachment; filename="<clave_acceso>.pdf"`.

**Contenido del PDF (formato factura SRI):**
- Logo de Orpey (buscar `frontend/dist/logo-orpey.png`, si no usar texto)
- **Emisor:** BALTODANO Catarine Daniel ABRAHAM / RUC 0964794234001, Guayaquil, Bastion Popular, Bloque 2, Solar 7. Régimen General.
- **Datos factura:** número 001-001-000000002, fecha emisión, ambiente (PRODUCCIÓN/PRUEBAS), clave de acceso (49 dígitos), número de autorización (si autorizada) + fecha.
- **Cliente:** nombre, cédula/RUC, dirección si existe.
- **Detalle:** descripción del servicio/equipo + subtotal (leer de la orden → equipos/cotización, o del XML). 
- **Totales:** Subtotal IVA 15%, IVA, Total.
- **Footer:** si está autorizada, el número de autorización prominente + "CONSULTE: https://cel.sri.gob.ec/".
- Si NO está autorizada, mostrar "DOCUMENTO SIN AUTORIZACIÓN" en rojo/pendiente.

> ⚠️ El PDF debe verse profesional. Reutilizar el patrón de `reportes.py` (SimpleDocTemplate + Platypus) y el CSS/logo de Orpey.

### 3. `GET /api/facturacion/{id}/consultar-autorizacion` — NUEVO
Consulta al SRI la autorización actual de la factura **sin retransmitir** (usar `consultar_autorizacion` de `transmision_sri.py` con el `ambiente` de la factura).
- Si el SRI devuelve `AUTORIZADO` → actualiza `estado_sri='autorizado'`, `numero_autorizacion`, `fecha_autorizacion`, y guarda `xml_autorizado` en `xml_respuesta_sri`.
- Si `EN PROCESO` → devuelve estado, no cambia.
- Si otro → actualiza estado.
- Response: `{ id, estado_sri, numero_autorizacion, fecha_autorizacion }`
- **Requiere admin** (usar `_es_admin`), igual que transmitir.

---

## 🖥️ FRONTEND (Facturas.jsx)

### Botones por fila/nombre de factura:
- **Descargar PDF** (siempre visible) → abre `/api/facturacion/{id}/pdf`
- **Descargar XML** (existente) → abre `/api/facturacion/{id}/xml`
- **Refrescar autorización** (icono de refrescar) → llama consultar-autorizacion, actualiza estado. Solo si estado es `recibida`/`en_proceso`/`firmado` (aún no autorizado).

### Estado de la tarjeta/fila:
- Si `estado_sri === "autorizado"` → badge verde "AUTORIZADO", mostrar número de autorización (corto) y enlace/descargar PDF destacado.
- Si `recibida`/`en_proceso` → badge amarillo "EN PROCESO" + botón "Refrescar".
- Si error → badge rojo + mensaje.

### Funciones API a añadir en `orpey-api.js`:
```js
// Descargar PDF factura
export function descargarPdfFactura(facturaId) {
  window.open(`${URL_BASE}/api/facturacion/${facturaId}/pdf`, '_blank');
}
// Consultar autorización
export async function consultarAutorizacion(facturaId) {
  return await hacerPeticion(`/api/facturacion/${facturaId}/consultar-autorizacion`, {
    method: 'POST',
  });
}
```

---

## 🔧 NOTAS TÉCNICAS
- Backend: `backend/src/routers/facturacion.py` (router), modelo `FacturaElectronica` en `models.py`.
- `transmision_sri.py` ya tiene `consultar_autorizacion(clave_acceso, ambiente, ruta_p12, password_p12)`.
- PDF: `reportlab>=4.0.0` ya en `pyproject.toml`, patrón en `reportes.py`. Reutilizar.
- El XML autorizado (con númeroAutorizacion) se guarda en `xml_respuesta_sri` cuando el SRI autoriza.
- Logo: `frontend/dist/logo-orpey.png` (ruta relativa desde backend podría ser `../../frontend/dist/logo-orpey.png` — verificar).

---

## ✅ CRITERIO DE ACEPTACIÓN
1. `GET /api/facturacion/{id}/xml` sirve el XML autorizado si existe.
2. `GET /api/facturacion/{id}/pdf` genera PDF con formato SRI correcto (datos emisor, cliente, detalle, IVA, total, autorización).
3. `POST /api/facturacion/{id}/consultar-autorizacion` refresca el estado contra el SRI.
4. Frontend: botones Descargar PDF / Descargar XML / Refrescar autorización funcionando.
5. El flujo completo funciona: emitir → transmitir → autorizar → descargar.

---

*Especificación v1 — CEO Lux, 03/09/2026.*

## ⚡ Mejora de Eficiencia de Autorización (2026-09-03)

### Problema detectado
El flujo de transmisión síncrono usaba solo `6 intentos × 3s = ~18s` de retry. Si el SRI tardaba más en procesar (común en temporada de declaraciones), la factura quedaba en estado "recibida" (EN PROCESO) y solo un monitor manual podía completarla.

### Solución implementada (2 capas, como sistemas certificados)

**1. Retry agresivo síncrono** (`transmision_sri.py`)
- Nueva función con `modo_agresivo=True` (default).
- Backoff variable: 2-3s (intentos 1-5) → 4s (6-15) → 6s (16-30) → 8s (31-45) → 10s (46+).
- ~10 reintentos por defecto (~30s): captura la autorización típica sin bloquear la UI.
- Si aún no autoriza, devuelve estado EN PROCESO (no es error).

**2. Worker de fondo persistente** (`worker_autorizacion.py` + systemd)
- Escanea la BD cada 45s por comprobantes en `firmado/recibida/en_proceso`.
- Consulta la autorización al SRI y actualiza la BD cuando AUTORIZADO/DEVUELTO.
- Corre como servicio `orpey-worker-autorizacion.service` (reinicia auto, sobrevive reboot).
- GARANTIZA que ninguna factura quede sin autorizar, sin bloquear la UI.

### Servicio systemd
```bash
sudo systemctl status orpey-worker-autorizacion   # estado
sudo systemctl restart orpey-worker-autorizacion  # reiniciar
sudo systemctl stop orpey-worker-autorizacion     # detener
```
Log: `/home/skorggamor/app-orpey/logs/worker_autorizacion.log`

### Resultado
- Factura id=21 (producción) siendo monitoreada automáticamente.
- Cuando el SRI la autorice, el worker actualiza la BD sola y la UI la muestra como "autorizado" con su N° de autorización.
- Futuras facturas: autorización lo antes posible (~30s síncrono) + respaldo infinito por worker.
