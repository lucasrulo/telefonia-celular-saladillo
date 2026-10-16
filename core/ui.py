"""Estilos, componentes visuales y utilidades de formato."""
from __future__ import annotations

import html

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

LIME = "#D4FF3A"
VIOLET = "#8B5CFF"
CYAN = "#22D3EE"
PINK = "#FF4D8D"
AMBER = "#FFB020"
MUTED = "#8A8FA3"
PALETTE = [LIME, VIOLET, CYAN, PINK, AMBER, "#5EEAD4", "#A3A3FF", "#F472B6"]

ESTADO_COLOR = {
    "Para enviar": AMBER,
    "En reparación": CYAN,
    "Reparado": LIME,
    "Sin solución": PINK,
    "Devuelto": VIOLET,
}

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500&display=swap');

:root {{
  --lime:{LIME}; --violet:{VIOLET}; --cyan:{CYAN}; --pink:{PINK}; --amber:{AMBER};
  --bg:#07070C; --card:rgba(255,255,255,.035); --stroke:rgba(255,255,255,.08); --muted:{MUTED};
}}
html, body, [class*="css"], .stApp {{ font-family:'Inter',sans-serif; }}
.stApp {{
  background:
    radial-gradient(900px 500px at 8% -10%, rgba(139,92,255,.22), transparent 60%),
    radial-gradient(700px 400px at 100% 0%, rgba(34,211,238,.12), transparent 60%),
    radial-gradient(600px 400px at 50% 110%, rgba(212,255,58,.06), transparent 60%),
    var(--bg);
}}
h1,h2,h3,h4 {{ font-family:'Space Grotesk',Inter,sans-serif !important; letter-spacing:-.02em; }}
.block-container {{ padding-top:1.6rem; padding-bottom:3rem; max-width:1400px; }}
header[data-testid="stHeader"] {{ background:transparent; }}

/* Sidebar */
section[data-testid="stSidebar"] {{
  background:linear-gradient(180deg,#0B0B14 0%,#08080E 100%);
  border-right:1px solid var(--stroke);
}}
section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] {{
  border-radius:12px; margin:2px 6px; padding:.55rem .8rem; transition:all .15s;
}}
section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover {{ background:rgba(255,255,255,.05); }}
section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] {{
  background:linear-gradient(90deg,rgba(212,255,58,.16),rgba(212,255,58,.02));
  box-shadow:inset 3px 0 0 var(--lime);
}}

