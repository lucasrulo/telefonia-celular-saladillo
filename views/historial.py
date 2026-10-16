import io
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from core import db, ui

ui.hero("Análisis", "Historial de ventas", "Buscá tickets, mirá el detalle y anulá si hace falta (devuelve el stock).")

c1, c2, c3 = st.columns([1, 1, 1.4])
desde = c1.date_input("Desde", value=(datetime.now() - timedelta(days=7)).date())
hasta = c2.date_input("Hasta", value=datetime.now().date())
ver_anuladas = c3.toggle("Mostrar anuladas")
v = db.ventas_df(datetime.combine(desde, datetime.min.time()), datetime.combine(hasta, datetime.max.time()),
                 incluir_anuladas=ver_anuladas)

if v.empty:
    st.info("Sin ventas en el rango.")
    st.stop()

v["ganancia"] = v["total"] - v["costo_total"]
ok = v[v["anulada"] == False]  # noqa: E712
ui.kpis([("Tickets", ui.num(len(ok)), None, ui.CYAN), ("Total", ui.ars(ok["total"].sum()), None, ui.LIME),
         ("Ganancia", ui.ars(ok["ganancia"].sum()), None, ui.VIOLET),
         ("Descuentos otorgados", ui.ars(ok["descuento"].sum()), None, ui.PINK)])

evt = st.dataframe(
    v[["id", "fecha", "cliente", "medio_pago", "subtotal", "descuento", "total", "ganancia", "anulada"]],
    hide_index=True, width="stretch", height=380, on_select="rerun", selection_mode="single-row",
    column_config={"id": st.column_config.NumberColumn("#", format="%d"),
                   "fecha": st.column_config.DatetimeColumn("Fecha", format="DD/MM/YY HH:mm"),
                   **{c: st.column_config.NumberColumn(c.capitalize(), format="$ %.0f")
                      for c in ["subtotal", "descuento", "total", "ganancia"]}})

if evt.selection.rows:
    row = v.iloc[evt.selection.rows[0]]
    with st.container(border=True):
        st.markdown(f"### Ticket #{int(row['id'])} · {ui.ars(row['total'])}"
                    f"{' · <span style=color:#FF4D8D>ANULADA</span>' if row['anulada'] else ''}", unsafe_allow_html=True)
        det = db.items_de_venta(int(row["id"]))
        det["subtotal"] = det["cantidad"] * det["precio_unit"]
        st.dataframe(det[["codigo", "nombre", "cantidad", "precio_unit", "costo_unit", "subtotal"]], hide_index=True,
                     width="stretch",
                     column_config={c: st.column_config.NumberColumn(format="$ %.0f") for c in ["precio_unit", "costo_unit", "subtotal"]})
        if not row["anulada"]:
            with st.popover("Anular venta"):
                st.write("Se devuelve el stock de todos los artículos.")
                if st.button("Confirmar anulación", type="primary"):
                    db.anular_venta(int(row["id"]))
                    st.rerun()

buf = io.BytesIO()
with pd.ExcelWriter(buf) as xw:
    v.to_excel(xw, sheet_name="ventas", index=False)
    db.items_df(datetime.combine(desde, datetime.min.time()),
                datetime.combine(hasta, datetime.max.time())).to_excel(xw, sheet_name="detalle", index=False)
st.download_button("⬇️ Exportar Excel (ventas + detalle)", buf.getvalue(), f"ventas_{desde}_{hasta}.xlsx")
