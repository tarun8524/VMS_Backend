from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # MongoDB
    MONGODB_URL: str = "mongodb+srv://user:pass@cluster.mongodb.net/vms"
    DB_NAME: str = "VMS"

    # Qdrant
    QDRANT_URL: str = "https://your-cluster.qdrant.io"
    QDRANT_API_KEY: str = ""
    COLLECTION_NAME: str = "VMS"
    VECTOR_SIZE: int = 128
    MATCH_THRESHOLD: float = 0.50

    # JWT
    SECRET_KEY: str = "super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    # Email / SMTP
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""          # your Gmail / SMTP username
    SMTP_PASSWORD: str = ""      # app-password or SMTP password
    EMAIL_FROM_NAME: str = "VisitorVault VMS"
    EMAIL_FROM: str = ""         # same as SMTP_USER usually

    # App public URL (used in email links/maps)
    APP_URL: str = "http://localhost:3000"

    # Locations stored in DB seed — these are the predefined coords
    # Block A: 17°21'09.1"N 82°32'13.2"E
    # Block B: 17°21'25.4"N 82°32'19.6"E

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
