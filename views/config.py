import io
import random
import zipfile
from datetime import datetime, timedelta

import streamlit as st

from core import db, storage, ui

ui.hero("Sistema", "Configuración", "Nombre del local, fee de mano de obra y categorías.")

with st.container(border=True):
    with st.form("cfg"):
        a, b = st.columns(2)
        negocio = a.text_input("Nombre del negocio", value=db.get_config("negocio"))
        fee = b.number_input("Fee general de mano de obra por reparación ($)", min_value=0.0, step=500.0, format="%.0f",
                             value=db.fee_mano_obra(), help="Se precarga en cada reparación nueva; podés cambiarlo caso por caso.")
        cats = st.text_area("Categorías (separadas por coma)", value=db.get_config("categorias"))
        if st.form_submit_button("Guardar", type="primary"):
            db.set_config("negocio", negocio.strip() or "CeluPOS")
            db.set_config("fee_mano_obra", fee)
            db.set_config("categorias", ",".join(c.strip() for c in cats.split(",") if c.strip()))
            st.toast("✓ Configuración guardada")
            st.rerun()

with st.container(border=True):
    st.markdown("#### 💾 Datos y respaldo")
    est = storage.estado()
    if est["habilitado"]:
        c = storage.cfg()
        st.markdown(f"Los datos se guardan como CSV en el repo privado **{c['repo']}** (carpeta `{c['folder']}/`). "
                    "Cada cambio es un commit: tenés el historial completo y podés volver a cualquier versión.")
    else:
        st.warning("Guardado sólo en esta computadora (carpeta data/). Configurá GITHUB_TOKEN y DATA_REPO para tener respaldo en GitHub.")
    b1, b2 = st.columns(2)
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        for n, t in db.exportar_csv().items():
            z.writestr(f"{n}.csv", t)
    b1.download_button("⬇️ Descargar backup (CSV en .zip)", zbuf.getvalue(),
                       f"celupos_backup_{datetime.now():%Y%m%d_%H%M}.zip", width="stretch")
    if est["habilitado"] and b2.button("☁️ Forzar guardado completo", width="stretch"):
        db.persistir_todo("Guardado completo manual")
        st.toast("✓ Guardado") if not storage.estado()["error"] else st.error(storage.estado()["error"])

with st.container(border=True):
    st.markdown("#### 🔫 Pistola lectora")
    st.markdown("""
- Cualquier lector **USB o Bluetooth en modo teclado (HID)** funciona sin drivers: lee el código y manda *Enter*.
- Configurá el lector con sufijo **Enter / CR** (viene así de fábrica en el 95% de los casos).
- En *Punto de venta* el campo de escaneo queda con foco automático: disparás y el producto entra al carrito.
- Si escaneás un código que no existe, la caja te ofrece darlo de alta en el momento.
""")

