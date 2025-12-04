from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from app.core.config import MONGO_URI, DATABASE_NAME
import certifi

client = AsyncIOMotorClient(MONGO_URI,tlsCAFile=certifi.where())
db = client["RAPIFARMA"]


def get_collection(nombre: str) -> AsyncIOMotorCollection:
    return db[nombre]
