"""Geração local do relatório financeiro em PDF para download imediato."""

from __future__ import annotations

from datetime import date, datetime
from html import escape
from io import BytesIO

import pandas as pd
from reportlab.graphics.charts.doughnut import Doughnut
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from utils.formatting import format_brl, format_percent


BRAND_NAVY = HexColor("#0F172A")
BRAND_BLUE = HexColor("#3B82F6")
BRAND_CYAN = HexColor("#22D3EE")
TEXT = HexColor("#172033")
MUTED = HexColor("#64748B")
SURFACE = HexColor("#F1F5F9")
SUCCESS = HexColor("#059669")
DANGER = HexColor("#DC2626")
CHART_COLORS = [
    HexColor("#3B82F6"),
    HexColor("#8B5CF6"),
    HexColor("#22D3EE"),
    HexColor("#10B981"),
    HexColor("#F59E0B"),
    HexColor("#F43F5E"),
    HexColor("#6366F1"),
    HexColor("#14B8A6"),
    HexColor("#FB7185"),
]


def _safe(value: object) -> str:
    """Escapa textos inseridos em componentes XML do ReportLab."""
    return escape(str(value or ""), quote=False)


def _styles() -> dict[str, ParagraphStyle]:
    """Define a tipografia do relatório sem depender de fontes externas."""
    sample = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "RevoTitle",
            parent=sample["Title"],
            fontName="Helvetica-Bold",
            fontSize=21,
            leading=25,
            textColor=colors.white,
            alignment=TA_LEFT,
            spaceAfter=1 * mm,
        ),
        "subtitle": ParagraphStyle(
            "RevoSubtitle",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=HexColor("#CBD5E1"),
        ),
        "section": ParagraphStyle(
            "RevoSection",
            parent=sample["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=TEXT,
            spaceBefore=4 * mm,
            spaceAfter=2.5 * mm,
        ),
        "body": ParagraphStyle(
            "RevoBody",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=TEXT,
        ),
        "small": ParagraphStyle(
            "RevoSmall",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=MUTED,
        ),
        "metric_label": ParagraphStyle(
            "MetricLabel",
            parent=sample["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=10,
            textColor=MUTED,
            alignment=TA_CENTER,
        ),
        "metric_value": ParagraphStyle(
            "MetricValue",
            parent=sample["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=TEXT,
            alignment=TA_CENTER,
        ),
        "table": ParagraphStyle(
            "TableText",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=TEXT,
        ),
    }


def _page_footer(canvas, document) -> None:
    """Inclui rodapé discreto e numeração em todas as páginas."""
    canvas.saveState()
    canvas.setStrokeColor(HexColor("#E2E8F0"))
    canvas.line(18 * mm, 13 * mm, A4[0] - 18 * mm, 13 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 8.5 * mm, "Revo — relatório financeiro pessoal")
    canvas.drawRightString(
        A4[0] - 18 * mm,
        8.5 * mm,
        f"Página {document.page}",
    )
    canvas.restoreState()


def _metric_cell(label: str, value: str, styles: dict[str, ParagraphStyle]) -> Table:
    """Cria um cartão compacto de indicador para o cabeçalho do relatório."""
    card = Table(
        [
            [Paragraph(_safe(label.upper()), styles["metric_label"])],
            [Paragraph(_safe(value), styles["metric_value"])],
        ],
        colWidths=[40 * mm],
        rowHeights=[8 * mm, 12 * mm],
    )
    card.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SURFACE),
                ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#E2E8F0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
            ]
        )
    )
    return card


