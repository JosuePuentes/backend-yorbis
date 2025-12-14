from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase
from app.core.config import MONGO_URI, DATABASE_NAME
import certifi

client = AsyncIOMotorClient(MONGO_URI,tlsCAFile=certifi.where())
db = client[DATABASE_NAME or "ferreteria_los_puentes"]


def get_collection(nombre: str) -> AsyncIOMotorCollection:
    return db[nombre]

def get_database() -> AsyncIOMotorDatabase:
    """Obtiene la instancia de la base de datos para usar en transacciones"""
    return db

def get_client() -> AsyncIOMotorClient:
    """Obtiene el cliente de MongoDB para usar en transacciones"""
    return client
