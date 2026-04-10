"""
PDF Report Generator
====================
Generates a comprehensive PDF report using reportlab.
"""

import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, Image, PageBreak, KeepTogether)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import pandas as pd
import numpy as np


# Color scheme
DARK_BG = colors.HexColor('#1B2838')
ACCENT_BLUE = colors.HexColor('#58a6ff')
ACCENT_GREEN = colors.HexColor('#3fb950')
ACCENT_RED = colors.HexColor('#f85149')
TEXT_COLOR = colors.HexColor('#2d2d2d')
LIGHT_GRAY = colors.HexColor('#f0f0f0')
WHITE = colors.white


def generate_pdf_report(strategy_results: dict, portfolio_results: dict,
                         all_metrics_is: list, all_metrics_oos: list = None,
                         execution_timings: dict = None,
                         output_path='output/Qode_Assignment2_Report.pdf',
                         plots_dir='output/plots'):
    """Generate the comprehensive PDF report."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Title'],
        fontSize=24, alignment=TA_CENTER, spaceAfter=12,
        textColor=DARK_BG, fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle', parent=styles['Normal'],
        fontSize=14, alignment=TA_CENTER, spaceAfter=20,
        textColor=colors.HexColor('#555555'), fontName='Helvetica'
    )
    heading1_style = ParagraphStyle(
        'CustomH1', parent=styles['Heading1'],
        fontSize=18, spaceAfter=12, spaceBefore=20,
        textColor=DARK_BG, fontName='Helvetica-Bold'
    )
    heading2_style = ParagraphStyle(
        'CustomH2', parent=styles['Heading2'],
        fontSize=14, spaceAfter=8, spaceBefore=12,
        textColor=colors.HexColor('#333333'), fontName='Helvetica-Bold'
    )
    body_style = ParagraphStyle(
        'CustomBody', parent=styles['Normal'],
        fontSize=10, spaceAfter=6, leading=14,
        textColor=TEXT_COLOR
    )
    small_style = ParagraphStyle(
        'CustomSmall', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor('#666666')
    )

    story = []
    page_width = A4[0] - 3*cm

    # ============ PAGE 1: COVER ============
    story.append(Spacer(1, 2*inch))
    story.append(Paragraph("Nifty Intraday Options Strategies", title_style))
    story.append(Paragraph("Backtest Report", title_style))
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("Qode Advisors LLP — Quant Research Analyst Assessment", subtitle_style))
    story.append(Paragraph("Author: Vinay Jogani", subtitle_style))
    story.append(Paragraph(f"Date: {datetime.now().strftime('%B %Y')}", subtitle_style))
    story.append(Spacer(1, 0.5*inch))

    # Key stats box
    combined_metrics = portfolio_results.get('combined_metrics', {})
    key_stats = [
        ['Total Strategies', '3'],
        ['Data Period', 'Oct 2024 — Mar 2026'],
        ['In-Sample', 'Oct 2024 — Oct 2025'],
        ['Out-of-Sample', 'Nov 2025 — Mar 2026'],
        ['Combined Calmar', f"{combined_metrics.get('Calmar_Ratio', 'N/A')}"],
        ['Combined Sharpe', f"{combined_metrics.get('Sharpe_Ratio', 'N/A')}"],
        ['Total Net PnL', f"Rs. {combined_metrics.get('Total_Net_PnL', 0):,.0f}"],
    ]
    stats_table = Table(key_stats, colWidths=[3*inch, 3*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_GRAY),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(stats_table)
    story.append(PageBreak())

    # ============ PAGES 2-3: EXECUTIVE SUMMARY ============
    story.append(Paragraph("1. Executive Summary", heading1_style))
    story.append(Paragraph(
        "This report presents the backtest results of three intraday Nifty options trading strategies "
        "designed to capture different market regimes: mean reversion, directional momentum, and semi-directional "
        "bias. Each strategy is backtested on 1-minute OHLCV options data from October 2024 to October 2025 (in-sample) and validated on "
        "November 2025 to March 2026 (out-of-sample). The combined portfolio is optimized for maximum "
        "Calmar ratio.",
        body_style
    ))
    story.append(Spacer(1, 0.3*inch))

    # Summary metrics table
    story.append(Paragraph("Performance Summary — In-Sample", heading2_style))
    summary_data = [['Strategy', 'CAGR', 'Max DD', 'Sharpe', 'Calmar', 'Win Rate', 'Net PnL']]
    for m in all_metrics_is:
        summary_data.append([
            m.get('Strategy', ''),
            f"{m.get('CAGR', 0):.1%}",
            f"{m.get('Max_Drawdown', 0):.1%}",
            f"{m.get('Sharpe_Ratio', 0):.2f}",
            f"{m.get('Calmar_Ratio', 0):.2f}",
            f"{m.get('Win_Rate', 0):.1%}",
            f"Rs.{m.get('Total_Net_PnL', 0):,.0f}"
        ])
    # Add combined
    summary_data.append([
        'Combined',
        f"{combined_metrics.get('CAGR', 0):.1%}",
        f"{combined_metrics.get('Max_Drawdown', 0):.1%}",
        f"{combined_metrics.get('Sharpe_Ratio', 0):.2f}",
        f"{combined_metrics.get('Calmar_Ratio', 0):.2f}",
        f"{combined_metrics.get('Win_Rate', 0):.1%}",
        f"Rs.{combined_metrics.get('Total_Net_PnL', 0):,.0f}"
    ])

    summary_table = Table(summary_data, colWidths=[1.5*inch, 0.8*inch, 0.8*inch,
                                                     0.8*inch, 0.8*inch, 0.8*inch, 1.2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('BACKGROUND', (0, -1), (-1, -1), LIGHT_GRAY),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.3*inch))

    # Combined equity curve image
    eq_curve_path = os.path.join(plots_dir, 'combined_equity_curve.png')
    if os.path.exists(eq_curve_path):
        story.append(Image(eq_curve_path, width=page_width, height=3.5*inch))
    story.append(PageBreak())

    # ============ PAGES 4-5: DATA & METHODOLOGY ============
    story.append(Paragraph("2. Data & Methodology", heading1_style))

    story.append(Paragraph("2.1 Data Source", heading2_style))
    story.append(Paragraph(
        "1-minute OHLCV data for NIFTY options sourced from Google Drive. The dataset covers "
        "October 2024 to March 2026 (~17 months) with options organized by weekly expiry dates. "
        "Each expiry folder contains CSV files for individual strike-type combinations.",
        body_style
    ))

    story.append(Paragraph("2.2 Data Processing", heading2_style))
    story.append(Paragraph(
        "Raw CSV files were parsed, standardized, and filtered to market hours (09:15-15:29). "
        "Synthetic Nifty spot prices were derived using put-call parity at each timestamp. "
        "Data was split into in-sample (Oct 2024 - Oct 2025) and out-of-sample (Nov 2025 - Mar 2026) periods.",
        body_style
    ))

    story.append(Paragraph("2.3 Transaction Cost Model", heading2_style))
    txn_data = [
        ['Component', 'Rate'],
        ['Brokerage', 'Rs. 20/order (x2 for entry+exit)'],
        ['STT', '0.0625% on sell-side premium'],
        ['Exchange charges', '0.053% on both sides'],
        ['GST', '18% on brokerage + exchange'],
        ['Slippage', 'Rs. 0.50/unit on both sides'],
    ]
    txn_table = Table(txn_data, colWidths=[2*inch, 4*inch])
    txn_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(txn_table)

    if execution_timings:
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("2.4 Execution Timing", heading2_style))
        timing_data = [['Phase', 'Time (seconds)']]
        for phase, time_s in execution_timings.items():
            timing_data.append([phase, f'{time_s:.2f}s'])
        timing_table = Table(timing_data, colWidths=[3*inch, 2*inch])
        timing_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), DARK_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ]))
        story.append(timing_table)
    story.append(PageBreak())

    # ============ PAGES 6-7: PARAMETERIZATION & OOS DEGRADATION ============
    story.append(Paragraph("2.5 Parameterization & Heuristics Justification", heading2_style))
    story.append(Paragraph(
        "Quantitative systems translate human concepts into rigid heuristics. The following parameters were strictly modeled: "
        "<b>09:15–09:45 Base Window:</b> Selected to circumvent the extreme bid-ask spread expansion and erratic liquidity natively found in the first minutes of the open. "
        "<b>1.5x Premium Stop-Loss (Mean Reversion):</b> Functionally limits Nifty's freedom to roughly a 0.75% standard deviation. A hard stop safeguards the algorithm against structural intraday tail-risks."
        "<b>Filter: Premium > Rs.5:</b> A safety block prohibiting the algorithm from selling deeply OTM penny-fractional options which carry massive synthetic gamma risk and offer no edge.",
        body_style
    ))
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph("2.6 Assumptions & Strategy Limitations", heading2_style))
    story.append(Paragraph(
        "<b>Greek Equivalency (Delta Limits):</b> For the 'Directional Breakout' system, calculating true Option Delta requires a local Black-Scholes implied-volatility surface generator. Due to execution constraints, we utilized a rigid 'Strike offset (ATM + 150)' as a proxy for Target Delta. In an institutional production environment, this would be updated to dynamically select strikes mapping to a precise ~0.25 Target Delta irrespective of the current VIX regime.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Dynamic Slippage Modeling:</b> We modeled execution slippage dynamically as max(Rs. 0.50, 1% of Option Premium). Furthermore, exits flagged explicitly as Stop-Loss triggers automatically incurred a structural +1% 'Market Order-Book Tear' penalty to mathematically simulate the reality of gap-through slippage.",
        body_style
    ))
    story.append(Spacer(1, 0.2*inch))

    story.append(Paragraph("2.7 OOS Regime Degradation & Tradability Analysis", heading2_style))
    story.append(Paragraph(
        "<b>Is it Tradable? Leveraging the Edge:</b> To render the system practically tradable, we established volatility-adjusted Dynamic Margin Sizing. Rather than deploying exactly 1 lot per signal, each strategy deploys ~90% of its Rs. 33L margin equivalent dynamically (achieving 15-20 lots intrinsically). This leverages the absolute return and mathematically dilutes the flat Rs. 20 brokerage cost to near irrelevance.",
        body_style
    ))
    story.append(Paragraph(
        "<b>OOS Divergence & Curve-Fitting Analysis:</b> A critical observation is the sharp divergence between the perfectly rising In-Sample (IS) curve and the negative drift in the Out-Of-Sample (OOS) data structure. We explicitly identify that the hardcoded temporal exits (e.g., locking profits at exactly 80%) were likely structurally over-fitted (curve-fit) to the specific trending dynamics of 2024. The failure of the Directional breakout engine OOS proves structural regime degradation (e.g., shifting toward mean-reverting tight ranges). The strategy lacks forward-walk vitality and requires adaptive regime switching before live execution.",
        body_style
    ))
    story.append(PageBreak())

    # ============ PAGES 6-15: INDIVIDUAL STRATEGY RESULTS ============
    strategy_descriptions = {
        'MeanReversion': {
            'title': 'Strategy 1: Mean Reversion (Short Straddle)',
            'concept': 'Sells ATM straddle at 09:20, profits from time decay and range-bound markets.',
            'entry': 'Sell 1 ATM CE + 1 ATM PE at 09:20',
            'exit': 'Combined SL: 1.5x entry premium. Target: 0.5x entry. Time exit: 15:15.',
            'edge': 'Theta decay provides a statistical edge. Most days, Nifty stays within the straddle range.',
            'weakness': 'Vulnerable to large intraday moves and gap openings. Loses big on trending days.'
        },
        'Directional': {
            'title': 'Strategy 2: Directional (Momentum Breakout)',
            'concept': 'Buys OTM options in the direction of the first 30-minute breakout.',
            'entry': 'Buy OTM CE (ATM+150) if Nifty up >0.5% by 09:45, or OTM PE (ATM-150) if down >0.5%.',
            'exit': 'SL: 40% of premium. Target: 100% gain. Trailing SL at 50%/80% profit levels.',
            'edge': 'Captures strong intraday trends with limited downside (premium paid).',
            'weakness': 'Many false breakouts. Low win rate compensated by large winners.'
        },
        'SemiDirectional': {
            'title': 'Strategy 3: Semi-Directional (Ratio Credit Spread)',
            'concept': 'Sells a ratio credit spread based on overnight gap and early momentum bias.',
            'entry': 'Sell 2 OTM options + Buy 1 OTM option (hedge) at 09:30.',
            'exit': 'Combined MTM SL: 2x net credit. Target: 60% of net credit.',
            'edge': 'Collects premium with directional bias while hedging tail risk.',
            'weakness': 'Loses when the market reverses strongly against the indicated bias.'
        }
    }

    for strat_name, desc in strategy_descriptions.items():
        story.append(Paragraph(desc['title'], heading1_style))

        story.append(Paragraph(f"<b>Concept:</b> {desc['concept']}", body_style))
        story.append(Paragraph(f"<b>Entry:</b> {desc['entry']}", body_style))
        story.append(Paragraph(f"<b>Exit:</b> {desc['exit']}", body_style))
        story.append(Paragraph(f"<b>Edge:</b> {desc['edge']}", body_style))
        story.append(Paragraph(f"<b>Weakness:</b> {desc['weakness']}", body_style))
        story.append(Spacer(1, 0.2*inch))

        # Find metrics for this strategy
        strat_metrics = None
        for m in all_metrics_is:
            if m.get('Strategy', '') == strat_name:
                strat_metrics = m
                break

        if strat_metrics:
            story.append(Paragraph("Performance Metrics (In-Sample)", heading2_style))
            metrics_display = [['Metric', 'Value']]
            for key in ['CAGR', 'Max_Drawdown', 'Sharpe_Ratio', 'Sortino_Ratio',
                         'Calmar_Ratio', 'Win_Rate', 'Profit_Factor', 'Payoff_Ratio',
                         'Max_Consecutive_Wins', 'Max_Consecutive_Losses',
                         'Recovery_Factor', 'Expectancy', 'Annual_Volatility',
                         'Total_Net_PnL', 'Total_Trading_Days', 'Total_Trades',
                         'Trade_Win_Rate', 'Avg_Trade_Profit', 'Avg_Trade_Loss',
                         'Avg_PnL_Per_Trade']:
                val = strat_metrics.get(key, 'N/A')
                if isinstance(val, float):
                    if key in ['CAGR', 'Max_Drawdown', 'Win_Rate', 'Annual_Volatility', 'Trade_Win_Rate']:
                        val = f"{val:.2%}"
                    elif key in ['Total_Net_PnL', 'Expectancy', 'Avg_Trade_Profit', 'Avg_Trade_Loss', 'Avg_PnL_Per_Trade']:
                        val = f"Rs.{val:,.0f}"
                    else:
                        val = f"{val:.4f}"
                metrics_display.append([key.replace('_', ' '), str(val)])

            m_table = Table(metrics_display, colWidths=[2.5*inch, 2*inch])
            m_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), DARK_BG),
                ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
            ]))
            story.append(m_table)

        story.append(PageBreak())

    # ============ PAGES 16-18: PORTFOLIO CONSTRUCTION ============
    story.append(Paragraph("3. Portfolio Construction", heading1_style))

    story.append(Paragraph("3.1 Correlation Matrix", heading2_style))
    corr_path = os.path.join(plots_dir, 'correlation_matrix.png')
    if os.path.exists(corr_path):
        story.append(Image(corr_path, width=4*inch, height=3.5*inch))

    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("3.2 Portfolio Allocation", heading2_style))
    weights = portfolio_results.get('weights', {})
    weight_data = [['Strategy', 'Weight']]
    for name, w in weights.items():
        weight_data.append([name, f'{w:.1%}'])
    w_table = Table(weight_data, colWidths=[3*inch, 2*inch])
    w_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
    ]))
    story.append(w_table)

    pie_path = os.path.join(plots_dir, 'portfolio_weights_pie.png')
    if os.path.exists(pie_path):
        story.append(Spacer(1, 0.2*inch))
        story.append(Image(pie_path, width=4*inch, height=4*inch))
    story.append(PageBreak())

    # ============ PAGES 19-21: COMBINED RESULTS ============
    story.append(Paragraph("4. Combined Portfolio Results", heading1_style))

    story.append(Paragraph("4.1 Performance Metrics", heading2_style))
    if combined_metrics:
        cm_data = [['Metric', 'Value']]
        for key in ['CAGR', 'Max_Drawdown', 'Sharpe_Ratio', 'Sortino_Ratio',
                     'Calmar_Ratio', 'Win_Rate', 'Profit_Factor', 'Recovery_Factor',
                     'Annual_Volatility', 'Total_Net_PnL', 'Total_Return_Pct',
                     'Final_NAV']:
            val = combined_metrics.get(key, 'N/A')
            if isinstance(val, float):
                if key in ['CAGR', 'Max_Drawdown', 'Win_Rate', 'Annual_Volatility']:
                    val = f"{val:.2%}"
                elif key in ['Total_Net_PnL']:
                    val = f"Rs.{val:,.0f}"
                else:
                    val = f"{val:.4f}"
            cm_data.append([key.replace('_', ' '), str(val)])

        cm_table = Table(cm_data, colWidths=[2.5*inch, 2*inch])
        cm_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), DARK_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ]))
        story.append(cm_table)

    story.append(Spacer(1, 0.3*inch))
    dd_path = os.path.join(plots_dir, 'combined_drawdown.png')
    if os.path.exists(dd_path):
        story.append(Paragraph("4.2 Drawdown", heading2_style))
        story.append(Image(dd_path, width=page_width, height=3*inch))

    story.append(PageBreak())

    # OOS comparison
    if all_metrics_oos:
        story.append(Paragraph("4.3 In-Sample vs Out-of-Sample", heading2_style))
        comp_data = [['Strategy', 'IS Sharpe', 'OOS Sharpe', 'IS Calmar', 'OOS Calmar']]
        for m_is in all_metrics_is:
            name = m_is.get('Strategy', '')
            m_oos = next((m for m in all_metrics_oos if m.get('Strategy', '') == name), {})
            comp_data.append([
                name,
                f"{m_is.get('Sharpe_Ratio', 0):.2f}",
                f"{m_oos.get('Sharpe_Ratio', 'N/A')}",
                f"{m_is.get('Calmar_Ratio', 0):.2f}",
                f"{m_oos.get('Calmar_Ratio', 'N/A')}"
            ])
        comp_table = Table(comp_data, colWidths=[1.5*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch])
        comp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), DARK_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ]))
        story.append(comp_table)
    story.append(PageBreak())

    # ============ STRATEGY COMPARISON ============
    story.append(Paragraph("5. Strategy Comparison", heading1_style))
    comp_bar_path = os.path.join(plots_dir, 'strategy_comparison_bar.png')
    if os.path.exists(comp_bar_path):
        story.append(Image(comp_bar_path, width=page_width, height=3.5*inch))
    story.append(Spacer(1, 0.3*inch))

    cum_pnl_path = os.path.join(plots_dir, 'cumulative_pnl_rupees.png')
    if os.path.exists(cum_pnl_path):
        story.append(Image(cum_pnl_path, width=page_width, height=3.5*inch))
    story.append(PageBreak())

    # ============ RISK ANALYSIS ============
    story.append(Paragraph("6. Risk Analysis", heading1_style))

    combined_pnl = portfolio_results.get('combined_daily_pnl', pd.Series())
    if len(combined_pnl) > 0:
        story.append(Paragraph("6.1 Worst 5 Days", heading2_style))
        worst_5 = combined_pnl.nsmallest(5)
        worst_data = [['Date', 'Daily PnL']]
        for date, pnl in worst_5.items():
            worst_data.append([str(date), f'Rs.{pnl:,.0f}'])
        w5_table = Table(worst_data, colWidths=[2.5*inch, 2*inch])
        w5_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), DARK_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ]))
        story.append(w5_table)

        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("6.2 Tail Risk (Worst 5% of Days)", heading2_style))
        tail_threshold = combined_pnl.quantile(0.05)
        tail_days = combined_pnl[combined_pnl <= tail_threshold]
        story.append(Paragraph(
            f"5th percentile daily PnL: Rs.{tail_threshold:,.0f}. "
            f"Average loss on worst 5% days: Rs.{tail_days.mean():,.0f}. "
            f"Number of such days: {len(tail_days)}.",
            body_style
        ))

    dist_path = os.path.join(plots_dir, 'daily_pnl_distribution.png')
    if os.path.exists(dist_path):
        story.append(Spacer(1, 0.2*inch))
        story.append(Image(dist_path, width=page_width, height=3*inch))
    story.append(PageBreak())

    # ============ CONCLUSIONS ============
    story.append(Paragraph("7. Conclusions & Future Improvements", heading1_style))

    story.append(Paragraph("7.1 What Worked", heading2_style))
    story.append(Paragraph(
        "Mean reversion strategies (straddle) benefited from Nifty's tendency toward "
        "mean-reverting behavior on most trading days. The combined portfolio achieved diversification "
        "benefits through uncorrelated strategy returns. Aggressive position sizing (20 lots) minimized "
        "the percentage drag of flat rupee brokerage costs.",
        body_style
    ))

    story.append(Paragraph("7.2 What Didn't Work", heading2_style))
    story.append(Paragraph(
        "Directional strategies suffered from false breakouts and low win rates. "
        "Semi-directional was sensitive to bias determination accuracy.",
        body_style
    ))

    story.append(Paragraph("7.3 Future Improvements", heading2_style))
    improvements = [
        "Implement dynamic position sizing based on VIX/implied volatility levels",
        "Add regime detection (trending vs rangebound) for adaptive strategy selection",
        "Use bid-ask spread data for more accurate slippage modeling",
        "Implement intraday Greeks-based hedging for the multi-leg strategies",
        "Add machine learning for breakout signal validation",
        "Test on BankNifty and FinNifty for cross-product diversification",
    ]
    for imp in improvements:
        story.append(Paragraph(f"• {imp}", body_style))

    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("7.4 Real-World Considerations", heading2_style))
    story.append(Paragraph(
        "In live trading, execution speed is critical for the breakout strategies. API-based order "
        "placement should target <500ms latency. Liquidity may be limited for deep OTM strikes. "
        "Margin requirements will constrain position sizing for short option strategies. "
        "Regular monitoring and circuit-breaker mechanisms are essential for risk management.",
        body_style
    ))

    # Build PDF
    doc.build(story)
    print(f"PDF report saved to {output_path}")
