"""
Script para asegurar que el usuario esté correctamente configurado para login
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
import certifi

MONGO_URI = "mongodb+srv://rapifarma:w1Y7HoezUiMtfrWt@cluster0.9nirn5t.mongodb.net/?appName=Cluster0"
DATABASE_NAME = "ferreteria_los_puentes"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def fix_user():
    """Asegura que el usuario esté correctamente configurado"""
    client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client[DATABASE_NAME]
    usuarios_collection = db["USUARIOS"]
    
    correo = "ferreterialospuentes@gmail.com"
    contraseña = "admin"
    
    try:
        print("=" * 60)
        print("🔧 Corrigiendo usuario para login")
        print("=" * 60)
        
        # Buscar usuario (probando diferentes variaciones)
        usuario = await usuarios_collection.find_one({"correo": correo})
        
        if not usuario:
            # Buscar con diferentes variaciones
            usuario = await usuarios_collection.find_one({"correo": correo.lower()})
        if not usuario:
            usuario = await usuarios_collection.find_one({"correo": correo.upper()})
        if not usuario:
            # Buscar cualquier usuario que contenga el correo
            all_users = await usuarios_collection.find({}).to_list(length=None)
            for u in all_users:
                if u.get("correo", "").lower() == correo.lower():
                    usuario = u
                    break
        
        if not usuario:
            print(f"❌ Usuario no encontrado. Creando nuevo usuario...")
            nuevo_usuario = {
                "correo": correo.lower().strip(),
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
            print(f"✅ Usuario encontrado: {usuario.get('correo')}")
            
            # Normalizar el correo a minúsculas
            correo_normalizado = correo.lower().strip()
            if usuario.get("correo") != correo_normalizado:
                print(f"   Corrigiendo correo: {usuario.get('correo')} -> {correo_normalizado}")
                await usuarios_collection.update_one(
                    {"_id": usuario["_id"]},
                    {"$set": {"correo": correo_normalizado}}
                )
                usuario["correo"] = correo_normalizado
        
        # Asegurar que la contraseña esté correctamente hasheada
        print(f"\n🔐 Verificando contraseña...")
        
        # Crear un nuevo hash para asegurar que funcione
        nuevo_hash = pwd_context.hash(contraseña)
        
        # Verificar que el hash funciona
        if not pwd_context.verify(contraseña, nuevo_hash):
            print("❌ Error: El nuevo hash no funciona (esto no debería pasar)")
        else:
            print("✅ Nuevo hash creado y verificado")
        
        # Actualizar la contraseña en la base de datos
        await usuarios_collection.update_one(
            {"_id": usuario["_id"]},
            {"$set": {"contraseña": nuevo_hash}}
        )
        print("✅ Contraseña actualizada en la base de datos")
        
        # Verificación final
        print(f"\n🔍 Verificación final...")
        usuario_final = await usuarios_collection.find_one({"_id": usuario["_id"]})
        
        # Probar login
        correo_test = usuario_final["correo"].lower().strip()
        contraseña_test = contraseña.strip()
        hash_test = usuario_final["contraseña"]
        
        login_exitoso = pwd_context.verify(contraseña_test, hash_test)
        
        print(f"   Correo en BD: {correo_test}")
        print(f"   Contraseña válida: {login_exitoso}")
        
        if login_exitoso:
            print("\n✅ Usuario configurado correctamente. Login debería funcionar.")
        else:
            print("\n❌ Aún hay problemas. Revisa los logs.")
        
        print("\n" + "=" * 60)
        print("📋 Credenciales finales:")
        print(f"   Correo: {correo_test}")
        print(f"   Contraseña: {contraseña}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(fix_user())

