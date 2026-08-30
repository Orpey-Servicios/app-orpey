"""
Generador de PDF para órdenes de servicio.

Usa ReportLab para crear PDFs profesionales con:
- Logo de Orpey Servicios
- Datos del cliente
- Datos del equipo
- Información financiera
- Términos y condiciones

El PDF se genera en memoria (no se guarda en disco).
"""

from io import BytesIO
from decimal import Decimal
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus.flowables import Flowable


# =====================================================
# COLORES DE ORPEY SERVICIOS (Basados en index.css)
# =====================================================

ORPEY_PRIMARY = HexColor("#FBC305")    # Amarillo Orpey
ORPEY_SECONDARY = HexColor("#353534")   # Gris oscuro Orpey
ORPEY_ACCENT = HexColor("#E5E7EB")      # Gris claro para bordes
ORPEY_LIGHT = HexColor("#FFF3CC")       # Amarillo suave
ORPEY_WHITE = HexColor("#ffffff")
ORPEY_GRAY = HexColor("#6B7280")
ORPEY_DARK = HexColor("#1F2937")

import os

def obtener_logo(width=140, height=45):
    """Intenta cargar el logo preservando la relación de aspecto si solo se da height."""
    posibles_rutas = [
        "/home/skorggamor/app-orpey/frontend/public/logo-orpey.png",
        "/home/skorggamor/app-orpey/datos-orpey/logo-orpey-png.png",
        "./frontend/public/logo-orpey.png",
        "../frontend/public/logo-orpey.png"
    ]
    
    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            try:
                from reportlab.lib.utils import ImageReader
                img = ImageReader(ruta)
                w, h = img.getSize()
                if h > 0:
                    aspect = w / float(h)
                    # Ya que el logo está perfectamente recortado, usamos el alto solicitado
                    actual_width = height * aspect
                    return Image(ruta, width=actual_width, height=height, kind='proportional')
                return Image(ruta, width=width, height=height, kind='proportional')
            except:
                continue
                
    return LogoOrpey(width, height)


class LogoOrpey(Flowable):
    """
    Dibuja el logo de Orpey Servicios como texto estilizado.
    Se usa cuando no hay archivo de logo PNG disponible.
    """
    def __init__(self, width=160, height=50):
        Flowable.__init__(self)
        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):
        return (self.width, self.height)

    def draw(self):
        # Fondo del logo
        self.canv.setFillColor(ORPEY_SECONDARY)
        self.canv.roundRect(0, 0, self.width, self.height, 8, fill=1, stroke=0)
        
        # Texto del logo
        self.canv.setFillColor(ORPEY_PRIMARY)
        self.canv.setFont("Helvetica-Bold", 18)
        self.canv.drawCentredString(self.width/2, self.height/2 - 6, "ORPEY")

        # Texto SERVICIOS
        self.canv.setFillColor(ORPEY_WHITE)
        self.canv.setFont("Helvetica-Bold", 10)
        self.canv.drawString(12, 6, "SERVICIOS Técnicos")


