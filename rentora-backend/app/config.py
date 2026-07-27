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
    # Razorpay test/live keys - leave blank to keep using the simple
    # "dev mode" instant-pay button (no real payment gateway).
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""

    # Comma-separated list of frontend URLs allowed to call this API
    # (CORS). Defaults cover local development (Live Server's usual
    # ports). In production, set this in .env to your real deployed
    # frontend URL(s), e.g. "https://rentora.netlify.app" - never leave
    # this as "*" once real users/tokens are involved.
    allowed_origins: str = "http://localhost:5500,http://127.0.0.1:5500,http://localhost:5501,http://127.0.0.1:5501"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
