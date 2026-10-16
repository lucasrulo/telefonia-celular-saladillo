from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core import db, ui

ui.hero("Análisis", "Dashboard", "Ventas, ganancia, stock y servicio técnico en una sola pantalla.")

# ---------- Período ----------
hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
presets = {
    "Hoy": (hoy, datetime.now()),
    "7 días": (hoy - timedelta(days=6), datetime.now()),
    "Este mes": (hoy.replace(day=1), datetime.now()),
    "Mes anterior": ((hoy.replace(day=1) - timedelta(days=1)).replace(day=1), hoy.replace(day=1) - timedelta(seconds=1)),
    "90 días": (hoy - timedelta(days=89), datetime.now()),
    "Este año": (hoy.replace(month=1, day=1), datetime.now()),
    "Personalizado": None,
}
p = st.segmented_control("Período", list(presets), default="Este mes", label_visibility="collapsed") or "Este mes"
if p == "Personalizado":
    rng = st.date_input("Rango", value=(hoy.date() - timedelta(days=30), hoy.date()))
    if isinstance(rng, tuple) and len(rng) == 2:
        desde, hasta = datetime.combine(rng[0], datetime.min.time()), datetime.combine(rng[1], datetime.max.time())
    else:
        st.stop()
else:
    desde, hasta = presets[p]
dur = hasta - desde
p_desde, p_hasta = desde - dur - timedelta(seconds=1), desde - timedelta(seconds=1)

v = db.ventas_df(desde, hasta)
vp = db.ventas_df(p_desde, p_hasta)
it = db.items_df(desde, hasta)
prods = db.listar_productos()
rep_raw = db.reparaciones_df()


def delta(a, b):
    if not b:
        return ""
    d = (a - b) / abs(b)
    color = "#D4FF3A" if d >= 0 else "#FF4D8D"
    return f"<span style='color:{color}'>{'▲' if d >= 0 else '▼'} {abs(d):.0%}</span> vs período anterior"


bruta = v["total"].sum() if not v.empty else 0
costo = v["costo_total"].sum() if not v.empty else 0
gan = bruta - costo
bruta_p = vp["total"].sum() if not vp.empty else 0
gan_p = (vp["total"] - vp["costo_total"]).sum() if not vp.empty else 0
tickets = len(v)
unidades = it["cantidad"].sum() if not it.empty else 0

# Reparaciones entregadas en el período
if not rep_raw.empty:
    r = rep_raw.copy()
    r["fecha_entrega"] = pd.to_datetime(r["fecha_entrega"])
    for c in ["cobrado", "costo_repuesto", "mano_obra", "presupuesto"]:
        r[c] = r[c].fillna(0)
    rd = r[(r["estado"] == "Devuelto") & r["fecha_entrega"].between(desde, hasta)]
    rep_cobrado = rd["cobrado"].sum()
    rep_gan = (rd["cobrado"] - rd["costo_repuesto"] - rd["mano_obra"]).sum()
    en_taller = r[r["estado"].isin(["Para enviar", "En reparación"])]
else:
    rd = pd.DataFrame()
    rep_cobrado = rep_gan = 0
    en_taller = pd.DataFrame()

st.markdown("##### 💰 Ventas")
ui.kpis([
    ("Venta bruta", ui.ars(bruta), delta(bruta, bruta_p), ui.LIME),
    ("Ganancia bruta", ui.ars(gan), delta(gan, gan_p), ui.VIOLET),
    ("Margen", f"{(gan / bruta if bruta else 0):.1%}", f"costo mercadería {ui.ars(costo)}", ui.CYAN),
    ("Tickets", ui.num(tickets), f"ticket promedio <b>{ui.ars(bruta / tickets if tickets else 0)}</b>", ui.AMBER),
    ("Unidades vendidas", ui.num(unidades), f"{unidades / tickets if tickets else 0:.1f} por ticket", ui.PINK),
])