def crear_pdf_orden(orden_data, cliente_data, config_data):
    """
    Crea un PDF de orden de servicio optimizado para una sola página.
    """
    buffer = BytesIO()

    # Configurar el documento (márgenes reducidos para que quepa en una página)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=5,
        bottomMargin=20,
        title=f"Orden de Servicio {orden_data.get('numero_orden', 'N/A')}"
    )

    # Crear estilos personalizados compactos
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        'Subtitulo',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        textColor=ORPEY_SECONDARY,
        spaceBefore=10,
        spaceAfter=5,
        borderPadding=(0, 0, 2, 0),
        borderWidth=0,
        borderColor=ORPEY_GRAY
    ))

    styles.add(ParagraphStyle(
        'LabelCampo',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        textColor=ORPEY_GRAY,
        spaceAfter=0
    ))

    styles.add(ParagraphStyle(
        'ValorCampo',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=ORPEY_DARK,
        spaceAfter=2
    ))

    styles.add(ParagraphStyle(
        'MontoCampo',
        parent=styles['ValorCampo'],
        alignment=TA_RIGHT
    ))

    styles.add(ParagraphStyle(
        'Terminos',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=6.5,
        textColor=ORPEY_GRAY,
        alignment=TA_JUSTIFY,
        leading=8,
        spaceAfter=0
    ))

    contenido = []

    # =====================================================
    # ENCABEZADO (Logo y datos negocio)
    # =====================================================
    # Obtener fecha y hora
    fecha_ingreso = orden_data.get('fecha_ingreso')
    fecha_str = "N/A"
    hora_str = "N/A"
    if fecha_ingreso:
        if isinstance(fecha_ingreso, str):
            # Formato ISO: 2024-05-10T15:30:00
            try:
                dt = datetime.fromisoformat(fecha_ingreso.replace('Z', ''))
                fecha_str = dt.strftime('%d/%m/%Y')
                hora_str = dt.strftime('%H:%M')
            except:
                fecha_str = fecha_ingreso[:10]
        else:
            fecha_str = fecha_ingreso.strftime('%d/%m/%Y')
            hora_str = fecha_ingreso.strftime('%H:%M')

    # Datos del negocio y Orden en el Header
    info_header = [
        [obtener_logo(height=45),
         Paragraph(
             f"<b><font color='#353534' size='14'>SERVICIO TÉCNICO</font></b><br/>"
             f"<b><font color='#FBC305' size='12'>ORDEN DE SERVICIO N° {orden_data.get('numero_orden', 'N/A')}</font></b>",
             styles['Normal']),
         Paragraph(
             f"<b>FECHA: {fecha_str}</b><br/>"
             f"<font size='9'>HORA: {hora_str}</font>",
             ParagraphStyle('FechaH', parent=styles['Normal'], alignment=TA_RIGHT, leading=12))
        ]
    ]

    tabla_encabezado = Table(info_header, colWidths=[180, 200, 120], hAlign='LEFT')
    tabla_encabezado.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
    ]))
    contenido.append(tabla_encabezado)
    contenido.append(HRFlowable(width="100%", thickness=2, color=ORPEY_PRIMARY, spaceBefore=10, spaceAfter=8))

    # =====================================================
    # DATOS DEL CLIENTE Y GENERALES (En 2 columnas)
    # =====================================================
    datos_principales = [
        [Paragraph("<b>DATOS DEL CLIENTE</b>", styles['Subtitulo']), 
         Paragraph("<b>INFORMACIÓN ADICIONAL</b>", styles['Subtitulo'])]
    ]
    
    # Contenido columna cliente
    col_cliente = [
        f"<b>Nombre:</b> {cliente_data.get('nombre', '')} {cliente_data.get('apellido', '')}",
        f"<b>Teléfono:</b> {cliente_data.get('telefono', '')}",
        f"<b>Cédula/RUC:</b> {cliente_data.get('cedula_ruc', 'N/A')}",
        f"<b>Dirección:</b> {cliente_data.get('direccion', 'N/A')}"
    ]
    
    # Contenido columna adicional
    garantia_dias = orden_data.get('garantia_dias', 0)
    tecnico = f"{orden_data.get('tecnico_nombre', '')} {orden_data.get('tecnico_apellido', '')}".strip() or "No asignado"
    col_extra = [
        f"<b>Técnico:</b> {tecnico}",
        f"<b>Garantía:</b> {garantia_dias} días",
        f"<b>Estado:</b> {orden_data.get('estado', 'Revision').replace('_', ' ').title()}"
    ]

    max_filas = max(len(col_cliente), len(col_extra))
    for i in range(max_filas):
        c1 = col_cliente[i] if i < len(col_cliente) else ""
        c2 = col_extra[i] if i < len(col_extra) else ""
        datos_principales.append([Paragraph(c1, styles['ValorCampo']), Paragraph(c2, styles['ValorCampo'])])

    tabla_datos = Table(datos_principales, colWidths=[250, 250], hAlign='LEFT')
    tabla_datos.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 2),
        ('TOPPADDING', (0, 1), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    contenido.append(tabla_datos)

    # =====================================================
    # EQUIPOS (En tarjetas lado a lado)
    # =====================================================
    contenido.append(Paragraph("DATOS DEL EQUIPO Y DIAGNÓSTICO", styles['Subtitulo']))
    
    equipos = orden_data.get('equipos', [])
    tipo_equipo_map = {'pc_escritorio': 'PC', 'laptop': 'Laptop', 'impresora': 'Impresora', 'telefono': 'Teléfono', 'otro': 'Otro'}
    
    tarjetas_equipos = []
    for idx, eq in enumerate(equipos):
        acc = []
        if eq.get('cable'): acc.append('Cable')
        if eq.get('cargador'): acc.append('Cargador')
        acc_str = ", ".join(acc) if acc else "Ninguno"
        
        # Estructura compacta de la tarjeta
        info_eq = [
            [Paragraph(f"<b>EQUIPO {idx+1}: {tipo_equipo_map.get(eq.get('tipo_equipo'), 'Otro')}</b>", styles['LabelCampo'])],
            [Paragraph(f"<b>{eq.get('marca', 'N/A')} {eq.get('modelo', 'N/A')}</b>", styles['ValorCampo'])],
            [Paragraph(f"Accesorios: {acc_str}", styles['Terminos'])],
            [Paragraph(f"Clave: {eq.get('contrasena', 'N/A')}", styles['Terminos'])],
            [Paragraph("<b>Problema/Diagnóstico:</b>", styles['LabelCampo'])],
            [Paragraph(eq.get('descripcion_problema', ''), styles['Terminos'])],
            [Paragraph(eq.get('diagnostico', '') or eq.get('trabajo_a_realizar', '') or "Pendiente de revisión", styles['Terminos'])]
        ]
        
        t_eq = Table(info_eq, colWidths=[145])
        t_eq.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), ORPEY_LIGHT),
            ('BOX', (0, 0), (-1, -1), 0.5, ORPEY_ACCENT),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        tarjetas_equipos.append(t_eq)

    # Organizar tarjetas en filas de hasta 3
    filas_equipos = []
    for i in range(0, len(tarjetas_equipos), 3):
        fila = tarjetas_equipos[i:i+3]
        # IMPORTANTE: Rellenar la fila con celdas vacías si tiene menos de 3 equipos
        # Esto evita errores de "int() argument must be ... not 'NoneType'" en ReportLab
        while len(fila) < 3:
            fila.append(Paragraph("", styles['Normal']))
        filas_equipos.append(fila)
    
    if filas_equipos:
        tabla_cards = Table(filas_equipos, colWidths=[166, 166, 166], hAlign='LEFT')
        tabla_cards.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        contenido.append(tabla_cards)

    # =====================================================
    # DATOS FINANCIEROS (Tabla compacta)
    # =====================================================
    contenido.append(Paragraph("DATOS FINANCIEROS", styles['Subtitulo']))
    
    total = orden_data.get('total_orden', 0)
    abono = orden_data.get('abono', 0)
    pend = Decimal(str(total)) - Decimal(str(abono))

    fin_data = [
        [Paragraph("<b><font color='#FBC305'>Concepto</font></b>", styles['ValorCampo']), 
         Paragraph("<b><font color='#FBC305'>Monto</font></b>", styles['MontoCampo'])],
        [Paragraph("Total de la orden", styles['ValorCampo']), Paragraph(f"$ {total:.2f}", styles['MontoCampo'])],
        [Paragraph("Abono", styles['ValorCampo']), Paragraph(f"$ {abono:.2f}", styles['MontoCampo'])],
        [Paragraph("<b>Por cancelar</b>", styles['ValorCampo']), Paragraph(f"<b>$ {pend:.2f}</b>", styles['MontoCampo'])]
    ]

    t_fin = Table(fin_data, colWidths=[140, 80])
    t_fin.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), ORPEY_SECONDARY),
        ('GRID', (0, 0), (-1, -1), 0.5, ORPEY_ACCENT),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    
    # Colocar tabla financiera y firmas lado a lado
    firmas_data = [[
        t_fin, 
        Spacer(1,1), 
        Table([
            [Paragraph("_______________________<br/>Firma Cliente", styles['LabelCampo']),
             Paragraph("_______________________<br/>Firma Técnico", styles['LabelCampo'])]
        ], colWidths=[120, 120], hAlign='CENTER')
    ]]
    t_resumen = Table(firmas_data, colWidths=[240, 10, 250], hAlign='LEFT')
    t_resumen.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (2,0), (2,0), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    contenido.append(t_resumen)

    # =====================================================
    # TÉRMINOS Y CONDICIONES (En 2 columnas para ahorrar espacio)
    # =====================================================
    terminos_raw = config_data.get('terminos_garantia', '').split('\n')
    terminos_limpios = [t.strip() for t in terminos_raw if t.strip()]
    
    if terminos_limpios:
        contenido.append(Paragraph("TÉRMINOS Y CONDICIONES", styles['Subtitulo']))
        # Dividir términos en 2 columnas
        mitad = (len(terminos_limpios) + 1) // 2
        col1 = terminos_limpios[:mitad]
        col2 = terminos_limpios[mitad:]
        
        p_col1 = [Paragraph(f"{t}", styles['Terminos']) for t in col1]
        p_col2 = [Paragraph(f"{t}", styles['Terminos']) for t in col2]
        
        # Asegurar que las columnas no estén vacías para evitar errores de ReportLab
        if not p_col1: p_col1 = [Paragraph(" ", styles['Terminos'])]
        if not p_col2: p_col2 = [Paragraph(" ", styles['Terminos'])]
        
        t_terminos = Table([[p_col1, p_col2]], colWidths=[250, 250], hAlign='LEFT')
        t_terminos.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (0, 0), 20), # Espacio entre columnas
        ]))
        contenido.append(t_terminos)

    # Pie de página con datos de contacto mejorados
    contenido.append(Spacer(1, 10))
    contenido.append(HRFlowable(width="100%", thickness=1.5, color=ORPEY_PRIMARY, spaceBefore=10, spaceAfter=8))
    
    footer_info = [
        [
            Paragraph(f"<b>📍 Dirección:</b><br/>{config_data.get('direccion_negocio', 'Guayaquil, Bastion Popular, Bloque 2, Solar 7')}", styles['Terminos']),
            Paragraph(f"<b>📱 Whatsapp:</b><br/><font size='9' color='#353534'><b>+593 958 894 099</b></font>", styles['Terminos']),
            Paragraph(f"<b>📸 Instagram:</b> @orpey_<br/><b>👤 Facebook:</b> /orpeyservi", styles['Terminos'])
        ]
    ]
    
    t_footer = Table(footer_info, colWidths=[180, 160, 160], hAlign='LEFT')
    t_footer.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
    ]))
    contenido.append(t_footer)

    contenido.append(Spacer(1, 5))
    contenido.append(Paragraph(
        f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} | Orpey Servicios Técnicos | 🌐 orpeyservicios.com",
        ParagraphStyle('P', parent=styles['Normal'], alignment=TA_CENTER, fontSize=7, textColor=ORPEY_GRAY)
    ))

    doc.build(contenido)
    buffer.seek(0)
    return buffer



