import io

import pandas as pd
import streamlit as st

from core import db, ui

ss = st.session_state
ss.setdefault("ingreso_pid", None)
ss.setdefault("alta_codigo", "")

ui.hero("Inventario", "Productos y stock", "Alta en segundos: escaneás, ponés nombre y precio. Listo.")

prods = db.listar_productos(solo_activos=False)
activos = prods[prods["activo"] == True] if not prods.empty else prods  # noqa: E712
if not activos.empty:
    val_costo = (activos["stock"].clip(lower=0) * activos["costo"]).sum()
    val_venta = (activos["stock"].clip(lower=0) * activos["precio"]).sum()
    bajos = (activos["stock"] <= activos["stock_minimo"]).sum()
    ui.kpis([
        ("Artículos activos", ui.num(len(activos)), None, ui.CYAN),
        ("Unidades en stock", ui.num(activos["stock"].clip(lower=0).sum()), None, ui.VIOLET),
        ("Stock valorizado (costo)", ui.ars(val_costo), None, ui.LIME),
        ("Stock valorizado (venta)", ui.ars(val_venta), f"Ganancia potencial <b>{ui.ars(val_venta - val_costo)}</b>", ui.AMBER),
        ("Stock bajo / sin stock", ui.num(bajos), "para reponer", ui.PINK),
    ])

tab_alta, tab_ing, tab_inv, tab_mov = st.tabs(["➕ Alta de producto", "📦 Ingreso de stock", "🗂️ Inventario", "🔁 Movimientos"])

# ---------------- ALTA ----------------
with tab_alta:
    with st.container(border=True):
        with st.form("alta", clear_on_submit=True):
            c1, c2 = st.columns([1.3, 2])
            codigo = c1.text_input("Escaneá el código de barras", placeholder="Disparo de pistola o vacío para código interno")
            nombre = c2.text_input("Nombre del artículo", placeholder="Ej: Funda silicona iPhone 15 negra")
            c3, c4, c5, c6, c7 = st.columns([1.4, 1, 1, 1, 1])
            cat = c3.selectbox("Categoría", db.categorias())
            costo = c4.number_input("Costo", min_value=0.0, step=100.0, format="%.0f")
            markup = c5.number_input("Markup %", min_value=0.0, step=5.0, value=0.0,
                                     help="Si dejás el precio en 0, se calcula: costo × (1 + markup)")
            precio = c6.number_input("Precio venta", min_value=0.0, step=100.0, format="%.0f")
            stock = c7.number_input("Stock inicial", min_value=0, step=1)
            c8, c9 = st.columns([1, 4])
            stock_min = c8.number_input("Stock mínimo", min_value=0, step=1, value=1)
            ok = st.form_submit_button("Guardar producto", type="primary", width="stretch")
        if ok:
            codigo = codigo.strip() or db.siguiente_codigo_interno()
            if not nombre.strip():
                st.error("El nombre es obligatorio.")
            elif db.buscar_por_codigo(codigo):
                ex = db.buscar_por_codigo(codigo)
                st.warning(f"El código `{codigo}` ya existe: **{ex['nombre']}** (stock {ex['stock']}). "
                           "Usá la pestaña *Ingreso de stock* para sumarle unidades.")
            else:
                if precio == 0 and markup > 0:
                    precio = round(costo * (1 + markup / 100), -1)
                db.crear_producto(codigo, nombre, cat, costo, precio, stock, stock_min)
                st.success(f"✓ {nombre} creado con código `{codigo}` · {ui.mars(precio)}")
    st.caption("Tip: con la pistola, hacé clic en el campo de código y disparale al producto. "
               "Si no tiene código, dejalo vacío y se genera uno interno (INT000001…).")

# ---------------- INGRESO ----------------
with tab_ing:
    with st.form("scan_ing", clear_on_submit=True, border=False):
        a, b = st.columns([5, 1])
        cod = a.text_input("Escaneá el producto que ingresa", placeholder="▌ Esperando lectura…")
        buscar = b.form_submit_button("Buscar", width="stretch")
    if buscar and cod.strip():
        p = db.buscar_por_codigo(cod)
        if p:
            ss.ingreso_pid = p["id"]
        else:
            st.warning("No existe ese código. Dalo de alta en la pestaña *Alta de producto*.")
            ss.ingreso_pid = None
    if not prods.empty:
        sel = st.selectbox("…o elegilo de la lista", prods["id"], index=None,
                           format_func=lambda i: f"{prods.set_index('id').at[i, 'nombre']} · {prods.set_index('id').at[i, 'codigo']}",
                           placeholder="Buscar por nombre")
        if sel is not None:
            ss.ingreso_pid = int(sel)

    if ss.ingreso_pid:
        p = prods.set_index("id").loc[ss.ingreso_pid]
        with st.container(border=True):
            st.markdown(f"### {ui.esc(p['nombre'])}")
            st.markdown(f"<span class='muted'>{ui.esc(p['codigo'])} · {ui.esc(p['categoria'])} · stock actual "
                        f"<b style='color:#fff'>{p['stock']}</b> · costo {ui.ars(p['costo'])} · precio {ui.ars(p['precio'])}</span>",
                        unsafe_allow_html=True)
            with st.form("ingreso"):
                x1, x2, x3 = st.columns(3)
                cant = x1.number_input("Cantidad que ingresa", min_value=1, step=1, value=1)
                nc = x2.number_input("Costo unitario", min_value=0.0, step=100.0, format="%.0f", value=float(p["costo"]))
                npv = x3.number_input("Precio de venta", min_value=0.0, step=100.0, format="%.0f", value=float(p["precio"]))
                nota = st.text_input("Nota / proveedor (opcional)")
                if st.form_submit_button("Confirmar ingreso", type="primary", width="stretch"):
                    db.ingresar_stock(int(ss.ingreso_pid), int(cant), nc, npv, nota)
                    st.success(f"✓ +{cant} unidades · nuevo stock {int(p['stock']) + int(cant)}")
                    ss.ingreso_pid = None
                    st.rerun()

