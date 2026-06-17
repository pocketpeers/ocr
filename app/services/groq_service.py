from ..settings import settings_service
from ..dtos.OcrResponse import OcrResponse
from groq import Groq
from groq import APIStatusError, APIConnectionError
from datetime import date, datetime
from decimal import Decimal
from typing import List, Tuple
import json
import re

class GroqService:
    client:Groq
    model:str = "llama-3.3-70b-versatile"
    
    def __init__(self):
        self.apiKey = settings_service.settings.GROQ_API_KEY
        self.client = Groq(api_key=self.apiKey)
    
    def getJsonFromOcrText(self,text:str)->OcrResponse:
        fallback_response = self._parse_receipt_text(text)

        system_prompt:str = (
            "Eres una API que extrae datos de recibos OCR. "
            "Responde solo con un objeto JSON valido con este formato:\n"
            '{'
            '"amount": 0.0, '
            '"name": "string", '
            '"issueDate": "YYYY-MM-DD", '
            '"receiptNumber": "string", '
            '"dataFields": { "key": "value" }'
            '} '
            "Si no encuentras un dato, usa los valores ya inferidos en el texto del usuario."
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    "Texto OCR:\n"
                    f"{text}\n\n"
                    "Valores inferidos como respaldo:\n"
                    f"{fallback_response.model_dump_json()}"
                )
            }
        ]
        
        try:
            chat_completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"}
            )
            result_str = chat_completion.choices[0].message.content
            result_dict = json.loads(result_str)
            result_dict["dataFields"] = {
                **fallback_response.dataFields,
                **result_dict.get("dataFields", {}),
                "parser": "groq",
            }
            return OcrResponse(**result_dict)
        except (APIStatusError, APIConnectionError, json.JSONDecodeError, ValueError) as exc:
            fallback_response.dataFields["parser"] = "fallback"
            fallback_response.dataFields["parserError"] = str(exc)
            return fallback_response

    def _parse_receipt_text(self, text: str) -> OcrResponse:
        lines = self._clean_lines(text)
        amount = self._extract_amount(lines)
        issue_date = self._extract_date(lines)
        receipt_number = self._extract_receipt_number(lines)
        name = self._extract_name(lines)

        return OcrResponse(
            amount=amount,
            name=name,
            issueDate=issue_date,
            receiptNumber=receipt_number,
            dataFields={
                "rawText": "\n".join(lines),
                "detectedLines": lines,
            }
        )

    def _clean_lines(self, text: str) -> List[str]:
        if not text:
            return []

        normalized = text.replace("\\n", "\n").replace("\\r", "\n")
        normalized = normalized.replace("[", "\n").replace("]", "\n")
        normalized = normalized.replace("'", "").replace('"', "")
        return [
            re.sub(r"\s+", " ", line).strip()
            for line in normalized.splitlines()
            if line.strip()
        ]

    def _extract_amount(self, lines: List[str]) -> Decimal:
        candidates: List[Tuple[int, Decimal]] = []
        priority_words = ("total", "importe", "monto", "pagar", "venta")

        for line in lines:
            lower_line = line.lower()
            priority = 1 if any(word in lower_line for word in priority_words) else 0
            for match in re.findall(r"(?:s\/|soles|pen)?\s*(\d{1,5}(?:[.,]\d{2}))", lower_line):
                try:
                    candidates.append((priority, Decimal(match.replace(",", "."))))
                except Exception:
                    continue

        if not candidates:
            return Decimal("0.00")

        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return candidates[0][1]

    def _extract_date(self, lines: List[str]) -> date:
        date_patterns = (
            r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b",
            r"\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b",
        )

        for line in lines:
            for pattern in date_patterns:
                match = re.search(pattern, line)
                if not match:
                    continue

                parts = [int(part) for part in match.groups()]
                try:
                    if len(str(match.group(1))) == 4:
                        return date(parts[0], parts[1], parts[2])

                    year = parts[2] + 2000 if parts[2] < 100 else parts[2]
                    return date(year, parts[1], parts[0])
                except ValueError:
                    continue

        return datetime.now().date()

    def _extract_receipt_number(self, lines: List[str]) -> str:
        pattern = re.compile(
            r"(?:boleta|factura|ticket|recibo|nro|n\.|numero|serie|doc(?:umento)?)\D*([A-Z0-9]{1,6}[- ]?\d{3,12})",
            re.IGNORECASE,
        )

        for line in lines:
            match = pattern.search(line)
            if match:
                return match.group(1).replace(" ", "-")

        for line in lines:
            match = re.search(r"\b([A-Z]\d{3}[- ]?\d{3,12}|\d{3,6}[- ]\d{3,12})\b", line, re.IGNORECASE)
            if match:
                return match.group(1).replace(" ", "-")

        return "OCR-PENDING"

    def _extract_name(self, lines: List[str]) -> str:
        ignored_words = (
            "ruc", "dni", "boleta", "factura", "ticket", "recibo", "fecha",
            "total", "subtotal", "igv", "importe", "monto", "direccion",
            "telefono", "cliente",
        )

        for line in lines[:10]:
            lower_line = line.lower()
            has_letters = re.search(r"[a-zA-Z]", line) is not None
            has_ignored_word = any(word in lower_line for word in ignored_words)
            if has_letters and not has_ignored_word and len(line) >= 3:
                return line[:120]

        return "Comprobante OCR"
    
