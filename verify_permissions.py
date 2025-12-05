"""
Script para verificar los permisos actuales del usuario
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

MONGO_URI = "mongodb+srv://rapifarma:w1Y7HoezUiMtfrWt@cluster0.9nirn5t.mongodb.net/?appName=Cluster0"
DATABASE_NAME = "ferreteria_los_puentes"

async def verify_permissions():
    """Verifica los permisos actuales del usuario"""
    client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client[DATABASE_NAME]
    usuarios_collection = db["USUARIOS"]
    
    correo = "ferreterialospuentes@gmail.com"
    
    try:
        print("=" * 60)
        print("🔍 Verificando permisos del usuario")
        print("=" * 60)
        
        # Buscar usuario
        usuario = await usuarios_collection.find_one({"correo": correo})
        
        if not usuario:
            print(f"❌ Usuario '{correo}' no encontrado")
            return
        
        print(f"✅ Usuario encontrado: {usuario.get('correo')}")
        print(f"   ID: {usuario.get('_id')}")
        
        permisos = usuario.get("permisos", [])
        print(f"\n📋 Permisos actuales ({len(permisos)}):")
        
        if permisos:
            for i, permiso in enumerate(permisos, 1):
                print(f"   {i}. {permiso}")
        else:
            print("   ⚠ No tiene permisos asignados")
        
        print("\n" + "=" * 60)
        
        # Si tiene menos de 80 permisos, actualizar
        if len(permisos) < 80:
            print("\n⚠ El usuario tiene menos permisos de los esperados")
            print("   Ejecutando actualización...")
            
            from grant_all_permissions import TODOS_LOS_PERMISOS
            await usuarios_collection.update_one(
                {"correo": correo},
                {"$set": {"permisos": TODOS_LOS_PERMISOS}}
            )
            
            # Verificar nuevamente
            usuario_actualizado = await usuarios_collection.find_one({"correo": correo})
            permisos_actualizados = usuario_actualizado.get("permisos", [])
            
            print(f"\n✅ Permisos actualizados: {len(permisos_actualizados)} permisos")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(verify_permissions())

