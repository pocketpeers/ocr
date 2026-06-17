from paddleocr import PaddleOCR
from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
from typing import List, Optional
import os
import shutil
import io
import requests
from ..model.ocr_process import OcrProcess
import numpy as np
class OcrService:
    ocrClient:PaddleOCR
    outputDir:str = "output"
    
    def __init__(self):
        self.ocrClient = PaddleOCR(
            use_doc_orientation_classify=True,
            use_doc_unwarping=True,
            use_textline_orientation=True,
            lang="es"
        )
        # Asegurar que la carpeta output existe al iniciar
        if not os.path.exists(self.outputDir):
            os.makedirs(self.outputDir)

    def _open_rgb_image(self, image_bytes: bytes) -> Image.Image:
        try:
            image = Image.open(io.BytesIO(image_bytes))
            image.load()
        except UnidentifiedImageError as exc:
            raise ValueError("El archivo recibido no es una imagen valida") from exc

        return image.convert("RGB")
    
    async def doOcrFromFile(self,file:UploadFile)->OcrProcess:
        self.cleanOutputDir()
        image_bytes= await file.read()
        image = self._open_rgb_image(image_bytes)
        image_np = np.array(image)
        
        result = self.ocrClient.predict(input=image_np)
        
        for row in result:
            row.save_to_img(self.outputDir)
        
        ocr_image = self.getOcrImageFromSystemFile() or image
        result_text = self._get_result_text(result)
        
        return OcrProcess(result_text,ocr_image)
        
    async def doOcrFromImageUrl(self,imageUrl:str)->OcrProcess:
        self.cleanOutputDir()
        response = requests.get(imageUrl)
        if response.status_code != 200:
            raise ValueError("No se pudo obtener la imagen desde la URL")
    
        image = self._open_rgb_image(response.content)
        image_np = np.array(image)
        
        result = self.ocrClient.predict(input=image_np)
                
        for row in result:
            row.save_to_img(self.outputDir)
        
        ocr_image = self.getOcrImageFromSystemFile() or image
        result_text = self._get_result_text(result)
        
        return OcrProcess(result_text,ocr_image)

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
        
    def getOcrImageFromSystemFile(self) -> Optional[Image.Image]:
        # Buscar la primera imagen con 'ocr' en su nombre dentro de outputDir
        for filename in os.listdir(self.outputDir):
            if "ocr" in filename.lower() and filename.lower().endswith((".png", ".jpg", ".jpeg")):
                image_path = os.path.join(self.outputDir, filename)
                img = Image.open(image_path)
                return img
        return None
        
    def cleanOutputDir(self):
        if os.path.exists(self.outputDir):
            for filename in os.listdir(self.outputDir):
                file_path = os.path.join(self.outputDir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
        else:
            os.makedirs(self.outputDir)    
