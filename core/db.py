"""Capa de datos: SQLAlchemy portable (SQLite local o Postgres en la nube)."""
from __future__ import annotations

import os
from datetime import datetime

import pandas as pd
import streamlit as st
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, MetaData, String,
    Table, Text, create_engine, func, insert, select, update, delete,
)

metadata = MetaData()

productos = Table(
    "productos", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("codigo", String(64), unique=True, nullable=False, index=True),
    Column("nombre", String(200), nullable=False),
    Column("categoria", String(80), default="General"),
    Column("costo", Float, default=0),
    Column("precio", Float, default=0),
    Column("stock", Integer, default=0),
    Column("stock_minimo", Integer, default=1),
    Column("activo", Boolean, default=True),
    Column("creado", DateTime, default=datetime.now),
    Column("actualizado", DateTime, default=datetime.now),
)

movimientos = Table(
    "movimientos_stock", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("producto_id", Integer, ForeignKey("productos.id"), index=True),
    Column("tipo", String(20)),  # ingreso | venta | ajuste | anulacion
    Column("cantidad", Integer),
    Column("costo_unit", Float),
    Column("referencia", String(60)),
    Column("nota", Text),
    Column("fecha", DateTime, default=datetime.now),
)

historial_precios = Table(
    "historial_precios", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("producto_id", Integer, ForeignKey("productos.id"), index=True),
    Column("costo_anterior", Float),
    Column("costo_nuevo", Float),
    Column("precio_anterior", Float),
    Column("precio_nuevo", Float),
    Column("motivo", String(120)),
    Column("fecha", DateTime, default=datetime.now),
)

ventas = Table(
    "ventas", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("fecha", DateTime, default=datetime.now, index=True),
    Column("subtotal", Float),
    Column("descuento", Float, default=0),
    Column("total", Float),
    Column("costo_total", Float),
    Column("medio_pago", String(40)),
    Column("cliente", String(120)),
    Column("anulada", Boolean, default=False),
)

venta_items = Table(
    "venta_items", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("venta_id", Integer, ForeignKey("ventas.id"), index=True),
    Column("producto_id", Integer, ForeignKey("productos.id")),
    Column("codigo", String(64)),
    Column("nombre", String(200)),
    Column("categoria", String(80)),
    Column("cantidad", Integer),
    Column("precio_unit", Float),
    Column("costo_unit", Float),
)

reparaciones = Table(
    "reparaciones", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("fecha_ingreso", DateTime, default=datetime.now, index=True),
    Column("cliente", String(120)),
    Column("telefono", String(40)),
    Column("marca", String(60)),
    Column("modelo", String(120)),
    Column("imei", String(40)),
    Column("falla", Text),          # reparación a realizar
    Column("accesorios", String(200)),
    Column("presupuesto", Float, default=0),
    Column("senia", Float, default=0),
    Column("costo_repuesto", Float, default=0),
    Column("mano_obra", Float, default=0),
    Column("estado", String(30), default="Para enviar", index=True),
    Column("resultado", String(30)),  # Reparado | Sin solución
    Column("cobrado", Float, default=0),
    Column("fecha_estado", DateTime, default=datetime.now),
    Column("fecha_entrega", DateTime),
    Column("notas", Text),
)

reparacion_log = Table(
    "reparacion_log", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("reparacion_id", Integer, ForeignKey("reparaciones.id"), index=True),
    Column("estado", String(30)),
    Column("nota", Text),
    Column("fecha", DateTime, default=datetime.now),
)

config = Table(
    "config", metadata,
    Column("clave", String(60), primary_key=True),
    Column("valor", String(400)),
)

ESTADOS = ["Para enviar", "En reparación", "Reparado", "Sin solución", "Devuelto"]
MEDIOS_PAGO = ["Efectivo", "Débito", "Crédito", "Transferencia", "Mercado Pago"]
DEFAULT_CONFIG = {
    "negocio": "CeluPOS",
    "fee_mano_obra": "15000",
    "categorias": "Celulares,Fundas,Cargadores,Cables,Auriculares,Templados,Accesorios,Repuestos",
}


