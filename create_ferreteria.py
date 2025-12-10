"""
Script para crear una ferretería en la colección FARMACIAS
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

MONGO_URI = "mongodb+srv://rapifarma:w1Y7HoezUiMtfrWt@cluster0.9nirn5t.mongodb.net/?appName=Cluster0"
DATABASE_NAME = "ferreteria_los_puentes"

async def crear_ferreteria():
    """Crea una ferretería en la colección FARMACIAS"""
    client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client[DATABASE_NAME]
    farmacias_collection = db["FARMACIAS"]
    
    try:
        print("=" * 60)
        print("🏪 Creando ferretería")
        print("=" * 60)
        
        # Verificar si ya existe alguna ferretería
        farmacias_existentes = await farmacias_collection.find({}).to_list(length=None)
        
        # Obtener el siguiente ID disponible
        if farmacias_existentes:
            # Buscar el ID más alto
            ids_numericos = []
            for farm in farmacias_existentes:
                if 'id' in farm:
                    try:
                        ids_numericos.append(int(farm['id']))
                    except:
                        pass
            
            if ids_numericos:
                siguiente_id = str(max(ids_numericos) + 1).zfill(2)
            else:
                siguiente_id = "01"
        else:
            siguiente_id = "01"
        
        # Crear la ferretería
        ferreteria = {
            "id": siguiente_id,
            "nombre": "Ferretería Los Puentes"
        }
        
        # Verificar si ya existe una con ese nombre
        existente = await farmacias_collection.find_one({"nombre": "Ferretería Los Puentes"})
        if existente:
            print(f"⚠ Ya existe una ferretería con ese nombre")
            print(f"   ID: {existente.get('id')}")
            print(f"   Nombre: {existente.get('nombre')}")
            
            # Actualizar el usuario para que tenga esta ferretería
            usuarios_collection = db["USUARIOS"]
            await usuarios_collection.update_one(
                {"correo": "ferreterialospuentes@gmail.com"},
                {"$set": {"farmacias": {existente.get('id'): "Ferretería Los Puentes"}}}
            )
            print(f"✅ Usuario actualizado con la ferretería")
            return
        
        # Insertar la ferretería
        resultado = await farmacias_collection.insert_one(ferreteria)
        print(f"✅ Ferretería creada exitosamente!")
        print(f"   ID: {siguiente_id}")
        print(f"   Nombre: Ferretería Los Puentes")
        print(f"   MongoDB ID: {resultado.inserted_id}")
        
        # Actualizar el usuario para que tenga esta ferretería
        usuarios_collection = db["USUARIOS"]
        await usuarios_collection.update_one(
            {"correo": "ferreterialospuentes@gmail.com"},
            {"$set": {"farmacias": {siguiente_id: "Ferretería Los Puentes"}}}
        )
        print(f"\n✅ Usuario actualizado con la ferretería")
        
        print("\n" + "=" * 60)
        print("📋 Resumen:")
        print(f"   Ferretería ID: {siguiente_id}")
        print(f"   Nombre: Ferretería Los Puentes")
        print(f"   Usuario: ferreterialospuentes@gmail.com")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(crear_ferreteria())