/* Hero */
.hero {{ display:flex; align-items:flex-end; justify-content:space-between; gap:1rem; margin-bottom:1.2rem; flex-wrap:wrap; }}
.hero .eyebrow {{ font-family:'JetBrains Mono',monospace; font-size:.72rem; letter-spacing:.18em; text-transform:uppercase; color:var(--lime); }}
.hero h1 {{ font-size:2.4rem; line-height:1.05; margin:.25rem 0 0; padding:0;
  background:linear-gradient(90deg,#fff 30%, #B9B3FF 100%); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
.hero p {{ color:var(--muted); margin:.35rem 0 0; }}

/* KPI cards */
.kpi-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:14px; margin:.2rem 0 1.1rem; }}
.kpi {{
  position:relative; overflow:hidden; padding:18px 18px 16px; border-radius:20px;
  background:var(--card); border:1px solid var(--stroke); backdrop-filter:blur(12px);
  transition:transform .15s, border-color .15s;
}}
.kpi:hover {{ transform:translateY(-2px); border-color:rgba(255,255,255,.16); }}
.kpi::before {{ content:""; position:absolute; inset:0 0 auto 0; height:3px; background:var(--accent,var(--lime)); opacity:.9; }}
.kpi::after {{ content:""; position:absolute; width:140px; height:140px; right:-50px; top:-60px; border-radius:50%;
  background:var(--accent,var(--lime)); opacity:.08; filter:blur(10px); }}
.kpi .lbl {{ font-size:.74rem; color:var(--muted); text-transform:uppercase; letter-spacing:.09em; font-weight:600; }}
.kpi .val {{ font-family:'Space Grotesk',Inter,sans-serif; font-size:clamp(1.2rem,1.5vw,1.85rem); font-weight:700; margin-top:6px; color:#fff; white-space:nowrap; }}
.kpi .sub {{ font-size:.8rem; color:var(--muted); margin-top:2px; }}
.kpi .sub b {{ color:var(--accent,var(--lime)); font-weight:600; }}

/* Glass panel */
.panel {{ background:var(--card); border:1px solid var(--stroke); border-radius:20px; padding:18px 20px; }}
div[data-testid="stVerticalBlockBorderWrapper"] {{ border-radius:20px !important; border-color:var(--stroke) !important; background:var(--card); }}

/* Scanner */
.scan-hint {{ display:flex; align-items:center; gap:10px; color:var(--muted); font-size:.85rem; margin:-.2rem 0 .6rem; }}
.pulse {{ width:9px; height:9px; border-radius:50%; background:var(--lime); box-shadow:0 0 0 0 rgba(212,255,58,.7); animation:pulse 1.6s infinite; }}
@keyframes pulse {{ 0%{{box-shadow:0 0 0 0 rgba(212,255,58,.6)}} 70%{{box-shadow:0 0 0 10px rgba(212,255,58,0)}} 100%{{box-shadow:0 0 0 0 rgba(212,255,58,0)}} }}
div[data-testid="stTextInput"] input[aria-label*="Escaneá"] {{
  font-family:'JetBrains Mono',monospace; font-size:1.25rem; padding:.9rem 1rem; height:auto;
  border:1.5px solid rgba(212,255,58,.35); background:rgba(212,255,58,.04);
}}
div[data-testid="stTextInput"] input[aria-label*="Escaneá"]:focus {{ border-color:var(--lime); box-shadow:0 0 0 4px rgba(212,255,58,.15); }}

/* Cart */
.cart-row {{ display:flex; justify-content:space-between; align-items:center; padding:12px 0; border-bottom:1px dashed var(--stroke); }}
.cart-name {{ font-weight:600; }}
.cart-meta {{ color:var(--muted); font-size:.8rem; font-family:'JetBrains Mono',monospace; }}
.total-box {{ border-radius:22px; padding:22px; margin-top:6px;
  background:linear-gradient(135deg,rgba(212,255,58,.95),rgba(170,230,30,.95)); color:#0A0A0A; }}
.total-box .t-lbl {{ font-size:.75rem; letter-spacing:.14em; text-transform:uppercase; font-weight:700; opacity:.7; }}
.total-box .t-val {{ font-family:'Space Grotesk',Inter,sans-serif; font-size:2.8rem; font-weight:700; line-height:1.05; }}
.total-box .t-sub {{ font-size:.85rem; opacity:.75; }}

/* Chips */
.chip {{ display:inline-flex; align-items:center; gap:6px; padding:3px 10px; border-radius:999px; font-size:.75rem; font-weight:600;
  border:1px solid color-mix(in srgb, var(--c) 45%, transparent); color:var(--c); background:color-mix(in srgb, var(--c) 12%, transparent); }}
.chip::before {{ content:""; width:6px; height:6px; border-radius:50%; background:var(--c); }}

/* Kanban */
.kcol-h {{ display:flex; justify-content:space-between; align-items:center; padding:10px 14px; border-radius:14px; margin-bottom:10px;
  background:color-mix(in srgb, var(--c) 10%, transparent); border:1px solid color-mix(in srgb, var(--c) 30%, transparent); }}
.kcol-h span:first-child {{ font-family:'Space Grotesk',Inter,sans-serif; font-weight:600; color:var(--c); }}
.kcol-h span:last-child {{ font-family:'JetBrains Mono',monospace; font-size:.8rem; color:#fff; background:rgba(255,255,255,.08); border-radius:8px; padding:2px 8px; }}
.kcard {{ background:rgba(255,255,255,.04); border:1px solid var(--stroke); border-radius:16px; padding:12px 14px; margin-bottom:10px; }}
.kcard .m {{ font-weight:700; font-family:'Space Grotesk',Inter,sans-serif; }}
.kcard .c {{ color:var(--muted); font-size:.8rem; }}
.kcard .f {{ font-size:.82rem; margin:6px 0; color:#D9DBE5; }}
.kcard .n {{ display:flex; justify-content:space-between; font-family:'JetBrains Mono',monospace; font-size:.78rem; color:var(--muted); }}
.kcard .n b {{ color:#fff; }}

/* Buttons & inputs */
.stButton>button, .stDownloadButton>button, .stFormSubmitButton>button {{ border-radius:12px; font-weight:600; transition:all .15s; }}
button[kind^="primary"], button[data-testid^="stBaseButton-primary"] {{ color:#0A0A0A !important; box-shadow:0 8px 24px -10px rgba(212,255,58,.6); }}
button[kind^="primary"] p, button[data-testid^="stBaseButton-primary"] p {{ color:#0A0A0A !important; font-weight:700; }}
.stButton>button:hover {{ transform:translateY(-1px); }}
div[data-baseweb="input"], div[data-baseweb="select"]>div, div[data-baseweb="textarea"] {{ border-radius:12px !important; }}
.stTabs [data-baseweb="tab-list"] {{ gap:6px; background:rgba(255,255,255,.03); padding:6px; border-radius:14px; border:1px solid var(--stroke); }}
.stTabs [data-baseweb="tab"] {{ border-radius:10px; padding:8px 16px; height:auto; }}
.stTabs [aria-selected="true"] {{ background:rgba(212,255,58,.12); }}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ display:none; }}
[data-testid="InputInstructions"] {{ display:none; }}
[data-testid="stDataFrame"] {{ border-radius:14px; overflow:hidden; border:1px solid var(--stroke); }}
.brand {{ display:flex; align-items:center; gap:10px; padding:4px 8px 14px; }}
.brand .logo {{ width:36px; height:36px; border-radius:11px; display:grid; place-items:center; font-weight:800; color:#0A0A0A;
  background:conic-gradient(from 200deg, var(--lime), var(--cyan), var(--violet), var(--lime)); font-family:'Space Grotesk',Inter,sans-serif; }}
.brand .name {{ font-family:'Space Grotesk',Inter,sans-serif; font-weight:700; font-size:1.15rem; }}
.brand .tag {{ font-size:.7rem; color:var(--muted); font-family:'JetBrains Mono',monospace; }}
.muted {{ color:var(--muted); }}
</style>
"""


def setup_page():
    st.markdown(CSS, unsafe_allow_html=True)
    _plotly_theme()


def _plotly_theme():
    t = go.layout.Template()
    t.layout = go.Layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#C9CBD6", size=12),
        colorway=PALETTE,
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(gridcolor="rgba(255,255,255,.05)", zeroline=False, linecolor="rgba(255,255,255,.1)"),
        yaxis=dict(gridcolor="rgba(255,255,255,.06)", zeroline=False),
        legend=dict(orientation="h", y=-0.15, bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="#14141F", bordercolor="#2A2A3A", font=dict(color="#fff")),
        title=dict(font=dict(family="Space Grotesk", size=16, color="#fff"), x=0.01),
    )
    pio.templates["celupos"] = t
    pio.templates.default = "celupos"


def ars(x, dec=0) -> str:
    try:
        x = float(x)
    except (TypeError, ValueError):
        x = 0.0
    s = f"{abs(x):,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{'-' if x < 0 else ''}$ {s}"


def mars(x, dec=0) -> str:
    """ars() escapado para st.markdown/toast (evita que dos '$' se interpreten como LaTeX)."""
    return ars(x, dec).replace("$", "\\$")


def num(x) -> str:
    try:
        return f"{int(x):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "0"


def hero(eyebrow: str, title: str, subtitle: str = ""):
    st.markdown(
        f"""<div class="hero"><div><div class="eyebrow">{html.escape(eyebrow)}</div>
        <h1>{html.escape(title)}</h1>{f'<p>{html.escape(subtitle)}</p>' if subtitle else ''}</div></div>""",
        unsafe_allow_html=True)


def kpis(items: list[tuple]):
    """items: (label, value, sub, accent_color)"""
    cards = []
    for it in items:
        lbl, val, sub, color = (list(it) + [None, None])[:4]
        cards.append(
            f'<div class="kpi" style="--accent:{color or LIME}"><div class="lbl">{html.escape(lbl)}</div>'
            f'<div class="val">{val}</div>{f"<div class=sub>{sub}</div>" if sub else ""}</div>')
    st.markdown(f'<div class="kpi-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def chip(estado: str) -> str:
    return f'<span class="chip" style="--c:{ESTADO_COLOR.get(estado, MUTED)}">{html.escape(estado or "")}</span>'


def sidebar_brand(nombre: str):
    ini = (nombre or "C")[:1].upper()
    st.sidebar.markdown(
        f'<div class="brand"><div class="logo">{html.escape(ini)}</div><div>'
        f'<div class="name">{html.escape(nombre)}</div><div class="tag">POS · STOCK · SERVICE</div></div></div>',
        unsafe_allow_html=True)


def autofocus(label_contains: str):
    """Mantiene el foco en el input del escáner tras cada rerun (la pistola tipea + Enter)."""
    st.session_state["_af"] = st.session_state.get("_af", 0) + 1
    st.html(
        f"""<!-- af {st.session_state['_af']} --><script>
        (function(){{
          const doc = window.parent.document;
          function f(){{
            const el = [...doc.querySelectorAll('input')].find(i => (i.getAttribute('aria-label')||'').includes({label_contains!r}));
            const a = doc.activeElement;
            if (el && (!a || !['INPUT','TEXTAREA','SELECT'].includes(a.tagName))) el.focus();
          }}
          setTimeout(f, 150); setTimeout(f, 700);
        }})();
        </script>""",
        unsafe_allow_javascript=True,
    )


def esc(s) -> str:
    return html.escape("" if s is None else str(s))