def _expenses_donut(expenses: pd.DataFrame) -> Drawing | None:
    """Monta um gráfico de rosca com as despesas agregadas por categoria."""
    if expenses.empty:
        return None
    grouped = (
        expenses.groupby("Categoria", as_index=False)["Valor"]
        .sum()
        .sort_values("Valor", ascending=False)
    )
    grouped = grouped[grouped["Valor"] > 0]
    if grouped.empty:
        return None
    if len(grouped) > 6:
        other_total = float(grouped.iloc[5:]["Valor"].sum())
        grouped = pd.concat(
            [
                grouped.head(5),
                pd.DataFrame([{"Categoria": "Outras", "Valor": other_total}]),
            ],
            ignore_index=True,
        )

    total = float(grouped["Valor"].sum())
    drawing = Drawing(172 * mm, 82 * mm)
    chart = Doughnut()
    chart.x = 5 * mm
    chart.y = 7 * mm
    chart.width = 66 * mm
    chart.height = 66 * mm
    chart.innerRadiusFraction = 0.55
    chart.data = [float(value) for value in grouped["Valor"]]
    chart.labels = [
        f"{category} — {value / total:.0%}"
        for category, value in zip(grouped["Categoria"], grouped["Valor"], strict=True)
    ]
    chart.sideLabels = True
    chart.checkLabelOverlap = True
    chart.simpleLabels = False
    chart.slices.fontName = "Helvetica"
    chart.slices.fontSize = 7
    chart.slices.strokeWidth = 0.4
    chart.slices.strokeColor = colors.white
    for index in range(len(chart.data)):
        chart.slices[index].fillColor = CHART_COLORS[index % len(CHART_COLORS)]
    drawing.add(chart)
    drawing.add(
        String(
            128 * mm,
            37 * mm,
            "Despesas por categoria",
            textAnchor="middle",
            fontName="Helvetica-Bold",
            fontSize=10,
            fillColor=TEXT,
        )
    )
    drawing.add(
        String(
            128 * mm,
            29 * mm,
            format_brl(total),
            textAnchor="middle",
            fontName="Helvetica-Bold",
            fontSize=14,
            fillColor=BRAND_BLUE,
        )
    )
    return drawing


def _table(data: list[list[object]], widths: list[float], header: bool = True) -> Table:
    """Aplica o padrão visual das tabelas do relatório."""
    report_table = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.35, HexColor("#E2E8F0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 2.2 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.2 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 1.8 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8 * mm),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, HexColor("#F8FAFC")]),
    ]
    if header:
        style.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BRAND_NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 7.5),
            ]
        )
    report_table.setStyle(TableStyle(style))
    return report_table


