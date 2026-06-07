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
    receiptNumber: str
    dataFields: Dict[str, Any]