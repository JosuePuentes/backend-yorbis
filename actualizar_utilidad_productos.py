"""
Script para actualizar todos los productos del inventario con utilidad del 40%
Calcula precio_venta y utilidad para productos que no los tengan
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import certifi

# Cargar variables de entorno
load_dotenv()

# Obtener variables de entorno
MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME") or "ferreteria_los_puentes"

# Si no está configurada, usar la URI por defecto
if not MONGO_URI:
    MONGO_URI = "mongodb+srv://rapifarma:w1Y7HoezUiMtfrWt@cluster0.9nirn5t.mongodb.net/?appName=Cluster0"
    print("⚠️  Usando URI por defecto (no se encontró MONGO_URI en variables de entorno)")

async def actualizar_utilidad_productos():
    """Actualiza todos los productos del inventario con utilidad del 40%"""
    print("🔄 Actualizando utilidad de productos al 40%...")
    
    client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client[DATABASE_NAME or "ferreteria_los_puentes"]
    inventarios_collection = db["INVENTARIOS"]
    
    try:
        # Obtener todos los productos
        productos = await inventarios_collection.find({}).to_list(length=None)
        total_productos = len(productos)
        
        print(f"📦 Encontrados {total_productos} productos")
        
        productos_actualizados = 0
        productos_sin_costo = 0
        productos_ya_actualizados = 0
        
        for producto in productos:
            costo = float(producto.get("costo", 0))
            precio_venta_actual = float(producto.get("precio_venta", 0))
            utilidad_actual = producto.get("utilidad")
            
            # Solo actualizar si tiene costo
            if costo > 0:
                # Calcular precio_venta con 40% de utilidad si no existe o es 0
                if not precio_venta_actual or precio_venta_actual == 0:
                    precio_venta_nuevo = costo / 0.60
                    utilidad_nueva = precio_venta_nuevo - costo
                    
                    await inventarios_collection.update_one(
                        {"_id": producto["_id"]},
                        {
                            "$set": {
                                "precio_venta": round(precio_venta_nuevo, 2),
                                "utilidad": round(utilidad_nueva, 2),
                                "porcentaje_utilidad": 40.0
                            }
                        }
                    )
                    productos_actualizados += 1
                    print(f"  ✅ {producto.get('nombre', 'Sin nombre')}: Costo ${costo} → Precio ${round(precio_venta_nuevo, 2)} (Utilidad: ${round(utilidad_nueva, 2)})")
                elif not utilidad_actual:
                    # Si tiene precio_venta pero no utilidad, calcularla
                    utilidad_nueva = precio_venta_actual - costo
                    porcentaje = (utilidad_nueva / costo) * 100 if costo > 0 else 0
                    
                    await inventarios_collection.update_one(
                        {"_id": producto["_id"]},
                        {
                            "$set": {
                                "utilidad": round(utilidad_nueva, 2),
                                "porcentaje_utilidad": round(porcentaje, 2)
                            }
                        }
                    )
                    productos_actualizados += 1
                    print(f"  ✅ {producto.get('nombre', 'Sin nombre')}: Utilidad calculada ${round(utilidad_nueva, 2)} ({round(porcentaje, 2)}%)")
                else:
                    productos_ya_actualizados += 1
            else:
                productos_sin_costo += 1
        
        print(f"\n{'='*60}")
        print(f"📊 RESUMEN:")
        print(f"{'='*60}")
        print(f"  Total productos: {total_productos}")
        print(f"  ✅ Productos actualizados: {productos_actualizados}")
        print(f"  ✓ Productos ya actualizados: {productos_ya_actualizados}")
        print(f"  ⚠ Productos sin costo: {productos_sin_costo}")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ Error actualizando productos: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(actualizar_utilidad_productos())

