from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True, env_prefix="APP_")

    SECRET_KEY: str
    DEBUG: bool = False
    CORS_ORIGINS: list[str] | str

    DATABASE_URL: str

    @property
    def cors_origins(self) -> list[str]:
        if isinstance(self.CORS_ORIGINS, str):
            return [
                origin.strip()
                for origin in self.CORS_ORIGINS.split(",")
                if origin.strip()
            ]
        return self.CORS_ORIGINS


# settings = AppConfig()
settings = AppConfig()
