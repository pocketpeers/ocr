from ..settings import settings_service
from ..dtos.OcrResponse import OcrResponse
from groq import Groq
import json

class GroqService:
    apiKey:str = settings_service.settings.GROQ_API_KEY
    client:Groq
    model:str = "llama-3.3-70b-versatile"
    
    def __init__(self):
        self.client = Groq(api_key=self.apiKey)
    
    def getJsonFromOcrText(self,text:str)->OcrResponse:
        system_prompt:str = (
            "Eres una API que extrae datos de recibos OCR. "
            "Responde solo con un objeto JSON con este formato:\n"
            '{'
            '"amount": 0.0, '
            '"name": "string", '
            '"issueDate": "YYYY-MM-DD", '
            '"receiptNumber": "string", '
            '"dataFields": { "key": "value" }'
            '}'
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extrae los datos del texto OCR: {text}"}
        ]
        
        chat_completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"}
        )
        result_str = chat_completion.choices[0].message.content
        result_dict = json.loads(result_str)
        return OcrResponse(**result_dict)
    