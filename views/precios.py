import numpy as np
import streamlit as st

from core import db, ui

ss = st.session_state
ui.hero("Inventario", "Actualizar precios", "Aumentos masivos con preview, por categoría o markup, y redondeo prolijo.")

prods = db.listar_productos()
tab_m, tab_i, tab_h = st.tabs(["⚡ Actualización masiva", "🎯 Por código", "🕓 Historial"])


def redondear(serie, paso):
    if paso <= 1:
        return serie.round(0)
    return (np.ceil(serie / paso) * paso).astype(float)


with tab_m:
    if prods.empty:
        st.info("No hay productos.")
    else:
        with st.container(border=True):
            c1, c2, c3 = st.columns([1.6, 1.4, 1])
            cats = c1.multiselect("Categorías (vacío = todas)", sorted(prods["categoria"].dropna().unique()))
            q = c2.text_input("Filtrar por nombre (opcional)", placeholder="Ej: Samsung")
            red = c3.selectbox("Redondeo hacia arriba", [1, 10, 50, 100, 500, 1000], index=3,
                               format_func=lambda x: "Sin redondeo" if x == 1 else f"a $ {x}")
            modo = st.radio("Qué hacer", ["Aumentar precio de venta %", "Aumentar costo % (y mantener margen)",
                                          "Recalcular precio por markup sobre costo"], horizontal=True)
            pct = st.number_input("Markup %" if "markup" in modo else "Porcentaje (negativo = baja)",
                                  value=10.0, step=1.0)

        sel = prods.copy()
        if cats:
            sel = sel[sel["categoria"].isin(cats)]
        if q:
            sel = sel[sel["nombre"].str.contains(q, case=False, na=False)]
        sel = sel[["id", "codigo", "nombre", "categoria", "costo", "precio"]].copy()
        if modo.startswith("Aumentar precio"):
            sel["costo_nuevo"] = sel["costo"]
            sel["precio_nuevo"] = redondear(sel["precio"] * (1 + pct / 100), red)
        elif modo.startswith("Aumentar costo"):
            sel["costo_nuevo"] = (sel["costo"] * (1 + pct / 100)).round(2)
            sel["precio_nuevo"] = redondear(sel["precio"] * (1 + pct / 100), red)
        else:
            sel["costo_nuevo"] = sel["costo"]
            sel["precio_nuevo"] = redondear(sel["costo"] * (1 + pct / 100), red)
        sel["var"] = ((sel["precio_nuevo"] / sel["precio"].where(sel["precio"] > 0)) - 1).fillna(0) * 100
        sel.insert(0, "aplicar", True)

        st.markdown(f"**{len(sel)} productos** en el preview · destildá los que no quieras tocar")
        ed = st.data_editor(
            sel, hide_index=True, width="stretch", height=420, key=f"prev_{modo}_{pct}_{red}_{len(sel)}",
            disabled=["codigo", "nombre", "categoria", "costo", "precio", "var"],
            column_config={
                "id": None,
                "aplicar": st.column_config.CheckboxColumn("✓", width="small"),
                "costo": st.column_config.NumberColumn("Costo actual", format="$ %.0f"),
                "costo_nuevo": st.column_config.NumberColumn("Costo nuevo", format="$ %.0f"),
                "precio": st.column_config.NumberColumn("Precio actual", format="$ %.0f"),
                "precio_nuevo": st.column_config.NumberColumn("Precio nuevo", format="$ %.0f"),
                "var": st.column_config.NumberColumn("Var. %", format="%.1f%%"),
            })
        aplicar = ed[ed["aplicar"]]
        if st.button(f"Aplicar a {len(aplicar)} productos", type="primary", disabled=aplicar.empty):
            for _, r in aplicar.iterrows():
                db.actualizar_producto(int(r["id"]), motivo=f"Masivo: {modo} ({pct:+.1f}%)",
                                       costo=float(r["costo_nuevo"]), precio=float(r["precio_nuevo"]))
            st.toast(f"✓ {len(aplicar)} precios actualizados")
            st.rerun()

with tab_i:
    with st.form("scan_precio", clear_on_submit=True, border=False):
        a, b = st.columns([5, 1])
        cod = a.text_input("Escaneá el producto", placeholder="▌ Esperando lectura…")
        go_ = b.form_submit_button("Buscar", width="stretch")
    if go_ and cod.strip():
        p = db.buscar_por_codigo(cod)
        ss.precio_pid = p["id"] if p else None
        if not p:
            st.warning("Código inexistente")
    if ss.get("precio_pid"):
        p = db.buscar_por_codigo(prods.set_index("id").at[ss.precio_pid, "codigo"])
        with st.container(border=True):
            st.markdown(f"### {ui.esc(p['nombre'])}")
            with st.form("upd_precio"):
                x1, x2 = st.columns(2)
                nc = x1.number_input("Costo", min_value=0.0, step=100.0, format="%.0f", value=float(p["costo"]))
                npv = x2.number_input("Precio", min_value=0.0, step=100.0, format="%.0f", value=float(p["precio"]))
                if st.form_submit_button("Guardar", type="primary"):
                    db.actualizar_producto(p["id"], motivo="Manual", costo=nc, precio=npv)
                    st.toast(f"✓ {p['nombre']}: {ui.mars(p['precio'])} → {ui.mars(npv)}")
                    ss.precio_pid = None
                    st.rerun()

with tab_h:
    h = db.historial_precios_df()
    if h.empty:
        st.info("Sin cambios de precio registrados.")
    else:
        st.dataframe(h, hide_index=True, width="stretch", height=480, column_config={
            "fecha": st.column_config.DatetimeColumn("Fecha", format="DD/MM/YY HH:mm"),
            **{c: st.column_config.NumberColumn(c.replace("_", " ").capitalize(), format="$ %.0f")
               for c in ["costo_anterior", "costo_nuevo", "precio_anterior", "precio_nuevo"]}})
