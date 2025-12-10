"""
Script para verificar que el usuario existe y puede hacer login
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
import certifi

MONGO_URI = "mongodb+srv://rapifarma:w1Y7HoezUiMtfrWt@cluster0.9nirn5t.mongodb.net/?appName=Cluster0"
DATABASE_NAME = "ferreteria_los_puentes"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def verificar_usuario():
    """Verifica que el usuario existe y la contraseña funciona"""
    client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client[DATABASE_NAME]
    usuarios_collection = db["USUARIOS"]
    
    correo = "ferreterialospuentes@gmail.com"
    contraseña = "admin123"
    
    try:
        print("=" * 60)
        print("🔍 Verificando usuario y login")
        print("=" * 60)
        
        # Buscar usuario
        usuario = await usuarios_collection.find_one({"correo": correo})
        
        if not usuario:
            print(f"❌ Usuario '{correo}' NO encontrado en la base de datos")
            print("\n📝 Creando usuario...")
            
            nuevo_usuario = {
                "correo": correo,
                "contraseña": pwd_context.hash(contraseña),
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
            print(f"✅ Usuario creado con ID: {resultado.inserted_id}")
            usuario = nuevo_usuario
        else:
            print(f"✅ Usuario encontrado: {correo}")
            print(f"   ID: {usuario.get('_id')}")
        
        # Verificar contraseña
        if "contraseña" in usuario:
            contraseña_valida = pwd_context.verify(contraseña, usuario["contraseña"])
            if contraseña_valida:
                print(f"✅ Contraseña válida")
            else:
                print(f"❌ Contraseña NO válida")
                print("   Actualizando contraseña...")
                await usuarios_collection.update_one(
                    {"correo": correo},
                    {"$set": {"contraseña": pwd_context.hash(contraseña)}}
                )
                print("   ✅ Contraseña actualizada")
        else:
            print("⚠ Usuario no tiene contraseña, creando una...")
            await usuarios_collection.update_one(
                {"correo": correo},
                {"$set": {"contraseña": pwd_context.hash(contraseña)}}
            )
            print("   ✅ Contraseña creada")
        
        print("\n" + "=" * 60)
        print("📋 Credenciales verificadas:")
        print(f"   Correo: {correo}")
        print(f"   Contraseña: {contraseña}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(verificar_usuario())


