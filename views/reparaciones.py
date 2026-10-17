from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from core import db, ui

ss = st.session_state
SIGUIENTE = {"Para enviar": "En reparación", "En reparación": "Reparado", "Reparado": "Devuelto", "Sin solución": "Devuelto"}
MARCAS = ["Samsung", "Apple", "Motorola", "Xiaomi", "TCL", "Nokia", "LG", "Huawei", "Alcatel", "ZTE", "Otra"]


def calc(r: pd.DataFrame) -> pd.DataFrame:
    r = r.copy()
    for c in ["presupuesto", "senia", "costo_repuesto", "mano_obra", "cobrado"]:
        r[c] = r[c].fillna(0)
    r["costo_total"] = r["costo_repuesto"] + r["mano_obra"]
    r["saldo"] = (r["presupuesto"] - r["senia"]).clip(lower=0)
    r["ganancia_est"] = r["presupuesto"] - r["costo_total"]
    r["ganancia_real"] = (r["cobrado"] - r["costo_total"]).where(r["estado"] == "Devuelto")
    r["dias"] = (datetime.now() - pd.to_datetime(r["fecha_ingreso"])).dt.days
    return r


CONDICIONES_DEFAULT = ("El presupuesto puede variar si se detectan fallas adicionales; cualquier cambio se consulta previamente al cliente. "
                       "Pasados 90 días desde el aviso de equipo listo, el local no se responsabiliza por el mismo. "
                       "No nos hacemos responsables por la información contenida en el equipo ni por chips o memorias no declarados. "
                       "Para retirar el equipo es indispensable presentar esta orden.")