def _db_url() -> str:
    try:
        url = st.secrets.get("DATABASE_URL", "")
    except Exception:
        url = ""
    url = url or os.environ.get("DATABASE_URL", "")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if not url:
        os.makedirs("data", exist_ok=True)
        url = "sqlite:///data/celupos.db"
    return url


@st.cache_resource(show_spinner=False)
def get_engine():
    url = _db_url()
    kw = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kw["connect_args"] = {"check_same_thread": False}
    eng = create_engine(url, **kw)
    metadata.create_all(eng)
    with eng.begin() as c:
        existentes = {r[0] for r in c.execute(select(config.c.clave))}
        for k, v in DEFAULT_CONFIG.items():
            if k not in existentes:
                c.execute(insert(config).values(clave=k, valor=v))
    return eng


def is_sqlite() -> bool:
    return get_engine().url.get_backend_name() == "sqlite"


def df(stmt, params=None) -> pd.DataFrame:
    with get_engine().connect() as c:
        return pd.read_sql(stmt, c, params=params)


# ---------- config ----------
def get_config(clave: str) -> str:
    with get_engine().connect() as c:
        v = c.execute(select(config.c.valor).where(config.c.clave == clave)).scalar()
    return v if v is not None else DEFAULT_CONFIG.get(clave, "")


def set_config(clave: str, valor: str):
    with get_engine().begin() as c:
        r = c.execute(update(config).where(config.c.clave == clave).values(valor=str(valor)))
        if r.rowcount == 0:
            c.execute(insert(config).values(clave=clave, valor=str(valor)))


def categorias() -> list[str]:
    return [x.strip() for x in get_config("categorias").split(",") if x.strip()]


def fee_mano_obra() -> float:
    try:
        return float(get_config("fee_mano_obra"))
    except ValueError:
        return 0.0


# ---------- productos ----------
def buscar_por_codigo(codigo: str):
    codigo = (codigo or "").strip()
    if not codigo:
        return None
    with get_engine().connect() as c:
        r = c.execute(select(productos).where(productos.c.codigo == codigo)).mappings().first()
    return dict(r) if r else None


def listar_productos(solo_activos=True) -> pd.DataFrame:
    s = select(productos).order_by(productos.c.nombre)
    if solo_activos:
        s = s.where(productos.c.activo == True)  # noqa: E712
    return df(s)


def siguiente_codigo_interno() -> str:
    with get_engine().connect() as c:
        n = c.execute(select(func.count()).select_from(productos)
                      .where(productos.c.codigo.like("INT%"))).scalar() or 0
    while True:
        n += 1
        cod = f"INT{n:06d}"
        if not buscar_por_codigo(cod):
            return cod


def crear_producto(codigo, nombre, categoria, costo, precio, stock, stock_minimo=1) -> int:
    with get_engine().begin() as c:
        pid = c.execute(insert(productos).values(
            codigo=codigo.strip(), nombre=nombre.strip(), categoria=categoria,
            costo=float(costo), precio=float(precio), stock=int(stock),
            stock_minimo=int(stock_minimo), activo=True,
            creado=datetime.now(), actualizado=datetime.now(),
        )).inserted_primary_key[0]
        if int(stock) > 0:
            c.execute(insert(movimientos).values(
                producto_id=pid, tipo="ingreso", cantidad=int(stock), costo_unit=float(costo),
                referencia="Alta", fecha=datetime.now()))
    return pid


