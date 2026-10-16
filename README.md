# 📱 CeluPOS — Ventas, stock y servicio técnico para casas de celulares

App en **Streamlit** con punto de venta compatible con **pistola lectora de código de barras**, gestión de stock y precios, módulo de **reparaciones** con estados y costos, y **dashboard** de análisis.

## Módulos

| Módulo | Qué hace |
|---|---|
| **Punto de venta** | Escaneás con la pistola → el producto entra al carrito (el campo queda siempre con foco). Búsqueda por nombre, precio editable por línea, descuento $ o %, medios de pago, vuelto, ticket imprimible. Si el código no existe, lo das de alta ahí mismo. |
| **Servicio técnico** | Alta de equipo (marca, modelo, IMEI, falla, accesorios, cliente), presupuesto, seña, costo de repuesto + mano de obra (fee general configurable). Tablero tipo Kanban con estados **Para enviar → En reparación → Reparado / Sin solución → Devuelto**, historial de cambios, orden de servicio imprimible, listado con importes, costo y ganancia real. |
| **Productos y stock** | Alta rápida (código + nombre + costo + precio; si no tiene código se genera uno interno), ingreso de mercadería escaneando, inventario editable, export a Excel, log de movimientos. |
| **Actualizar precios** | Aumento masivo por % (precio o costo manteniendo margen) o por markup sobre costo, filtrado por categoría/nombre, redondeo, preview antes de aplicar, historial de cambios. |
| **Dashboard** | Venta bruta, ganancia, margen, tickets, ticket promedio, unidades, comparación vs período anterior, reparaciones cobradas y ganancia, total del negocio, stock en unidades y valorizado ($ costo / $ venta), evolución diaria, categorías, top productos, medios de pago, mapa de calor por día/hora, stock a reponer y stock inmovilizado. |
| **Historial de ventas** | Tickets por rango, detalle, anulación (devuelve stock), export Excel. |

## Correr local

```bash
pip install -r requirements.txt
streamlit run app.py
```
Sin configuración usa **SQLite** en `data/celupos.db`. En *Configuración* podés cargar datos demo para probar.

## Subir a GitHub + Streamlit Cloud

1. Creá un repo nuevo en GitHub (ej. `celupos`) y subí todos estos archivos (`git init && git add . && git commit -m "CeluPOS" && git remote add origin https://github.com/<usuario>/celupos.git && git push -u origin main`).
2. **Base de datos en la nube (obligatorio en Streamlit Cloud):** el disco de Streamlit Cloud se borra en cada reinicio, así que SQLite ahí pierde los datos. Creá un Postgres gratis en [Supabase](https://supabase.com) o [Neon](https://neon.tech) y copiá el connection string.
   - Supabase: *Project Settings → Database → Connection string → Session pooler* (puerto 5432).
3. En [share.streamlit.io](https://share.streamlit.io) → *New app* → elegí el repo, `app.py`.
4. *Advanced settings → Secrets*:
   ```toml
   DATABASE_URL = "postgresql://postgres.xxxx:CLAVE@aws-0-sa-east-1.pooler.supabase.com:5432/postgres"
   APP_PASSWORD = "una-clave-para-el-local"
   ```
Las tablas se crean solas al primer arranque.

## Pistola lectora

Cualquier lector USB/Bluetooth en modo teclado (HID) con sufijo *Enter* (default de fábrica). No necesita drivers ni configuración: abrís la app en el navegador de la PC del local y disparás.

## Estructura

```
app.py              # navegación + login opcional
core/db.py          # modelo de datos (SQLAlchemy: SQLite o Postgres)
core/ui.py          # estilos, KPIs, formato $
views/              # una página por módulo
.streamlit/         # tema + ejemplo de secrets
```
