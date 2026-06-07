from ..services.groq_service import GroqService
from ..services.ocr_service import OcrService
from ..services.upload_service import UploadService
from ..services.gateway_service import GatewayService
from fastapi import Depends
def get_groq_service():
    return GroqService()

def get_ocr_service():
    return OcrService()

def get_upload_service():
    return UploadService()

def get_gateway_service(
    ocr: OcrService = Depends(get_ocr_service),
    groq: GroqService = Depends(get_groq_service),
    upload: UploadService = Depends(get_upload_service),
):
    return GatewayService(ocr, groq, upload)
