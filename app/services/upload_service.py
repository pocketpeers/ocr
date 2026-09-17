from ..settings.settings_service import settings
import io
import requests
from PIL import Image

class UploadService:
    api_url:str = settings.UPLOAD_SERVICE_URL
    
    def crop_left_half(self, image: Image.Image) -> Image.Image:
        width, height = image.size
        return image.crop((0, 0, width // 2, height))
    
    def upload_image(self, image: Image.Image, filename: str = "image.png"):
        cropped_image = self.crop_left_half(image)

        buffer = io.BytesIO()
        format = image.format if image.format else 'PNG'
        cropped_image.save(buffer, format=format)
        buffer.seek(0)

        mime_type = f"image/{format.lower()}"
        files = {
            "file": (filename, buffer, mime_type)
        }

        response = requests.post(self.api_url, files=files, headers=self._service_headers())
        response.raise_for_status()
        return response.json()

    def _service_headers(self) -> dict:
        """Credencial con la que el OCR se identifica ante el backend.

        /api/v1/images esta en permitAll(), asi que en produccion Caddy rechaza
        con 403 los POST que no traigan ni Authorization ni este token. El OCR no
        tiene sesion de usuario —es un servicio hablandole a otro—, de modo que
        esta es su unica credencial posible.

        Se omite cuando no hay token configurado, que es el caso de desarrollo:
        ahi no hay proxy delante y el backend acepta la subida igual. Mandar la
        cabecera vacia seria peor, porque en produccion parecerian un token
        invalido y el 403 costaria mas de diagnosticar.
        """
        token = settings.SERVICE_TOKEN
        return {"X-Service-Token": token} if token else {}