"""
Script para crear índices optimizados para el punto de venta
Esto mejorará significativamente el rendimiento de las búsquedas de productos
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import certifi

# Cargar variables de entorno
load_dotenv()

# Obtener variables de entorno directamente (sin depender de config.py)
MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME") or "ferreteria_los_puentes"

# Si no está configurada, usar la URI por defecto (para desarrollo)
if not MONGO_URI:
    MONGO_URI = "mongodb+srv://rapifarma:w1Y7HoezUiMtfrWt@cluster0.9nirn5t.mongodb.net/?appName=Cluster0"
    print("⚠️  Usando URI por defecto (no se encontró MONGO_URI en variables de entorno)")

async def create_indexes():
    """Crea índices optimizados para búsquedas de productos"""
    print("🚀 Creando índices para optimizar búsquedas de productos...")
    
    client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client[DATABASE_NAME or "ferreteria_los_puentes"]
    inventarios_collection = db["INVENTARIOS"]
    
    try:
        # 1. Índice de texto para búsqueda rápida en múltiples campos
        # Este índice permite búsquedas de texto eficientes en codigo, nombre, descripcion y marca
        print("📝 Creando índice de texto...")
        try:
            await inventarios_collection.create_index([
                ("codigo", "text"),
                ("nombre", "text"),
                ("descripcion", "text"),
                ("marca", "text")
            ], name="text_search_index", default_language="es")
            print("   ✅ Índice de texto creado")
        except Exception as e:
            print(f"   ⚠ Error creando índice de texto (puede que ya exista): {e}")
        
        # 2. Índice compuesto para filtros comunes (farmacia + estado)
        print("📝 Creando índice compuesto (farmacia + estado)...")
        try:
            await inventarios_collection.create_index([
                ("farmacia", 1),
                ("estado", 1)
            ], name="farmacia_estado_index")
            print("   ✅ Índice compuesto creado")
        except Exception as e:
            print(f"   ⚠ Error creando índice compuesto (puede que ya exista): {e}")
        
        # 3. Índice en código para búsquedas exactas rápidas
        print("📝 Creando índice en código...")
        try:
            await inventarios_collection.create_index([("codigo", 1)], name="codigo_index")
            print("   ✅ Índice en código creado")
        except Exception as e:
            print(f"   ⚠ Error creando índice en código (puede que ya exista): {e}")
        
        # 4. Índice en nombre para búsquedas por nombre
        print("📝 Creando índice en nombre...")
        try:
            await inventarios_collection.create_index([("nombre", 1)], name="nombre_index")
            print("   ✅ Índice en nombre creado")
        except Exception as e:
            print(f"   ⚠ Error creando índice en nombre (puede que ya exista): {e}")
        
        # 5. Índice compuesto para búsquedas por farmacia + nombre (MUY COMÚN en punto de venta)
        print("📝 Creando índice compuesto (farmacia + nombre)...")
        try:
            await inventarios_collection.create_index([
                ("farmacia", 1),
                ("nombre", 1)
            ], name="farmacia_nombre_index")
            print("   ✅ Índice compuesto (farmacia + nombre) creado")
        except Exception as e:
            print(f"   ⚠ Error creando índice compuesto (farmacia + nombre) (puede que ya exista): {e}")
        
        # 6. Índice compuesto para búsquedas por farmacia + código (MUY COMÚN)
        print("📝 Creando índice compuesto (farmacia + código)...")
        try:
            await inventarios_collection.create_index([
                ("farmacia", 1),
                ("codigo", 1)
            ], name="farmacia_codigo_index")
            print("   ✅ Índice compuesto (farmacia + código) creado")
        except Exception as e:
            print(f"   ⚠ Error creando índice compuesto (farmacia + código) (puede que ya exista): {e}")
        
        # 7. Índice compuesto para estado + nombre (para filtrar inactivos rápidamente)
        print("📝 Creando índice compuesto (estado + nombre)...")
        try:
            await inventarios_collection.create_index([
                ("estado", 1),
                ("nombre", 1)
            ], name="estado_nombre_index")
            print("   ✅ Índice compuesto (estado + nombre) creado")
        except Exception as e:
            print(f"   ⚠ Error creando índice compuesto (estado + nombre) (puede que ya exista): {e}")
        
        # Listar todos los índices creados
        print("\n📋 Índices existentes en la colección INVENTARIOS:")
        indexes = await inventarios_collection.list_indexes().to_list(length=None)
        for index in indexes:
            print(f"   - {index.get('name', 'sin nombre')}: {index.get('key', {})}")
        
        print("\n✅ Proceso completado!")
        print("💡 Los índices mejorarán significativamente el rendimiento de las búsquedas")
        
    except Exception as e:
        print(f"❌ Error creando índices: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(create_indexes())


