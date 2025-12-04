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
    try:
        usuario = await autenticar_usuario(correo, contraseña)
        if not usuario:
            return None
        
        from app.core.config import SECRET_KEY
        if not SECRET_KEY:
            print("ERROR: SECRET_KEY no está configurada")
            return None
        
        token = crear_token_jwt({"sub": usuario["correo"]})
        print(f"token:{token}")
        if return_user:
            return usuario, token
        return token
    except Exception as e:
        print(f"Error en login_y_token: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
