"""
Script para actualizar el correo del usuario a ferreterialospuentes@gmail.com
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

# Configuración
MONGO_URI = "mongodb+srv://rapifarma:w1Y7HoezUiMtfrWt@cluster0.9nirn5t.mongodb.net/?appName=Cluster0"
DATABASE_NAME = "ferreteria_los_puentes"

async def actualizar_correo():
    """Actualiza el correo del usuario"""
    client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client[DATABASE_NAME]
    usuarios_collection = db["USUARIOS"]
    
    correo_viejo = "ferreterialospuentes"
    correo_nuevo = "ferreterialospuentes@gmail.com"
    
    try:
        print("=" * 60)
        print("📧 Actualizando correo del usuario")
        print("=" * 60)
        print(f"Correo anterior: {correo_viejo}")
        print(f"Correo nuevo: {correo_nuevo}")
        print("=" * 60)
        
        # Buscar usuario con el correo viejo
        usuario = await usuarios_collection.find_one({"correo": correo_viejo})
        
        if not usuario:
            print(f"\n⚠ No se encontró usuario con correo '{correo_viejo}'")
            # Intentar crear uno nuevo con el correo correcto
            print("   Creando nuevo usuario con el correo correcto...")
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            
            nuevo_usuario = {
                "correo": correo_nuevo,
                "contraseña": pwd_context.hash("admin123"),
                "permisos": [
                    "ver_inicio",
                    "ver_about",
                    "agregar_cuadre",
                    "verificar_cuadres",
                    "ver_cuadres_dia",
                    "verificar_gastos"
                ]
            }
            
            resultado = await usuarios_collection.insert_one(nuevo_usuario)
            print(f"✅ Usuario creado con correo: {correo_nuevo}")
            print(f"   ID: {resultado.inserted_id}")
        else:
            # Actualizar el correo
            await usuarios_collection.update_one(
                {"correo": correo_viejo},
                {"$set": {"correo": correo_nuevo}}
            )
            print(f"\n✅ Correo actualizado exitosamente!")
            print(f"   De: {correo_viejo}")
            print(f"   A: {correo_nuevo}")
        
        print("=" * 60)
        print("\n📋 Credenciales de acceso actualizadas:")
        print(f"   Correo: {correo_nuevo}")
        print(f"   Contraseña: admin123")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(actualizar_correo())

