from passlib.context import CryptContext

# Configuración para encriptar y verificar contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verificar_contraseña(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def hashear_contraseña(password):
    return pwd_context.hash(password)
