from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "mysql+pymysql://root:password@localhost:3306/rentora"
    jwt_secret: str = "change-this-secret-key"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080
    google_client_id: str = ""
    email_host: str = "smtp.gmail.com"
    email_port: int = 587
    email_user: str = ""
    email_password: str = ""

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
