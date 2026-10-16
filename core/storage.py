"""Persistencia en CSV dentro de un repo privado de GitHub.

- Al arrancar: baja los CSV del repo y arma la base de trabajo (SQLite local).
- Después de cada operación: exporta las tablas que cambiaron a CSV y las sube en UN commit.
- Siempre deja además una copia local en data/csv/.
Cada commit es un backup: GitHub guarda el historial completo de cambios.
"""
from __future__ import annotations

import hashlib
import os
import threading
from datetime import datetime

import requests
import streamlit as st

_lock = threading.Lock()
_hash_subido: dict[str, str] = {}   # último contenido subido por tabla
_pendientes: set[str] = set()       # tablas con cambios que no se pudieron subir
_estado = {"ultimo_ok": None, "error": None}


def _secret(k, default=""):
    try:
        v = st.secrets.get(k, "")
    except Exception:
        v = ""
    return v or os.environ.get(k, default)


def cfg():
    return {
        "token": _secret("GITHUB_TOKEN"),
        "repo": _secret("DATA_REPO"),            # ej: "lucasrulo/celupos-datos"
        "branch": _secret("DATA_BRANCH", "main"),
        "folder": _secret("DATA_FOLDER", "datos"),
    }


def habilitado() -> bool:
    c = cfg()
    return bool(c["token"] and c["repo"])


def _req(method, path, **kw):
    c = cfg()
    api = _secret("GITHUB_API", "https://api.github.com")
    r = requests.request(method, f"{api}/repos/{c['repo']}{path}", timeout=30, headers={
        "Authorization": f"Bearer {c['token']}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"}, **kw)
    return r


def _inicializar_repo_vacio():
    """Un repo recién creado sin archivos no tiene rama: creamos un README."""
    import base64
    c = cfg()
    r = _req("PUT", f"/contents/{c['folder']}/LEEME.md", json={
        "message": "Inicializa almacenamiento CeluPOS", "branch": c["branch"],
        "content": base64.b64encode("Datos de CeluPOS (no editar a mano).\n".encode()).decode()})
    if r.status_code not in (200, 201):
        raise RuntimeError(f"No pude inicializar el repo de datos: {r.status_code} {r.text[:200]}")


def descargar_todo() -> dict[str, str]:
    """Devuelve {tabla: csv_texto}. Lanza excepción si no puede leer (nunca arranca vacío por error)."""
    import base64
    c = cfg()
    r = _req("GET", f"/contents/{c['folder']}", params={"ref": c["branch"]})
    if r.status_code == 404:
        repo = _req("GET", "")
        if repo.status_code != 200:
            raise RuntimeError(f"No encuentro el repo '{c['repo']}' o el token no tiene acceso ({repo.status_code}).")
        return {}  # repo existe pero todavía no hay datos
    if r.status_code != 200:
        raise RuntimeError(f"GitHub respondió {r.status_code}: {r.text[:200]}")
    out = {}
    for f in r.json():
        if f["type"] == "file" and f["name"].endswith(".csv"):
            b = _req("GET", f"/git/blobs/{f['sha']}")
            if b.status_code != 200:
                raise RuntimeError(f"No pude bajar {f['name']}: {b.status_code}")
            texto = base64.b64decode(b.json()["content"]).decode("utf-8")
            nombre = f["name"][:-4]
            out[nombre] = texto
            _hash_subido[nombre] = hashlib.sha1(texto.encode()).hexdigest()
    return out


def _commit(archivos: dict[str, str], mensaje: str):
    c = cfg()
    for intento in range(3):
        ref = _req("GET", f"/git/ref/heads/{c['branch']}")
        if ref.status_code in (404, 409):
            _inicializar_repo_vacio()
            continue
        ref.raise_for_status()
        head = ref.json()["object"]["sha"]
        base_tree = _req("GET", f"/git/commits/{head}").json()["tree"]["sha"]
        tree = _req("POST", "/git/trees", json={"base_tree": base_tree, "tree": [
            {"path": f"{c['folder']}/{n}.csv", "mode": "100644", "type": "blob", "content": t}
            for n, t in archivos.items()]})
        tree.raise_for_status()
        com = _req("POST", "/git/commits", json={"message": mensaje, "tree": tree.json()["sha"], "parents": [head]})
        com.raise_for_status()
        upd = _req("PATCH", f"/git/refs/heads/{c['branch']}", json={"sha": com.json()["sha"]})
        if upd.status_code == 200:
            return
    raise RuntimeError("No se pudo actualizar la rama después de 3 intentos")


def guardar(csvs: dict[str, str], mensaje: str, forzar: bool = False):
    """Escribe copia local y sube a GitHub sólo lo que cambió. No lanza: deja estado para la UI."""
    os.makedirs("data/csv", exist_ok=True)
    for n, t in csvs.items():
        with open(f"data/csv/{n}.csv", "w", encoding="utf-8", newline="") as fh:
            fh.write(t)
    if not habilitado():
        return
    with _lock:
        cambiados = {n: t for n, t in csvs.items()
                     if forzar or hashlib.sha1(t.encode()).hexdigest() != _hash_subido.get(n)}
        _pendientes.update(cambiados)
        if not _pendientes:
            return
        # incluir también lo que haya quedado pendiente de un fallo anterior
        a_subir = {n: csvs[n] if n in csvs else open(f"data/csv/{n}.csv", encoding="utf-8").read()
                   for n in _pendientes}
        try:
            _commit(a_subir, f"{mensaje} · {datetime.now():%d/%m/%Y %H:%M:%S}")
            for n, t in a_subir.items():
                _hash_subido[n] = hashlib.sha1(t.encode()).hexdigest()
            _pendientes.clear()
            _estado.update(ultimo_ok=datetime.now(), error=None)
        except Exception as e:  # noqa: BLE001
            _estado["error"] = str(e)[:300]


def estado():
    return {"habilitado": habilitado(), "pendientes": sorted(_pendientes), **_estado}
