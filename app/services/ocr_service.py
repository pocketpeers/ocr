from paddleocr import PaddleOCR
from fastapi import UploadFile
from PIL import Image
from typing import Optional
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
    
    async def doOcrFromFile(self,file:UploadFile)->OcrProcess:
        image_bytes= await file.read()
        image = Image.open(io.BytesIO(image_bytes))
        
        result = self.ocrClient.predict(image)
        
        for row in result:
            row.save_to_img(self.outputDir)
        
        ocr_image = self.getOcrImageFromSystemFile() 
        result_text = str(result[0]["rec_texts"])
        
        return OcrProcess(result_text,ocr_image)
        
    async def doOcrFromImageUrl(self,imageUrl:str)->OcrProcess:
        self.cleanOutputDir()
        response = requests.get(imageUrl)
        if response.status_code != 200:
            raise ValueError("No se pudo obtener la imagen desde la URL")
    
        image = Image.open(io.BytesIO(response.content))
        image_np = np.array(image)
        
        result = self.ocrClient.predict(input=image_np)
                
        for row in result:
            row.save_to_img(self.outputDir)
        
        ocr_image = self.getOcrImageFromSystemFile() 
        result_text = str(result[0]["rec_texts"])
        
        return OcrProcess(result_text,ocr_image)
        
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