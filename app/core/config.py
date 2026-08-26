from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    KAKAO_REST_API_KEY: str = ""
    KMA_SERVICE_KEY: str = ""
    TOUR_API_KEY: str = ""
    GOOGLE_PLACES_API_KEY: str = ""
    CLAUDE_API_KEY: str = ""
    ODSAY_API_KEY: str

    class Config:
        env_file = ".env"


settings = Settings()  # type: ignore
