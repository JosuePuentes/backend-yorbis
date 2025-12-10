"""
Script para verificar la conexión a MongoDB y los índices existentes
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

MONGO_URI = "mongodb+srv://rapifarma:w1Y7HoezUiMtfrWt@cluster0.9nirn5t.mongodb.net/?appName=Cluster0"
DATABASE_NAME = "ferreteria_los_puentes"

async def verify_connection_and_indexes():
    """Verifica la conexión a MongoDB y los índices existentes"""
    print("🔌 Conectando a MongoDB...")
    client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
    
    try:
        # Verificar conexión
        print("✅ Conexión establecida exitosamente")
        
        # Verificar que la base de datos existe
        db = client[DATABASE_NAME]
        print(f"\n📊 Base de datos: {DATABASE_NAME}")
        
        # Listar colecciones
        collections = await db.list_collection_names()
        print(f"\n📚 Colecciones encontradas: {len(collections)}")
        if collections:
            for col in collections[:10]:
                print(f"   - {col}")
            if len(collections) > 10:
                print(f"   ... y {len(collections) - 10} más")
        
        # Verificar índices en INVENTARIOS
        print(f"\n🔍 Verificando índices en la colección INVENTARIOS...")
        inventarios_collection = db["INVENTARIOS"]
        
        # Contar documentos
        count = await inventarios_collection.count_documents({})
        print(f"   📦 Documentos en INVENTARIOS: {count}")
        
        # Listar índices
        indexes = await inventarios_collection.list_indexes().to_list(length=None)
        print(f"\n📋 Índices existentes ({len(indexes)}):")
        
        has_text_index = False
        has_compound_index = False
        has_codigo_index = False
        has_nombre_index = False
        
        for index in indexes:
            index_name = index.get('name', 'sin nombre')
            index_key = index.get('key', {})
            index_type = index.get('textIndexVersion') or index.get('weights')
            
            print(f"\n   📌 {index_name}:")
            print(f"      Claves: {index_key}")
            
            if index_type:
                print(f"      Tipo: Índice de texto")
                has_text_index = True
            elif 'codigo' in index_key and len(index_key) == 1:
                has_codigo_index = True
            elif 'nombre' in index_key and len(index_key) == 1:
                has_nombre_index = True
            elif 'farmacia' in index_key and 'estado' in index_key:
                has_compound_index = True
        
        # Resumen de optimizaciones
        print(f"\n{'='*60}")
        print("📊 RESUMEN DE OPTIMIZACIONES:")
        print(f"{'='*60}")
        print(f"   ✅ Índice de texto: {'SÍ' if has_text_index else 'NO'}")
        print(f"   ✅ Índice compuesto (farmacia + estado): {'SÍ' if has_compound_index else 'NO'}")
        print(f"   ✅ Índice en código: {'SÍ' if has_codigo_index else 'NO'}")
        print(f"   ✅ Índice en nombre: {'SÍ' if has_nombre_index else 'NO'}")
        
        if not (has_text_index or has_compound_index or has_codigo_index or has_nombre_index):
            print(f"\n⚠️  ADVERTENCIA: No se encontraron índices optimizados.")
            print(f"   Ejecuta 'python create_indexes.py' para crearlos.")
        else:
            print(f"\n✅ Los índices optimizados están configurados correctamente!")
        
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()
        print("🔌 Conexión cerrada")

if __name__ == "__main__":
    asyncio.run(verify_connection_and_indexes())