def orden_html(r: dict) -> str:
    """Orden de reparación en A4 apaisada: copia LOCAL a la izquierda y copia CLIENTE a la derecha."""
    neg = ui.esc(db.get_config("negocio"))
    dire = ui.esc(db.get_config("direccion"))
    tel_local = ui.esc(db.get_config("telefono_local"))
    cond = ui.esc(db.get_config("condiciones") or CONDICIONES_DEFAULT)
    ingreso = pd.to_datetime(r["fecha_ingreso"])
    pres = float(r["presupuesto"] or 0)
    senia = float(r["senia"] or 0)
    saldo = max(pres - senia, 0)
    nro = f"{int(r['id']):06d}"
    contacto = " · ".join(x for x in [dire, tel_local] if x)

    def fila(lbl, val, grande=False):
        return f"<tr><th>{lbl}</th><td class='{'big' if grande else ''}'>{val or '&nbsp;'}</td></tr>"

    def copia(tipo: str) -> str:
        es_local = tipo == "local"
        etiqueta = "COPIA LOCAL" if es_local else "COPIA CLIENTE"
        extra = ""
        if es_local:
            extra = f"""
            <div class="sec">Uso interno</div>
            <table class="t">
              {fila("Costo repuesto", ui.ars(r.get("costo_repuesto") or 0) if r.get("costo_repuesto") else "")}
              {fila("Técnico / envío a", "")}
              {fila("Notas", ui.esc(r.get("notas") or ""))}
            </table>
            <div class="firmas"><div>Firma y aclaración del cliente<br><small>Acepto presupuesto y condiciones</small></div></div>"""
        else:
            extra = f"""
            <div class="cond"><b>Condiciones:</b> {cond}</div>
            <div class="firmas"><div>Firma y sello del local</div></div>"""
        return f"""
        <section class="copia">
          <header>
            <div><div class="neg">{neg}</div><div class="sub">{contacto or "Servicio técnico"}</div></div>
            <div class="nro"><span>ORDEN N°</span><b>{nro}</b><em>{etiqueta}</em></div>
          </header>
          <div class="fecha">Ingreso: <b>{ingreso:%d/%m/%Y %H:%M}</b></div>
          <div class="sec">Cliente</div>
          <table class="t">
            {fila("Nombre", ui.esc(r.get("cliente")))}
            {fila("Teléfono", ui.esc(r.get("telefono")))}
          </table>
          <div class="sec">Equipo</div>
          <table class="t">
            {fila("Marca / Modelo", f"{ui.esc(r.get('marca'))} {ui.esc(r.get('modelo'))}", True)}
            {fila("IMEI / Serie", ui.esc(r.get("imei")))}
            {fila("Deja con", ui.esc(r.get("accesorios")))}
            {fila("Reparación / falla", ui.esc(r.get("falla")))}
          </table>
          <div class="importes">
            <div><span>Presupuesto</span><b>{ui.ars(pres)}</b></div>
            <div><span>Seña</span><b>{ui.ars(senia)}</b></div>
            <div class="saldo"><span>Saldo a pagar</span><b>{ui.ars(saldo)}</b></div>
          </div>
          {extra}
        </section>"""

    return f"""<!doctype html><html><head><meta charset='utf-8'><title>Orden {nro}</title>
<style>
@page {{ size: A4 landscape; margin: 7mm; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; }}
body {{ font-family: Arial, Helvetica, sans-serif; color: #111; font-size: 10.5pt; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
.hoja {{ width: 283mm; height: 195mm; display: flex; margin: 0 auto; }}
.copia {{ width: 50%; height: 100%; padding: 4mm 7mm; display: flex; flex-direction: column; overflow: hidden; }}
.corte {{ width: 0; border-left: 1.5px dashed #777; position: relative; }}
.corte span {{ position: absolute; top: 50%; left: -9px; transform: rotate(-90deg); transform-origin: center; font-size: 8pt; color: #777; white-space: nowrap; background: #fff; padding: 0 4px; translate: -42% 0; }}
header {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2.5px solid #111; padding-bottom: 3mm; }}
.neg {{ font-size: 16pt; font-weight: 800; letter-spacing: -.3px; }}
.sub {{ font-size: 8.5pt; color: #444; margin-top: 1mm; }}
.nro {{ text-align: right; border: 2px solid #111; border-radius: 6px; padding: 1.5mm 3mm; min-width: 38mm; }}
.nro span {{ display: block; font-size: 7pt; letter-spacing: 1px; }}
.nro b {{ display: block; font-size: 17pt; font-family: 'Courier New', monospace; }}
.nro em {{ display: block; font-style: normal; font-size: 7.5pt; font-weight: 700; background: #111; color: #fff; text-align: center; margin: 1mm -3mm -1.5mm; padding: .6mm 0; border-radius: 0 0 4px 4px; }}
.fecha {{ margin: 2.5mm 0 1mm; font-size: 9.5pt; }}
.sec {{ margin-top: 2.5mm; font-size: 7.5pt; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase; color: #555; }}
.t {{ width: 100%; border-collapse: collapse; margin-top: .8mm; }}
.t th {{ width: 34mm; text-align: left; font-weight: 600; font-size: 8.5pt; color: #333; vertical-align: top; padding: 1.4mm 0; }}
.t td {{ border-bottom: 1px solid #bbb; padding: 1.4mm 1mm; vertical-align: top; }}
.t td.big {{ font-weight: 700; font-size: 11.5pt; }}
.importes {{ display: flex; gap: 2mm; margin-top: 3.5mm; }}
.importes div {{ flex: 1; border: 1.2px solid #111; border-radius: 5px; padding: 1.5mm 2mm; }}
.importes span {{ display: block; font-size: 7.5pt; color: #444; }}
.importes b {{ font-size: 12pt; }}
.importes .saldo {{ background: #111; color: #fff; }}
.importes .saldo span {{ color: #ddd; }}
.cond {{ margin-top: 3mm; font-size: 7.5pt; line-height: 1.35; color: #333; text-align: justify; }}
.firmas {{ margin-top: auto; display: flex; justify-content: flex-end; padding-top: 6mm; }}
.firmas div {{ width: 62mm; border-top: 1px solid #111; text-align: center; font-size: 8pt; padding-top: 1mm; }}
.firmas small {{ color: #555; }}
.no-print {{ text-align: center; padding: 10px; font-family: Arial; background: #f3f3f3; }}
.no-print button {{ font-size: 14px; padding: 8px 18px; cursor: pointer; }}
@media print {{ .no-print {{ display: none; }} }}
</style></head>
<body onload="setTimeout(() => window.print(), 300)">
<div class="no-print">Configurá la impresión en <b>A4 · Horizontal</b> y márgenes <b>Ninguno/Predeterminados</b>. <button onclick="window.print()">🖨️ Imprimir</button></div>
<div class="hoja">
  {copia("local")}
  <div class="corte"><span>✂ cortar por aquí</span></div>
  {copia("cliente")}
</div>
</body></html>"""


