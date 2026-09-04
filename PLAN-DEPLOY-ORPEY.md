# 🚀 PLAN DE DEPLOY — app-orpey → VPS Contabo (5.189.165.55)

> **Documento maestro de planificación.**
> Creado: 2026-09-03 | Autor: CEO Lux
> Estado: ⏳ PLANIFICADO — listo para ejecutar cuando demos luz verde
> ⚠️ El VPS está en uso por el agente de AbastoAPP. NO tocar servidor hasta avisar.

---

## 🎯 LOS 3 PASOS ANTES DEL DEPLOY (hoja de ruta de hoy después del almuerzo)

> Daniel quiere hacer esto DESPUÉS del almuerzo y ANTES de ejecutar el deploy:

1. **Implementaciones a app-orpey** — @backend-dev aplica nuevas funciones/mejoras
2. **Probar una factura REAL** — verificar emisión electrónica SRI con validez fiscal
3. **Deploy al VPS** — con buenas prácticas y aislamiento total

---

## 📋 RESUMEN EJECUTIVO

Deploy de app-orpey (FastAPI + React) junto a AbastoAPP con **aislamiento total**:

| Componente | Puerto | Red docker |
|-----------|--------|-----------|
| orpey-backend-1 (FastAPI) | Interno | orpey_net |
| orpey-db-1 (Postgres 16) | Interno (5432 NO expuesto) | orpey_net |
| orpey-nginx-1 (frontend + proxy) | **8001** (único expuesto) | orpey_net |

**Aislamiento garantizado:**
- ✅ Red docker propia `orpey_net` (no cruza con `abasto_net`)
- ✅ Base de datos independiente `orpey_db` (container propio)
- ✅ Puerto 8001 (no toca el 8000 de Abasto)
- ✅ Cero compartición de recursos

**No se toca:** AbastoAPP, su container, su BD, ni el puerto 8000.

---

## 🔍 DATOS IMPORTANTES (descubiertos hoy 03/09/2026)

### La fuente de verdad de datos es la BD LOCAL, NO los archivos SQL viejos

| Fuente | Clientes | Órdenes | Esquema | ¿Usar? |
|--------|----------|---------|---------|--------|
| `orpey_db_backup.sql` | ~25 (viejo) | pocas | **VIEJO** (`cedula`, `equipo_tipo`) | ❌ No (dump de abril) |
| `schema_completo.sql` | 25 (seed) | 0 | nuevo (ejemplo) | ❌ No (solo referencia) |
| **`orpey_db` LOCAL (corriendo)** | **41** | **21** (hasta ORP-0059) | ✅ ACTUAL | ✅ **SÍ — migrar esta** |

**BD local actual:** 41 clientes, 21 órdenes, 1 cotización, 1 nota de venta, 2 técnicos, 4 usuarios. Incluye la ORP-0021 cancelada ayer.

### Cómo migrar los datos (corrección al plan original)
En vez de usar archivos SQL viejos, hacer un **dump fresco** justo antes del deploy:
```bash
pg_dump -U skorggamor -d orpey_db > /tmp/orpey_db_fresh_dump_YYYYMMDD.sql
```
Ese dump fresco = `seed.sql` del VPS. Cero pérdida de datos.

---

## 🔒 FIXES DE SEGURIDAD PRE-DEPLOY (lecciones del deploy de Abasto)

Estos cambios se hacen **localmente** antes de subir. No tocan el VPS.

| Archivo | Cambio | Línea aprox. |
|---|---|---|
| `backend/src/utils/auth.py` | JWT SECRET_KEY desde env var (no hardcodeado) | ~32 |
| `backend/src/main.py` | CORS origins configurable (no `*`) | ~98-104 |
| `backend/src/services/facturacion_sri.py` | Ruta default `.firma_p12.pass` → `/app/firma/` | ~646 |
| `backend/src/routers/facturacion.py` | Ruta default `.p12` → configurable | ~61 |
| `backend/pyproject.toml` | Verificar dependencias (lxml, signxml, cryptography, httpx) | deps |

**Reglas de secrets:**
- JWT secret: `python3 -c "import secrets; print(secrets.token_urlsafe(64))"`
- DB password: `openssl rand -base64 32`
- NUNCA commitear `.env` a git
- `.env` en VPS con `chmod 600`

---

## 🧾 FACTURACIÓN ELECTRÓNICA REAL (prueba post-fixes, pre-deploy)

**Estado verificado (03/09/2026):** ✅ Autorizado como emisor electrónico, RUC ACTIVO, Régimen General.
**⚠️ Restricción:** permiso de facturación limitado a 3 meses (por IVA pendientes). Amplía a 12 meses al presentarlas.

**Para probar factura real:**
- Ambiente = `"2"` (producción), con `confirmar_produccion: true` (guard de seguridad)
- El container accederá al `.p12` de la firma (mount read-only en `/app/firma/`)
- Conexión SOAP saliente a `cel.sri.gob.ec:443` (producción)
- Objetivo: estado `Autorizado` con número de autorización real (49 dígitos)

**Monto a pagar factura:** depende de la orden que se facture (respetar tope consumidor final $50 si aplica).

---

## 🏗️ ESTRUCTURA DE ARCHIVOS EN EL VPS (`/opt/app-orpey/`)

```
/opt/app-orpey/
├── docker-compose.yml          # 3 services: db, backend, nginx
├── .env                        # secrets (chmod 600, NO en git)
├── backend/
│   ├── Dockerfile              # multi-stage python:3.12-slim
│   ├── pyproject.toml
│   ├── src/
│   └── seed.sql                # ← dump fresco de la BD local
├── nginx/
│   ├── nginx.conf              # reverse proxy + SPA estático
│   └── Dockerfile              # nginx:alpine
├── frontend/
│   └── dist/                   # build de Vite (ya existe en local)
└── data/pgdata/                # volumen persistente Postgres
```

