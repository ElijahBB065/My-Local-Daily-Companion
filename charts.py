"""
charts.py
Plotly chart builders shared by both tabs, using a validated
colorblind-safe categorical/status palette. Status colors (used for
delay severity and AQI category bands) are never the only cue -- every
chart that uses them also prints the number or a direct label.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# --- ink / chrome ---
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"
SURFACE = "#fcfcfb"

# --- categorical slots (fixed order, fixed meaning) ---
BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
YELLOW = "#eda100"
VIOLET = "#4a3aa7"

STATUS_GOOD = "#0ca30c"
STATUS_WARNING = "#c98500"
STATUS_CRITICAL = "#d03b3b"

FONT = dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK_PRIMARY)

HOUR_LABELS = [f"{h%12 or 12}{'a' if h < 12 else 'p'}" for h in range(24)]


def _base_layout(title: str, show_legend: bool = False) -> dict:
    layout = dict(
        title=dict(text=title, font=dict(size=15, color=INK_PRIMARY), y=0.97, yanchor="top"),
        plot_bgcolor=SURFACE,
        paper_bgcolor=SURFACE,
        font=FONT,
        margin=dict(l=10, r=10, t=48, b=55 if show_legend else 30),
        hoverlabel=dict(bgcolor=SURFACE, font=dict(color=INK_PRIMARY)),
    )
    if show_legend:
        layout["legend"] = dict(
            orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5,
            font=dict(color=INK_SECONDARY, size=12),
        )
    else:
        layout["showlegend"] = False
    return layout


# --------------------------------------------------------------------------
# Transit charts
# --------------------------------------------------------------------------
def delay_pattern_chart(hourly_df: pd.DataFrame) -> go.Figure:
    """Area/line chart of typical delay minutes throughout the day."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=HOUR_LABELS, y=hourly_df["avg_delay_min"],
        mode="lines", line=dict(color=BLUE, width=2.5, shape="spline"),
        fill="tozeroy", fillcolor="rgba(42,120,214,0.12)",
        hovertemplate="%{x}<br>Typical delay: %{y:.1f} min<extra></extra>",
    ))
    fig.update_layout(**_base_layout("⏱️ Typical delay by time of day"))
    fig.update_yaxes(title="Avg. delay (minutes)", gridcolor=GRIDLINE, zerolinecolor=BASELINE, rangemode="tozero")
    fig.update_xaxes(showgrid=False, linecolor=BASELINE, dtick=2)
    return fig


def route_efficiency_chart(line_df: pd.DataFrame) -> go.Figure:
    """Horizontal bar of on-time performance % per line, color-coded by
    severity tier and always printed as a direct label."""
    def tier_color(v):
        if v >= 90:
            return STATUS_GOOD
        if v >= 80:
            return STATUS_WARNING
        return STATUS_CRITICAL

    df = line_df.sort_values("on_time_pct")
    colors = [tier_color(v) for v in df["on_time_pct"]]
    labels = [f"{v:.0f}%" for v in df["on_time_pct"]]

    fig = go.Figure(go.Bar(
        x=df["on_time_pct"], y=df["line"], orientation="h",
        marker_color=colors, text=labels, textposition="outside",
        textfont=dict(color=INK_PRIMARY, size=12),
        hovertemplate="%{y}<br>On-time: %{x:.1f}%<extra></extra>",
    ))
    fig.update_layout(**_base_layout("🚦 On-time performance by line"))
    fig.update_xaxes(title="% of trips on time", range=[0, 105], gridcolor=GRIDLINE, zerolinecolor=BASELINE)
    fig.update_yaxes(showgrid=False, linecolor=BASELINE)
    return fig


# --------------------------------------------------------------------------
# Air quality charts
# --------------------------------------------------------------------------
_AQI_BANDS = [
    (0, 50, "#0ca30c"), (50, 100, "#d4b106"), (100, 150, "#e8720c"),
    (150, 200, "#d03b3b"), (200, 300, "#8f3f97"), (300, 400, "#7e0023"),
]


def aqi_trend_chart(hourly_df: pd.DataFrame, current_hour: int) -> go.Figure:
    """AQI throughout the day, plotted over lightly-tinted EPA category
    bands so the reader can see at a glance which health category each
    hour falls into -- not just a bare number."""
    fig = go.Figure()

    y_max = max(110, float(hourly_df["aqi"].max()) * 1.15)
    for lo, hi, color in _AQI_BANDS:
        if lo >= y_max:
            continue
        fig.add_hrect(y0=lo, y1=min(hi, y_max), fillcolor=color, opacity=0.10, line_width=0)

    fig.add_trace(go.Scatter(
        x=HOUR_LABELS, y=hourly_df["aqi"],
        mode="lines+markers", line=dict(color=INK_PRIMARY, width=2.5),
        marker=dict(size=5, color=INK_PRIMARY),
        hovertemplate="%{x}<br>AQI: %{y}<extra></extra>",
    ))
    fig.add_vline(x=current_hour, line_dash="dot", line_color=VIOLET, line_width=2)
    fig.add_annotation(
        x=current_hour, y=y_max, text="now", showarrow=False,
        font=dict(color=VIOLET, size=11), yshift=6,
    )

    fig.update_layout(**_base_layout("📈 Hourly AQI trend"))
    fig.update_yaxes(title="AQI", range=[0, y_max], gridcolor=GRIDLINE, zerolinecolor=BASELINE)
    fig.update_xaxes(showgrid=False, linecolor=BASELINE, dtick=2)
    return fig


def pollutant_breakdown_chart(sub_indices: dict) -> go.Figure:
    """Small bar comparing each measured pollutant's own AQI sub-index --
    shows which pollutant is actually driving today's overall number."""
    from air_quality import aqi_category  # local import avoids a circular import at module load

    names = list(sub_indices.keys())
    values = list(sub_indices.values())
    colors = [aqi_category(v)[1] for v in values]
    labels = [f"AQI {v}" for v in values]

    fig = go.Figure(go.Bar(
        x=names, y=values, marker_color=colors, text=labels, textposition="outside",
        textfont=dict(color=INK_PRIMARY, size=12),
        hovertemplate="%{x}<br>AQI: %{y}<extra></extra>",
    ))
    fig.update_layout(**_base_layout("🔬 What's driving today's AQI?"))
    fig.update_yaxes(title="AQI sub-index", gridcolor=GRIDLINE, zerolinecolor=BASELINE, rangemode="tozero")
    fig.update_xaxes(showgrid=False, linecolor=BASELINE)
    return fig