@st.dialog("Orden de servicio", width="large")
def abrir(rid: int):
    r = db.get_reparacion(rid)
    if not r:
        st.error("No existe")
        return
    st.markdown(f"### #{r['id']} · {ui.esc(r['marca'])} {ui.esc(r['modelo'])} &nbsp; {ui.chip(r['estado'])}",
                unsafe_allow_html=True)
    st.caption(f"{r['cliente']} · {r['telefono'] or 's/tel'} · ingresó {pd.to_datetime(r['fecha_ingreso']):%d/%m/%Y}")
    with st.form(f"edit_{rid}"):
        a, b, c = st.columns(3)
        estado = a.selectbox("Estado", db.ESTADOS, index=db.ESTADOS.index(r["estado"]))
        presupuesto = b.number_input("Presupuesto", min_value=0.0, step=1000.0, format="%.0f", value=float(r["presupuesto"] or 0))
        senia = c.number_input("Seña", min_value=0.0, step=1000.0, format="%.0f", value=float(r["senia"] or 0))
        d, e, f = st.columns(3)
        repuesto = d.number_input("Costo repuesto", min_value=0.0, step=1000.0, format="%.0f", value=float(r["costo_repuesto"] or 0))
        mo = e.number_input("Mano de obra", min_value=0.0, step=1000.0, format="%.0f", value=float(r["mano_obra"] or 0))
        default_cobro = float(r["cobrado"] or 0) or (float(r["presupuesto"] or 0) if r["resultado"] != "Sin solución" else float(r["senia"] or 0))
        cobrado = f.number_input("Total cobrado al entregar", min_value=0.0, step=1000.0, format="%.0f", value=default_cobro,
                                 help="Se usa para la ganancia real cuando el estado es Devuelto")
        falla = st.text_area("Reparación a realizar", value=r["falla"] or "", height=80)
        g, h = st.columns(2)
        cliente = g.text_input("Cliente", value=r["cliente"] or "")
        tel = h.text_input("Teléfono", value=r["telefono"] or "")
        nota = st.text_input("Nota para el historial (opcional)")
        costo_tot = repuesto + mo
        st.markdown(f"**Costo total:** {ui.mars(costo_tot)} · **Ganancia estimada:** "
                    f"<span style='color:#D4FF3A'>{ui.mars(presupuesto - costo_tot)}</span> · **Saldo a cobrar:** {ui.mars(max(presupuesto - senia, 0))}",
                    unsafe_allow_html=True)
        guardar = st.form_submit_button("Guardar cambios", type="primary", width="stretch")
    if guardar:
        db.actualizar_reparacion(rid, nota=nota, estado=estado, presupuesto=presupuesto, senia=senia,
                                 costo_repuesto=repuesto, mano_obra=mo, cobrado=cobrado if estado == "Devuelto" else r["cobrado"],
                                 falla=falla, cliente=cliente, telefono=tel)
        st.rerun()

    x1, x2 = st.columns(2)
    x1.download_button("🖨️ Imprimir orden (2 copias A4)", orden_html(r), f"orden_{rid:06d}.html", "text/html", width="stretch")
    with x2.popover("🗑️ Eliminar", width="stretch"):
        st.write("¿Seguro? No se puede deshacer.")
        if st.button("Sí, eliminar", type="primary"):
            db.eliminar_reparacion(rid)
            st.rerun()
    log = db.log_reparacion(rid)
    if not log.empty:
        st.markdown("##### Historial")
        for _, l in log.iterrows():
            st.markdown(f"<span class='muted'>{pd.to_datetime(l['fecha']):%d/%m %H:%M}</span> &nbsp; {ui.chip(l['estado'])} "
                        f"&nbsp; {ui.esc(l['nota'] or '')}", unsafe_allow_html=True)


