"""Generate architecture diagram SVG for app-orpey"""
import math
import xml.etree.ElementTree as ET

W, H = 1400, 900
SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
INK_NS = "http://www.inkscape.org/namespaces/inkscape"

ET.register_namespace("", SVG_NS)
ET.register_namespace("inkscape", INK_NS)
ET.register_namespace("xlink", XLINK_NS)

def ns(name):
    return name

def svg_tag(el, attrs):
    et = ET.SubElement(root, el)
    for k, v in attrs.items():
        et.set(k, str(v))
    return et

root = ET.Element(f"{{{SVG_NS}}}svg")
root.set("width", str(W))
root.set("height", str(H))
root.set("viewBox", f"0 0 {W} {H}")

def rect(x, y, w, h, **kw):
    attrs = {"x": str(x), "y": str(y), "width": str(w), "height": str(h)}
    attrs.update({k: str(v) for k, v in kw.items()})
    return svg_tag("rect", attrs)

def text(x, y, content, **kw):
    attrs = {"x": str(x), "y": str(y)}
    attrs.update({k: str(v) for k, v in kw.items()})
    el = svg_tag("text", attrs)
    el.text = str(content) if content else ""
    return el

def line(x1, y1, x2, y2, **kw):
    attrs = {"x1": str(x1), "y1": str(y1), "x2": str(x2), "y2": str(y2)}
    attrs.update({k: str(v) for k, v in kw.items()})
    return svg_tag("line", attrs)

def text_block(x, y, items, size=11, fill="#444"):
    els = []
    for i, item in enumerate(items):
        if isinstance(item, tuple):
            t, sub = item
            t_el = text(x + 6, y + i * (size + 4), t, font_size=str(size), fill=fill,
                       font_family="sans-serif", font_weight="bold")
            s_el = text(x + 6 + 6, y + (i + 0.5) * (size + 4), sub, font_size=str(size - 2),
                       fill=fill, opacity="0.8", font_family="sans-serif")
            els.extend([t_el, s_el])
        else:
            el = text(x + 6, y + i * (size + 4), item, font_size=str(size),
                     fill=fill, font_family="sans-serif")
            els.append(el)
    return els

def module_box(x, y, w, h, title, items, color="#4A90D9"):
    rect(x, y, w, h, fill=color, stroke=color, rx="6")
    text(x + w/2, y + 22, title, font_size="12", fill="#fff" if color != "#eee" else "#333",
         font_weight="bold", text_anchor="middle", font_family="sans-serif")
    if items:
        line(x+5, y+32, x+w-5, y+32, stroke="#fff", stroke_width="0.5", opacity="0.3")
        rect(x+4, y+35, w-8, h-40, fill="#fff", rx="4", opacity="0.08")
        text_block(x+4, y+50, items, fill="#fff")

# ---- Background ----
rect(0, 0, W, H, fill="#1a1a2e")
for i in range(0, W, 40):
    line(i, 0, i, H, stroke="#ffffff", stroke_width="0.2", opacity="0.03")
for i in range(0, H, 40):
    line(0, i, W, i, stroke="#ffffff", stroke_width="0.2", opacity="0.03")

# ---- Header ----
rect(50, 20, 1300, 60, fill="#16213e", stroke="#0f3460", rx="10")
text(W/2, 55, "Orpey Servicios - Arquitectura del Sistema", font_size="22",
     fill="#e0e0e0", font_weight="bold", text_anchor="middle", font_family="sans-serif")

# ---- Columns ----
col_w = 390
gap = 30
x1, x2, x3 = 50, 50 + col_w + gap, 50 + 2*(col_w + gap)
col_h = 730
col_y = 105

for cx, label in [(x1, "FRONTEND (React + Vite)"),
                   (x2, "BACKEND (FastAPI + Python)"),
                   (x3, "BASE DE DATOS (PostgreSQL)")]:
    rect(cx-5, col_y-5, col_w+10, col_h+10, fill="#0a1628", stroke="#1a3a5c", rx="8")
    text(cx + col_w/2, col_y + 15, label, font_size="11", fill="#5a7a9a",
         font_weight="bold", text_anchor="middle", font_family="sans-serif")

# ---- FRONTEND ----
fx = x1 + 10
fw = col_w - 20

module_box(fx, col_y+25, fw, 48, "Login", ["JWT Auth", "Toggle Password"], "#1a5276")
module_box(fx, col_y+80, fw, 55, "Dashboard", ["7 stats cards", "Ultimas 5 ordenes"], "#1a5276")
module_box(fx, col_y+142, fw, 72, "Ordenes de Servicio", ["Listado con filtros", "Formulario multi-equipo", "Detalle + PDF/WhatsApp"], "#2980b9")
module_box(fx, col_y+221, fw, 55, "Clientes", ["Tabla + busqueda", "Modal CRUD", "Ficha + historial"], "#2471a3")
module_box(fx, col_y+283, fw, 48, "Tecnicos", ["Cards con modal", "CRUD completo"], "#1f618d")
module_box(fx, col_y+338, fw, 55, "Cotizaciones", ["Tabla + filtros", "Aprobar presupuesto"], "#1a5276")
module_box(fx, col_y+400, fw, 55, "Notas de Venta", ["IVA Ecuador 15%", "Descarga PDF"], "#2471a3")
module_box(fx, col_y+462, fw, 48, "Usuarios", ["CRUD solo admin", "Roles: admin/tec/asis"], "#1a5276")
module_box(fx, col_y+517, fw, 72, "Componentes Compartidos", ["AuthContext (JWT)", "BarraLateral + Encabezado", "RutaProtegida (HOC)", "orpey-api.js cliente"], "#154360")
module_box(fx, col_y+605, fw, 35, "", [("", "React 18 · Vite 5 · React Router 7")], "#1b4f72")

