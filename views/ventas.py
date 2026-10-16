from datetime import datetime

import streamlit as st

from core import db, ui

SCAN_LABEL = "Escaneá o tipeá el código de barras"

ss = st.session_state
ss.setdefault("cart", {})
ss.setdefault("no_encontrado", None)
ss.setdefault("ultima_venta", None)


def add_to_cart(p: dict, qty: int = 1):
    pid = p["id"]
    if pid in ss.cart:
        ss.cart[pid]["cantidad"] += qty
    else:
        ss.cart[pid] = {
            "id": pid, "codigo": p["codigo"], "nombre": p["nombre"], "categoria": p["categoria"],
            "precio": float(p["precio"]), "costo": float(p["costo"]), "cantidad": qty, "stock": int(p["stock"]),
        }
        ss[f"p_{pid}"] = float(p["precio"])
    ss[f"q_{pid}"] = ss.cart[pid]["cantidad"]


def remove(pid):
    ss.cart.pop(pid, None)


def sync_qty(pid):
    ss.cart[pid]["cantidad"] = int(ss[f"q_{pid}"])


def sync_price(pid):
    ss.cart[pid]["precio"] = float(ss[f"p_{pid}"])


def on_search():
    sel = ss.get("buscador")
    if sel is not None:
        p = db.buscar_por_codigo(sel)
        if p:
            add_to_cart(p)
    ss.buscador = None


def vaciar():
    for pid in list(ss.cart):
        ss.pop(f"q_{pid}", None)
        ss.pop(f"p_{pid}", None)
    ss.cart = {}


ui.hero("Operación · Caja", "Punto de venta", "Apuntá con la pistola y disparás. El código entra solo.")

izq, der = st.columns([1.75, 1], gap="large")

with izq:
    with st.form("scan", clear_on_submit=True, border=False):
        c1, c2 = st.columns([5, 1])
        codigo = c1.text_input(SCAN_LABEL, placeholder="▌ Esperando lectura…", label_visibility="collapsed")
        enviar = c2.form_submit_button("Agregar", width="stretch", type="primary")
    st.markdown('<div class="scan-hint"><span class="pulse"></span>Escáner listo · también podés tipear el código y Enter</div>',
                unsafe_allow_html=True)

    if enviar and codigo.strip():
        p = db.buscar_por_codigo(codigo)
        if p:
            add_to_cart(p)
            ss.no_encontrado = None
            if not p["activo"]:
                st.toast(f"⚠️ {p['nombre']} está marcado como inactivo")
        else:
            ss.no_encontrado = codigo.strip()

    prods = db.listar_productos()
    if not prods.empty:
        opciones = dict(zip(prods["codigo"], prods["nombre"] + "  ·  " + prods["codigo"] +
                            "  ·  " + prods["precio"].map(ui.ars) + "  ·  stock " + prods["stock"].astype(str)))
        st.selectbox("Buscar producto por nombre", options=list(opciones), index=None,
                     format_func=lambda k: opciones.get(k, k), key="buscador", on_change=on_search,
                     placeholder="🔎 Buscar por nombre si no tiene código…", label_visibility="collapsed")

    if ss.no_encontrado:
        with st.container(border=True):
            st.markdown(f"#### Código `{ui.esc(ss.no_encontrado)}` no existe — ¿lo damos de alta ahora?")
            with st.form("alta_rapida", clear_on_submit=True):
                a1, a2 = st.columns([2, 1])
                nombre = a1.text_input("Nombre del artículo")
                cat = a2.selectbox("Categoría", db.categorias())
                b1, b2, b3 = st.columns(3)
                costo = b1.number_input("Costo", min_value=0.0, step=100.0, format="%.0f")
                precio = b2.number_input("Precio venta", min_value=0.0, step=100.0, format="%.0f")
                stock = b3.number_input("Stock inicial", min_value=0, step=1, value=1)
                g1, g2 = st.columns(2)
                ok = g1.form_submit_button("Crear y agregar al carrito", type="primary", width="stretch")
                cancel = g2.form_submit_button("Cancelar", width="stretch")
            if ok:
                if not nombre.strip():
                    st.error("Poné un nombre")
                else:
                    db.crear_producto(ss.no_encontrado, nombre, cat, costo, precio, stock)
                    add_to_cart(db.buscar_por_codigo(ss.no_encontrado))
                    ss.no_encontrado = None
                    st.rerun()
            if cancel:
                ss.no_encontrado = None
                st.rerun()

    # ---------- Carrito ----------
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        n_items = sum(i["cantidad"] for i in ss.cart.values())
        h1, h2 = st.columns([4, 1])
        h1.markdown(f"### Carrito <span class='muted' style='font-size:1rem'>· {n_items} unidades</span>", unsafe_allow_html=True)
        if ss.cart:
            h2.button("Vaciar", on_click=vaciar, width="stretch")
        if not ss.cart:
            st.markdown("<div class='muted' style='padding:28px 0;text-align:center'>Todavía no hay productos. "
                        "Escaneá el primero 👆</div>", unsafe_allow_html=True)
        for pid, it in list(ss.cart.items()):
            c = st.columns([3.6, 1.6, 1.1, 1.4, 0.5], vertical_alignment="center")
            alerta = " · <span style='color:#FF4D8D'>sin stock suficiente</span>" if it["cantidad"] > it["stock"] else ""
            c[0].markdown(f"<div class='cart-name'>{ui.esc(it['nombre'])}</div>"
                          f"<div class='cart-meta'>{ui.esc(it['codigo'])} · stock {it['stock']}{alerta}</div>",
                          unsafe_allow_html=True)
            c[1].number_input("Precio", key=f"p_{pid}", min_value=0.0, step=100.0, format="%.0f", on_change=sync_price,
                              args=(pid,), label_visibility="collapsed")
            c[2].number_input("Cant", key=f"q_{pid}", min_value=1, step=1, on_change=sync_qty,
                              args=(pid,), label_visibility="collapsed")
            c[3].markdown(f"<div style='text-align:right;font-family:Space Grotesk,Inter,sans-serif;font-weight:700;font-size:1.1rem'>"
                          f"{ui.ars(it['precio'] * it['cantidad'])}</div>", unsafe_allow_html=True)
            c[4].button("", icon=":material/delete:", key=f"rm_{pid}", on_click=remove, args=(pid,), help="Quitar")

