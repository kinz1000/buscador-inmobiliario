from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "Buscador Inmobiliario"
    database_url: str = "sqlite:///data/inmuebles.db"

    zones: str = "Aluche,Campamento,Los Cármenes,Lucero"

    imap_host: str = "imap.gmail.com"
    imap_port: int = 993
    imap_user: str = ""
    imap_password: str = ""

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    notification_email: str = ""
    alert_email: str = ""

    check_interval_minutes: int = 5

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def zone_list(self) -> list[str]:
        return [
            zone.strip()
            for zone in self.zones.split(",")
            if zone.strip()
        ]


settings = Settings()