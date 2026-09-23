from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./writlynxai.db"
    session_ttl_seconds: int = 3600
    authorization_ttl_seconds: int = 120
    nonce_bytes: int = 24
    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_prefix="WRITLYNX_",
        env_file=".env",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
