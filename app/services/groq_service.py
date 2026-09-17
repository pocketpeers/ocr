from ..settings import settings_service
from ..dtos.OcrResponse import OcrResponse
from groq import Groq
from groq import APIStatusError, APIConnectionError
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Tuple
import json
import re

class GroqService:
    client:Groq
    # Groq retiro llama-3.3-70b-versatile de su catalogo y devolvia
    # "404 model_not_found", asi que toda peticion caia al parser de regex de
    # _parse_receipt_text sin que se notara: el JSON llegaba igual, solo que
    # con "parser": "fallback" en dataFields.
    #
    # Groq rota su catalogo cada cierto tiempo. Si vuelve a dar 404, la lista
    # vigente esta en https://api.groq.com/openai/v1/models
    model:str = "openai/gpt-oss-20b"

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
            '"issuerRuc": "string", '
            '"dataFields": { "key": "value" }'
            '} '
            "El issuerRuc son los 11 digitos del RUC del emisor, sin espacios ni guiones. "
            "Si no encuentras un dato, usa los valores ya inferidos en el texto del usuario. "
            "Si un dato no aparece ni fue inferido, responde null: nunca inventes un "
            "numero de comprobante ni un RUC, porque el backend los usa para detectar "
            "boletas repetidas y un valor inventado acusaria a un usuario honesto."
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
        issuer_ruc = self._extract_ruc(lines)
        name = self._extract_name(lines)

        return OcrResponse(
            amount=amount,
            name=name,
            issueDate=issue_date,
            receiptNumber=receipt_number,
            issuerRuc=issuer_ruc,
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

    def _extract_receipt_number(self, lines: List[str]) -> Optional[str]:
        pattern = re.compile(
            r"(?:boleta|factura|ticket|recibo|nro|n\.|numero|serie|doc(?:umento)?)\D*([A-Z0-9]{1,6}[- ]?\d{3,12})",
            re.IGNORECASE,
        )

        for line in lines:
            match = pattern.search(line)
            if match:
                return self._normalize_receipt_number(match.group(1))

        for line in lines:
            match = re.search(r"\b([A-Z]\d{3}[- ]?\d{3,12}|\d{3,6}[- ]\d{3,12})\b", line, re.IGNORECASE)
            if match:
                return self._normalize_receipt_number(match.group(1))

        # None, no un centinela. El backend compara este valor contra los ya
        # registrados para detectar boletas repetidas: cualquier texto fijo
        # haria que dos comprobantes ilegibles distintos parecieran el mismo.
        return None

    def _normalize_receipt_number(self, raw: str) -> str:
        # A mayusculas porque el OCR alterna entre "B001-123" y "b001-123" sobre
        # la misma boleta, y dos grafias del mismo documento tienen que colapsar
        # en la misma llave o la deteccion de duplicados se pierde.
        return raw.replace(" ", "-").upper()

    def _extract_ruc(self, lines: List[str]) -> Optional[str]:
        """RUC del emisor: 11 digitos que empiezan en 10, 15, 17 o 20.

        Se prefiere el que aparece junto a la palabra RUC y, entre varios, el
        que pasa el digito verificador. El respaldo existe porque el OCR
        confunde digitos con frecuencia: si ningun candidato valida, vale mas
        entregar el rotulado que ninguno, ya que el backend solo lo usa junto
        con el numero de comprobante y nunca por si solo.
        """
        labelled: List[str] = []
        loose: List[str] = []

        for line in lines:
            for match in re.finditer(r"\b((?:10|15|17|20)\d{9})\b", line):
                candidate = match.group(1)
                if re.search(r"r\.?\s*u\.?\s*c", line, re.IGNORECASE):
                    labelled.append(candidate)
                else:
                    loose.append(candidate)

        for group in (labelled, loose):
            for candidate in group:
                if self._is_valid_ruc(candidate):
                    return candidate

        return labelled[0] if labelled else None

    @staticmethod
    def _is_valid_ruc(ruc: str) -> bool:
        # Digito verificador de SUNAT: modulo 11 sobre los diez primeros
        # digitos con pesos fijos. Descarta casi todas las cadenas de once
        # cifras que el OCR inventa a partir de telefonos o codigos de barras.
        weights = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
        total = sum(int(digit) * weight for digit, weight in zip(ruc, weights))
        remainder = 11 - (total % 11)
        if remainder == 10:
            remainder = 0
        elif remainder == 11:
            remainder = 1
        return remainder == int(ruc[10])

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
    
