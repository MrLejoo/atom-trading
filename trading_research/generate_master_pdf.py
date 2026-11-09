# -*- coding: utf-8 -*-
"""
Generador Maestro del Compendio de Trading en PDF.
Sintetiza 73 videos de 3 fuentes:
1. Bootcamp 2.0 (TJR Trades) - 13 videos
2. Esses Bootcamp (Fede Esses) - 50 videos
3. Trading Strategies (The Trading Channel / Price Action Master) - 10 videos
"""

import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from pdf_canvas import NumberedCanvas

def build_pdf(filename="e:/Gravi/trading_research/Compendio_Maestro_Trading_Bootcamps_Estrategias.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=30,
        textColor=colors.HexColor('#0F172A'),
        alignment=1, # Center
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#334155'),
        alignment=1,
        spaceAfter=30
    )

    h1_style = ParagraphStyle(
        'Header1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#1E3A8A'),
        spaceBefore=18,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Header2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#0F766E'),
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )

    h3_style = ParagraphStyle(
        'Header3',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'BulletDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor('#1E293B'),
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )

    callout_alert_style = ParagraphStyle(
        'CalloutAlert',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#991B1B')
    )

    callout_alert_text = ParagraphStyle(
        'CalloutAlertText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#7F1D1D')
    )

    callout_tip_style = ParagraphStyle(
        'CalloutTip',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#166534')
    )

    callout_tip_text = ParagraphStyle(
        'CalloutTipText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#14532D')
    )

    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor('#1E293B')
    )

    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )

    story = []

    def make_alert_box(title, text):
        content = [
            Paragraph(f"<b>[DISCREPANCIA / CONTRADICCIÓN CRÍTICA] {title}</b>", callout_alert_style),
            Spacer(1, 3),
            Paragraph(text, callout_alert_text)
        ]
        t = Table([[content]], colWidths=[504])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FEF2F2')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#DC2626')),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ]))
        return t

    def make_tip_box(title, text):
        content = [
            Paragraph(f"<b>[REGLA DE ORO / CONSENSO INTEGRADO] {title}</b>", callout_tip_style),
            Spacer(1, 3),
            Paragraph(text, callout_tip_text)
        ]
        t = Table([[content]], colWidths=[504])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F0FDF4')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#16A34A')),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ]))
        return t

    # -------------------------------------------------------------
    # PORTADA
    # -------------------------------------------------------------
    story.append(Spacer(1, 40))
    story.append(Paragraph("ENCICLOPEDIA Y COMPENDIO MAESTRO DE TRADING", title_style))
    story.append(Paragraph("<b>Síntesis Integral de Bootcamps Institucionales (SMC / ICT), Psicología Operativa y Estrategias Técnicas de Alta Probabilidad</b>", subtitle_style))
    
    meta_box = [
        Paragraph("<b>Metodología de Investigación:</b> Extracción exhaustiva y minería de texto sobre 73 masterclasses y sesiones de trading en vivo.", body_style),
        Paragraph("<b>Fuentes Analizadas:</b>", body_style),
        Paragraph("• <i>Boot Camp 2.0 (TJR Trades):</i> 13 Masterclasses de ejecución en Forex/Metales/Índices y gestión cuantitativa.", bullet_style),
        Paragraph("• <i>Esses Bootcamp (Fede Esses):</i> 50 Módulos formativos desde fundamentos de velas hasta Smart Money Concepts (FVG, CISD, SMT, Quartiles, Scaling empresarial y LLC).", bullet_style),
        Paragraph("• <i>Trading Strategies Master:</i> 10 Masterclasses de Price Action puro, Gatillos de Estructura, Head & Shoulders institucional y Patrones de Velas de 7 Cifras.", bullet_style),
        Paragraph("<b>Traducción y Unificación:</b> Redactado 100% en Español técnico, fusionando conceptos idénticos para crear la versión óptima definitiva y marcando explícitamente contradicciones metodológicas y mitos populares.", body_style)
    ]
    t_meta = Table([[meta_box]], colWidths=[504])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('LEFTPADDING', (0,0), (-1,-1), 14),
        ('RIGHTPADDING', (0,0), (-1,-1), 14),
        ('TOPPADDING', (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(t_meta)
    
    story.append(Spacer(1, 30))
    story.append(Paragraph("<b>Estructura del Manual:</b>", h3_style))
    story.append(Paragraph("<b>1. MÓDULO I:</b> Fusión Máster de los Bootcamps SMC/ICT (La Mejor Versión Integrada de TJR Trades + Fede Esses).", body_style))
    story.append(Paragraph("<b>2. MÓDULO II:</b> Compendio de Estrategias Técnicas de Alta Frecuencia y Acción del Precio.", body_style))
    story.append(Paragraph("<b>3. MÓDULO III:</b> Matriz Cuantitativa de Gestión de Riesgo y Operativa en Cuentas Fondeadas.", body_style))
    story.append(Paragraph("<b>4. MÓDULO IV:</b> Psicotrading, Disciplina Táctica y Profesionalización Fiscal/Empresarial.", body_style))
    story.append(Paragraph("<b>5. MÓDULO V:</b> Auditoría Crítica de Contradicciones, Mitos y Alertas de Ejecución.", body_style))
    story.append(Paragraph("<b>6. MÓDULO VI:</b> Glosario Técnico de Términos Institucionales (A-Z).", body_style))
    
    story.append(PageBreak())

    # -------------------------------------------------------------
    # MÓDULO I: FUSIÓN MÁSTER BOOTCAMPS SMC / ICT
    # -------------------------------------------------------------
    story.append(Paragraph("MÓDULO I: FUSIÓN MÁSTER DE LOS BOOTCAMPS (SMC / ICT)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E3A8A'), spaceAfter=12))
    
    story.append(Paragraph("1.1 Fundamentos de la Liquidez y Mecánica de Subasta Interbancaria", h2_style))
    story.append(Paragraph(
        "El mercado no se mueve por capricho ni por meras líneas de soporte o resistencia minorista; se mueve en busca de <b>liquidez</b> (órdenes pendientes acumuladas: Buy Stops y Sell Stops). "
        "Tanto el Bootcamp de Fede Esses como el Bootcamp 2.0 de TJR convergen en una verdad operativa: <i>'El mercado es un algoritmo de entrega de precios diseñado para buscar liquidez o reequilibrar ineficiencias'</i>.",
        body_style
    ))
    story.append(Paragraph("<b>Las dos formas primarias de liquidez institucional:</b>", h3_style))
    story.append(Paragraph("• <b>Liquidez Externa (External Range Liquidity):</b> Máximos y mínimos clave en temporalidades mayores (Daily, 4H, 1H). Representa los máximos del día previo (PDH), mínimos del día previo (PDL), máximos semanales (PWH/PWL) o máximos/mínimos de sesiones anteriores (Asian High/Low). Los algoritmos institucionales inducen a la masa a colocar stops por encima o debajo de estos niveles para absorber contrapartida.", bullet_style))
    story.append(Paragraph("• <b>Liquidez Interna (Internal Range Liquidity):</b> Desequilibrios e ineficiencias dentro de un rango operativo previo. Tras barrer un extremo externo, el precio regresa a buscar liquidez interna representada por <i>Fair Value Gaps (FVG)</i> y <i>Order Blocks (OB)</i> no mitigados.", bullet_style))

    story.append(Spacer(1, 5))
    story.append(make_tip_box(
        "Ciclo Constante del Mercado",
        "El precio siempre oscila entre dos estados: de Liquidez Externa hacia Liquidez Interna (expansión y retroceso a Fair Value Gaps / Order Blocks), y luego desde Liquidez Interna hacia Liquidez Externa (continuación de tendencia o reversión)."
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph("1.2 Mapeo Estructural: Estructura Interna vs. Externa (BOS, CHoCH y MSS)", h2_style))
    story.append(Paragraph(
        "Uno de los mayores errores del trader novato es confundir una corrección menor con un cambio de tendencia real. La integración óptima de ambos bootcamps define con precisión:",
        body_style
    ))
    story.append(Paragraph("• <b>Estructura Externa (Swing Structure):</b> Puntos estructurales mayores (Higher Highs, Higher Lows en 4H / 1H / 15m) que determinan el <i>Order Flow</i> general. Un quiebre de estructura externa con cierre de cuerpo de vela (BOS - Break of Structure) confirma la dirección del flujo institucional.", bullet_style))
    story.append(Paragraph("• <b>Estructura Interna (Sub-structure):</b> El movimiento fractal dentro de una pierna estructural mayor (observado en 5m, 1m). Un cambio de carácter interno (CHoCH / MSS - Market Structure Shift) en temporalidad baja alerta de un retroceso hacia una zona de descuento/premium, o la culminación de un pullback para incorporarse a la tendencia mayor.", bullet_style))
    story.append(Paragraph("• <b>Validación con Cuerpo vs. Mecha:</b> Para validar un rompimiento estructural definitivo se exige <b>cierre de cuerpo de vela</b> más allá del nivel. Si solo cruza la mecha y el cuerpo cierra dentro, no es un BOS: es una <b>toma de liquidez (Sweep / Purge)</b>.", bullet_style))

    story.append(Paragraph("1.3 Ineficiencias de Mercado: Fair Value Gaps (FVG) e Inverse FVG (IFVG)", h2_style))
    story.append(Paragraph(
        "El <b>Fair Value Gap (FVG)</b> o Desequilibrio de Valor Razonable representa una entrega ineficiente de órdenes en un patrón de tres velas continuas: en una vela alcista fuerte, el mínimo de la vela 3 no se solapa con el máximo de la vela 1, dejando un vacío donde solo existió volumen comprador (BISI - Buy-side Imbalance Sell-side Inefficiency). En dirección bajista se genera un SIBI.",
        body_style
    ))
    story.append(Paragraph("<b>Uso Operativo y Refinamiento del FVG:</b>", h3_style))
    story.append(Paragraph("• <b>Consequent Encroachment (C.E. - Nivel 50%):</b> Es el punto medio del vacío. Las instituciones frecuentemente reaccionan exactamente en el 50% del FVG. Si el precio cierra con cuerpo por debajo del 50% de un FVG alcista, la ineficiencia pierde validez.", bullet_style))
    story.append(Paragraph("• <b>Inverse Fair Value Gap (IFVG):</b> Cuando un FVG previo no respeta el precio y es atravesado con violencia por el cuerpo de las velas, cambia su polaridad. Un FVG alcista violado se transforma en un IFVG de resistencia bajista instantánea, convirtiéndose en uno de los modelos de entrada de mayor fiabilidad estadística.", bullet_style))

    story.append(Paragraph("1.4 Bloques de Órdenes Institucionales (Order Blocks y Breaker Blocks)", h2_style))
    story.append(Paragraph(
        "Un <b>Order Block (OB)</b> genuino no es simplemente la última vela alcista o bajista antes de un movimiento. Para ser un bloque de alta probabilidad, debe cumplir tres filtros obligatorios:",
        body_style
    ))
    story.append(Paragraph("1. <b>Toma previa de liquidez:</b> La vela o mecha del OB debe haber barrido un máximo o mínimo previo.", bullet_style))
    story.append(Paragraph("2. <b>Generación de Desplazamiento e Ineficiencia:</b> La salida del OB debe ser agresiva y dejar un FVG visible adyacente.", bullet_style))
    story.append(Paragraph("3. <b>Rompimiento Estructural:</b> El desplazamiento generado por el bloque debe quebrar la estructura previa (BOS/MSS).", bullet_style))
    story.append(Paragraph("• <b>Breaker Block:</b> Un Order Block fallido que previamente tomó liquidez pero que luego fue vulnerado con agresividad. Al regresar a él, actúa como bloque de mitigación inverso de alta velocidad.", bullet_style))

    story.append(Paragraph("1.5 Conceptos Avanzados: CISD (Change In State of Delivery) y SMT Divergence", h2_style))
    story.append(Paragraph(
        "Fede Esses profundiza en herramientas algorítmicas clave que complementan la ejecución rápida de TJR:",
        body_style
    ))
    story.append(Paragraph("• <b>CISD (Change in State of Delivery):</b> Es la confirmación definitiva de que el algoritmo interbancario ha cambiado de estado de entrega (de alcista a bajista o viceversa). Se produce cuando la serie de velas consecutivas que precedieron a la toma de liquidez es completamente anulada y cerrada con cuerpo por la dirección contraria. Elimina la ambigüedad del CHoCH tradicional.", bullet_style))
    story.append(Paragraph("• <b>Divergencia SMT (Smart Money Tool):</b> Comparativa intermercado entre activos correlacionados (ej. EURUSD vs. GBPUSD, o ES / S&P500 vs. NQ / Nasdaq). Ocurre cuando un activo marca un nuevo máximo mientras el correlacionado falla en marcarlo (hace un Lower High). Esta anomalía delata absorción y anticipa giros violentos de mercado antes de que ocurran en el gráfico individual.", bullet_style))

    story.append(Paragraph("1.6 Killzones, Horarios Operativos y la Teoría de los Cuartos", h2_style))
    story.append(Paragraph(
        "El trading institucional está regido por el tiempo antes que por el precio. Operar fuera de las <b>Killzones</b> expone al trader a consolidaciones erráticas y manipulación de baja liquidez:",
        body_style
    ))
    story.append(Paragraph("• <b>London Killzone:</b> 02:00 AM - 05:00 AM (Hora NY / Este de EE.UU.). Caracterizada por la formación del 'Judas Swing' (falso rompimiento asiático) que genera el mínimo o máximo del día.", bullet_style))
    story.append(Paragraph("• <b>New York Open Killzone:</b> 07:00 AM - 10:00 AM (Hora NY). Mayor volumen del día. Expansión y continuación de Londres o reversión macro tras la apertura del mercado accionario de NY (09:30 AM).", bullet_style))
    story.append(Paragraph("• <b>Teoría de los Cuartos (Quarterly Theory):</b> El tiempo se divide en ciclos de 90 minutos (ciclos de 6 horas divididos en 4 fases de 90 min): Acumulación (A), Manipulación (M), Distribución (D) y Reversión/Expansión (X). Identificar el cuarto horario en el que se encuentra la sesión permite predecir cuándo vendrá la trampa y cuándo la verdadera carrera tendencial.", bullet_style))

    story.append(PageBreak())

    # -------------------------------------------------------------
    # MÓDULO II: COMPENDIO DE ESTRATEGIAS TÉCNICAS
    # -------------------------------------------------------------
    story.append(Paragraph("MÓDULO II: COMPENDIO DE ESTRATEGIAS TÉCNICAS Y ACCIÓN DEL PRECIO", h1_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E3A8A'), spaceAfter=12))

    story.append(Paragraph("2.1 Estrategia 1: Shift of Structure (MSS) + Mitigación de FVG / Breaker", h2_style))
    story.append(Paragraph(
        "Es el modelo troncal del trading contemporáneo. Combina la toma de liquidez macro con la precisión micro para obtener ratios superiores a 1:3.",
        body_style
    ))
    story.append(Paragraph("<b>Protocolo Paso a Paso de Ejecución:</b>", h3_style))
    story.append(Paragraph("1. <b>Contexto (1H/4H):</b> Esperar que el precio barre un nivel de liquidez relevante (PDH, PDL o Asian High/Low).", bullet_style))
    story.append(Paragraph("2. <b>Disparador (5m/1m):</b> Tras la barrida, esperar una vela de desplazamiento contundente que quiebre el último mínimo mayor (en caso bajista), generando un <i>Shift of Structure (MSS)</i> claro y dejando un <i>Fair Value Gap (FVG)</i>.", bullet_style))
    story.append(Paragraph("3. <b>Orden y Entrada:</b> Colocar una orden límite en la apertura o en el 50% (C.E.) del FVG.", bullet_style))
    story.append(Paragraph("4. <b>Stop Loss:</b> Protegido 1-2 pips por encima de la mecha del máximo que tomó la liquidez.", bullet_style))
    story.append(Paragraph("5. <b>Take Profit:</b> Objetivo en el siguiente grupo de liquidez opuesta (Sell-side Liquidity o mínimo del rango).", bullet_style))

    story.append(Paragraph("2.2 Estrategia 2: Break and Retest Clásico Optimizado con Confirmación de Velas", h2_style))
    story.append(Paragraph(
        "Presentada exhaustivamente en la playlist de <i>Trading Strategies</i> como la base que formó traders de 7 cifras. La versión moderna corrige los fallos del chartismo antiguo:",
        body_style
    ))
    story.append(Paragraph("<b>El Filtro de Alta Probabilidad para el Break and Retest:</b>", h3_style))
    story.append(Paragraph("• <b>Calidad del Quiebre:</b> No entrar en velas de rotura débiles o dojis. Se requiere una vela con al menos un 70% de cuerpo que cierre limpiamente fuera de la zona de soporte/resistencia horizontal clave.", bullet_style))
    story.append(Paragraph("• <b>Morfología del Re-test:</b> El precio debe retornar con volumen decreciente (velas pequeñas).", bullet_style))
    story.append(Paragraph("• <b>Vela Gatillo de Confirmación:</b> NO entrar al toque de la línea. Esperar una vela de rechazo (Hammer / Pinbar o Bullish Engulfing) que cierre a favor de la rotura. La entrada se realiza al cierre de dicha vela con Stop Loss por debajo del mínimo del rechazo.", bullet_style))

    story.append(Paragraph("2.3 Estrategia 3: Head and Shoulders (H&S) Institucional de Alta Frecuencia", h2_style))
    story.append(Paragraph(
        "Desmitificación del patrón hombro-cabeza-hombro clásico de manuales minoristas. En los mercados institucionales modernos, el patrón se interpreta bajo la lente de manipulación de liquidez:",
        body_style
    ))
    story.append(Paragraph("• <b>Hombro Izquierdo:</b> Establece el primer nivel de resistencia y el mínimo que marcará la línea de cuello (Neckline).", bullet_style))
    story.append(Paragraph("• <b>Cabeza (La Trampa Institucional):</b> Es una manipulación alcista que barre los stops de los vendedores del hombro izquierdo (Buy-side Liquidity). Una vez atrapados los compradores tardíos, el precio colapsa con violencia rompiendo la línea de cuello.", bullet_style))
    story.append(Paragraph("• <b>Hombro Derecho (La Entrada Óptima):</b> Corresponde al re-testeo de la zona del hombro izquierdo, coincidiendo habitualmente con un Order Block o nivel 61.8%-78.6% de Fibonacci. Entrada en la mitigación del hombro derecho antes de la expansión bajista masiva.", bullet_style))

    story.append(Paragraph("2.4 Estrategia 4: Patrones de Velas de Alta Fiabilidad (Engulfing & Reject Pinbars)", h2_style))
    story.append(Paragraph(
        "Las velas japonesas solo son válidas cuando se evalúan en <b>zonas de valor</b> (Key Levels / FVG / Liquidez):",
        body_style
    ))
    story.append(Paragraph("• <b>Bullish / Bearish Engulfing Institucional:</b> La vela envolvente debe devorar por completo el cuerpo y las mechas de la vela anterior con un incremento sustancial de volumen relativo. Indica absorción total del flujo contrario.", bullet_style))
    story.append(Paragraph("• <b>Mechas de Absorción (Rejection Candles):</b> Una mecha que representa más del 65% del rango total de la vela en un nivel de soporte macro señala una inyección masiva de liquidez institucional en contra de la ruptura minorista.", bullet_style))

    story.append(Paragraph("2.5 Estrategia 5: El Modelo Lifelong Strategy de Fede Esses (Futuros NQ/ES y Forex)", h2_style))
    story.append(Paragraph(
        "La estrategia definitiva de Fede Esses para cuentas de fondeo e índices americanos (Nasdaq y S&P500):",
        body_style
    ))
    story.append(Paragraph("1. Mapeo del rango asiático (08:00 PM - 00:00 AM NY) y rango de Londres.", bullet_style))
    story.append(Paragraph("2. En la sesión de New York (09:30 AM NY), identificar la toma del Asian High o Asian Low.", bullet_style))
    story.append(Paragraph("3. Esperar confirmación en 1 minuto o 5 minutos mediante <b>CISD</b> y creación de un <b>FVG</b>.", bullet_style))
    story.append(Paragraph("4. Si existe confluencia con divergencia <b>SMT</b> en el activo hermano (ES o NQ), la probabilidad sube por encima del 75%.", bullet_style))
    story.append(Paragraph("5. Salida fija en 1:2 o en la liquidez opuesta del día.", bullet_style))

    story.append(PageBreak())

    # -------------------------------------------------------------
    # MÓDULO III: GESTIÓN DE RIESGO Y CUENTAS FONDEADAS
    # -------------------------------------------------------------
    story.append(Paragraph("MÓDULO III: MATRIZ CUANTITATIVA DE GESTIÓN DE RIESGO Y PROP FIRMS", h1_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E3A8A'), spaceAfter=12))

    story.append(Paragraph("3.1 Matemáticas del Riesgo: Asimetría del Ratio Riesgo/Beneficio (RRR)", h2_style))
    story.append(Paragraph(
        "El trading es un negocio de probabilidades y distribución estadística de retornos, no de predicción infalible. "
        "La rentabilidad matemática se basa en la fórmula del <b>Valor Esperado (Expected Value - EV)</b>:",
        body_style
    ))
    story.append(Paragraph("<b>EV = (Win Rate × Ganancia Promedio) - (Loss Rate × Pérdida Promedio)</b>", h3_style))
    story.append(Paragraph(
        "Con un ratio Riesgo/Beneficio de 1:2, un trader solo necesita un 35% de acierto para ser rentable a largo plazo. "
        "Con un ratio de 1:3, requiere únicamente el 26% de acierto. Ambos bootcamps prohíben operar setups con RRR menor a 1:1.5.",
        body_style
    ))

    # Tabla de probabilidades
    prob_data = [
        [Paragraph("<b>Ratio R:B</b>", table_header), Paragraph("<b>Win Rate Mínimo (Breakeven)</b>", table_header), Paragraph("<b>Win Rate para 10% Mensual (con 20 ops)</b>", table_header), Paragraph("<b>Evaluación Táctica</b>", table_header)],
        [Paragraph("1:1", table_cell), Paragraph("50.0%", table_cell), Paragraph("60.0%", table_cell), Paragraph("No recomendado. Alta sensibilidad a comisiones.", table_cell)],
        [Paragraph("1:2", table_cell), Paragraph("33.3%", table_cell), Paragraph("45.0%", table_cell), Paragraph("Estándar óptimo para scalping y day trading.", table_cell)],
        [Paragraph("1:3", table_cell), Paragraph("25.0%", table_cell), Paragraph("37.5%", table_cell), Paragraph("Excelente para setups de Swing y Shift of Structure.", table_cell)],
        [Paragraph("1:5", table_cell), Paragraph("16.7%", table_cell), Paragraph("28.0%", table_cell), Paragraph("Alta varianza psicológica; muchas operaciones en Breakeven.", table_cell)]
    ]
    t_prob = Table(prob_data, colWidths=[80, 130, 144, 150])
    t_prob.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')])
    ]))
    story.append(t_prob)
    story.append(Spacer(1, 10))

    story.append(Paragraph("3.2 Protocolo de División de Posiciones (Split Positions y Scaling Out)", h2_style))
    story.append(Paragraph(
        "TJR Trades detalla en su día 8 una de las técnicas de preservación de capital más efectivas: <b>Split Positions</b>.",
        body_style
    ))
    story.append(Paragraph("• <b>Entrada Doble Fraccionada:</b> En lugar de abrir un lote de 1.0 en un único nivel, abrir dos órdenes de 0.50. Una en el extremo de confirmación y otra en la zona profunda de descuento del FVG.", bullet_style))
    story.append(Paragraph("• <b>TP1 Conservador + Breakeven:</b> Al alcanzar el 1:1 o 1:1.5 (primer máximo/mínimo interno), cerrar el 50% de la posición (orden 1) y mover automáticamente el Stop Loss de la posición restante a Breakeven. Esto elimina matemáticamente el riesgo de la operación.", bullet_style))
    story.append(Paragraph("• <b>Runner para TP2 y TP3:</b> La segunda mitad se deja correr hacia la liquidez mayor (1:3 o 1:4), capturando expansiones institucionales completas sin estrés emocional.", bullet_style))

    story.append(Paragraph("3.3 Gestión Específica para Empresas de Fondeo (Prop Firms)", h2_style))
    story.append(Paragraph(
        "Fede Esses (experto en cuentas de fondeo y gestión de réplica) y TJR estructuran reglas estrictas para no perder desafíos:",
        body_style
    ))
    story.append(Paragraph("• <b>Riesgo por Operación:</b> Máximo <b>0.25% a 0.50%</b> del balance total por trade. NUNCA arriesgar el 1% o 2% habitual de cuentas personales debido a los límites de Max Daily Loss (usualmente 4-5%) y Max Trailing Drawdown (8-10%).", bullet_style))
    story.append(Paragraph("• <b>Regla de Pérdida Diaria Máxima:</b> Si el trader encadena 2 pérdidas en el mismo día (-1% total), la plataforma se apaga obligatoriamente hasta el día siguiente. Queda terminantemente prohibido el 'Revenge Trading'.", bullet_style))
    story.append(Paragraph("• <b>Replicación de Cuentas (Copy Trading Institucional):</b> Para maximizar retornos sin aumentar el riesgo porcentual, operar una cuenta máster replicada en 5-10 cuentas fondeadas simultáneamente mediante software homologado (Trade Copier).", bullet_style))

    story.append(PageBreak())

    # -------------------------------------------------------------
    # MÓDULO IV: PSICOTRADING Y PROFESIONALIZACIÓN
    # -------------------------------------------------------------
    story.append(Paragraph("MÓDULO IV: PSICOTRADING, DISCIPLINA Y PROFESIONALIZACIÓN", h1_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E3A8A'), spaceAfter=12))

    story.append(Paragraph("4.1 Anatomía de la Pérdida: Cómo Aceptar un 'Red Day' sin Destruir la Cuenta", h2_style))
    story.append(Paragraph(
        "TJR Trades (Día 6 y Día 12) y Fede Esses (Día 14, 21 y 25) dedican sesiones completas a la relación mental con el stop loss: "
        "<i>'Un stop loss es el costo operativo inevitable de hacer negocios en los mercados financieros, idéntico a pagar el alquiler o la luz en una tienda física'</i>.",
        body_style
    ))
    story.append(Paragraph("<b>Los 3 tipos de pérdidas según TJR:</b>", h3_style))
    story.append(Paragraph("1. <b>Good Loss (Pérdida Buena):</b> Seguiste tu plan de trading a la perfección, tu ratio fue adecuado, respetaste el riesgo, pero la probabilidad no cayó de tu lado. Esta pérdida debe celebrarse porque refuerza tu disciplina.", bullet_style))
    story.append(Paragraph("2. <b>Bad Loss (Pérdida Mala):</b> Entraste por FOMO, sin confirmación o arriesgaste de más. Te causa dolor y remordimiento justificado.", bullet_style))
    story.append(Paragraph("3. <b>Bad Win (Ganancia Tóxica):</b> Rompiste tus reglas, sobreapalancaste la cuenta, hiciste gambling y el mercado se dio la vuelta salvándote y dándote dinero. <b>Es la más peligrosa de todas</b>, porque condiciona a tu cerebro a creer que la imprudencia es rentable.", bullet_style))

    story.append(Paragraph("4.2 Pre-Market, Rutina Operativa y Cuándo NO Operar", h2_style))
    story.append(Paragraph("<b>Filtros de abstención operativa de Fede Esses (Día 37):</b>", body_style))
    story.append(Paragraph("• <b>Noticias de Alto Impacto (NFP, CPI, Tasas FOMC):</b> No operar en los 15 minutos previos ni en los 15 minutos posteriores a noticias bancarias críticas. El ensanchamiento de spreads y los deslizamientos (*slippage*) vuelven inútil el stop loss técnico.", bullet_style))
    story.append(Paragraph("• <b>Falta de Claridad Estructural:</b> Si el gráfico Daily o de 4H está en consolidación cerrada sin toma de liquidez previa, no forzar operaciones en 1 minuto.", bullet_style))
    story.append(Paragraph("• <b>Estado Emocional Alterado:</b> Problemas personales, falta de sueño o resaca son causales inmediatas de no abrir el broker.", bullet_style))

    story.append(Paragraph("4.3 Bitácora y Diario de Trading (Trading Journal Cuantitativo)", h2_style))
    story.append(Paragraph(
        "Un trader sin journal no es un trader, es un apostador. El journal debe registrar obligatoriamente: "
        "Captura del gráfico en HTF y LTF antes y después de la entrada, activo, sesión, Killzone, tipo de setup (FVG, CISD, SMT), ratio proyectado vs. ratio ejecutado, estado emocional y error cometido.",
        body_style
    ))

    story.append(Paragraph("4.4 Estructuración Fiscal, Creación de LLC y Protección Patrimonial", h2_style))
    story.append(Paragraph(
        "Fede Esses (Día 46 y 49) añade un módulo único ausente en otros cursos: la transición de trader amateur a operador corporativo.",
        body_style
    ))
    story.append(Paragraph("• <b>Apertura de LLC en Estados Unidos (Delaware / Wyoming):</b> Permite a traders internacionales recibir pagos de Prop Firms y brokers sin bloqueos bancarios locales, optimizar la carga fiscal legalmente y separar la responsabilidad patrimonial personal.", bullet_style))
    story.append(Paragraph("• <b>Retiro y Reinversión de Ganancias:</b> Retirar periódicamente beneficios hacia cuentas bancarias corporativas o activos refugio (bienes raíces, fondos indexados) para no dejar capital ocioso en entidades de corretaje.", bullet_style))

    story.append(PageBreak())

    # -------------------------------------------------------------
    # MÓDULO V: AUDITORÍA CRÍTICA DE CONTRADICCIONES Y MITOS
    # -------------------------------------------------------------
    story.append(Paragraph("MÓDULO V: AUDITORÍA CRÍTICA DE CONTRADICCIONES, MITOS Y ALERTA DE EJECUCIÓN", h1_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#DC2626'), spaceAfter=12))

    story.append(Paragraph(
        "Durante la minería de texto y comparación cruzada entre los 3 bloques formativos, se identificaron <b>contradicciones conceptuales flagrantes</b> y <b>promesas de marketing engañosas</b>. Esta sección es vital para no caer en trampas conceptuales al operar con dinero real.",
        body_style
    ))
    story.append(Spacer(1, 4))

    # Alerta 1
    story.append(make_alert_box(
        "CONTRADICCIÓN 1: Soporte/Resistencia Clásico vs. Manipulación SMC (¿Son Válidos los Niveles Clásicos?)",
        "<b>La Contradicción:</b> La playlist de <i>Trading Strategies</i> afirma categóricamente que 'el Break and Retest de líneas de soporte y resistencia es la forma más fácil y consistente de hacer millones'. Por el contrario, <b>Fede Esses y TJR Trades</b> enseñan que las líneas de soporte y resistencia minoristas son precisamente las 'zonas de liquidez inducida' (Retail Liquidity Pool) donde las instituciones buscan colocar sus órdenes y barrer a la masa.<br/><br/>"
        "<b>Juicio Crítico y Veredicto Operativo:</b> Operar un Break & Retest clásico a ciegas en temporalidades bajas resulta en una tasa de pérdidas enorme porque la mayoría de rupturas son tomas de liquidez (falsos rompimientos). <b>Regla unificada:</b> Utilice los niveles de soporte/resistencia macro únicamente como zonas de referencia para esperar que el algoritmo barra la liquidez y genere un MSS/CISD institucional antes de entrar."
    ))
    story.append(Spacer(1, 8))

    # Alerta 2
    story.append(make_alert_box(
        "CONTRADICCIÓN 2: Rutina de Vida y Psicología (¿Disciplina Holística o 'Atarse los Zapatos'?)",
        "<b>La Contradicción:</b> En <i>Trading Strategies</i> (Video 8) el autor afirma: <i>'Si crees que meditar, llevar diario o levantarte a las 5:00 AM te hará mejor trader, estás totalmente equivocado; para mí el trading es como atarse los zapatos, opero igual sin dormir o sin bañarme'</i>. Esto choca frontalmente con <b>Fede Esses (Días 10, 20, 21, 23)</b> y <b>TJR Trades (Días 2 y 11)</b>, quienes insisten en que la psicología, el balance de vida, la meditación pre-market y el diario son el 80% del éxito en el trading profesional.<br/><br/>"
        "<b>Juicio Crítico y Veredicto Operativo:</b> La postura de 'Trading Strategies' promueve un sesgo de falsa autosuficiencia peligroso para el 99% de los traders. La falta de sueño y la indisciplina personal aumentan drásticamente el cortisol y los sesgos cognitivos, disparando el sobreapalancamiento en rachas de pérdidas."
    ))
    story.append(Spacer(1, 8))

    # Alerta 3
    story.append(make_alert_box(
        "CONTRADICCIÓN 3: Títulos Sensacionalistas de Retornos Rápidos vs. Realidad de Fondeo",
        "<b>La Contradicción:</b> Videos con títulos como <i>'How I Made $70,000 in 1 Day'</i>, <i>'Made $26,000 in 12 Hours'</i> o <i>'Turned $1,100 Into $17,000 in 1 Month'</i> transmiten la ilusión de que el trading es un vehículo de enriquecimiento instantáneo mediante retornos del 1,500% mensual. En contraposición, Fede Esses y TJR recalcan que en cuentas de fondeo institucionales una rentabilidad consistente y profesional oscila entre el <b>3% y el 8% mensual</b>.<br/><br/>"
        "<b>Juicio Crítico y Veredicto Operativo:</b> Convertir $1,100 en $17,000 en 30 días requiere arriesgar entre un 10% y 20% por operación, una conducta estadística de ruina inminente (Gambling). Nunca extrapole el tamaño de los lotes de cuentas de YouTube a una cuenta fondeada real."
    ))
    story.append(Spacer(1, 8))

    # Alerta 4
    story.append(make_alert_box(
        "CONTRADICCIÓN 4: Indicadores Técnicos Clásicos vs. Precio Puro",
        "<b>La Contradicción:</b> Mientras algunas estrategias convencionales abusan de cruces de medias móviles (EMAs), RSI y Bandas de Bollinger, los Bootcamps SMC demuestran que los indicadores técnicos son derivados atrasados del precio. <b>Veredicto:</b> El único indicador 'institucional' aceptado es el volumen real, las sesiones horarias (Killzones) y las herramientas de divergencia intermercado (SMT)."
    ))

    story.append(PageBreak())

    # -------------------------------------------------------------
    # MÓDULO VI: GLOSARIO TÉCNICO INSTITUCIONAL (A-Z)
    # -------------------------------------------------------------
    story.append(Paragraph("MÓDULO VI: GLOSARIO TÉCNICO DE TRADING INSTITUCIONAL (A-Z)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E3A8A'), spaceAfter=12))

    glossary_items = [
        ("BOS (Break of Structure)", "Rompimiento de la estructura tendencial previa validado mediante el cierre del cuerpo de una vela por encima de un Higher High o por debajo de un Lower Low."),
        ("BSL (Buy-side Liquidity)", "Foco de liquidez compradora compuesto por órdenes de stop-loss de vendedores y órdenes de compra por ruptura situadas por encima de máximos clave."),
        ("CHoCH / MSS (Change of Character / Market Structure Shift)", "Primer indicio de cambio estructural cuando el precio quiebra el último mínimo mayor en tendencia alcista o el último máximo menor en bajista."),
        ("CISD (Change in State of Delivery)", "Concepto institucional avanzado enseñado por Fede Esses. Se confirma cuando la serie de velas contrarias que generaron una toma de liquidez es absorbida y superada con cierre de cuerpo."),
        ("Draw on Liquidity (DOL)", "El imán o destino algorítmico al que el precio se dirige con mayor probabilidad (ej. un FVG diario no mitigado o la liquidez del mínimo de la semana previa)."),
        ("FVG (Fair Value Gap)", "Desequilibrio de tres velas donde la mecha de la vela 1 y la mecha de la vela 3 no se tocan, dejando un vacío de cotización entregado a una sola banda del mercado."),
        ("IFVG (Inverse Fair Value Gap)", "Fair Value Gap violado que cambia su rol y pasa de actuar como soporte a actuar como resistencia inmediata (o viceversa)."),
        ("Judas Swing", "Movimiento de manipulación inicial al inicio de la sesión de Londres o New York que barre stops minoristas justo antes de iniciar la verdadera tendencia del día."),
        ("Order Block (OB)", "Bloque de acumulación de órdenes institucionales que precedió a un movimiento impulsivo con desplazamiento, toma de liquidez y quiebre estructural."),
        ("PDH / PDL (Previous Daily High / Low)", "Máximo y mínimo del día anterior. Son los objetivos de liquidez externa más comunes en el day trading intradía."),
        ("Quarterly Theory", "Teoría algorítmica temporal que segmenta las sesiones en cuartos de 90 minutos para identificar fases de acumulación, manipulación y distribución."),
        ("Risk-Reward Ratio (RRR)", "Relación matemática entre la distancia al stop-loss y la distancia al objetivo de ganancias."),
        ("SMT (Smart Money Tool / Divergence)", "Falta de correlación simétrica entre dos activos gemelos (ej. EURUSD vs. GBPUSD) en un extremo de mercado, indicando absorción institucional previa a un giro."),
        ("SSL (Sell-side Liquidity)", "Grupo de liquidez vendedora ubicado por debajo de mínimos clave donde residen los stop-loss de los compradores."),
        ("Sweep / Purge", "Toma de liquidez en la que el precio perfora un nivel únicamente con mecha y cierra de inmediato dentro del rango previo.")
    ]

    for term, desc in glossary_items:
        story.append(Paragraph(f"<b>• {term}:</b> {desc}", body_style))

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#CBD5E1'), spaceAfter=10))
    story.append(Paragraph("<b>Fin del Compendio Técnico Oficial.</b> Documento compilado y generado automáticamente a partir del corpus analizado de 73 videos.", ParagraphStyle('EndNote', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=8, textColor=colors.HexColor('#64748B'), alignment=1)))

    print(f"Building document to {filename}...")
    doc.build(story, canvasmaker=NumberedCanvas)
    print("PDF build successful!")

if __name__ == '__main__':
    build_pdf()
