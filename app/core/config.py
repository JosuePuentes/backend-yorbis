import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME") or "ferreteria_los_puentes"

# JWT config
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM") or "HS256"

# Validar variables críticas
if not SECRET_KEY:
    raise ValueError("SECRET_KEY no está configurada. Por favor configura la variable de entorno SECRET_KEY")
if not MONGO_URI:
    raise ValueError("MONGO_URI no está configurada. Por favor configura la variable de entorno MONGO_URI")