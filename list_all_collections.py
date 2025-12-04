"""
Script para listar todas las colecciones (incluso vacías) en la base de datos
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

MONGO_URI = "mongodb+srv://rapifarma:w1Y7HoezUiMtfrWt@cluster0.9nirn5t.mongodb.net/?appName=Cluster0"
DB_NAME = "ferreteria_los_puentes"

async def list_all_collections():
    """Lista todas las colecciones, incluso las vacías"""
    client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client[DB_NAME]
    
    try:
        # Obtener todas las colecciones (incluso vacías)
        print(f"📚 Todas las colecciones en '{DB_NAME}':\n")
        collections = await db.list_collection_names()
        
        if not collections:
            print("   ⚠ No hay colecciones")
        else:
            for collection_name in collections:
                # Contar documentos
                collection = db[collection_name]
                count = await collection.count_documents({})
                print(f"   - {collection_name} ({count} documentos)")
        
        print(f"\n✅ Total: {len(collections)} colecciones")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(list_all_collections())

