from paddleocr import PaddleOCR
from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
from typing import List, Optional
import os
import tempfile
import io
import requests
from ..model.ocr_process import OcrProcess
import numpy as np
class OcrService:
    """Lectura de comprobantes con PaddleOCR.

    Cada peticion escribe la imagen anotada en un directorio temporal propio.
    Antes todas compartian una carpeta "output" fija que se vaciaba al empezar
    y de la que luego se leia "el primer archivo que haya": con dos peticiones
    a la vez, una borraba el resultado de la otra y podia devolverle a alguien
    el recibo de otra persona. Por eso el servicio tenia que correr con un solo
    worker. Aislando el directorio, ese limite desaparece.
    """

    ocrClient:PaddleOCR

    def __init__(self):
        self.ocrClient = PaddleOCR(
            use_doc_orientation_classify=True,
            use_doc_unwarping=True,
            use_textline_orientation=True,
            lang="es"
        )

    def _open_rgb_image(self, image_bytes: bytes) -> Image.Image:
        try:
            image = Image.open(io.BytesIO(image_bytes))
            image.load()
        except UnidentifiedImageError as exc:
            raise ValueError("El archivo recibido no es una imagen valida") from exc

        return image.convert("RGB")
    
    async def doOcrFromFile(self,file:UploadFile)->OcrProcess:
        image_bytes = await file.read()
        return self._process(self._open_rgb_image(image_bytes))

    async def doOcrFromImageUrl(self,imageUrl:str)->OcrProcess:
        response = requests.get(imageUrl)
        if response.status_code != 200:
            raise ValueError("No se pudo obtener la imagen desde la URL")

        return self._process(self._open_rgb_image(response.content))

    def _process(self, image: Image.Image) -> OcrProcess:
        """Corre el OCR y recoge la imagen anotada sin dejar rastro en disco."""
        result = self.ocrClient.predict(input=np.array(image))

        # Un directorio por peticion, borrado al salir del with. Es lo que
        # permite atender varias a la vez sin que se pisen los resultados.
        with tempfile.TemporaryDirectory(prefix="pocketpeers-ocr-") as outputDir:
            for row in result:
                row.save_to_img(outputDir)
            ocr_image = self._read_annotated_image(outputDir) or image

        return OcrProcess(self._get_result_text(result), ocr_image)

    def _get_result_text(self, result) -> str:
        if not result:
            return ""

        lines: List[str] = []
        for row in result:
            texts = None
            if isinstance(row, dict):
                texts = row.get("rec_texts")
            else:
                try:
                    texts = row["rec_texts"]
                except Exception:
                    texts = None

            if isinstance(texts, list):
                lines.extend(str(text).strip() for text in texts if str(text).strip())
            elif texts:
                lines.append(str(texts).strip())

        if lines:
            return "\n".join(lines)

        return str(result)
        
    def _read_annotated_image(self, outputDir: str) -> Optional[Image.Image]:
        """La imagen con los recuadros que dibujo PaddleOCR, cargada en memoria.

        El copy() no es opcional. PIL abre los archivos de forma perezosa, asi
        que devolver el Image tal cual daria un objeto que apunta a un archivo
        que el directorio temporal borra al cerrarse; el fallo aparecería
        despues, al intentar usarlo, y lejos de aqui.

        Se ordenan los nombres para que, si hubiera varios candidatos, el
        elegido no dependa del orden en que el sistema de archivos los liste.
        """
        for filename in sorted(os.listdir(outputDir)):
            if "ocr" in filename.lower() and filename.lower().endswith((".png", ".jpg", ".jpeg")):
                with Image.open(os.path.join(outputDir, filename)) as img:
                    return img.copy()
        return None    