# ---- BACKEND ----
bx = x2 + 10
bw = col_w - 20

module_box(bx, col_y+25, bw, 40, "API Gateway", ["FastAPI · Uvicorn · 30+ endpoints"], "#1e8449")
module_box(bx, col_y+72, bw, 48, "Auth Module", ["JWT · bcrypt · HS256", "POST /api/auth/login"], "#1e8449")

routers = [
    "clientes.py - CRUD + busqueda",
    "ordenes.py - CRUD + dashboard",
    "tecnicos.py - CRUD completo",
    "cotizaciones.py - aprobar",
    "notas_venta.py - PDF + IVA",
    "reportes.py - PDF + WhatsApp",
    "pagos.py - abonos x orden",
    "notas.py - notas internas",
    "usuarios.py - solo admin",
]
module_box(bx, col_y+127, bw, 168, "Routers (9 modulos)", routers, "#27ae60")
module_box(bx, col_y+302, bw, 50, "Schemas (Pydantic v2)", ["25+ schemas validacion", "Request/Response typing"], "#1e8449")
module_box(bx, col_y+359, bw, 65, "Services", ["pdf_generator.py - ReportLab", "whatsapp.py - links wa.me"], "#229954")
module_box(bx, col_y+431, bw, 48, "Utils + Auth", ["auth.py - JWT encode/decode", "get_current_user, require_roles"], "#1e8449")
module_box(bx, col_y+486, bw, 40, "Config", ["database.py - asyncpg + SQLAlchemy async"], "#1e8449")
module_box(bx, col_y+533, bw, 40, "Tests", ["pytest + pytest-asyncio + httpx"], "#1e8449")
module_box(bx, col_y+590, bw, 35, "", [("", "Python 3.12 · SQLAlchemy 2.0 · Alembic")], "#1e8449")

# ---- DATABASE ----
dx = x3 + 10
dw = col_w - 20

module_box(dx, col_y+25, dw, 40, "PostgreSQL + asyncpg", ["Conexion asincrona · PL/pgSQL"], "#a04000")
module_box(dx, col_y+72, dw, 110, "Tablas Principales", [
    "ordenes_servicio - tabla principal",
    "equipos_orden - multi-equipo",
    "clientes - 25 registros",
    "tecnicos - del taller",
    "cotizaciones - presupuestos",
    "notas_venta - facturacion",
], "#e67e22")
module_box(dx, col_y+189, dw, 80, "Tablas Secundarias", [
    "pagos_orden - historial abonos",
    "notas_orden - notas internas",
    "usuarios - 3 roles",
    "configuracion_sistema - IVA",
], "#d35400")
module_box(dx, col_y+276, dw, 95, "Features DB", [
    "Auto-numeracion ORP-0001",
    "Columna generated por_cancelar",
    "Desactivacion logica",
    "vista_dashboard - 1 query",
    "Trigger sincronizacion",
], "#ba4a00")
module_box(dx, col_y+378, dw, 65, "SQL Scripts", [
    "schema_completo.sql",
    "IMPORTAR_A_POSTGRES.sql",
    "3 migraciones SQL",
], "#a04000")
module_box(dx, col_y+450, dw, 50, "Datos Iniciales", ["25 clientes · 2 usuarios · config"], "#d35400")
module_box(dx, col_y+515, dw, 35, "", [("", "PostgreSQL 16 · asyncpg · PL/pgSQL")], "#a04000")

# ---- Arrows ----
def arrow(x1, y1, x2, y2, color="#4a90d9"):
    line(x1, y1, x2, y2, stroke=color, stroke_width="1.5", stroke_dasharray="5,3", opacity="0.4")
    ang = math.atan2(y2 - y1, x2 - x1)
    hl = 8
    line(x2, y2, x2 - hl * math.cos(ang - 0.4), y2 - hl * math.sin(ang - 0.4),
         stroke=color, stroke_width="1.5", opacity="0.4")
    line(x2, y2, x2 - hl * math.cos(ang + 0.4), y2 - hl * math.sin(ang + 0.4),
         stroke=color, stroke_width="1.5", opacity="0.4")

arrow(x1 + col_w + 3, col_y + 80, x2 - 3, col_y + 80, "#4a90d9")
arrow(x1 + col_w + 3, col_y + 180, x2 - 3, col_y + 180, "#4a90d9")
arrow(x1 + col_w + 3, col_y + 300, x2 - 3, col_y + 300, "#4a90d9")
arrow(x2 + col_w + 3, col_y + 100, x3 - 3, col_y + 100, "#e67e22")
arrow(x2 + col_w + 3, col_y + 200, x3 - 3, col_y + 200, "#e67e22")

text(x1 + col_w + gap//2, col_y + 72, "HTTP (JSON)", font_size="9", fill="#5a7a9a",
     text_anchor="middle", font_family="sans-serif")
text(x2 + col_w + gap//2, col_y + 92, "SQL async", font_size="9", fill="#5a7a9a",
     text_anchor="middle", font_family="sans-serif")

# ---- Footer ----
rect(50, H-65, 1300, 45, fill="#16213e", stroke="#0f3460", rx="10")
text(W/2, H-40, "app-orpey - Bastion, Guayaquil - Ecuador - Stack: FastAPI + React + PostgreSQL",
     font_size="11", fill="#5a7a9a", text_anchor="middle", font_family="sans-serif")

tree = ET.ElementTree(root)
tree.write("/home/skorggamor/app-orpey/arquitectura.svg", encoding="utf-8", xml_declaration=True)
print("SVG generated: /home/skorggamor/app-orpey/arquitectura.svg")
