import asyncio
from passlib.context import CryptContext
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
import certifi
# Conexión a MongoDB
from app.core.config import MONGO_URI, DATABASE_NAME
client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
db = client[DATABASE_NAME or "ferreteria_los_puentes"]
print("Conexión a MongoDB establecida.", client)
# Obtener una colección
def get_collection(nombre: str) -> AsyncIOMotorCollection:
    return db[nombre]

# Hasheo de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Crear un usuario básico
async def crear_usuario_basico(correo: str, contraseña: str) -> dict:
    usuarios_collection = get_collection("USUARIOS")
    # Verificar si ya existe un usuario con ese correo
    usuario_existente = await usuarios_collection.find_one({"correo": correo})
    if usuario_existente:
        raise ValueError("Ya existe un usuario con ese correo.")

    # Hashear contraseña
    contraseña_segura = pwd_context.hash(contraseña)

    # Insertar usuario
    nuevo_usuario = {
        "correo": correo,
        "contraseña": contraseña_segura
    }

    resultado = await usuarios_collection.insert_one(nuevo_usuario)

    return {
        "id": str(resultado.inserted_id),
        "correo": correo
    }

# Crear un usuario con farmacias
async def crear_usuario_con_farmacias(correo: str, contraseña: str, farmacias: dict) -> dict:
    usuarios_collection = get_collection("USUARIOS")
    usuario_existente = await usuarios_collection.find_one({"correo": correo})
    if usuario_existente:
        raise ValueError("Ya existe un usuario con ese correo.")

    contraseña_segura = pwd_context.hash(contraseña)

    nuevo_usuario = {
        "correo": correo,
        "contraseña": contraseña_segura,
        "farmacias": farmacias,  # Debe ser un dict, por ejemplo: {"01": "santa elena", "02": "rapifarma"}
        "permisos": []  # Nuevo campo: lista de permisos
    }

    resultado = await usuarios_collection.insert_one(nuevo_usuario)

    return {
        "id": str(resultado.inserted_id),
        "correo": correo,
        "farmacias": farmacias,
        "permisos": [
            "ver_inicio",
            "ver_about",
            "agregar_cuadre",
            "verificar_cuadres",
            "ver_cuadres_dia",
            "verificar_gastos"
        ]
    }

# Función de prueba
async def main():
    try:
        farmacias = {
    "01": "Santa Elena",
    "02": "Sur America",
    "03": "Rapifarma",
    "04": "San Carlos",
    "05": "Las Alicias",
    "06": "San Martin",
    "07": "Milagro Norte"
  }
        nuevo = await crear_usuario_con_farmacias("carlaverapino25@gmail.com", "27552019", farmacias)
        print("Usuario creado:", nuevo)
        print("Permisos:", nuevo["permisos"])
    except ValueError as e:
        print("Error:", str(e))

# Ejecutar como script
if __name__ == "__main__":
    asyncio.run(main())