# ---------------- INVENTARIO ----------------
with tab_inv:
    if prods.empty:
        st.info("Todavía no cargaste productos.")
    else:
        f1, f2, f3, f4 = st.columns([2, 1.3, 1, 1])
        q = f1.text_input("Buscar", placeholder="Nombre o código")
        fcat = f2.multiselect("Categoría", sorted(prods["categoria"].dropna().unique()))
        solo_bajo = f3.toggle("Solo stock bajo")
        ver_inact = f4.toggle("Ver inactivos")
        v = prods.copy()
        if q:
            v = v[v["nombre"].str.contains(q, case=False, na=False) | v["codigo"].str.contains(q, case=False, na=False)]
        if fcat:
            v = v[v["categoria"].isin(fcat)]
        if solo_bajo:
            v = v[v["stock"] <= v["stock_minimo"]]
        if not ver_inact:
            v = v[v["activo"] == True]  # noqa: E712
        v = v[["id", "codigo", "nombre", "categoria", "costo", "precio", "stock", "stock_minimo", "activo"]].reset_index(drop=True)
        v["margen"] = ((v["precio"] - v["costo"]) / v["precio"].where(v["precio"] > 0)).fillna(0) * 100

        edit = st.data_editor(
            v, hide_index=True, width="stretch", height=480, key="inv_editor",
            disabled=["id", "codigo", "margen"],
            column_config={
                "id": None,
                "codigo": st.column_config.TextColumn("Código"),
                "nombre": st.column_config.TextColumn("Producto", width="large"),
                "categoria": st.column_config.SelectboxColumn("Categoría", options=db.categorias()),
                "costo": st.column_config.NumberColumn("Costo", format="$ %.0f", min_value=0),
                "precio": st.column_config.NumberColumn("Precio", format="$ %.0f", min_value=0),
                "stock": st.column_config.NumberColumn("Stock", step=1),
                "stock_minimo": st.column_config.NumberColumn("Mín.", step=1, min_value=0),
                "activo": st.column_config.CheckboxColumn("Activo"),
                "margen": st.column_config.ProgressColumn("Margen", format="%.0f%%", min_value=0, max_value=100),
            })
        g1, g2, _ = st.columns([1.2, 1.2, 3])
        if g1.button("💾 Guardar cambios", type="primary", width="stretch"):
            campos = ["nombre", "categoria", "costo", "precio", "stock", "stock_minimo", "activo"]
            orig = v.set_index("id")
            n = 0
            with db.lote("Edición de inventario"):
                for _, row in edit.iterrows():
                    o = orig.loc[row["id"]]
                    cambios = {c: row[c] for c in campos if pd.notna(row[c]) and row[c] != o[c]}
                    if cambios:
                        for c in ("stock", "stock_minimo"):
                            if c in cambios:
                                cambios[c] = int(cambios[c])
                        if "activo" in cambios:
                            cambios["activo"] = bool(cambios["activo"])
                        db.actualizar_producto(int(row["id"]), motivo="Edición inventario", **cambios)
                        n += 1
            if n:
                ss.pop("inv_editor", None)
                st.toast(f"✓ {n} producto(s) actualizados")
                st.rerun()
            else:
                st.info("No había cambios")
        buf = io.BytesIO()
        v.drop(columns=["id"]).to_excel(buf, index=False)
        g2.download_button("⬇️ Exportar Excel", buf.getvalue(), "inventario.xlsx", width="stretch")

# ---------------- MOVIMIENTOS ----------------
with tab_mov:
    from sqlalchemy import select
    s = (select(db.movimientos.c.fecha, db.productos.c.codigo, db.productos.c.nombre, db.movimientos.c.tipo,
                db.movimientos.c.cantidad, db.movimientos.c.costo_unit, db.movimientos.c.referencia, db.movimientos.c.nota)
         .join(db.productos, db.productos.c.id == db.movimientos.c.producto_id)
         .order_by(db.movimientos.c.fecha.desc()).limit(1000))
    mov = db.df(s)
    if mov.empty:
        st.info("Sin movimientos todavía.")
    else:
        tipos = st.multiselect("Tipo", sorted(mov["tipo"].unique()), default=sorted(mov["tipo"].unique()))
        st.dataframe(mov[mov["tipo"].isin(tipos)], hide_index=True, width="stretch", height=460,
                     column_config={"fecha": st.column_config.DatetimeColumn("Fecha", format="DD/MM/YY HH:mm"),
                                    "costo_unit": st.column_config.NumberColumn("Costo u.", format="$ %.0f")})