def avanzar(rid: int, estado_actual: str, alt: bool = False):
    nuevo = "Sin solución" if alt else SIGUIENTE[estado_actual]
    extra = {}
    if nuevo == "Devuelto":
        r = db.get_reparacion(rid)
        if not r["cobrado"]:
            extra["cobrado"] = r["presupuesto"] if r["estado"] == "Reparado" else (r["senia"] or 0)
    db.actualizar_reparacion(rid, estado=nuevo, nota="Cambio rápido desde tablero", **extra)


ui.hero("Operación · Servicio técnico", "Reparaciones", "Del mostrador al taller y de vuelta al cliente, todo trazado.")

raw = db.reparaciones_df()
rep = calc(raw) if not raw.empty else raw

if not rep.empty:
    taller = rep[rep["estado"].isin(["Para enviar", "En reparación"])]
    listos = rep[rep["estado"].isin(["Reparado", "Sin solución"])]
    mes = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    dev_mes = rep[(rep["estado"] == "Devuelto") & (pd.to_datetime(rep["fecha_entrega"]) >= mes)]
    ui.kpis([
        ("En taller", ui.num(len(taller)), f"<b>{ui.ars(taller['presupuesto'].sum())}</b> presupuestado", ui.CYAN),
        ("Listos para retirar", ui.num(len(listos)), f"saldo a cobrar <b>{ui.ars(listos['saldo'].sum())}</b>", ui.LIME),
        ("Señas en mano", ui.ars(rep[rep["estado"] != "Devuelto"]["senia"].sum()), "de equipos sin entregar", ui.AMBER),
        ("Facturado este mes", ui.ars(dev_mes["cobrado"].sum()), f"<b>{len(dev_mes)}</b> entregados", ui.VIOLET),
        ("Ganancia este mes", ui.ars(dev_mes["ganancia_real"].sum()),
         f"costo {ui.ars(dev_mes['costo_total'].sum())}", ui.PINK),
    ])

tab_k, tab_n, tab_l = st.tabs(["🧩 Tablero", "➕ Nuevo ingreso", "📋 Listado e importes"])

