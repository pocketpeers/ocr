---
title: PocketPeers OCR
emoji: 🧾
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# PocketPeers OCR

Servicio FastAPI que extrae datos de comprobantes de pago con PaddleOCR y los
estructura con Groq.

Este archivo es el README **del Space**, no el del repositorio. Hugging Face
lee la cabecera YAML de arriba para saber que es un Space de Docker y en que
puerto escucha la app. Al crear el Space, este archivo debe llamarse
`README.md` dentro del Space.

## Secretos que hay que configurar

En el Space: **Settings -> Variables and secrets**. Van como *Secrets*, no como
*Variables públicas*:

| Nombre | Valor |
|---|---|
| `ENVIRONMENT` | `prod` |
| `DEBUG` | `False` |
| `UPLOAD_SERVICE_URL` | `https://TU-VM.brazilsouth.cloudapp.azure.com/api/v1/images` |
| `GROQ_API_KEY` | Tu llave de Groq |
| `SERVICE_TOKEN` | El mismo valor que pusiste en el backend |

`settings_service.py` apunta a `.env.dev`, pero ese archivo no existe en el
contenedor: pydantic-settings cae de vuelta a las variables de entorno, que es
justo lo que inyecta Hugging Face. No hay que cambiar nada.

## Privacidad

Los Spaces gratuitos son **públicos por defecto**. Aquí viajan fotos de
recibos, así que conviene ponerlo en **privado** desde Settings.

## Nota sobre `UPLOAD_SERVICE_URL`

Se usa para dos cosas distintas con la misma base:

- `receipts_ocr_router.py` arma `{UPLOAD_SERVICE_URL}/{imageUrl}` para
  **descargar** la imagen original
- `upload_service.py` hace POST a `{UPLOAD_SERVICE_URL}` para **subir** la
  imagen ya procesada

Por eso tiene que apuntar al endpoint de imágenes del backend, sin barra final.
