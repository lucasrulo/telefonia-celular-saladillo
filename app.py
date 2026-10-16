import hmac

import streamlit as st

from core import db, storage, ui

st.set_page_config(page_title="CeluPOS", page_icon="📱", layout="wide", initial_sidebar_state="expanded")
ui.setup_page()


def _password_ok() -> bool:
    """Login opcional: si definís APP_PASSWORD en secrets, la app pide clave."""
    try:
        pwd = st.secrets.get("APP_PASSWORD", "")
    except Exception:
        pwd = ""
    if not pwd or st.session_state.get("auth_ok"):
        return True
    c = st.columns([1, 1.2, 1])[1]
    with c:
        st.markdown("<div style='height:12vh'></div>", unsafe_allow_html=True)
        ui.hero("Acceso", "CeluPOS", "Ingresá la clave del local")
        with st.form("login"):
            p = st.text_input("Clave", type="password")
            if st.form_submit_button("Entrar", type="primary", width="stretch"):
                if hmac.compare_digest(p, pwd):
                    st.session_state.auth_ok = True
                    st.rerun()
                st.error("Clave incorrecta")
    return False


if not _password_ok():
    st.stop()

try:
    db.get_engine()
except Exception as e:  # noqa: BLE001
    st.error("No pude leer los datos guardados en GitHub, así que la app no arranca para no perder nada.")
    st.code(str(e))
    st.info("Revisá GITHUB_TOKEN y DATA_REPO en Secrets, y que el token tenga permiso de lectura/escritura sobre ese repo.")
    if st.button("Reintentar"):
        st.cache_resource.clear()
        st.rerun()
    st.stop()

ui.sidebar_brand(db.get_config("negocio"))

pages = {
    "Operación": [
        st.Page("views/ventas.py", title="Punto de venta", icon=":material/point_of_sale:", default=True),
        st.Page("views/reparaciones.py", title="Servicio técnico", icon=":material/build:"),
    ],
    "Inventario": [
        st.Page("views/productos.py", title="Productos y stock", icon=":material/inventory_2:"),
        st.Page("views/precios.py", title="Actualizar precios", icon=":material/sell:"),
    ],
    "Análisis": [
        st.Page("views/dashboard.py", title="Dashboard", icon=":material/insights:"),
        st.Page("views/historial.py", title="Historial de ventas", icon=":material/receipt_long:"),
    ],
    "Sistema": [
        st.Page("views/config.py", title="Configuración", icon=":material/settings:"),
    ],
}
nav = st.navigation(pages)

with st.sidebar:
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    est = storage.estado()
    if not est["habilitado"]:
        st.caption("💾 Guardado local (data/) · sin respaldo en GitHub")
    elif est["error"] or est["pendientes"]:
        st.error(f"⚠️ Hay cambios sin subir a GitHub: {', '.join(est['pendientes'])}")
        if st.button("Reintentar guardado", width="stretch"):
            db.persistir(est["pendientes"], "Reintento de guardado")
            st.rerun()
    else:
        hora = est["ultimo_ok"].strftime("%H:%M:%S") if est["ultimo_ok"] else "—"
        st.caption(f"☁️ Guardado en GitHub · último cambio {hora}")

nav.run()
