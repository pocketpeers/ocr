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

        response = requests.post(self.api_url, files=files)
        response.raise_for_status()
        return response.json()