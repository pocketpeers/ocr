from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    ENVIRONMENT: str
    DEBUG: bool
    UPLOAD_SERVICE_URL: str
    GROQ_API_KEY: str

    # Credencial de servicio para escribir en /api/v1/images del backend.
    #
    # Ese endpoint esta en permitAll(), asi que en produccion Caddy bloquea los
    # POST que no traigan ni Authorization ni este token: sin el, el OCR recibe
    # 403 al devolver la imagen procesada. Opcional a proposito, porque en
    # desarrollo no hay proxy delante y exigirlo obligaria a definirlo para
    # correr el servicio en local.
    SERVICE_TOKEN: Optional[str] = None

    class Config:
        env_file = ".env.dev"  # o cambia esto dinámicamente

settings = Settings()
