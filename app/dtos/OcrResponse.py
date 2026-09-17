from pydantic import BaseModel
from typing import Dict, Any
from decimal import Decimal
from datetime import date
from typing import Optional

class OcrResponse(BaseModel):
    imagePath: Optional[str] = None
    amount: Decimal
    name: str
    issueDate: date
    # Opcionales a proposito. Antes receiptNumber devolvia el literal
    # "OCR-PENDING" cuando no se encontraba numero, y ese centinela hacia que
    # todos los comprobantes ilegibles compartieran el mismo valor: con el
    # indice unico del backend, el segundo usuario con una foto borrosa habria
    # quedado bloqueado por el primero. Ausente tiene que ser null, no un texto.
    receiptNumber: Optional[str] = None
    issuerRuc: Optional[str] = None
    dataFields: Dict[str, Any]
