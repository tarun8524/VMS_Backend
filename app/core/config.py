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

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
