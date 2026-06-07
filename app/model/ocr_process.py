from PIL import Image

class OcrProcess:
    text:str
    imageProccesed:Image.Image
    
    def __init__(self, text: str, imageProccesed: Image.Image):
        self.text = text
        self.imageProccesed = imageProccesed