with tab_k:
    if rep.empty:
        st.info("Sin reparaciones cargadas. Arrancá en *Nuevo ingreso*.")
    else:
        b1, b2 = st.columns([3, 1])
        q = b1.text_input("Buscar", placeholder="Cliente, modelo, IMEI o #orden", label_visibility="collapsed")
        dias_dev = b2.selectbox("Devueltos", [7, 30, 90], format_func=lambda d: f"Devueltos últimos {d} días",
                                label_visibility="collapsed")
        k = rep.copy()
        if q:
            m = (k["cliente"].str.contains(q, case=False, na=False) | k["modelo"].str.contains(q, case=False, na=False)
                 | k["imei"].fillna("").str.contains(q, case=False) | (k["id"].astype(str) == q.strip("#")))
            k = k[m]
        k = k[(k["estado"] != "Devuelto") | (pd.to_datetime(k["fecha_entrega"]) >= datetime.now() - timedelta(days=dias_dev))]
        cols = st.columns(len(db.ESTADOS), gap="small")
        for col, est in zip(cols, db.ESTADOS):
            sub = k[k["estado"] == est]
            with col:
                st.markdown(f"<div class='kcol-h' style='--c:{ui.ESTADO_COLOR[est]}'><span>{est}</span>"
                            f"<span>{len(sub)}</span></div>", unsafe_allow_html=True)
                st.caption(ui.ars(sub["presupuesto"].sum()))
                for _, r in sub.head(30).iterrows():
                    st.markdown(
                        f"""<div class='kcard'><div class='m'>#{r['id']} · {ui.esc(r['marca'])} {ui.esc(r['modelo'])}</div>
                        <div class='c'>{ui.esc(r['cliente'])} · {r['dias']}d</div>
                        <div class='f'>{ui.esc((r['falla'] or '')[:70])}</div>
                        <div class='n'><span>Pres. <b>{ui.ars(r['presupuesto'])}</b></span><span>Seña <b>{ui.ars(r['senia'])}</b></span></div></div>""",
                        unsafe_allow_html=True)
                    c1, c2 = st.columns(2)
                    if c1.button("Abrir", key=f"ab_{r['id']}", width="stretch"):
                        abrir(int(r["id"]))
                    if est in SIGUIENTE:
                        lbl = {"Para enviar": "Enviar →", "En reparación": "Listo ✓", "Reparado": "Entregar",
                               "Sin solución": "Entregar"}[est]
                        c2.button(lbl, key=f"av_{r['id']}", width="stretch", type="primary",
                                  on_click=avanzar, args=(int(r["id"]), est))
                    if est == "En reparación":
                        st.button("✕ Sin solución", key=f"ss_{r['id']}", width="stretch",
                                  on_click=avanzar, args=(int(r["id"]), est, True))

with tab_n:
    with st.container(border=True):
        with st.form("nueva_rep", clear_on_submit=True):
            st.markdown("#### Equipo")
            a, b, c = st.columns([1, 1.6, 1.4])
            marca = a.selectbox("Marca", MARCAS)
            modelo = b.text_input("Modelo", placeholder="Ej: Galaxy A54")
            imei = c.text_input("IMEI / Serie (opcional)")
            falla = st.text_area("Reparación a realizar / falla", placeholder="Ej: cambio de módulo, no carga, pin de carga…", height=80)
            accesorios = st.text_input("Deja con (opcional)", placeholder="Funda, chip, cargador…")
            st.markdown("#### Cliente")
            d, e = st.columns(2)
            cliente = d.text_input("Nombre")
            tel = e.text_input("Teléfono / WhatsApp")
            st.markdown("#### Importes")
            f, g, h, i = st.columns(4)
            presupuesto = f.number_input("Presupuesto", min_value=0.0, step=1000.0, format="%.0f")
            deja_senia = g.toggle("¿Deja seña?")
            senia = h.number_input("Monto seña", min_value=0.0, step=1000.0, format="%.0f")
            estado = i.selectbox("Estado inicial", ["Para enviar", "En reparación"])
            j, k_, _ = st.columns([1, 1, 2])
            repuesto = j.number_input("Costo repuesto (si ya lo sabés)", min_value=0.0, step=1000.0, format="%.0f")
            mo = k_.number_input("Mano de obra", min_value=0.0, step=500.0, format="%.0f", value=db.fee_mano_obra(),
                                 help="Fee general configurable en Configuración")
            ok = st.form_submit_button("Registrar ingreso", type="primary", width="stretch")
        if ok:
            if not modelo.strip() or not cliente.strip():
                st.error("Modelo y cliente son obligatorios.")
            else:
                rid = db.crear_reparacion(
                    cliente=cliente.strip(), telefono=tel.strip(), marca=marca, modelo=modelo.strip(), imei=imei.strip(),
                    falla=falla.strip(), accesorios=accesorios.strip(), presupuesto=presupuesto,
                    senia=senia if deja_senia else 0, costo_repuesto=repuesto, mano_obra=mo, estado=estado)
                st.success(f"✓ Orden #{rid} registrada")
                st.download_button("🖨️ Imprimir orden (copia local + cliente, A4)", orden_html(db.get_reparacion(rid)),
                                   f"orden_{rid:06d}.html", "text/html")