with der:
    subtotal = sum(i["precio"] * i["cantidad"] for i in ss.cart.values())
    costo = sum(i["costo"] * i["cantidad"] for i in ss.cart.values())

    with st.container(border=True):
        st.markdown("### Cobro")
        medio = st.segmented_control("Medio de pago", db.MEDIOS_PAGO, default="Efectivo", key="medio")
        d1, d2 = st.columns(2)
        tipo_desc = d1.radio("Descuento", ["$", "%"], horizontal=True, key="tipo_desc")
        val_desc = d2.number_input("Valor", min_value=0.0, step=1.0 if tipo_desc == "%" else 100.0, key="val_desc")
        descuento = subtotal * min(val_desc, 100) / 100 if tipo_desc == "%" else min(val_desc, subtotal)
        cliente = st.text_input("Cliente (opcional)", key="cliente")
        total = subtotal - descuento
        ganancia = total - costo
        st.markdown(
            f"""<div class="total-box"><div class="t-lbl">Total a cobrar</div>
            <div class="t-val">{ui.ars(total)}</div>
            <div class="t-sub">Subtotal {ui.ars(subtotal)} · Desc. {ui.ars(descuento)}</div></div>""",
            unsafe_allow_html=True)
        if medio == "Efectivo" and ss.cart:
            paga = st.number_input("Paga con", min_value=0.0, step=1000.0, format="%.0f", key="paga_con")
            if paga:
                st.markdown(f"**Vuelto:** <span style='color:#D4FF3A;font-size:1.3rem;font-family:Space Grotesk'>"
                            f"{ui.mars(paga - total)}</span>", unsafe_allow_html=True)
        st.caption(f"Ganancia estimada de esta venta: {ui.ars(ganancia)}"
                   f"{f' ({ganancia / total:.0%})' if total else ''}")

        if st.button("✓  Confirmar venta", type="primary", width="stretch", disabled=not ss.cart):
            items = list(ss.cart.values())
            vid = db.registrar_venta(items, medio or "Efectivo", descuento, cliente)
            ss.ultima_venta = {"id": vid, "items": items, "total": total, "subtotal": subtotal,
                               "descuento": descuento, "medio": medio, "cliente": cliente,
                               "fecha": datetime.now().strftime("%d/%m/%Y %H:%M")}
            vaciar()
            for k in ("val_desc", "cliente", "paga_con"):
                ss.pop(k, None)
            st.rerun()

    if ss.ultima_venta:
        v = ss.ultima_venta
        st.success(f"Venta #{v['id']} registrada · {ui.mars(v['total'])}")
        filas = "".join(f"<tr><td>{i['cantidad']} x {ui.esc(i['nombre'])}</td>"
                        f"<td style='text-align:right'>{ui.ars(i['precio'] * i['cantidad'])}</td></tr>" for i in v["items"])
        ticket = f"""<html><head><meta charset='utf-8'><title>Ticket {v['id']}</title>
        <style>body{{font-family:monospace;width:280px;margin:auto}}td{{padding:2px 0}}h2,p{{text-align:center;margin:4px}}</style></head>
        <body onload='window.print()'><h2>{ui.esc(db.get_config('negocio'))}</h2><p>Ticket #{v['id']} · {v['fecha']}</p>
        <p>{ui.esc(v['cliente'] or '')}</p><hr><table width='100%'>{filas}</table><hr>
        <table width='100%'><tr><td>Subtotal</td><td style='text-align:right'>{ui.ars(v['subtotal'])}</td></tr>
        <tr><td>Descuento</td><td style='text-align:right'>-{ui.ars(v['descuento'])}</td></tr>
        <tr><td><b>TOTAL</b></td><td style='text-align:right'><b>{ui.ars(v['total'])}</b></td></tr></table>
        <p>Pago: {ui.esc(v['medio'])}</p><p>¡Gracias por tu compra!</p><p style='font-size:10px'>Comprobante no válido como factura</p></body></html>"""
        b1, b2 = st.columns(2)
        b1.download_button("🧾 Ticket", ticket, file_name=f"ticket_{v['id']}.html", mime="text/html",
                           width="stretch")
        if b2.button("Cerrar", width="stretch"):
            ss.ultima_venta = None
            st.rerun()

    # Mini resumen del día
    hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    vd = db.ventas_df(hoy, datetime.now())
    tot_hoy = vd["total"].sum() if not vd.empty else 0
    gan_hoy = (vd["total"] - vd["costo_total"]).sum() if not vd.empty else 0
    ui.kpis([("Vendido hoy", ui.ars(tot_hoy), f"<b>{len(vd)}</b> tickets", ui.LIME),
             ("Ganancia hoy", ui.ars(gan_hoy), None, ui.VIOLET)])

if not ss.no_encontrado:
    ui.autofocus("Escaneá")
