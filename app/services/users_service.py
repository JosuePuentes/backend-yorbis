from app.core.auth import verificar_contraseña
from app.db.mongo import get_collection
from app.core.jwt import crear_token_jwt

async def autenticar_usuario(correo: str, contraseña: str):
    try:
        # Limpiar el correo (quitar espacios)
        correo = correo.strip().lower()
        
        users = get_collection("USUARIOS")
        usuario = await users.find_one({"correo": correo})
        
        print(f"[AUTH] Buscando usuario: {correo}")
        print(f"[AUTH] Usuario encontrado: {usuario is not None}")
        
        if not usuario:
            print(f"[AUTH] Usuario no encontrado: {correo}")
            return None
        
        if "contraseña" not in usuario:
            print(f"[AUTH] Usuario no tiene contraseña almacenada")
            return None
        
        # Verificar contraseña
        print(f"[AUTH] Verificando contraseña...")
        contraseña_valida = verificar_contraseña(contraseña, usuario["contraseña"])
        print(f"[AUTH] Contraseña válida: {contraseña_valida}")
        
        if not contraseña_valida:
            print(f"[AUTH] Contraseña incorrecta para usuario: {correo}")
            return None
        
        print(f"[AUTH] Autenticación exitosa para: {correo}")
        return usuario
    except Exception as e:
        print(f"[AUTH] Error en autenticar_usuario: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

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
