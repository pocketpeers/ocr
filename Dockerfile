# syntax=docker/dockerfile:1.4
# Imagen del servicio OCR para Hugging Face Spaces (SDK: docker).
#
# PaddleOCR se queda tal cual esta: mismos 5 modelos, misma configuracion,
# mismos resultados. Lo unico que cambia es donde corre.
#
# La directiva syntax de arriba no es decorativa: este archivo usa heredocs
# dentro de RUN (la conversion del requirements y la precarga de modelos), y
# esos necesitan un frontend 1.4 o superior. Sin la linea, el build depende de
# que version de BuildKit tenga el constructor.

FROM python:3.12-slim

# Dependencias nativas que pide opencv (lo usa paddleocr por debajo).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt del repo esta guardado en UTF-16 (lo genero un `pip freeze`
# desde PowerShell). pip en Linux lo lee como binario y falla. Se convierte
# aqui para no tener que tocar el archivo original.
COPY requirements.txt /tmp/requirements.raw
RUN python - <<'PY'
raw = open('/tmp/requirements.raw', 'rb').read()
encoding = 'utf-16' if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8'
open('/tmp/requirements.txt', 'w').write(raw.decode(encoding))
PY

RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Hugging Face corre el contenedor como uid 1000. Paddle descarga sus modelos
# a $HOME/.paddlex, asi que ese directorio tiene que ser escribible por ese
# usuario o el arranque falla con permiso denegado.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR $HOME/app
COPY --chown=user:user app ./app

# Precarga de los modelos durante el build.
#
# Sin esto, la primera peticion real tendria que descargar los 5 modelos
# ademas de procesar la imagen, y se pasaria del readTimeout de 180 s del
# backend. Hornearlos en la imagen hace que el arranque en frio sea solo
# cargar, no descargar.
#
# Se corre un predict de verdad y no solo el constructor: construir el
# pipeline no descarga todo. Varios modelos de PaddleX bajan recien en la
# primera inferencia, asi que sin este paso el contenedor arrancaria "listo"
# y se pondria a descargar igual con el primer comprobante encima.
#
# La imagen sintetica imita un comprobante para recorrer el mismo camino que
# una foto real: deteccion, orientacion, desenrollado y reconocimiento.
RUN python - <<'WARMUP'
import numpy as np
from PIL import Image, ImageDraw
from paddleocr import PaddleOCR

ocr = PaddleOCR(
    use_doc_orientation_classify=True,
    use_doc_unwarping=True,
    use_textline_orientation=True,
    lang="es",
)

canvas = Image.new("RGB", (480, 320), "white")
draw = ImageDraw.Draw(canvas)
draw.text((24, 120), "BOLETA DE VENTA", fill="black")
draw.text((24, 160), "TOTAL S/ 25.00", fill="black")

try:
    ocr.predict(input=np.array(canvas))
    print("warmup: modelos descargados y pipeline ejercitado")
except Exception as exc:
    # Que falle la inferencia sobre una imagen sintetica no es motivo para
    # romper el build: lo que importaba, la descarga, ya ocurrio.
    print("warmup: predict fallo (no critico):", exc)
WARMUP

# Hugging Face expone el 7860 por defecto.
EXPOSE 7860

# --workers 1 a proposito, no por ahorrar memoria.
#
# OcrService escribe todos sus resultados en el mismo directorio "output/":
# cleanOutputDir() lo vacia al inicio de cada peticion y
# getOcrImageFromSystemFile() devuelve el primer archivo que encuentra. Con
# dos workers, una peticion borra el resultado de la otra y puede devolver el
# recibo de otro usuario. Un solo worker serializa las peticiones y lo evita.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
