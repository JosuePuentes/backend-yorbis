"""
Script para crear un usuario en la base de datos ferreteria_los_puentes
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
import certifi

# Configuración
MONGO_URI = "mongodb+srv://rapifarma:w1Y7HoezUiMtfrWt@cluster0.9nirn5t.mongodb.net/?appName=Cluster0"
DATABASE_NAME = "ferreteria_los_puentes"

# Hasheo de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def crear_usuario():
    """Crea un usuario en la base de datos"""
    client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client[DATABASE_NAME]
    usuarios_collection = db["USUARIOS"]
    
    correo = "ferreterialospuentes"
    contraseña = "admin123"
    
    try:
        print("=" * 60)
        print("🔐 Creando usuario en la base de datos")
        print("=" * 60)
        print(f"📧 Correo: {correo}")
        print(f"🔑 Contraseña: {contraseña}")
        print("=" * 60)
        
        # Verificar si ya existe el usuario
        usuario_existente = await usuarios_collection.find_one({"correo": correo})
        if usuario_existente:
            print(f"\n⚠ El usuario '{correo}' ya existe en la base de datos")
            print("   ¿Deseas actualizar la contraseña? (S/N)")
            # Por ahora, actualizaremos la contraseña automáticamente
            contraseña_segura = pwd_context.hash(contraseña)
            await usuarios_collection.update_one(
                {"correo": correo},
                {"$set": {"contraseña": contraseña_segura}}
            )
            print(f"✅ Contraseña actualizada para el usuario '{correo}'")
            return
        
        # Hashear contraseña
        contraseña_segura = pwd_context.hash(contraseña)
        
        # Crear usuario
        nuevo_usuario = {
            "correo": correo,
            "contraseña": contraseña_segura,
            "permisos": [
                "ver_inicio",
                "ver_about",
                "agregar_cuadre",
                "verificar_cuadres",
                "ver_cuadres_dia",
                "verificar_gastos"
            ]
        }
        
        # Insertar usuario
        resultado = await usuarios_collection.insert_one(nuevo_usuario)
        
        print(f"\n✅ Usuario creado exitosamente!")
        print(f"   ID: {resultado.inserted_id}")
        print(f"   Correo: {correo}")
        print(f"   Contraseña: {contraseña}")
        print("=" * 60)
        print("\n📋 Credenciales de acceso:")
        print(f"   Correo: {correo}")
        print(f"   Contraseña: {contraseña}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error al crear usuario: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(crear_usuario())