def ingresar_stock(pid: int, cantidad: int, costo_nuevo: float | None = None,
                   precio_nuevo: float | None = None, nota: str = "", tipo="ingreso"):
    with get_engine().begin() as c:
        p = c.execute(select(productos).where(productos.c.id == pid)).mappings().first()
        vals = {"stock": p["stock"] + int(cantidad), "actualizado": datetime.now()}
        cambia_costo = costo_nuevo is not None and float(costo_nuevo) != float(p["costo"])
        cambia_precio = precio_nuevo is not None and float(precio_nuevo) != float(p["precio"])
        if cambia_costo:
            vals["costo"] = float(costo_nuevo)
        if cambia_precio:
            vals["precio"] = float(precio_nuevo)
        c.execute(update(productos).where(productos.c.id == pid).values(**vals))
        c.execute(insert(movimientos).values(
            producto_id=pid, tipo=tipo, cantidad=int(cantidad),
            costo_unit=float(costo_nuevo if costo_nuevo is not None else p["costo"]),
            referencia=tipo.capitalize(), nota=nota, fecha=datetime.now()))
        if cambia_costo or cambia_precio:
            c.execute(insert(historial_precios).values(
                producto_id=pid, costo_anterior=p["costo"], costo_nuevo=vals.get("costo", p["costo"]),
                precio_anterior=p["precio"], precio_nuevo=vals.get("precio", p["precio"]),
                motivo="Ingreso de stock", fecha=datetime.now()))


def actualizar_producto(pid: int, motivo="Edición", **campos):
    with get_engine().begin() as c:
        p = c.execute(select(productos).where(productos.c.id == pid)).mappings().first()
        if p is None:
            return
        nuevo_costo = float(campos.get("costo", p["costo"]))
        nuevo_precio = float(campos.get("precio", p["precio"]))
        if "stock" in campos and int(campos["stock"]) != int(p["stock"]):
            c.execute(insert(movimientos).values(
                producto_id=pid, tipo="ajuste", cantidad=int(campos["stock"]) - int(p["stock"]),
                costo_unit=nuevo_costo, referencia="Ajuste manual", fecha=datetime.now()))
        campos["actualizado"] = datetime.now()
        c.execute(update(productos).where(productos.c.id == pid).values(**campos))
        if nuevo_costo != float(p["costo"]) or nuevo_precio != float(p["precio"]):
            c.execute(insert(historial_precios).values(
                producto_id=pid, costo_anterior=p["costo"], costo_nuevo=nuevo_costo,
                precio_anterior=p["precio"], precio_nuevo=nuevo_precio,
                motivo=motivo, fecha=datetime.now()))


def historial_precios_df() -> pd.DataFrame:
    s = (select(historial_precios.c.fecha, productos.c.codigo, productos.c.nombre,
                historial_precios.c.costo_anterior, historial_precios.c.costo_nuevo,
                historial_precios.c.precio_anterior, historial_precios.c.precio_nuevo,
                historial_precios.c.motivo)
         .join(productos, productos.c.id == historial_precios.c.producto_id)
         .order_by(historial_precios.c.fecha.desc()).limit(500))
    return df(s)


# ---------- ventas ----------
def registrar_venta(items: list[dict], medio_pago: str, descuento: float, cliente: str) -> int:
    subtotal = sum(i["precio"] * i["cantidad"] for i in items)
    costo_total = sum(i["costo"] * i["cantidad"] for i in items)
    total = max(subtotal - float(descuento or 0), 0)
    now = datetime.now()
    with get_engine().begin() as c:
        vid = c.execute(insert(ventas).values(
            fecha=now, subtotal=subtotal, descuento=float(descuento or 0), total=total,
            costo_total=costo_total, medio_pago=medio_pago, cliente=cliente, anulada=False,
        )).inserted_primary_key[0]
        for i in items:
            c.execute(insert(venta_items).values(
                venta_id=vid, producto_id=i["id"], codigo=i["codigo"], nombre=i["nombre"],
                categoria=i.get("categoria"), cantidad=i["cantidad"],
                precio_unit=i["precio"], costo_unit=i["costo"]))
            c.execute(update(productos).where(productos.c.id == i["id"])
                      .values(stock=productos.c.stock - i["cantidad"]))
            c.execute(insert(movimientos).values(
                producto_id=i["id"], tipo="venta", cantidad=-i["cantidad"],
                costo_unit=i["costo"], referencia=f"Venta #{vid}", fecha=now))
    return vid