st.markdown("##### 🔧 Servicio técnico + total negocio")
ui.kpis([
    ("Reparaciones cobradas", ui.ars(rep_cobrado), f"<b>{len(rd)}</b> equipos entregados", ui.CYAN),
    ("Ganancia reparaciones", ui.ars(rep_gan), None, ui.VIOLET),
    ("En taller ahora", ui.num(len(en_taller)),
     f"<b>{ui.ars(en_taller['presupuesto'].sum() if not en_taller.empty else 0)}</b> a facturar", ui.AMBER),
    ("Ingreso total negocio", ui.ars(bruta + rep_cobrado), "ventas + reparaciones", ui.LIME),
    ("Ganancia total negocio", ui.ars(gan + rep_gan), None, ui.PINK),
])

if not prods.empty:
    s = prods.copy()
    s["stock_pos"] = s["stock"].clip(lower=0)
    st.markdown("##### 📦 Stock")
    ui.kpis([
        ("Unidades en stock", ui.num(s["stock_pos"].sum()), f"{len(s)} artículos", ui.CYAN),
        ("Stock a costo", ui.ars((s["stock_pos"] * s["costo"]).sum()), None, ui.VIOLET),
        ("Stock a precio venta", ui.ars((s["stock_pos"] * s["precio"]).sum()), None, ui.LIME),
        ("Sin stock", ui.num((s["stock"] <= 0).sum()), None, ui.PINK),
        ("Stock bajo", ui.num(((s["stock"] > 0) & (s["stock"] <= s["stock_minimo"])).sum()), None, ui.AMBER),
    ])

# ---------- Gráficos ----------
if v.empty and rd.empty:
    st.info("No hay ventas en este período todavía.")
else:
    with st.container(border=True):
        serie = pd.DataFrame(index=pd.date_range(desde.date(), hasta.date(), freq="D"))
        if not v.empty:
            vv = v.copy()
            vv["dia"] = pd.to_datetime(vv["fecha"]).dt.normalize()
            g = vv.groupby("dia").agg(venta=("total", "sum"), costo=("costo_total", "sum"))
            serie = serie.join(g)
        if not rd.empty:
            serie = serie.join(rd.assign(dia=rd["fecha_entrega"].dt.normalize()).groupby("dia")["cobrado"].sum().rename("reparaciones"))
        serie = serie.fillna(0)
        for c in ["venta", "costo", "reparaciones"]:
            if c not in serie:
                serie[c] = 0
        serie["ganancia"] = serie["venta"] - serie["costo"]
        fig = go.Figure()
        fig.add_bar(x=serie.index, y=serie["venta"], name="Venta bruta", marker_color=ui.LIME, marker_line_width=0)
        fig.add_bar(x=serie.index, y=serie["reparaciones"], name="Reparaciones", marker_color=ui.CYAN, marker_line_width=0)
        fig.add_scatter(x=serie.index, y=serie["ganancia"], name="Ganancia ventas", mode="lines+markers",
                        line=dict(color=ui.VIOLET, width=3, shape="spline"), marker=dict(size=6))
        fig.update_layout(barmode="stack", title="Evolución diaria", height=360, bargap=.35, yaxis_tickprefix="$ ")
        st.plotly_chart(fig, width="stretch")

    if not it.empty:
        it["venta"] = it["cantidad"] * it["precio_unit"]
        it["ganancia"] = it["cantidad"] * (it["precio_unit"] - it["costo_unit"])
        c1, c2 = st.columns([1, 1.4])
        with c1, st.container(border=True):
            cat = it.groupby("categoria", dropna=False)["venta"].sum().reset_index().sort_values("venta", ascending=False)
            fig = px.pie(cat, names="categoria", values="venta", hole=.68, title="Venta por categoría",
                         color_discrete_sequence=ui.PALETTE)
            fig.update_traces(textinfo="percent", textfont_color="#0A0A0A")
            fig.update_layout(height=360, annotations=[dict(text=ui.ars(cat["venta"].sum()), showarrow=False,
                                                            font=dict(size=18, family="Space Grotesk", color="#fff"))])
            st.plotly_chart(fig, width="stretch")
        with c2, st.container(border=True):
            metrica = st.radio("Top 10 por", ["venta", "ganancia", "cantidad"], horizontal=True,
                               format_func=str.capitalize, key="top_m")
            top = it.groupby("nombre")[["venta", "ganancia", "cantidad"]].sum().nlargest(10, metrica).iloc[::-1].reset_index()
            fig = px.bar(top, x=metrica, y="nombre", orientation="h", title="Productos estrella",
                         color=metrica, color_continuous_scale=[[0, ui.VIOLET], [1, ui.LIME]])
            fig.update_layout(height=320, coloraxis_showscale=False, yaxis_title=None, xaxis_title=None)
            st.plotly_chart(fig, width="stretch")

        c3, c4 = st.columns([1, 1.4])
        with c3, st.container(border=True):
            mp = v.groupby("medio_pago")["total"].sum().reset_index().sort_values("total")
            fig = px.bar(mp, x="total", y="medio_pago", orientation="h", title="Medios de pago",
                         color_discrete_sequence=[ui.CYAN])
            fig.update_layout(height=300, yaxis_title=None, xaxis_title=None)
            st.plotly_chart(fig, width="stretch")
        with c4, st.container(border=True):
            h = v.copy()
            h["f"] = pd.to_datetime(h["fecha"])
            h["dow"] = h["f"].dt.dayofweek
            h["hora"] = h["f"].dt.hour
            dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
            hm = h.pivot_table(index="dow", columns="hora", values="total", aggfunc="sum").reindex(range(7)).fillna(0)
            hm = hm.reindex(columns=range(8, 22), fill_value=0)
            fig = px.imshow(hm.values, x=[f"{x}h" for x in hm.columns], y=dias, aspect="auto",
                            color_continuous_scale=[[0, "#11111A"], [.5, ui.VIOLET], [1, ui.LIME]], title="Mapa de calor · ¿cuándo vendés?")
            fig.update_layout(height=300, coloraxis_showscale=False)
            st.plotly_chart(fig, width="stretch")