def crear_pdf_nota_venta(nota_data, orden_data, cliente_data, config_data):
    """
    Crea un PDF de nota de venta con la nueva identidad visual.
    """
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=50,
        leftMargin=50,
        topMargin=40,
        bottomMargin=40,
        title=f"Nota de Venta {nota_data.get('numero_nota', 'N/A')}"
    )

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        'SubtituloNota',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=ORPEY_SECONDARY,
        spaceBefore=15,
        spaceAfter=8,
    ))

    styles.add(ParagraphStyle(
        'ValorNota',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=ORPEY_DARK,
        spaceAfter=4
    ))

    contenido = []

    # Encabezado
    encabezado_data = [
        [obtener_logo(height=45),
         Paragraph(
             f"<b><font color='#353534' size='11'>{config_data.get('nombre_negocio', 'ORPEY SERVICIOS Técnicos')}</font></b><br/>"
             f"<font color='#6B7280' size='8'>{config_data.get('direccion_negocio', 'Guayaquil, Ecuador')}</font>",
             styles['Normal'])
        ]
    ]

    tabla_encabezado = Table(encabezado_data, colWidths=[150, 310])
    tabla_encabezado.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    contenido.append(tabla_encabezado)
    contenido.append(HRFlowable(width="100%", thickness=2, color=ORPEY_PRIMARY, spaceAfter=5))

    # Título
    contenido.append(Paragraph(
        f"<b><font color='#353534' size='16'>NOTA DE VENTA N° {nota_data.get('numero_nota', 'N/A')}</font></b>",
        styles['Normal']
    ))
    contenido.append(Spacer(1, 6))
    
    fecha_emision = nota_data.get('fecha_emision')
    if fecha_emision:
        if isinstance(fecha_emision, str):
            fecha_str = fecha_emision[:10]
        else:
            fecha_str = fecha_emision.strftime('%d/%m/%Y')
        contenido.append(Paragraph(f"<font color='#6B7280' size='9'>Fecha de emisión: {fecha_str}</font>", styles['Normal']))

    contenido.append(Spacer(1, 15))

    # Datos del cliente
    contenido.append(Paragraph("DATOS DEL CLIENTE", styles['SubtituloNota']))
    contenido.append(HRFlowable(width="100%", thickness=1, color=ORPEY_ACCENT, spaceAfter=8))

    contenido.append(Paragraph(f"<b>Nombre:</b> {cliente_data.get('nombre', '')} {cliente_data.get('apellido', '')}", styles['ValorNota']))
    contenido.append(Paragraph(f"<b>Cédula/RUC:</b> {cliente_data.get('cedula_ruc', '')}", styles['ValorNota']))
    contenido.append(Paragraph(f"<b>Teléfono:</b> {cliente_data.get('telefono', '')}", styles['ValorNota']))

    contenido.append(Spacer(1, 10))

    # Detalle del servicio
    contenido.append(Paragraph("DETALLE DEL SERVICIO", styles['SubtituloNota']))
    contenido.append(HRFlowable(width="100%", thickness=1, color=ORPEY_ACCENT, spaceAfter=8))

    tipo_equipo_map = {'pc_escritorio': 'PC', 'laptop': 'Laptop', 'impresora': 'Impresora', 'telefono': 'Teléfono', 'otro': 'Otro'}

    contenido.append(Paragraph(f"<b>Orden N°:</b> {orden_data.get('numero_orden', '')}", styles['ValorNota']))
    
    equipos = orden_data.get('equipos', [])
    for idx, eq in enumerate(equipos):
        equipo_str = f"{tipo_equipo_map.get(eq.get('tipo_equipo', ''), 'Otro')} {eq.get('marca', '')} {eq.get('modelo', '')}".strip()
        label = "<b>Equipo:</b>" if len(equipos) == 1 else f"<b>Equipo {idx+1}:</b>"
        contenido.append(Paragraph(f"{label} {equipo_str}", styles['ValorNota']))
        if eq.get('descripcion_problema'):
            contenido.append(Paragraph(f"<b>Descripción:</b> {eq.get('descripcion_problema', '')}", styles['ValorNota']))

    contenido.append(Spacer(1, 10))

    # Totales
    contenido.append(Paragraph("RESUMEN DE PAGO", styles['SubtituloNota']))
    
    subtotal = nota_data.get('subtotal', 0)
    iva = nota_data.get('iva', 0)
    total = nota_data.get('total', 0)

    # Estilos blancos para el header de la tabla
    estilo_header_nv = ParagraphStyle('HeaderNV', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=ORPEY_WHITE, spaceAfter=0)
    estilo_header_nv_r = ParagraphStyle('HeaderNVR', parent=estilo_header_nv, alignment=TA_RIGHT)
    # Estilo blanco para la fila TOTAL
    estilo_total_nv = ParagraphStyle('TotalNV', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=ORPEY_DARK, spaceAfter=0)
    estilo_total_nv_r = ParagraphStyle('TotalNVR', parent=estilo_total_nv, alignment=TA_RIGHT)

    datos_totales = [
        [Paragraph("<b>Concepto</b>", estilo_header_nv), Paragraph("<b>Valor</b>", estilo_header_nv_r)],
        ["Subtotal", f"$ {subtotal:.2f}"],
        [f"IVA ({config_data.get('iva_porcentaje', '15')}%)", f"$ {iva:.2f}"],
        [Paragraph("<b>TOTAL</b>", estilo_total_nv), Paragraph(f"<b>$ {total:.2f}</b>", estilo_total_nv_r)]
    ]

    tabla_totales = Table(datos_totales, colWidths=[280, 100])
    tabla_totales.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), ORPEY_SECONDARY),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, ORPEY_ACCENT),
        ('BACKGROUND', (0, -1), (-1, -1), ORPEY_LIGHT),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    contenido.append(tabla_totales)

    # Pie
    contenido.append(Spacer(1, 40))
    contenido.append(HRFlowable(width="100%", thickness=0.5, color=ORPEY_GRAY, spaceAfter=10))
    contenido.append(Paragraph(
        f"Gracias por confiar en {config_data.get('nombre_negocio', 'ORPEY SERVICIOS')} | orpeyservicios.com",
        ParagraphStyle('PieNota', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8, textColor=ORPEY_GRAY)
    ))

    doc.build(contenido)
    buffer.seek(0)
    return buffer

