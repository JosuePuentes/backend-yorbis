from app.core.auth import verificar_contraseña
from app.db.mongo import get_collection
from app.core.jwt import crear_token_jwt

async def autenticar_usuario(correo: str, contraseña: str):
    users = get_collection("USUARIOS")
    usuario = await users.find_one({"correo": correo})
    print(f"usuario: {usuario}")
    if not usuario:
        return None
    if not verificar_contraseña(contraseña, usuario["contraseña"]):
        return None
    return usuario

# Ejemplo de login_y_token
async def login_y_token(correo, contraseña, return_user=False):
    usuario = await autenticar_usuario(correo, contraseña)
    if not usuario:
        return None
    token = crear_token_jwt({"sub": usuario["correo"]})
    print(f"token:{token}")
    if return_user:
        return usuario, token
    return token