# ---------- Stock ----------
if not prods.empty:
    c5, c6 = st.columns([1.3, 1])
    with c5, st.container(border=True):
        sc = prods.assign(stock_pos=prods["stock"].clip(lower=0))
        sc["a costo"] = sc["stock_pos"] * sc["costo"]
        sc["a venta"] = sc["stock_pos"] * sc["precio"]
        sg = sc.groupby("categoria")[["a costo", "a venta"]].sum().reset_index().sort_values("a venta", ascending=False)
        fig = px.bar(sg, x="categoria", y=["a costo", "a venta"], barmode="group", title="Stock valorizado por categoría",
                     color_discrete_sequence=[ui.VIOLET, ui.LIME], labels={"value": "$", "variable": "", "categoria": ""})
        fig.update_layout(height=340)
        st.plotly_chart(fig, width="stretch")
    with c6, st.container(border=True):
        st.markdown("#### ⚠️ Reponer")
        bajo = prods[prods["stock"] <= prods["stock_minimo"]].sort_values("stock")[["nombre", "stock", "stock_minimo"]]
        if bajo.empty:
            st.success("Todo con stock 👌")
        else:
            st.dataframe(bajo, hide_index=True, width="stretch", height=260,
                         column_config={"nombre": "Producto", "stock": "Stock", "stock_minimo": "Mín."})

    if not it.empty:
        vendidos = set(it["producto_id"].unique())
        quietos = prods[(~prods["id"].isin(vendidos)) & (prods["stock"] > 0)].copy()
        if not quietos.empty:
            quietos["inmovilizado"] = quietos["stock"] * quietos["costo"]
            with st.expander(f"🧊 Stock inmovilizado: {len(quietos)} artículos sin ventas en el período · "
                             f"{ui.ars(quietos['inmovilizado'].sum())} a costo"):
                st.dataframe(quietos.sort_values("inmovilizado", ascending=False)[["codigo", "nombre", "categoria", "stock", "inmovilizado"]],
                             hide_index=True, width="stretch",
                             column_config={"inmovilizado": st.column_config.NumberColumn("$ a costo", format="$ %.0f")})