def anular_venta(vid: int):
    with get_engine().begin() as c:
        v = c.execute(select(ventas).where(ventas.c.id == vid)).mappings().first()
        if not v or v["anulada"]:
            return
        items = c.execute(select(venta_items).where(venta_items.c.venta_id == vid)).mappings().all()
        for i in items:
            c.execute(update(productos).where(productos.c.id == i["producto_id"])
                      .values(stock=productos.c.stock + i["cantidad"]))
            c.execute(insert(movimientos).values(
                producto_id=i["producto_id"], tipo="anulacion", cantidad=i["cantidad"],
                costo_unit=i["costo_unit"], referencia=f"Anula venta #{vid}", fecha=datetime.now()))
        c.execute(update(ventas).where(ventas.c.id == vid).values(anulada=True))


def ventas_df(desde: datetime, hasta: datetime, incluir_anuladas=False) -> pd.DataFrame:
    s = select(ventas).where(ventas.c.fecha >= desde, ventas.c.fecha <= hasta)
    if not incluir_anuladas:
        s = s.where(ventas.c.anulada == False)  # noqa: E712
    return df(s.order_by(ventas.c.fecha.desc()))


def items_df(desde: datetime, hasta: datetime) -> pd.DataFrame:
    s = (select(venta_items, ventas.c.fecha, ventas.c.medio_pago)
         .join(ventas, ventas.c.id == venta_items.c.venta_id)
         .where(ventas.c.fecha >= desde, ventas.c.fecha <= hasta, ventas.c.anulada == False))  # noqa: E712
    return df(s)


def items_de_venta(vid: int) -> pd.DataFrame:
    return df(select(venta_items).where(venta_items.c.venta_id == vid))


# ---------- reparaciones ----------
def crear_reparacion(**d) -> int:
    now = datetime.now()
    d.setdefault("estado", "Para enviar")
    with get_engine().begin() as c:
        rid = c.execute(insert(reparaciones).values(
            fecha_ingreso=now, fecha_estado=now, **d)).inserted_primary_key[0]
        c.execute(insert(reparacion_log).values(
            reparacion_id=rid, estado=d["estado"], nota="Ingreso del equipo", fecha=now))
    return rid


def actualizar_reparacion(rid: int, nota: str = "", **campos):
    now = datetime.now()
    with get_engine().begin() as c:
        r = c.execute(select(reparaciones).where(reparaciones.c.id == rid)).mappings().first()
        if r is None:
            return
        nuevo_estado = campos.get("estado", r["estado"])
        if nuevo_estado != r["estado"]:
            campos["fecha_estado"] = now
            if nuevo_estado in ("Reparado", "Sin solución"):
                campos["resultado"] = nuevo_estado
            if nuevo_estado == "Devuelto":
                campos["fecha_entrega"] = now
                if not (campos.get("resultado") or r["resultado"]):
                    campos["resultado"] = "Reparado"
            c.execute(insert(reparacion_log).values(
                reparacion_id=rid, estado=nuevo_estado, nota=nota, fecha=now))
        elif nota:
            c.execute(insert(reparacion_log).values(
                reparacion_id=rid, estado=nuevo_estado, nota=nota, fecha=now))
        c.execute(update(reparaciones).where(reparaciones.c.id == rid).values(**campos))


def reparaciones_df() -> pd.DataFrame:
    return df(select(reparaciones).order_by(reparaciones.c.fecha_ingreso.desc()))


def get_reparacion(rid: int):
    with get_engine().connect() as c:
        r = c.execute(select(reparaciones).where(reparaciones.c.id == rid)).mappings().first()
    return dict(r) if r else None


def log_reparacion(rid: int) -> pd.DataFrame:
    return df(select(reparacion_log).where(reparacion_log.c.reparacion_id == rid)
              .order_by(reparacion_log.c.fecha))


def eliminar_reparacion(rid: int):
    with get_engine().begin() as c:
        c.execute(delete(reparacion_log).where(reparacion_log.c.reparacion_id == rid))
        c.execute(delete(reparaciones).where(reparaciones.c.id == rid))
