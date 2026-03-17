from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.core.config import settings

_client: QdrantClient = None


def get_qdrant() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
    return _client


def ensure_collection():
    client = get_qdrant()
    existing = [c.name for c in client.get_collections().collections]
    if settings.COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=settings.COLLECTION_NAME,
            vectors_config=VectorParams(
                size=settings.VECTOR_SIZE,
                distance=Distance.EUCLID,
            ),
        )
        print(f"✅ Qdrant collection '{settings.COLLECTION_NAME}' created")
    else:
        print(f"✅ Qdrant collection '{settings.COLLECTION_NAME}' ready")


def upsert_face(visitor_uid: str, encoding: list[float], meta: dict):
    client = get_qdrant()
    client.upsert(
        collection_name=settings.COLLECTION_NAME,
        points=[PointStruct(id=visitor_uid, vector=encoding, payload=meta)],
    )


def search_face(encoding: list[float], limit: int = 5):
    client = get_qdrant()
    return client.query_points(
        collection_name=settings.COLLECTION_NAME,
        query=encoding,
        limit=limit,
        with_payload=True,
    ).points


def delete_face(visitor_uid: str):
    client = get_qdrant()
    client.delete(collection_name=settings.COLLECTION_NAME, points_selector=[visitor_uid])
