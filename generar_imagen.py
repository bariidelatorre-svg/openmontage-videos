#!/usr/bin/env python3
"""Genera imágenes con Nano Banana Pro en Kie.ai (https://docs.kie.ai), manteniendo la identidad de una clienta.

Flujo: verifica el saldo -> sube las referencias de identidad (y la escena, si hay) -> crea la tarea
-> consulta el estado hasta que termine -> descarga en clientes/<clienta>/salidas/ -> informa créditos.

Protección de créditos:
  - Una sola imagen por ejecución, sin reintentos automáticos.
  - Solo 1K/2K (4K cuesta más y está bloqueado).
  - Si el saldo no alcanza para una imagen (o quedaría por debajo de --reserva), no se genera nada.
  - Kie.ai es prepago: cuando el saldo llega a 0 no hay cobros adicionales.

La API key se lee de KIE_API_KEY; nunca se imprime.

Uso:
    python generar_imagen.py "recrear la escena con el mismo outfit y luz" --escena clientes/gisel/escenas/escena-01-piso-taza.jpg
    python generar_imagen.py "retrato de estudio, fondo beige" --relacion 9:16
"""
import argparse
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

API_BASE = "https://api.kie.ai/api/v1"
UPLOAD_URL = "https://kieai.redpandaai.co/api/file-stream-upload"
MODELO = "nano-banana-pro"
COSTO_POR_IMAGEN = 18  # créditos de Nano Banana Pro en 1K/2K
RELACIONES = ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]
MAX_IMAGENES_INPUT = 8  # límite de la API
RAIZ = Path(__file__).resolve().parent

# Referencias de identidad: pocas y neutras (las primeras pesan más)
REFS_PREFERIDAS = ["ref-pro-mano-menton", "ref-pro-cabeza-inclinada", "ref-pro-mano-mejilla-luz", "ref-pro-primer-plano", "ref-aprobada-sueter-crema", "ref-cuerpo-pasillo-vestido-cafe", "ref-cuerpo-sillon-naranja"]
MAX_REFS_IDENTIDAD = 7

# Bloque 1 (identidad) y bloque 7 (restricciones) fijos; los bloques 2-6 los da el prompt.
INSTRUCCION_IDENTIDAD = (
    "Identity: the first {n} images are the identity reference. Preserve the recognizable facial features, "
    "facial proportions, body proportions, skin tone and overall identity of the woman from the identity "
    "reference with extremely high fidelity."
)
INSTRUCCION_ESCENA = (
    "The last image is only a style/scene inspiration (pose, composition, light, outfit, setting). "
    "It must NOT change the woman's identity: never take her face or body from it."
)
INSTRUCCION_CORRECCION = (
    "The last image is the image to edit: keep everything in it exactly the same (composition, pose, "
    "background, light, outfit, makeup, hair) and only fix what is requested, using the identity reference "
    "as ground truth for the woman's face."
)
RESTRICCIONES = (
    "Constraints: no beauty-filter skin, no face slimming, no narrower jaw or thinner cheeks than the identity reference, no change of facial proportions, no exaggerated "
    "smile, no artificial HDR, no text, no logos, no tattoos."
)


