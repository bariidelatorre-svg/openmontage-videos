#!/usr/bin/env python3
"""Genera imágenes con la API de Kie.ai (https://docs.kie.ai).

Flujo: crea la tarea (POST /api/v1/jobs/createTask), consulta el estado
(GET /api/v1/jobs/recordInfo) hasta que termine y descarga el resultado en salidas/.

La API key se lee de la variable de entorno KIE_API_KEY; nunca se imprime.

Uso:
    python generar_imagen.py "un gato astronauta" 16:9
    python generar_imagen.py "retrato al óleo" 1:1 --modelo z-image
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API_BASE = "https://api.kie.ai/api/v1"
MODELO_POR_DEFECTO = "z-image"  # el modelo de imagen más económico de Kie.ai
RELACIONES = ["1:1", "4:3", "3:4", "16:9", "9:16"]
CARPETA_SALIDA = Path(__file__).resolve().parent / "salidas"


def obtener_api_key():
    key = os.environ.get("KIE_API_KEY")
    if not key:
        sys.exit("Error: la variable de entorno KIE_API_KEY no está definida.")
    return key


def llamar_api(metodo, ruta, api_key, cuerpo=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(
        f"{API_BASE}{ruta}",
        data=datos,
        method=metodo,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            respuesta = json.load(resp)
    except urllib.error.HTTPError as e:
        sys.exit(f"Error HTTP {e.code} en {ruta}: {e.read().decode(errors='replace')}")
    if respuesta.get("code") != 200:
        sys.exit(f"Error de la API en {ruta}: {respuesta.get('code')} - {respuesta.get('msg')}")
    return respuesta["data"]


def crear_tarea(api_key, modelo, prompt, relacion):
    data = llamar_api("POST", "/jobs/createTask", api_key, {
        "model": modelo,
        "input": {"prompt": prompt, "aspect_ratio": relacion},
    })
    return data["taskId"]


def esperar_resultado(api_key, task_id, intervalo=3, timeout=600):
    inicio = time.time()
    while time.time() - inicio < timeout:
        data = llamar_api("GET", f"/jobs/recordInfo?taskId={task_id}", api_key)
        estado = data.get("state")
        if estado == "success":
            return json.loads(data["resultJson"])["resultUrls"]
        if estado == "fail":
            sys.exit(f"La tarea falló: {data.get('failCode')} - {data.get('failMsg')}")
        print(f"  estado: {estado}...")
        time.sleep(intervalo)
    sys.exit(f"Tiempo de espera agotado ({timeout}s) para la tarea {task_id}.")


def descargar(urls, task_id):
    CARPETA_SALIDA.mkdir(exist_ok=True)
    rutas = []
    for i, url in enumerate(urls):
        extension = Path(url.split("?")[0]).suffix or ".png"
        destino = CARPETA_SALIDA / f"{task_id}_{i}{extension}"
        urllib.request.urlretrieve(url, destino)
        rutas.append(destino)
    return rutas


def main():
    parser = argparse.ArgumentParser(description="Genera imágenes con Kie.ai")
    parser.add_argument("prompt", help="Descripción de la imagen (máx. 1000 caracteres)")
    parser.add_argument("relacion", choices=RELACIONES, help="Relación de aspecto")
    parser.add_argument("--modelo", default=MODELO_POR_DEFECTO,
                        help=f"Modelo de Kie.ai (por defecto: {MODELO_POR_DEFECTO})")
    args = parser.parse_args()

    api_key = obtener_api_key()
    print(f"Creando tarea con el modelo {args.modelo}...")
    task_id = crear_tarea(api_key, args.modelo, args.prompt, args.relacion)
    print(f"Tarea creada: {task_id}")
    urls = esperar_resultado(api_key, task_id)
    for ruta in descargar(urls, task_id):
        print(f"Imagen guardada en {ruta}")


if __name__ == "__main__":
    main()
