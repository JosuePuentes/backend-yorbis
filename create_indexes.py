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
    print("ADVERTENCIA: Usando URI por defecto (no se encontro MONGO_URI en variables de entorno)")

async def create_indexes():
    """Crea índices optimizados para búsquedas de productos"""
    print("Creando indices para optimizar busquedas de productos...")
    
    client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client[DATABASE_NAME or "ferreteria_los_puentes"]
    inventarios_collection = db["INVENTARIOS"]
    
    try:
        # 1. Indice de texto para busqueda rapida en multiples campos
        # Este indice permite busquedas de texto eficientes en codigo, nombre, descripcion y marca
        print("Creando indice de texto...")
        try:
            await inventarios_collection.create_index([
                ("codigo", "text"),
                ("nombre", "text"),
                ("descripcion", "text"),
                ("marca", "text")
            ], name="text_search_index", default_language="es")
            print("   OK: Indice de texto creado")
        except Exception as e:
            print(f"   ADVERTENCIA: Error creando indice de texto (puede que ya exista): {e}")
        
        # 2. Indice compuesto para filtros comunes (farmacia + estado)
        print("Creando indice compuesto (farmacia + estado)...")
        try:
            await inventarios_collection.create_index([
                ("farmacia", 1),
                ("estado", 1)
            ], name="farmacia_estado_index")
            print("   OK: Indice compuesto creado")
        except Exception as e:
            print(f"   ADVERTENCIA: Error creando indice compuesto (puede que ya exista): {e}")
        
        # 3. Indice en codigo para busquedas exactas rapidas
        print("Creando indice en codigo...")
        try:
            await inventarios_collection.create_index([("codigo", 1)], name="codigo_index")
            print("   OK: Indice en codigo creado")
        except Exception as e:
            print(f"   ADVERTENCIA: Error creando indice en codigo (puede que ya exista): {e}")
        
        # 4. Indice en nombre para busquedas por nombre
        print("Creando indice en nombre...")
        try:
            await inventarios_collection.create_index([("nombre", 1)], name="nombre_index")
            print("   OK: Indice en nombre creado")
        except Exception as e:
            print(f"   ADVERTENCIA: Error creando indice en nombre (puede que ya exista): {e}")
        
        # 5. Indice compuesto para busquedas por farmacia + nombre (MUY COMUN en punto de venta)
        print("Creando indice compuesto (farmacia + nombre)...")
        try:
            await inventarios_collection.create_index([
                ("farmacia", 1),
                ("nombre", 1)
            ], name="farmacia_nombre_index")
            print("   OK: Indice compuesto (farmacia + nombre) creado")
        except Exception as e:
            print(f"   ADVERTENCIA: Error creando indice compuesto (farmacia + nombre) (puede que ya exista): {e}")
        
        # 6. Indice compuesto para busquedas por farmacia + codigo (MUY COMUN)
        print("Creando indice compuesto (farmacia + codigo)...")
        try:
            await inventarios_collection.create_index([
                ("farmacia", 1),
                ("codigo", 1)
            ], name="farmacia_codigo_index")
            print("   OK: Indice compuesto (farmacia + codigo) creado")
        except Exception as e:
            print(f"   ADVERTENCIA: Error creando indice compuesto (farmacia + codigo) (puede que ya exista): {e}")
        
        # 7. Indice compuesto para estado + nombre (para filtrar inactivos rapidamente)
        print("Creando indice compuesto (estado + nombre)...")
        try:
            await inventarios_collection.create_index([
                ("estado", 1),
                ("nombre", 1)
            ], name="estado_nombre_index")
            print("   OK: Indice compuesto (estado + nombre) creado")
        except Exception as e:
            print(f"   ADVERTENCIA: Error creando indice compuesto (estado + nombre) (puede que ya exista): {e}")
        
        # 8. Indice compuesto CRITICO para verinventarios: farmacia + estado + nombre
        # Este indice optimiza la consulta mas comun: filtrar por farmacia, estado activo y ordenar por nombre
        print("Creando indice compuesto CRITICO (farmacia + estado + nombre)...")
        try:
            await inventarios_collection.create_index([
                ("farmacia", 1),
                ("estado", 1),
                ("nombre", 1)
            ], name="farmacia_estado_nombre_index", background=True)
            print("   OK: Indice compuesto CRITICO (farmacia + estado + nombre) creado")
        except Exception as e:
            print(f"   ADVERTENCIA: Error creando indice compuesto CRITICO (puede que ya exista): {e}")
        
        # 9. Indice compuesto para estado + nombre (sin farmacia) - para consultas generales
        print("Creando indice compuesto (estado + nombre) optimizado...")
        try:
            await inventarios_collection.create_index([
                ("estado", 1),
                ("nombre", 1)
            ], name="estado_nombre_optimizado_index", background=True)
            print("   OK: Indice compuesto (estado + nombre) optimizado creado")
        except Exception as e:
            print(f"   ADVERTENCIA: Error creando indice (puede que ya exista): {e}")
        
        # Listar todos los indices creados
        print("\nIndices existentes en la coleccion INVENTARIOS:")
        indexes = await inventarios_collection.list_indexes().to_list(length=None)
        for index in indexes:
            print(f"   - {index.get('name', 'sin nombre')}: {index.get('key', {})}")
        
        print("\nProceso completado!")
        print("Los indices mejoraran significativamente el rendimiento de las busquedas")
        
    except Exception as e:
        print(f"ERROR creando indices: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(create_indexes())