def build_financial_report(
    user: dict,
    months: int,
    start_date: date,
    end_date: date,
    transactions: pd.DataFrame,
    holdings: pd.DataFrame,
) -> bytes:
    """Retorna um PDF com o panorama financeiro da conta no período escolhido."""
    styles = _styles()
    income = float(
        transactions.loc[transactions["Tipo"] == "Receita", "Valor"].sum()
    ) if not transactions.empty else 0.0
    expense = float(
        transactions.loc[transactions["Tipo"] == "Despesa", "Valor"].sum()
    ) if not transactions.empty else 0.0
    balance = income - expense
    savings_rate = (balance / income * 100) if income else 0.0
    portfolio_cost = (
        float((holdings["Quantidade"] * holdings["Preço médio"]).sum())
        if not holdings.empty
        else 0.0
    )

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title=f"Relatório financeiro Revo — {months} meses",
        author="Revo",
        subject="Resumo financeiro pessoal",
    )
    story: list = []

    header = Table(
        [
            [
                Paragraph("Revo", styles["title"]),
                Paragraph(
                    "RELATÓRIO FINANCEIRO<br/>"
                    f"{start_date:%d/%m/%Y} a {end_date:%d/%m/%Y}",
                    ParagraphStyle(
                        "HeaderMeta",
                        parent=styles["subtitle"],
                        alignment=2,
                    ),
                ),
            ],
            [
                Paragraph(
                    f"Panorama de {_safe(user.get('name', 'Usuário'))} — "
                    f"{_safe(user.get('email', ''))}",
                    styles["subtitle"],
                ),
                Paragraph(
                    f"Gerado em {datetime.now():%d/%m/%Y às %H:%M}",
                    ParagraphStyle(
                        "GeneratedAt",
                        parent=styles["subtitle"],
                        alignment=2,
                    ),
                ),
            ],
        ],
        colWidths=[100 * mm, 72 * mm],
    )
    header.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BRAND_NAVY),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7 * mm),
                ("TOPPADDING", (0, 0), (-1, 0), 6 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 1 * mm),
                ("TOPPADDING", (0, 1), (-1, 1), 1 * mm),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 6 * mm),
            ]
        )
    )
    story.extend([header, Spacer(1, 6 * mm)])

    metrics = Table(
        [[
            _metric_cell("Receitas", format_brl(income), styles),
            _metric_cell("Despesas", format_brl(expense), styles),
            _metric_cell("Saldo do período", format_brl(balance), styles),
            _metric_cell("Taxa de economia", format_percent(savings_rate), styles),
        ]],
        colWidths=[43 * mm] * 4,
    )
    metrics.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 1.2 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 1.2 * mm),
            ]
        )
    )
    story.extend([metrics, Spacer(1, 3 * mm)])

    expenses = transactions.loc[transactions["Tipo"] == "Despesa"] if not transactions.empty else transactions
    donut = _expenses_donut(expenses)
    if donut:
        story.extend([Paragraph("Composição das despesas", styles["section"]), donut])
    else:
        story.extend(
            [
                Paragraph("Composição das despesas", styles["section"]),
                Paragraph(
                    "Não há despesas registradas no período selecionado.",
                    styles["body"],
                ),
            ]
        )

    story.append(Paragraph("Resumo mensal", styles["section"]))
    if transactions.empty:
        story.append(Paragraph("Não há movimentações no período.", styles["body"]))
    else:
        monthly = transactions.copy()
        monthly["Mês"] = pd.to_datetime(monthly["Data"]).dt.to_period("M").astype(str)
        monthly = (
            monthly.pivot_table(
                index="Mês",
                columns="Tipo",
                values="Valor",
                aggfunc="sum",
                fill_value=0,
            )
            .reset_index()
            .sort_values("Mês")
        )
        monthly_rows = [["Mês", "Receitas", "Despesas", "Saldo"]]
        for row in monthly.itertuples(index=False):
            row_data = row._asdict()
            month_income = float(row_data.get("Receita", 0))
            month_expense = float(row_data.get("Despesa", 0))
            month_date = datetime.strptime(str(row_data["Mês"]), "%Y-%m")
            monthly_rows.append(
                [
                    month_date.strftime("%m/%Y"),
                    format_brl(month_income),
                    format_brl(month_expense),
                    format_brl(month_income - month_expense),
                ]
            )
        story.append(_table(monthly_rows, [32 * mm, 46 * mm, 46 * mm, 48 * mm]))

    story.append(Paragraph("Movimentações do período", styles["section"]))
    if transactions.empty:
        story.append(Paragraph("Nenhuma movimentação encontrada.", styles["body"]))
    else:
        recent_rows: list[list[object]] = [["Data", "Tipo", "Categoria", "Descrição", "Valor"]]
        for _, item in transactions.sort_values("Data", ascending=False).head(25).iterrows():
            item_date = pd.Timestamp(item["Data"]).date()
            recent_rows.append(
                [
                    item_date.strftime("%d/%m/%Y"),
                    _safe(item["Tipo"]),
                    _safe(item["Categoria"]),
                    Paragraph(_safe(item["Descrição"] or "—"), styles["table"]),
                    format_brl(float(item["Valor"])),
                ]
            )
        story.append(
            _table(
                recent_rows,
                [22 * mm, 21 * mm, 31 * mm, 60 * mm, 38 * mm],
            )
        )
        if len(transactions) > 25:
            story.append(
                Paragraph(
                    f"Exibindo as 25 movimentações mais recentes de {len(transactions)} registros.",
                    styles["small"],
                )
            )

    story.append(Paragraph("Portfólio virtual", styles["section"]))
    portfolio_intro = Paragraph(
        f"Custo total cadastrado: <b>{_safe(format_brl(portfolio_cost))}</b>. "
        "Os valores abaixo representam o preço médio informado e não uma cotação em tempo real.",
        styles["body"],
    )
    if holdings.empty:
        story.extend(
            [
                portfolio_intro,
                Spacer(1, 2 * mm),
                Paragraph("Nenhum investimento cadastrado.", styles["body"]),
            ]
        )
    else:
        holding_rows: list[list[object]] = [["Ativo", "Quantidade", "Preço médio", "Custo cadastrado"]]
        for _, item in holdings.iterrows():
            holding_rows.append(
                [
                    _safe(item["Ativo"]),
                    f"{float(item['Quantidade']):,.4f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    format_brl(float(item["Preço médio"])),
                    format_brl(float(item["Quantidade"] * item["Preço médio"])),
                ]
            )
        story.append(
            KeepTogether(
                [
                    portfolio_intro,
                    Spacer(1, 2 * mm),
                    _table(holding_rows, [34 * mm, 40 * mm, 48 * mm, 50 * mm]),
                ]
            )
        )

    story.extend(
        [
            Spacer(1, 5 * mm),
            Paragraph(
                "Este documento é um resumo informativo dos dados registrados pela própria pessoa usuária. "
                "Ele não constitui recomendação de investimento, orientação contábil ou aconselhamento financeiro.",
                styles["small"],
            ),
        ]
    )

    document.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return buffer.getvalue()