# La carga demo sólo existe sin GitHub, para no mezclar datos de prueba con los reales
if not storage.habilitado():
    with st.container(border=True):
        st.markdown("#### 🧪 Datos de demostración")
        st.caption("Carga productos, ventas de los últimos 60 días y reparaciones de ejemplo para ver el dashboard. "
                   "Usalo solo en una base vacía.")
        if st.button("Cargar datos demo"):
            with db.lote("Carga de datos demo"):
                rnd = random.Random(7)
                demo = [
                    ("Celulares", "Samsung Galaxy A15 128GB", 180000, 239999), ("Celulares", "Motorola Moto G24 128GB", 150000, 199999),
                    ("Celulares", "Xiaomi Redmi 13C 128GB", 140000, 189999), ("Celulares", "iPhone 13 128GB (reacond.)", 520000, 689999),
                    ("Fundas", "Funda silicona iPhone 13", 2500, 8999), ("Fundas", "Funda antigolpe Galaxy A15", 2200, 7999),
                    ("Templados", "Vidrio templado 9D universal", 600, 3999), ("Templados", "Templado privacidad iPhone", 1500, 6999),
                    ("Cargadores", "Cargador 20W USB-C", 4500, 12999), ("Cargadores", "Cargador 33W carga rápida", 6000, 16999),
                    ("Cables", "Cable USB-C a USB-C 1m", 1200, 4999), ("Cables", "Cable Lightning 1m", 1500, 5999),
                    ("Auriculares", "Auriculares Bluetooth TWS", 7000, 19999), ("Auriculares", "Auriculares cable 3.5mm", 1500, 4999),
                    ("Accesorios", "Soporte auto magnético", 2500, 8999), ("Accesorios", "Power bank 10.000mAh", 9000, 22999),
                    ("Repuestos", "Módulo Samsung A15", 25000, 0), ("Repuestos", "Batería Moto G24", 9000, 0),
                ]
                for i, (cat, nom, costo, precio) in enumerate(demo):
                    cod = f"77900{i:08d}"
                    if not db.buscar_por_codigo(cod):
                        db.crear_producto(cod, nom, cat, costo, precio, rnd.randint(2, 40), 3)
                prods = db.listar_productos()
                vendibles = prods[prods["precio"] > 0].to_dict("records")
                from sqlalchemy import update
                for d in range(60, -1, -1):
                    for _ in range(rnd.randint(3, 12)):
                        items = []
                        for p in rnd.sample(vendibles, rnd.randint(1, 3)):
                            if p["categoria"] == "Celulares" and rnd.random() > .25:
                                continue  # los celulares se venden menos seguido
                            items.append({**p, "cantidad": rnd.randint(1, 2)})
                        if not items:
                            continue
                        vid = db.registrar_venta(items, rnd.choice(db.MEDIOS_PAGO), 0, "")
                        fecha = (datetime.now() - timedelta(days=d)).replace(hour=rnd.randint(9, 20), minute=rnd.randint(0, 59))
                        with db.get_engine().begin() as c:
                            c.execute(update(db.ventas).where(db.ventas.c.id == vid).values(fecha=fecha))
                with db.get_engine().begin() as c:  # reponer stock realista tras las ventas demo
                    for pid in prods["id"]:
                        c.execute(update(db.productos).where(db.productos.c.id == int(pid)).values(stock=rnd.choice([0, 1, 2, 4, 6, 8, 12, 15, 20])))
                modelos = [("Samsung", "Galaxy A32", "Cambio de módulo"), ("Apple", "iPhone 11", "Cambio de batería"),
                           ("Motorola", "Moto G60", "Pin de carga"), ("Xiaomi", "Redmi Note 10", "No enciende"),
                           ("Samsung", "Galaxy S21", "Vidrio trasero"), ("Apple", "iPhone XR", "Face ID"),
                           ("Motorola", "Moto E22", "Cambio de módulo"), ("TCL", "30 SE", "Software / flasheo")]
                nombres = ["Juan Pérez", "María Gómez", "Lucía Fernández", "Carlos Díaz", "Sofía López", "Martín Ruiz", "Ana Torres", "Diego Silva"]
                for i in range(16):
                    ma, mo, fa = rnd.choice(modelos)
                    pres = rnd.choice([25000, 35000, 45000, 60000, 85000])
                    rid = db.crear_reparacion(cliente=rnd.choice(nombres), telefono=f"11{rnd.randint(40000000, 69999999)}", marca=ma,
                                              modelo=mo, falla=fa, presupuesto=pres, senia=rnd.choice([0, 0, 10000, 15000]),
                                              costo_repuesto=round(pres * rnd.uniform(.25, .45), -2), mano_obra=db.fee_mano_obra())
                    with db.get_engine().begin() as c:
                        c.execute(update(db.reparaciones).where(db.reparaciones.c.id == rid).values(
                            fecha_ingreso=datetime.now() - timedelta(days=rnd.randint(0, 20), hours=rnd.randint(0, 8))))
                    camino = rnd.choice([[], ["En reparación"], ["En reparación", "Reparado"], ["En reparación", "Sin solución"],
                                         ["En reparación", "Reparado", "Devuelto"], ["En reparación", "Reparado", "Devuelto"]])
                    for e in camino:
                        extra = {"cobrado": pres} if e == "Devuelto" else {}
                        db.actualizar_reparacion(rid, estado=e, **extra)
            db.persistir(list(db.TABLAS), "Carga de datos demo")
            st.success("Datos demo cargados ✓")
