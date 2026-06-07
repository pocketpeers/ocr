from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ENVIRONMENT: str
    DEBUG: bool
    UPLOAD_SERVICE_URL: str
    GROQ_API_KEY: str

    class Config:
        env_file = ".env.dev"  # o cambia esto dinámicamente

settings = Settings()