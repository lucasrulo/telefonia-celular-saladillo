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

## Dónde se guardan los datos

Todo queda en **archivos CSV** (una tabla por archivo: productos, ventas, detalle de ventas, movimientos de stock, historial de precios, reparaciones, historial de reparaciones y configuración).

- **Con respaldo en GitHub (recomendado):** los CSV viven en un repo **privado** tuyo. Al arrancar, la app los descarga; después de cada operación (venta, alta, cambio de estado…) sube las tablas que cambiaron en un commit. Cada commit es un backup: en GitHub ves el historial y podés volver a cualquier versión.
- Si al arrancar no puede leer GitHub, **la app no arranca** (así nunca pisa tus datos con una base vacía).
- Si falla una subida (sin internet), la barra lateral avisa "cambios sin subir" con un botón para reintentar; el próximo guardado también sube lo pendiente.
- Siempre queda además una copia local en `data/csv/`, y en *Configuración* podés descargar un backup .zip con todos los CSV.
- Sin configurar GitHub, guarda sólo en la PC (`data/`).

## Puesta en marcha (GitHub + Streamlit Cloud)

1. **Repo de la app:** creá un repo `telefonia-celular-saladillo` y subí estos archivos.
2. **Repo de datos:** creá OTRO repo, **privado**, vacío (ej. `telefonia-celular-saladillo-datos`). Tiene que ser otro repo porque Streamlit reinicia la app cada vez que cambia el repo de la app.
3. **Token:** GitHub → Settings → Developer settings → *Fine-grained tokens* → Generate. *Repository access:* sólo `telefonia-celular-saladillo-datos`. *Permissions → Contents:* **Read and write**. Poné vencimiento largo (o sin vencimiento) y anotá la fecha si vence.
4. **Streamlit Cloud** ([share.streamlit.io](https://share.streamlit.io)) → *New app* → repo `lucasrulo/telefonia-celular-saladillo`, archivo `app.py` → *Advanced settings → Secrets*:
   ```toml
   DATA_REPO = "lucasrulo/telefonia-celular-saladillo-datos"
   GITHUB_TOKEN = "github_pat_..."
   APP_PASSWORD = "una-clave-para-el-local"
   ```
5. Abrís la app y la barra lateral muestra "☁️ Guardado en GitHub".

### Correr en la PC del local
```bash
pip install -r requirements.txt
streamlit run app.py
```
Para que también respalde en GitHub, copiá `.streamlit/secrets.toml.example` a `.streamlit/secrets.toml` y completalo.

> No uses la app en la nube y en la PC al mismo tiempo: cada una tiene su copia de trabajo y la última que guarda pisa las tablas de la otra. Usá una sola (la de Streamlit Cloud sirve desde cualquier PC o celular).

## Pistola lectora

Cualquier lector USB/Bluetooth en modo teclado (HID) con sufijo *Enter* (default de fábrica). No necesita drivers ni configuración: abrís la app en el navegador de la PC del local y disparás.

## Estructura

```
app.py              # navegación + login opcional
core/db.py          # modelo de datos (SQLite de trabajo)
core/storage.py     # guardado en CSV + sincronización con GitHub
core/ui.py          # estilos, KPIs, formato $
views/              # una página por módulo
.streamlit/         # tema + ejemplo de secrets
```