with tab_l:
    if rep.empty:
        st.info("Sin datos.")
    else:
        f1, f2, f3 = st.columns([2, 1.2, 1.2])
        estados = f1.multiselect("Estados", db.ESTADOS, default=db.ESTADOS)
        desde = f2.date_input("Ingreso desde", value=(datetime.now() - timedelta(days=90)).date())
        hasta = f3.date_input("Hasta", value=datetime.now().date())
        l = rep[rep["estado"].isin(estados) & (pd.to_datetime(rep["fecha_ingreso"]).dt.date.between(desde, hasta))]
        ui.kpis([
            ("Órdenes", ui.num(len(l)), None, ui.CYAN),
            ("Presupuestado", ui.ars(l["presupuesto"].sum()), None, ui.VIOLET),
            ("Costo (rep. + MO)", ui.ars(l["costo_total"].sum()),
             f"repuestos {ui.ars(l['costo_repuesto'].sum())} · MO {ui.ars(l['mano_obra'].sum())}", ui.AMBER),
            ("Cobrado (devueltos)", ui.ars(l["cobrado"].where(l["estado"] == "Devuelto").sum()), None, ui.LIME),
            ("Ganancia real", ui.ars(l["ganancia_real"].sum()), None, ui.PINK),
        ])
        g1, g2 = st.columns([1, 1.4])
        with g1:
            cnt = l["estado"].value_counts().reindex(db.ESTADOS).fillna(0).reset_index()
            cnt.columns = ["estado", "n"]
            fig = px.pie(cnt, names="estado", values="n", hole=.65, color="estado",
                         color_discrete_map=ui.ESTADO_COLOR, title="Órdenes por estado")
            fig.update_traces(textinfo="value")
            st.plotly_chart(fig, width="stretch")
        with g2:
            ag = l.groupby("estado")[["presupuesto", "costo_total"]].sum().reindex(db.ESTADOS).fillna(0).reset_index()
            fig = px.bar(ag, x="estado", y=["presupuesto", "costo_total"], barmode="group", title="Importes por estado",
                         color_discrete_sequence=[ui.LIME, ui.VIOLET], labels={"value": "$", "variable": ""})
            st.plotly_chart(fig, width="stretch")

        vista = l[["id", "fecha_ingreso", "cliente", "telefono", "marca", "modelo", "falla", "estado", "resultado",
                   "presupuesto", "senia", "saldo", "costo_repuesto", "mano_obra", "costo_total", "cobrado",
                   "ganancia_est", "ganancia_real", "dias"]]
        money = {c: st.column_config.NumberColumn(c.replace("_", " ").capitalize(), format="$ %.0f")
                 for c in ["presupuesto", "senia", "saldo", "costo_repuesto", "mano_obra", "costo_total", "cobrado",
                           "ganancia_est", "ganancia_real"]}
        evt = st.dataframe(vista, hide_index=True, width="stretch", height=440, on_select="rerun",
                           selection_mode="single-row", key="rep_tabla",
                           column_config={"id": st.column_config.NumberColumn("#", format="%d"),
                                          "fecha_ingreso": st.column_config.DatetimeColumn("Ingreso", format="DD/MM/YY"),
                                          **money})
        sel_rows = evt.selection.rows
        if sel_rows:
            rid_sel = int(vista.iloc[sel_rows[0]]["id"])
            if ss.get("rep_last_sel") != rid_sel:
                ss.rep_last_sel = rid_sel
                abrir(rid_sel)
        else:
            ss.rep_last_sel = None
        st.download_button("⬇️ Exportar CSV", vista.to_csv(index=False).encode("utf-8-sig"), "reparaciones.csv")
