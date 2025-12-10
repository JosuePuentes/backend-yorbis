"""
Script para probar el login y verificar qué está fallando
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
import certifi

MONGO_URI = "mongodb+srv://rapifarma:w1Y7HoezUiMtfrWt@cluster0.9nirn5t.mongodb.net/?appName=Cluster0"
DATABASE_NAME = "ferreteria_los_puentes"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def test_login():
    """Prueba el proceso de login completo"""
    client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client[DATABASE_NAME]
    usuarios_collection = db["USUARIOS"]
    
    correo = "ferreterialospuentes@gmail.com"
    contraseña = "admin123"
    
    try:
        print("=" * 60)
        print("🔐 Probando proceso de login")
        print("=" * 60)
        
        # 1. Buscar usuario
        print(f"\n1️⃣ Buscando usuario: {correo}")
        usuario = await usuarios_collection.find_one({"correo": correo})
        
        if not usuario:
            print("❌ Usuario NO encontrado")
            return
        else:
            print(f"✅ Usuario encontrado")
            print(f"   ID: {usuario.get('_id')}")
            print(f"   Correo: {usuario.get('correo')}")
            print(f"   Tiene contraseña: {'contraseña' in usuario}")
        
        # 2. Verificar contraseña
        if "contraseña" not in usuario:
            print("\n❌ Usuario no tiene contraseña almacenada")
            return
        
        print(f"\n2️⃣ Verificando contraseña...")
        contraseña_hash = usuario["contraseña"]
        print(f"   Hash almacenado: {contraseña_hash[:20]}...")
        
        # Intentar verificar
        try:
            es_valida = pwd_context.verify(contraseña, contraseña_hash)
            if es_valida:
                print("✅ Contraseña VÁLIDA")
            else:
                print("❌ Contraseña INVÁLIDA")
                print("\n🔄 Actualizando contraseña...")
                nuevo_hash = pwd_context.hash(contraseña)
                await usuarios_collection.update_one(
                    {"correo": correo},
                    {"$set": {"contraseña": nuevo_hash}}
                )
                print("✅ Contraseña actualizada")
        except Exception as e:
            print(f"❌ Error al verificar contraseña: {e}")
            print("\n🔄 Re-creando hash de contraseña...")
            nuevo_hash = pwd_context.hash(contraseña)
            await usuarios_collection.update_one(
                {"correo": correo},
                {"$set": {"contraseña": nuevo_hash}}
            )
            print("✅ Hash de contraseña actualizado")
        
        # 3. Verificar nuevamente
        print(f"\n3️⃣ Verificación final...")
        usuario_actualizado = await usuarios_collection.find_one({"correo": correo})
        es_valida_final = pwd_context.verify(contraseña, usuario_actualizado["contraseña"])
        
        if es_valida_final:
            print("✅ Login debería funcionar correctamente ahora")
        else:
            print("❌ Aún hay problemas con la contraseña")
        
        print("\n" + "=" * 60)
        print("📋 Credenciales finales:")
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
    asyncio.run(test_login())


