"""
Script para clonar la estructura de una base de datos MongoDB (sin datos)
y crear una nueva base de datos con la misma estructura.
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import certifi
from pymongo.errors import OperationFailure

# Configuración de conexión
# Nota: Si el password tiene caracteres especiales, usa urllib.parse.quote_plus() para codificarlos
MONGO_URI = "mongodb+srv://rapifarma:w1Y7HoezUiMtfrWt@cluster0.9nirn5t.mongodb.net/?appName=Cluster0"
SOURCE_DB_NAME = "RAPIFARMA"
TARGET_DB_NAME = "ferreteria_los_puentes"  # MongoDB no permite espacios en nombres de BD

async def get_collection_indexes(client, db_name, collection_name):
    """Obtiene todos los índices de una colección"""
    db = client[db_name]
    collection = db[collection_name]
    
    try:
        indexes = await collection.list_indexes().to_list(length=None)
        return indexes
    except Exception as e:
        print(f"Error obteniendo índices de {collection_name}: {e}")
        return []

async def get_collection_validation(client, db_name, collection_name):
    """Obtiene las reglas de validación de una colección"""
    db = client[db_name]
    try:
        # Obtener información de la colección usando listCollections
        cursor = db.list_collections(filter={"name": collection_name})
        collections = await cursor.to_list(length=1)
        
        if collections and len(collections) > 0:
            options = collections[0].get("options", {})
            validator = options.get("validator")
            validation_level = options.get("validationLevel", "strict")
            validation_action = options.get("validationAction", "error")
            
            if validator:
                return {
                    "validator": validator,
                    "validationLevel": validation_level,
                    "validationAction": validation_action
                }
    except Exception as e:
        # Silenciar errores de validación si no existen
        pass
    
    return None

async def copy_collection_structure(client, source_db, target_db, collection_name):
    """Copia la estructura de una colección (índices y validaciones) sin datos"""
    source_collection = source_db[collection_name]
    target_collection = target_db[collection_name]
    
    print(f"\n📋 Procesando colección: {collection_name}")
    
    # 1. Obtener y copiar índices
    try:
        indexes = await source_collection.list_indexes().to_list(length=None)
        print(f"   Encontrados {len(indexes)} índices")
        
        for index in indexes:
            index_name = index.get("name")
            if index_name == "_id_":  # El índice _id se crea automáticamente
                continue
            
            index_keys = index.get("key", {})
            index_options = {k: v for k, v in index.items() if k not in ["v", "key", "name", "ns"]}
            
            try:
                await target_collection.create_index(
                    list(index_keys.items()),
                    name=index_name,
                    **index_options
                )
                print(f"   ✓ Índice '{index_name}' creado")
            except Exception as e:
                print(f"   ⚠ Error creando índice '{index_name}': {e}")
    except Exception as e:
        print(f"   ⚠ Error procesando índices: {e}")
    
    # 2. Obtener y copiar validaciones
    try:
        validation_info = await get_collection_validation(client, SOURCE_DB_NAME, collection_name)
        if validation_info and validation_info.get("validator"):
            # Crear la colección con validación usando collMod
            try:
                await target_db.command({
                    "collMod": collection_name,
                    "validator": validation_info["validator"],
                    "validationLevel": validation_info.get("validationLevel", "strict"),
                    "validationAction": validation_info.get("validationAction", "error")
                })
                print(f"   ✓ Validaciones copiadas")
            except Exception as e:
                # Si la colección ya existe, intentar modificar
                pass  # Las validaciones son opcionales
    except Exception:
        pass  # Las validaciones son opcionales

async def main():
    """Función principal"""
    print("=" * 60)
    print("🚀 Iniciando clonación de estructura de base de datos")
    print("=" * 60)
    print(f"📦 Base de datos origen: {SOURCE_DB_NAME}")
    print(f"📦 Base de datos destino: {TARGET_DB_NAME}")
    print("=" * 60)
    
    # Conectar a MongoDB
    client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
    
    try:
        # Obtener lista de colecciones de la base de datos origen
        source_db = client[SOURCE_DB_NAME]
        collections = await source_db.list_collection_names()
        
        if not collections:
            print(f"\n⚠ No se encontraron colecciones en {SOURCE_DB_NAME}")
            return
        
        print(f"\n📚 Colecciones encontradas: {len(collections)}")
        for col in collections:
            print(f"   - {col}")
        
        # Crear referencia a la base de datos destino
        target_db = client[TARGET_DB_NAME]
        
        # Verificar que la base de datos destino esté vacía o confirmar creación
        target_collections = await target_db.list_collection_names()
        if target_collections:
            print(f"\n⚠ La base de datos '{TARGET_DB_NAME}' ya existe y tiene {len(target_collections)} colecciones")
            print("   Continuando con la copia de estructura...")
        
        # Copiar estructura de cada colección
        print(f"\n🔄 Copiando estructura de colecciones...")
        for collection_name in collections:
            await copy_collection_structure(client, source_db, target_db, collection_name)
        
        print("\n" + "=" * 60)
        print("✅ Proceso completado exitosamente!")
        print("=" * 60)
        print(f"📦 Nueva base de datos '{TARGET_DB_NAME}' creada con la estructura de '{SOURCE_DB_NAME}'")
        print("   (Sin datos, solo estructura: índices y validaciones)")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error durante el proceso: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()
        print("\n🔌 Conexión cerrada")

if __name__ == "__main__":
    asyncio.run(main())

