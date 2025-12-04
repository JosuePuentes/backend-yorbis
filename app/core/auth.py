from passlib.context import CryptContext
import bcrypt

# Configuración para encriptar y verificar contraseñas
# Usar bcrypt directamente para evitar problemas con passlib
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verificar_contraseña(plain_password, hashed_password):
    """
    Verifica una contraseña contra un hash usando bcrypt directamente.
    """
    try:
        # Asegurar que la contraseña sea string
        if not isinstance(plain_password, str):
            plain_password = str(plain_password)
        
        # Asegurar que el hash sea string
        if not isinstance(hashed_password, str):
            hashed_password = str(hashed_password)
        
        # Verificar usando passlib (que usa bcrypt internamente)
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError as e:
        # Si hay un error de bcrypt, intentar con bcrypt directamente
        if "password cannot be longer than 72 bytes" in str(e):
            try:
                # Usar bcrypt directamente como fallback
                if isinstance(plain_password, str):
                    plain_password = plain_password.encode('utf-8')
                if isinstance(hashed_password, str):
                    hashed_password = hashed_password.encode('utf-8')
                return bcrypt.checkpw(plain_password, hashed_password)
            except Exception:
                return False
        print(f"Error verificando contraseña: {e}")
        return False
    except Exception as e:
        print(f"Error verificando contraseña: {e}")
        return False

def hashear_contraseña(password):
    """
    Hashea una contraseña usando bcrypt.
    """
    try:
        # Asegurar que la contraseña sea string
        if not isinstance(password, str):
            password = str(password)
        
        return pwd_context.hash(password)
    except Exception as e:
        print(f"Error hasheando contraseña: {e}")
        # Fallback a bcrypt directo
        if isinstance(password, str):
            password = password.encode('utf-8')
        return bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')