def tapar_cara(ruta, caja):
    """Pixela la cara de la persona en la imagen de escena para que no contamine la identidad."""
    from PIL import Image
    img = Image.open(ruta).convert("RGB")
    w, h = img.size
    x1, y1, x2, y2 = (int(v * d) for v, d in zip(caja, (w, h, w, h)))
    zona = img.crop((x1, y1, x2, y2))
    zona = zona.resize((max(1, (x2 - x1) // 24), max(1, (y2 - y1) // 24))).resize(zona.size, Image.NEAREST)
    img.paste(zona, (x1, y1))
    destino = Path(tempfile.gettempdir()) / f"escena-sin-cara-{uuid.uuid4().hex[:8]}.jpg"
    img.save(destino, quality=92)
    return destino


def api_key():
    key = os.environ.get("KIE_API_KEY")
    if not key:
        sys.exit("Error: la variable de entorno KIE_API_KEY no está definida.")
    return key


def peticion(req):
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            respuesta = json.load(resp)
    except urllib.error.HTTPError as e:
        sys.exit(f"Error HTTP {e.code}: {e.read().decode(errors='replace')}")
    if respuesta.get("code") != 200:
        sys.exit(f"Error de la API: {respuesta.get('code')} - {respuesta.get('msg')}")
    return respuesta["data"]


def llamar_api(metodo, ruta, key, cuerpo=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    return peticion(urllib.request.Request(
        f"{API_BASE}{ruta}", data=datos, method=metodo,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    ))


def saldo(key):
    return float(llamar_api("GET", "/chat/credit", key))


def subir_archivo(key, ruta):
    """Sube un archivo a Kie.ai (se borra a las 24 h) y devuelve su URL."""
    limite = f"----kie{uuid.uuid4().hex}"
    tipo = mimetypes.guess_type(ruta.name)[0] or "application/octet-stream"
    nombre = f"{uuid.uuid4().hex[:8]}-{ruta.name}"
    partes = [
        f'--{limite}\r\nContent-Disposition: form-data; name="uploadPath"\r\n\r\nimages/referencias\r\n'.encode(),
        f'--{limite}\r\nContent-Disposition: form-data; name="fileName"\r\n\r\n{nombre}\r\n'.encode(),
        f'--{limite}\r\nContent-Disposition: form-data; name="file"; filename="{nombre}"\r\n'
        f"Content-Type: {tipo}\r\n\r\n".encode() + ruta.read_bytes() + b"\r\n",
        f"--{limite}--\r\n".encode(),
    ]
    data = peticion(urllib.request.Request(
        UPLOAD_URL, data=b"".join(partes), method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": f"multipart/form-data; boundary={limite}"},
    ))
    return data["downloadUrl"]


def referencias_identidad(clienta, cupo):
    carpeta = RAIZ / "clientes" / clienta / "referencias"
    if not carpeta.is_dir():
        sys.exit(f"Error: no existe {carpeta}. Nunca se genera sin referencias de identidad.")
    archivos = {p.stem: p for p in carpeta.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")}
    orden = [archivos.pop(n) for n in REFS_PREFERIDAS if n in archivos] + sorted(archivos.values())
    if not orden:
        sys.exit(f"Error: {carpeta} no tiene imágenes de referencia.")
    return orden[:cupo]


def esperar_resultado(key, task_id, intervalo=4, timeout=900):
    inicio = time.time()
    while time.time() - inicio < timeout:
        data = llamar_api("GET", f"/jobs/recordInfo?taskId={task_id}", key)
        estado = data.get("state")
        if estado == "success":
            return json.loads(data["resultJson"])["resultUrls"]
        if estado == "fail":
            sys.exit(f"La tarea falló: {data.get('failCode')} - {data.get('failMsg')}")
        time.sleep(intervalo)
    sys.exit(f"Tiempo de espera agotado; revisá la tarea {task_id} antes de volver a generar.")


def main():
    parser = argparse.ArgumentParser(description="Genera una imagen con Nano Banana Pro (Kie.ai) con identidad fija")
    parser.add_argument("prompt", help="Cambios o descripción de la escena")
    parser.add_argument("--clienta", default="gisel", help="Carpeta en clientes/ (por defecto: gisel)")
    parser.add_argument("--relacion", default="4:5", choices=RELACIONES, help="Relación de aspecto (por defecto 4:5)")
    parser.add_argument("--resolucion", default="2K", choices=["1K", "2K"], help="Resolución (por defecto 2K)")
    parser.add_argument("--escena", type=Path, help="Imagen de referencia de escena a recrear (cámara, outfit, luz...)")
    parser.add_argument("--corregir", type=Path,
                        help="Imagen ya generada a corregir (solo cambia lo pedido en el prompt)")
    parser.add_argument("--tapar-cara", type=float, nargs=4, metavar=("X1", "Y1", "X2", "Y2"),
                        help="Caja de la cara en la escena (fracciones 0-1) a pixelar antes de subirla")
    parser.add_argument("--reserva", type=float, default=0,
                        help="No generar si el saldo quedaría por debajo de este número de créditos")
    args = parser.parse_args()

    key = api_key()
    saldo_inicial = saldo(key)
    if saldo_inicial - COSTO_POR_IMAGEN < args.reserva:
        sys.exit(f"Generación cancelada: saldo {saldo_inicial:g} créditos, costo {COSTO_POR_IMAGEN}, "
                 f"reserva {args.reserva:g}. No se gastó nada.")

    if args.corregir and args.escena:
        sys.exit("Error: usar --corregir o --escena, no ambos.")
    for extra in (args.corregir, args.escena):
        if extra and not extra.is_file():
            sys.exit(f"Error: no existe {extra}")
    rutas = referencias_identidad(args.clienta, MAX_REFS_IDENTIDAD)
    n_identidad = len(rutas)
    if args.corregir:
        rutas.append(args.corregir)
    if args.escena:
        rutas.append(tapar_cara(args.escena, args.tapar_cara) if args.tapar_cara else args.escena)
    urls = [subir_archivo(key, r) for r in rutas]

    prompt = " ".join(filter(None, [
        INSTRUCCION_IDENTIDAD.format(n=n_identidad),
        INSTRUCCION_CORRECCION if args.corregir else "",
        INSTRUCCION_ESCENA if args.escena else "",
        args.prompt,
        RESTRICCIONES,
    ]))
    task_id = llamar_api("POST", "/jobs/createTask", key, {
        "model": MODELO,
        "input": {"prompt": prompt, "image_input": urls, "aspect_ratio": args.relacion,
                  "resolution": args.resolucion, "output_format": "png"},
    })["taskId"]
    print(f"Tarea {task_id} creada ({MODELO}, {args.resolucion}, {args.relacion}, {len(urls)} referencias)")

    resultado = esperar_resultado(key, task_id)
    salida = RAIZ / "clientes" / args.clienta / "salidas"
    salida.mkdir(parents=True, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d-%H%M%S")
    for i, url in enumerate(resultado):
        destino = salida / f"{args.clienta}-{marca}-{i}{Path(url.split('?')[0]).suffix or '.png'}"
        urllib.request.urlretrieve(url, destino)
        print(f"Imagen: {destino.relative_to(RAIZ)}")
        print(f"URL de descarga (Kie.ai, temporal): {url}")

    saldo_final = saldo(key)
    print(f"Créditos: {saldo_inicial:g} -> {saldo_final:g} (gastados {saldo_inicial - saldo_final:g}). "
          f"Alcanzan para {int(saldo_final // COSTO_POR_IMAGEN)} imágenes más.")


if __name__ == "__main__":
    main()
