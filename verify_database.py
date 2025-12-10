"""
Script para verificar y crear la base de datos ferreteria_los_puentes
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

MONGO_URI = "mongodb+srv://rapifarma:w1Y7HoezUiMtfrWt@cluster0.9nirn5t.mongodb.net/?appName=Cluster0"

async def verify_and_create_db():
    """Verifica y crea la base de datos si es necesario"""
    client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
    
    try:
        # Listar todas las bases de datos
        print("📋 Bases de datos disponibles:")
        db_list = await client.list_database_names()
        for db_name in db_list:
            print(f"   - {db_name}")
        
        # Verificar si existe ferreteria_los_puentes
        target_db_name = "ferreteria_los_puentes"
        target_db = client[target_db_name]
        
        if target_db_name in db_list:
            print(f"\n✅ La base de datos '{target_db_name}' existe")
        else:
            print(f"\n⚠ La base de datos '{target_db_name}' no aparece en la lista")
            print("   (Esto es normal si está vacía - MongoDB no muestra BDs vacías)")
        
        # Verificar colecciones
        print(f"\n📚 Colecciones en '{target_db_name}':")
        collections = await target_db.list_collection_names()
        
        if collections:
            print(f"   Encontradas {len(collections)} colecciones:")
            for col in collections[:10]:  # Mostrar las primeras 10
                print(f"   - {col}")
            if len(collections) > 10:
                print(f"   ... y {len(collections) - 10} más")
        else:
            print("   ⚠ No hay colecciones (la BD está vacía)")
            print("   Creando una colección de prueba para hacer visible la BD...")
            
            # Crear una colección de prueba con un documento
            test_collection = target_db["_test_visibility"]
            await test_collection.insert_one({"test": True, "created": "para hacer visible la BD"})
            print("   ✅ Colección de prueba creada")
        
        # Verificar que ahora aparece en la lista
        print(f"\n🔄 Verificando nuevamente...")
        db_list_after = await client.list_database_names()
        if target_db_name in db_list_after:
            print(f"✅ '{target_db_name}' ahora es visible en MongoDB Atlas")
        else:
            print(f"⚠ '{target_db_name}' aún no aparece (puede tardar unos segundos)")
        
        print("\n" + "=" * 60)
        print("✅ Verificación completada")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(verify_and_create_db())


