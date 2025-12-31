from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 33333

    # Database
    MYSQL_HOST: str
    MYSQL_PORT: int = 3306
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_DATABASE: str

    # Redis
    REDIS_HOST: str
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    # CORS
    CORS_ALLOWED_FRONTEND_URL: str

    # OAuth - Google
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""

    # OAuth - Kakao
    KAKAO_CLIENT_ID: str = ""
    KAKAO_CLIENT_SECRET: str = ""
    KAKAO_REDIRECT_URI: str = ""

    # OAuth - Naver
    NAVER_CLIENT_ID: str = ""
    NAVER_CLIENT_SECRET: str = ""
    NAVER_REDIRECT_URI: str = ""

    # OAuth - Meta
    META_CLIENT_ID: str = ""
    META_CLIENT_SECRET: str = ""
    META_REDIRECT_URI: str = ""

    # Security
    CSRF_SECRET_KEY: str
    COOKIE_SECURE: bool = False  # Set True in production (HTTPS)
    COOKIE_SAMESITE: str = "lax"

    # JWT Settings
    JWT_SECRET_KEY: str = ""  # Secret key for JWT signing
    JWT_ENCRYPTION_KEY: str = ""  # Key for AES encryption of user-specific keys
    JWT_EXPIRY_HOURS: int = 12  # Token validity period in hours
    JWT_HTTPONLY: bool = True  # HttpOnly flag for JWT cookie

    # Environment
    ENVIRONMENT: str = "local"  # local, staging, production

    # Session (legacy - kept for backward compatibility)
    SESSION_TTL_SECONDS: int = 86400  # 24 hours

    # Frontend URL for redirects after OAuth
    FRONTEND_URL: str

    # Qdrant Vector DB
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_GRPC_PORT: int = 6334
    QDRANT_API_KEY: str = ""  # Optional, for cloud Qdrant
    QDRANT_COLLECTION_NAME: str = "counsel_data"
    QDRANT_VECTOR_SIZE: int = 384  # sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

    # AWS S3 Settings
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str
    AWS_S3_BUCKET: str

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_local(self) -> bool:
        """Check if running in local development environment."""
        return self.ENVIRONMENT.lower() == "local"

    @property
    def effective_cookie_secure(self) -> bool:
        """Get effective cookie secure setting based on environment.

        Local environment: False (allows HTTP)
        Production environment: True (requires HTTPS)
        """
        if self.is_local:
            return False
        return self.COOKIE_SECURE or self.is_production

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra env vars like MYSQL_ROOT_PASSWORD


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
