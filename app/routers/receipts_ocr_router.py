from fastapi import APIRouter,UploadFile,File,Depends
from ..dtos.OcrRequest import OcrRequest
from ..dtos.OcrResponse import OcrResponse
from ..services.gateway_service import GatewayService
from ..settings.settings_service import settings
from ..dependencies.dependecies_services import get_gateway_service

router = APIRouter(
    prefix="/receipt-ocr",
    tags=["Receipt OCR"]
)

@router.post(path="")
async def ocr_process(
    body:OcrRequest,
    gateway_service: GatewayService = Depends(get_gateway_service)
)->OcrResponse:
    urlImage:str = f"{settings.UPLOAD_SERVICE_URL}/{body.imageUrl}"
    return await gateway_service.ocrProcess(urlImage)
