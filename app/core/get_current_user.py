from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.db.mongo import get_collection
from app.core.config import SECRET_KEY, ALGORITHM

# Configuración para obtener el token del header Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        correo: str = payload.get("sub")
        if correo is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    usuarios = get_collection("USUARIOS")
    usuario = await usuarios.find_one({"correo": correo})
    if usuario is None:
        raise credentials_exception
    usuario["_id"] = str(usuario["_id"])
    return usuario