def crear_pdf_cotizacion(cotizacion_data, cliente_data, config_data):
    """Crea un PDF de cotización optimizado."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=5, bottomMargin=20,
        title=f"Cotización {cotizacion_data.get('numero_cotizacion', 'N/A')}"
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('Subtitulo', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=11, textColor=ORPEY_SECONDARY, spaceBefore=10, spaceAfter=5, borderPadding=(0, 0, 2, 0), borderWidth=0, borderColor=ORPEY_GRAY))
    styles.add(ParagraphStyle('LabelCampo', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=ORPEY_GRAY, spaceAfter=0))
    styles.add(ParagraphStyle('ValorCampo', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=ORPEY_DARK, spaceAfter=2))
    styles.add(ParagraphStyle('MontoCampo', parent=styles['ValorCampo'], alignment=TA_RIGHT))
    styles.add(ParagraphStyle('Terminos', parent=styles['Normal'], fontName='Helvetica', fontSize=6.5, textColor=ORPEY_GRAY, alignment=TA_JUSTIFY, leading=8, spaceAfter=0))

    contenido = []

    # ENCABEZADO
    fecha_creacion = cotizacion_data.get('fecha_creacion')
    fecha_str = "N/A"
    if fecha_creacion:
        try:
            if isinstance(fecha_creacion, str): fecha_str = datetime.fromisoformat(fecha_creacion.replace('Z', '')).strftime('%d/%m/%Y')
            else: fecha_str = fecha_creacion.strftime('%d/%m/%Y')
        except: fecha_str = str(fecha_creacion)[:10]

    info_header = [
        [obtener_logo(height=45),
         Paragraph(f"<b><font color='#353534' size='14'>SERVICIO TÉCNICO</font></b><br/><b><font color='#FBC305' size='12'>COTIZACIÓN N° {cotizacion_data.get('numero_cotizacion', 'N/A')}</font></b>", styles['Normal']),
         Paragraph(f"<b>FECHA: {fecha_str}</b>", ParagraphStyle('FechaH', parent=styles['Normal'], alignment=TA_RIGHT, leading=12))
        ]
    ]
    tabla_encabezado = Table(info_header, colWidths=[180, 200, 120], hAlign='LEFT')
    tabla_encabezado.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('ALIGN', (0, 0), (0, 0), 'LEFT'), ('ALIGN', (1, 0), (1, 0), 'CENTER'), ('ALIGN', (2, 0), (2, 0), 'RIGHT'), ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0), ('LEFTPADDING', (0, 0), (-1, -1), 0)]))
    contenido.append(tabla_encabezado)
    contenido.append(HRFlowable(width="100%", thickness=2, color=ORPEY_PRIMARY, spaceBefore=10, spaceAfter=8))

    # DATOS DEL CLIENTE
    datos_principales = [[Paragraph("<b>DATOS DEL CLIENTE</b>", styles['Subtitulo']), Paragraph("<b>DETALLES</b>", styles['Subtitulo'])]]
    col_cliente = [f"<b>Nombre:</b> {cliente_data.get('nombre', '')} {cliente_data.get('apellido', '')}", f"<b>Teléfono:</b> {cliente_data.get('telefono', '')}", f"<b>Cédula/RUC:</b> {cliente_data.get('cedula_ruc', 'N/A')}"]
    col_extra = [f"<b>Validez:</b> {cotizacion_data.get('validez_dias', 7)} días", f"<b>Estado:</b> {cotizacion_data.get('estado', 'Abierta').title()}"]
    
    max_filas = max(len(col_cliente), len(col_extra))
    for i in range(max_filas):
        c1 = col_cliente[i] if i < len(col_cliente) else ""
        c2 = col_extra[i] if i < len(col_extra) else ""
        datos_principales.append([Paragraph(c1, styles['ValorCampo']), Paragraph(c2, styles['ValorCampo'])])

    tabla_datos = Table(datos_principales, colWidths=[250, 250], hAlign='LEFT')
    tabla_datos.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('BOTTOMPADDING', (0, 0), (-1, 0), 2), ('TOPPADDING', (0, 1), (-1, -1), 0), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)]))
    contenido.append(tabla_datos)

    # DETALLE DE LA COTIZACIÓN (tabla unificada con totales)
    contenido.append(Paragraph("DETALLE DE LA COTIZACIÓN", styles['Subtitulo']))

    # Estilos con texto blanco para filas oscuras
    estilo_blanco = ParagraphStyle('ValorBlanco', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=ORPEY_WHITE, spaceAfter=0)
    estilo_blanco_r = ParagraphStyle('MontoBlanco', parent=estilo_blanco, alignment=TA_RIGHT)
    # Estilo para header
    estilo_header = ParagraphStyle('HeaderCot', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=ORPEY_WHITE, spaceAfter=0)
    estilo_header_r = ParagraphStyle('HeaderCotR', parent=estilo_header, alignment=TA_RIGHT)

    items = cotizacion_data.get('items', [])
    total = float(cotizacion_data.get('total', 0))
    incluye_iva = cotizacion_data.get('incluye_iva', False)
    iva_porcentaje = float(config_data.get('iva_porcentaje', 15))

    # Si no hay items pero hay descripción (cotizaciones antiguas), crear ítem sintético
    if not items:
        desc = cotizacion_data.get('descripcion', 'Servicio')
        if desc == "Cotización General":
            desc = "Servicio"
        items = [{'descripcion': desc, 'cantidad': 1, 'precio_unitario': total, 'total_item': total}]

    # Construir tabla completa: header + items + totales
    tabla_completa = []

    # Header row
    tabla_completa.append([
        Paragraph("<b>Descripción</b>", estilo_header),
        Paragraph("<b>Cant.</b>", estilo_header),
        Paragraph("<b>P. Unitario</b>", estilo_header_r),
        Paragraph("<b>Total</b>", estilo_header_r)
    ])

    # Item rows
    for it in items:
        tabla_completa.append([
            Paragraph(it.get('descripcion', ''), styles['ValorCampo']),
            Paragraph(str(it.get('cantidad', 1)), styles['ValorCampo']),
            Paragraph(f"$ {float(it.get('precio_unitario', 0)):.2f}", styles['MontoCampo']),
            Paragraph(f"$ {float(it.get('total_item', 0)):.2f}", styles['MontoCampo'])
        ])

    # Separador visual: fila vacía delgada
    num_filas_items = len(tabla_completa)

    # Filas de totales (alineadas a la derecha, columnas 2-3)
    if incluye_iva:
        subtotal = total / (1 + (iva_porcentaje / 100))
        iva = total - subtotal
        tabla_completa.append([
            Paragraph("", styles['ValorCampo']), Paragraph("", styles['ValorCampo']),
            Paragraph("<b>Subtotal</b>", styles['MontoCampo']),
            Paragraph(f"$ {subtotal:.2f}", styles['MontoCampo'])
        ])
        tabla_completa.append([
            Paragraph("", styles['ValorCampo']), Paragraph("", styles['ValorCampo']),
            Paragraph(f"<b>IVA ({int(iva_porcentaje)}%)</b>", styles['MontoCampo']),
            Paragraph(f"$ {iva:.2f}", styles['MontoCampo'])
        ])

    # Fila TOTAL (fondo oscuro, texto blanco)
    tabla_completa.append([
        Paragraph("", styles['ValorCampo']), Paragraph("", styles['ValorCampo']),
        Paragraph("<b>TOTAL</b>", estilo_blanco_r),
        Paragraph(f"<b>$ {total:.2f}</b>", estilo_blanco_r)
    ])

    t_cot = Table(tabla_completa, colWidths=[250, 50, 100, 100])
    estilos_tabla = [
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), ORPEY_SECONDARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), ORPEY_WHITE),
        # Grid general
        ('GRID', (0, 0), (-1, num_filas_items - 1), 0.5, ORPEY_ACCENT),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        # Filas items alternadas
        ('ROWBACKGROUNDS', (0, 1), (-1, num_filas_items - 1), [ORPEY_WHITE, ORPEY_LIGHT]),
        # Fila TOTAL (última fila) - fondo oscuro
        ('BACKGROUND', (2, -1), (-1, -1), ORPEY_SECONDARY),
        ('TEXTCOLOR', (2, -1), (-1, -1), ORPEY_WHITE),
        # Bordes para filas de totales
        ('LINEABOVE', (2, num_filas_items), (-1, num_filas_items), 1, ORPEY_ACCENT),
        ('GRID', (2, num_filas_items), (-1, -1), 0.5, ORPEY_ACCENT),
    ]
    t_cot.setStyle(TableStyle(estilos_tabla))
    contenido.append(t_cot)

    # FOOTER
    contenido.append(Spacer(1, 30))
    contenido.append(HRFlowable(width="100%", thickness=1.5, color=ORPEY_PRIMARY, spaceBefore=10, spaceAfter=8))
    footer_info = [[
        Paragraph(f"<b>📍 Dirección:</b><br/>{config_data.get('direccion_negocio', 'Guayaquil, Ecuador')}", styles['Terminos']),
        Paragraph(f"<b>📱 Whatsapp:</b><br/><font size='9' color='#353534'><b>+593 958 894 099</b></font>", styles['Terminos']),
        Paragraph(f"<b>📸 Instagram:</b> @orpey_<br/><b>👤 Facebook:</b> /orpeyservi", styles['Terminos'])
    ]]
    t_footer = Table(footer_info, colWidths=[180, 160, 160], hAlign='LEFT')
    contenido.append(t_footer)

    doc.build(contenido)
    buffer.seek(0)
    return buffer
