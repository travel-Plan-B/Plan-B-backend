from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    KAKAO_REST_API_KEY: str = ""
    KMA_SERVICE_KEY: str = ""
    TOUR_API_KEY: str = ""
    GOOGLE_PLACES_API_KEY: str = ""

    class Config:
        env_file = ".env"


settings = Settings() # type: ignore
