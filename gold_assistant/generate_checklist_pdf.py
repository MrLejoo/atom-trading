# -*- coding: utf-8 -*-
"""
Generador del PDF de 1 página: Checklist Oficial de Entrada XAUUSD (FundingPips 10K)
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def build_checklist_pdf(filename="e:/Gravi/gold_assistant/Checklist_Entrada_Oro_XAUUSD.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'ChecklistTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor('#0F172A'),
        alignment=1,
        spaceAfter=4
    )

    sub_style = ParagraphStyle(
        'ChecklistSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#475569'),
        alignment=1,
        spaceAfter=8
    )

    h2_style = ParagraphStyle(
        'H2Style',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor('#1E3A8A'),
        spaceBefore=5,
        spaceAfter=3
    )

    rule_num = ParagraphStyle(
        'RuleNum',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#0F766E')
    )

    body_style = ParagraphStyle(
        'BodyTxt',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor('#1E293B')
    )

    alert_head = ParagraphStyle(
        'AlertHead',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#991B1B')
    )

    alert_txt = ParagraphStyle(
        'AlertTxt',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#7F1D1D')
    )

    story = []

    story.append(Paragraph("CHECKLIST OFICIAL DE ENTRADA: XAUUSD (ORO)", title_style))
    story.append(Paragraph("<b>Protocolo Institucional SMC / ICT para Cuenta FundingPips $10,000 USD</b><br/>Horario: 09:00 AM – 11:30 AM (Venezuela / UTC-4) | Riesgo Fijo: 0.50% ($50 USD) | Máx. 2 trades/día", sub_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1E3A8A'), spaceAfter=6))

    # Reglas en formato estructurado
    rules = [
        ("REGLA 1: FILTRO MACRO Y HORARIO", 
         "<b>Ventana Horaria:</b> La hora debe estar entre 09:00 AM y 11:30 AM (Venezuela).<br/>"
         "<b>Regla de Noticias USD:</b> Verificar el calendario de FundingPips. Prohibido abrir o cerrar trades 5 min antes y 5 min después de noticias rojas (CPI, NFP, FOMC, Powell). Si hay noticia, esperar a que pasen los 5 minutos."),
        
        ("REGLA 2: BARRIDA DE LIQUIDEZ (SWEEP / PURGE)",
         "<b>Toma de Extremo:</b> El precio debe perforar con mecha un foco de liquidez externa clave: Asian High/Low, PDH/PDL o Equal Highs/Lows.<br/>"
         "<b>Filtro de Mecha:</b> La perforación debe mostrar rechazo inmediato sin cierre de cuerpo consolidado más allá del extremo (evita operar continuaciones falsas)."),
        
        ("REGLA 3: CAMBIO DE ESTADO DE ENTREGA (CISD / MSS)",
         "<b>Desplazamiento Institucional:</b> En 1m o 5m, esperar una vela agresiva en dirección contraria a la barrida.<br/>"
         "<b>Confirmación de Cuerpo:</b> El cuerpo de la vela debe representar al menos el 50% de su rango total y anular con cierre de cuerpo la serie previa de velas que tomaron la liquidez (CISD de Fede Esses)."),
         
        ("REGLA 4: INEFICIENCIA Y ENTRADA (FVG / IFVG)",
         "<b>Fair Value Gap Visible:</b> El desplazamiento debe dejar un FVG claro de 3 velas (mínimo de vela 3 no toca máximo de vela 1 en compras, o viceversa en ventas).<br/>"
         "<b>Orden Límite:</b> Colocar Buy/Sell Limit en la apertura del FVG o en su 50% (Consequent Encroachment). Alternativa: Inverse FVG mitigado."),
         
        ("REGLA 5: VALIDACIÓN CUANTITATIVA Y SPLIT POSITIONS",
         "<b>Stop Loss Técnico:</b> Colocado a $1.00 - $1.50 dólares de cotización por encima del máximo o por debajo del mínimo de la barrida (distancia válida: entre $2.50 y $10.00 de riesgo).<br/>"
         "<b>Cálculo de Lote ($50 USD):</b> Lotes = 50 / (Distancia SL x 100).<br/>"
         "<b>Ejecución en 2 Órdenes:</b> Orden 1 (50% de lotes) a TP1 (1:1.5) -> al tocarse, asegura +$37.50 y mueve Orden 2 a Breakeven. Orden 2 (50% restante) corre libre hacia TP2 (1:3.0+).")
    ]

    for title, desc in rules:
        content = [
            Paragraph(f"<b>[ ] {title}</b>", rule_num),
            Spacer(1, 2),
            Paragraph(desc, body_style)
        ]
        t = Table([[content]], colWidths=[540])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(t)
        story.append(Spacer(1, 4))

    # Caja de advertencias / Bloqueos
    alert_content = [
        Paragraph("<b>FILTROS DE ABSTENCIÓN (PROHIBIDO OPERAR):</b>", alert_head),
        Paragraph("• Si faltan confirmaciones (menos de los 5 checks afirmativos): <b>NO SE EJECUTA</b>.<br/>"
                  "• Si ya se acumularon <b>2 pérdidas consecutivas en el día (-$100 USD = -1%)</b>: Terminal apagado hasta mañana.<br/>"
                  "• Si el spread en MT5 supera $0.45 dólares en el momento de la entrada: Esperar normalización de liquidez.<br/>"
                  "• Pasadas las 11:30 AM (Venezuela): Sesión terminada. Prohibido abrir nuevas posiciones en consolidación de mediodía.", alert_txt)
    ]
    t_alert = Table([[alert_content]], colWidths=[540])
    t_alert.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FEF2F2')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#DC2626')),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(Spacer(1, 4))
    story.append(t_alert)

    doc.build(story)
    print(f"Checklist PDF generado con éxito en: {filename}")

if __name__ == '__main__':
    build_checklist_pdf()