---

## ✅ CHECKLIST DE DEPLOY (cuando demos luz verde)

### FASE 0 — Preparación local
- [ ] Aplicar fixes de seguridad (ver tabla de arriba)
- [ ] Confirmar implementaciones de app-orpey hechas
- [ ] Confirmar factura real probada OK
- [ ] Generar secrets nuevos (JWT + DB password) — local, no en VPS
- [ ] `pg_dump` fresco de `orpey_db` → `/tmp/orpey_db_fresh_dump.sql`
- [ ] Verificar `frontend/dist/` está actualizado (`npm run build`)
- [ ] Estructura local de deploy en `/tmp/app-orpey-deploy/`
- [ ] Commit local de todos los fixes

### FASE 1 — Preparar archivos de deploy
- [ ] Dockerfiles (backend multi-stage + nginx)
- [ ] nginx.conf (reverse proxy `/api` + SPA)
- [ ] docker-compose.yml (3 services, red orpey_net)
- [ ] .env con secrets (chmod 600)
- [ ] seed.sql = dump fresco

### FASE 2 — Subir al VPS (solo cuando el agente de Abasto termine)
- [ ] `ssh root@5.189.165.55`
- [ ] `mkdir -p /opt/app-orpey`
- [ ] `scp -r /tmp/app-orpey-deploy/* root@5.189.165.55:/opt/app-orpey/`
- [ ] `chmod 600 /opt/app-orpey/.env`

### FASE 3 — Verificar conflictos
- [ ] `docker network ls` → confirmar `orpey_net` nueva, no toca `abasto_net`
- [ ] `ss -tlnp | grep 8001` → puerto libre
- [ ] `docker compose version`

### FASE 4 — Build e imagen
- [ ] `cd /opt/app-orpey && docker compose build`
- [ ] `docker images | grep orpey`

### FASE 5 — Levantar
- [ ] `docker compose up -d`
- [ ] `docker compose ps` → 3 containers Up/healthy
- [ ] `docker ps | grep abasto` → Abasto sigue corriendo OK

### FASE 6 — Validar
- [ ] `curl http://localhost:8001/health` → `{"status":"ok",...}`
- [ ] `curl -s http://localhost:8001/` → HTML del React
- [ ] `curl http://localhost:8001/api/clientes` → JSON (o 401 si requiere token)
- [ ] `docker compose logs orpey-backend-1 --tail=50` → sin errores
- [ ] `docker exec orpey-db-1 psql -U orpey -d orpey_db -c "SELECT COUNT(*) FROM clientes;"` → **41**
- [ ] `docker exec orpey-backend-1 ls -la /app/firma/firmadigital.p12` → firma montada

### FASE 7 — Firewall
- [ ] `ufw allow 8001/tcp && ufw reload`
- [ ] `curl http://5.189.165.55:8001/health` desde fuera

### FASE 8 — Post-deploy
- [ ] Login admin OK
- [ ] Crear orden de prueba
- [ ] Facturación SRI carga el .p12 (verificar en container)
- [ ] Backup del .env en lugar seguro offline
- [ ] Documentar en `~/recordatorios-registro/`

---

## ⚠️ RIESGOS Y MITIGACIONES

| # | Riesgo | Mitigación |
|---|--------|-----------|
| 1 | Seed SQL pisa datos reales | Usar DUMP FRESCO de BD local, no archivos viejos |
| 2 | .p12 no se monta | Verificar con `docker exec`; mount read-only |
| 3 | Puerto 8001 ocupado | `ss -tlnp` antes del deploy |
| 4 | Backend no conecta a Postgres | Healthcheck de orpey-db fuerza que espere |
| 5 | Facturación falla x password del .p12 | Env var `FIRMA_P12_PASSWORD` + archivo fallback |
| 6 | UFW bloquea Docker | `ufw allow 8001/tcp` (Docker bypassa UFW por defecto) |
| 7 | CORS rechaza | Configurar `ALLOWED_ORIGINS` en .env |
| 8 | Falta lxml/signxml en container | Incluir en Dockerfile builder |

---

## 📈 MONITOREO RECOMENDADO (post-deploy)

- **Uptime Kuma**: container aparte en `/opt/uptime-kuma/`, puerto 3001
  - Monitorea `http://5.189.165.55:8001/health` (app-orpey)
  - Monitorea `http://5.189.165.55:8000/health` (Abasto)
  - Envía alertas a Telegram/WhatsApp si caen
- **Backup Postgres** (cron):
  ```bash
  0 3 * * * docker exec orpey-db-1 pg_dump -U orpey orpey_db | gzip > /opt/backups/orpey_$(date +\%Y\%m\%d).sql.gz
  ```
  Rotación 7 días.

---

## 📌 ORDEN DE TRABAJO HOY (después del almuerzo)

1. **@backend-dev**: aplicar implementaciones pedidas a app-orpey
2. **Probar factura REAL** (ambiente 2, confirmar autorización SRI)
3. **Corregir** los fixes de seguridad en local (JWT, CORS, .p12)
4. **Preparar** dump fresco + estructura de deploy
5. **Esperar** que el agente de Abasto termine en el VPS
6. **Dar luz verde** y ejecutar checklist FASE 0 → FASE 8

---

*Documento maestro creado por CEO Lux — 03/09/2026.*
*Plan base: @backend-dev (sesión 03/09/2026).*
