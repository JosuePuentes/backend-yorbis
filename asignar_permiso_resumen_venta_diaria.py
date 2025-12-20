"""
Script para asignar el permiso 'resumen_venta_diaria' a un usuario
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import certifi

# Cargar variables de entorno
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME") or "ferreteria_los_puentes"

async def asignar_permiso():
    """
    Asigna el permiso 'resumen_venta_diaria' al usuario ferreterialospuentes@gmail.com
    """
    try:
        if not MONGO_URI:
            print("=" * 80)
            print("ERROR: MONGO_URI no esta configurada")
            print("=" * 80)
            print("\nPara usar este script, necesitas:")
            print("1. Crear un archivo .env en la raiz del proyecto con:")
            print("   MONGO_URI=mongodb+srv://usuario:password@cluster.mongodb.net/")
            print("   DATABASE_NAME=ferreteria_los_puentes")
            print("\n2. O configurar las variables de entorno del sistema")
            print("=" * 80)
            return
        
        # Conectar a MongoDB
        client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
        db = client[DATABASE_NAME]
        usuarios_collection = db["usuarios"]
        
        correo_usuario = "ferreterialospuentes@gmail.com"
        permiso = "resumen_venta_diaria"
        
        print("=" * 80)
        print(f"Asignando permiso '{permiso}' al usuario: {correo_usuario}")
        print("=" * 80)
        
        # Buscar el usuario
        usuario = await usuarios_collection.find_one({"correo": correo_usuario})
        
        if not usuario:
            print(f"\nERROR: Usuario con correo '{correo_usuario}' no encontrado")
            print("\nUsuarios disponibles:")
            usuarios = await usuarios_collection.find({}).to_list(length=10)
            for u in usuarios:
                print(f"   - {u.get('correo', 'N/A')}")
            return
        
        print(f"\nUsuario encontrado:")
        print(f"   Correo: {usuario.get('correo', 'N/A')}")
        print(f"   Permisos actuales: {len(usuario.get('permisos', []))} permisos")
        
        # Verificar si ya tiene el permiso
        permisos_actuales = usuario.get("permisos", [])
        if permiso in permisos_actuales:
            print(f"\nEl usuario ya tiene el permiso '{permiso}' asignado")
            print("No es necesario agregarlo nuevamente")
            return
        
        # Agregar el permiso usando $addToSet (evita duplicados)
        resultado = await usuarios_collection.update_one(
            {"correo": correo_usuario},
            {"$addToSet": {"permisos": permiso}}
        )
        
        if resultado.modified_count > 0:
            print(f"\nPermiso '{permiso}' asignado exitosamente")
            
            # Verificar que se agregó correctamente
            usuario_actualizado = await usuarios_collection.find_one({"correo": correo_usuario})
            permisos_finales = usuario_actualizado.get("permisos", [])
            
            if permiso in permisos_finales:
                print(f"Verificacion: El permiso '{permiso}' esta ahora en la lista de permisos")
                print(f"Total de permisos: {len(permisos_finales)}")
            else:
                print("ADVERTENCIA: El permiso no se encontro despues de la actualizacion")
        else:
            print(f"\nNo se pudo asignar el permiso (modified_count = 0)")
            print("Puede que el permiso ya exista o haya un error")
        
        print("\n" + "=" * 80)
        print("Proceso completado")
        print("=" * 80)
        
        # Cerrar conexión
        client.close()
        
    except Exception as e:
        print(f"Error asignando permiso: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(asignar_permiso())

