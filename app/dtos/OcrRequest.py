from pydantic import BaseModel

class OcrRequest(BaseModel):
    imageUrl:str