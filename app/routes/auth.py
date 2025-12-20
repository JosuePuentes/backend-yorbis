from fastapi import APIRouter, HTTPException, Body, Query, Depends
from app.schemas.auth import LoginInput, Cuadre
from app.services.users_service import login_y_token
from app.db.mongo import get_collection  # tu helper para acceder a la colección
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime, timedelta
import pytz
from pydantic import BaseModel
from typing import List, Optional
from fastapi import Depends
from app.core.get_current_user import get_current_user
import os
import boto3
from botocore.config import Config
from fastapi import Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import re

load_dotenv()

# Configuración de Cloudflare R2 desde variables de entorno
R2_BUCKET = os.getenv("VITE_R2_BUCKET")
R2_ACCOUNT_ID = os.getenv("VITE_R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.getenv("VITE_R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("VITE_R2_SECRET_ACCESS_KEY")
R2_ENDPOINT_URL = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

s3_client = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT_URL,
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    region_name="auto",
    config=Config(signature_version="s3v4")
)

router = APIRouter()

class Gasto(BaseModel):
    monto: float
    titulo: str
    descripcion: str
    localidad: str
    fecha: str  # Fecha de gasto (ej: "2025-06-23")
    tasa: Optional[float] = None
    divisa: Optional[str] = None
    fechaRegistro: Optional[datetime] = None  # Fecha de registro real (datetime)
    estado: str = "wait"
    imagenGasto: Optional[str] = None
    imagenesGasto: Optional[List[str]] = None

class CuentaPorPagar(BaseModel):
    fechaEmision: str
    fechaRecepcion: Optional[str] = None
    fechaVencimiento: Optional[str] = None  # Nuevo campo
    fechaRegistro: Optional[str] = None     # Nuevo campo
    diasCredito: int
    numeroFactura: str
    numeroControl: str
    proveedor: str
    descripcion: str
    monto: float
    retencion: Optional[float] = 0  # Nuevo campo retención
    divisa: str
    tasa: float
    estatus: str = "activa"
    usuarioCorreo: str
    farmacia: str
    imagenesCuentaPorPagar: List[str] = []  # <-- Añadir este campo

class Inventario(BaseModel):
    farmacia: str
    costo: float
    usuarioCorreo: str
    fecha: Optional[str] = None  # Ahora es opcional
    estado: str = "activo"  # Nuevo campo con valor por defecto

@router.get("/")
async def root():
    return {"message": "API funcionando"}

@router.get("/usuarios")
async def obtener_usuarios(usuario_actual: dict = Depends(get_current_user)):
    """
    Endpoint para obtener todos los usuarios.
    Requiere autenticación.
    """
    try:
        collection = get_collection("USUARIOS")
        usuarios = await collection.find({}).to_list(length=None)
        
        # Convertir _id a string y limpiar datos sensibles
        usuarios_limpios = []
        for usuario in usuarios:
            usuario["_id"] = str(usuario["_id"])
            # Remover la contraseña por seguridad
            if "contraseña" in usuario:
                del usuario["contraseña"]
            usuarios_limpios.append(usuario)
        
        return usuarios_limpios
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ENDPOINTS PARA MODIFICAR USUARIOS (Frontend usa /modificar-usuarios)
# ============================================================================

@router.get("/modificar-usuarios")
async def obtener_usuarios_modificar(usuario_actual: dict = Depends(get_current_user)):
    """
    Obtiene todos los usuarios para el módulo de modificación.
    Requiere autenticación.
    """
    try:
        collection = get_collection("USUARIOS")
        usuarios = await collection.find({}).to_list(length=None)
        
        # Convertir _id a string y limpiar datos sensibles
        usuarios_limpios = []
        for usuario in usuarios:
            usuario["_id"] = str(usuario["_id"])
            usuario["id"] = usuario["_id"]  # Agregar campo id para compatibilidad
            # Remover la contraseña por seguridad
            if "contraseña" in usuario:
                del usuario["contraseña"]
            usuarios_limpios.append(usuario)
        
        print(f"✅ [USUARIOS] Retornando {len(usuarios_limpios)} usuarios")
        return usuarios_limpios
    except Exception as e:
        print(f"❌ [USUARIOS] Error obteniendo usuarios: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/modificar-usuarios/me")
async def obtener_usuario_actual_modificar(usuario_actual: dict = Depends(get_current_user)):
    """
    Obtiene el usuario actual para el módulo de modificación.
    Requiere autenticación.
    """
    try:
        # Remover la contraseña por seguridad
        usuario_info = usuario_actual.copy()
        usuario_info["id"] = str(usuario_info.get("_id", ""))
        if "contraseña" in usuario_info:
            del usuario_info["contraseña"]
        
        return usuario_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/modificar-usuarios/{usuario_id}")
async def obtener_usuario_por_id(usuario_id: str, usuario_actual: dict = Depends(get_current_user)):
    """
    Obtiene un usuario específico por ID.
    Requiere autenticación.
    """
    try:
        collection = get_collection("USUARIOS")
        
        try:
            usuario_object_id = ObjectId(usuario_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="ID de usuario inválido")
        
        usuario = await collection.find_one({"_id": usuario_object_id})
        
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        usuario["_id"] = str(usuario["_id"])
        usuario["id"] = usuario["_id"]
        
        # Remover la contraseña por seguridad
        if "contraseña" in usuario:
            del usuario["contraseña"]
        
        return usuario
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/modificar-usuarios")
async def crear_usuario_nuevo(
    usuario_data: dict = Body(...),
    usuario_actual: dict = Depends(get_current_user)
):
    """
    Crea un nuevo usuario.
    Requiere autenticación.
    """
    try:
        from passlib.context import CryptContext
        
        collection = get_collection("USUARIOS")
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # Validar campos requeridos
        correo = usuario_data.get("correo", "").strip().lower()
        if not correo:
            raise HTTPException(status_code=400, detail="El campo 'correo' es requerido")
        
        contraseña = usuario_data.get("contraseña", "").strip()
        if not contraseña:
            raise HTTPException(status_code=400, detail="El campo 'contraseña' es requerido")
        
        # Verificar que el correo no exista
        usuario_existente = await collection.find_one({"correo": correo})
        if usuario_existente:
            raise HTTPException(status_code=400, detail=f"Ya existe un usuario con el correo '{correo}'")
        
        # Hashear contraseña
        contraseña_hash = pwd_context.hash(contraseña)
        
        # Crear nuevo usuario
        nuevo_usuario = {
            "correo": correo,
            "contraseña": contraseña_hash,
            "permisos": usuario_data.get("permisos", []),
            "farmacias": usuario_data.get("farmacias", {}),
            "fechaCreacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "usuarioCreacion": usuario_actual.get("correo", "unknown")
        }
        
        resultado = await collection.insert_one(nuevo_usuario)
        usuario_id = str(resultado.inserted_id)
        
        # Obtener usuario creado
        usuario_creado = await collection.find_one({"_id": resultado.inserted_id})
        usuario_creado["_id"] = usuario_id
        usuario_creado["id"] = usuario_id
        
        # Remover contraseña
        if "contraseña" in usuario_creado:
            del usuario_creado["contraseña"]
        
        print(f"✅ [USUARIOS] Usuario creado: {correo} - ID: {usuario_id}")
        
        return {
            "message": "Usuario creado exitosamente",
            "id": usuario_id,
            "usuario": usuario_creado
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [USUARIOS] Error creando usuario: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/modificar-usuarios/{usuario_id}")
async def actualizar_usuario(
    usuario_id: str,
    usuario_data: dict = Body(...),
    usuario_actual: dict = Depends(get_current_user)
):
    """
    Actualiza un usuario existente.
    Requiere autenticación.
    """
    try:
        from passlib.context import CryptContext
        
        collection = get_collection("USUARIOS")
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        try:
            usuario_object_id = ObjectId(usuario_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="ID de usuario inválido")
        
        # Verificar que el usuario existe
        usuario_existente = await collection.find_one({"_id": usuario_object_id})
        if not usuario_existente:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # Preparar datos de actualización
        update_data = {}
        
        # Actualizar correo si se proporciona
        if "correo" in usuario_data:
            nuevo_correo = usuario_data.get("correo", "").strip().lower()
            if nuevo_correo and nuevo_correo != usuario_existente.get("correo", ""):
                # Verificar que el nuevo correo no exista
                otro_usuario = await collection.find_one({"correo": nuevo_correo})
                if otro_usuario and str(otro_usuario["_id"]) != usuario_id:
                    raise HTTPException(status_code=400, detail=f"Ya existe un usuario con el correo '{nuevo_correo}'")
                update_data["correo"] = nuevo_correo
        
        # Actualizar contraseña si se proporciona
        if "contraseña" in usuario_data and usuario_data["contraseña"]:
            contraseña_hash = pwd_context.hash(usuario_data["contraseña"])
            update_data["contraseña"] = contraseña_hash
        
        # Actualizar permisos si se proporcionan
        if "permisos" in usuario_data:
            update_data["permisos"] = usuario_data["permisos"]
        
        # Actualizar farmacias si se proporcionan
        if "farmacias" in usuario_data:
            update_data["farmacias"] = usuario_data["farmacias"]
        
        # Agregar fecha de actualización
        update_data["fechaActualizacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        update_data["usuarioActualizacion"] = usuario_actual.get("correo", "unknown")
        
        # Actualizar usuario
        await collection.update_one(
            {"_id": usuario_object_id},
            {"$set": update_data}
        )
        
        # Obtener usuario actualizado
        usuario_actualizado = await collection.find_one({"_id": usuario_object_id})
        usuario_actualizado["_id"] = str(usuario_actualizado["_id"])
        usuario_actualizado["id"] = usuario_actualizado["_id"]
        
        # Remover contraseña
        if "contraseña" in usuario_actualizado:
            del usuario_actualizado["contraseña"]
        
        print(f"✅ [USUARIOS] Usuario actualizado: {usuario_id}")
        
        return {
            "message": "Usuario actualizado exitosamente",
            "usuario": usuario_actualizado
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [USUARIOS] Error actualizando usuario: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/modificar-usuarios/{usuario_id}/permisos")
async def actualizar_permisos_usuario(
    usuario_id: str,
    permisos_data: dict = Body(...),
    usuario_actual: dict = Depends(get_current_user)
):
    """
    Actualiza solo los permisos de un usuario.
    Requiere autenticación.
    """
    try:
        collection = get_collection("USUARIOS")
        
        try:
            usuario_object_id = ObjectId(usuario_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="ID de usuario inválido")
        
        # Verificar que el usuario existe
        usuario_existente = await collection.find_one({"_id": usuario_object_id})
        if not usuario_existente:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # Actualizar permisos
        permisos = permisos_data.get("permisos", [])
        
        await collection.update_one(
            {"_id": usuario_object_id},
            {
                "$set": {
                    "permisos": permisos,
                    "fechaActualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "usuarioActualizacion": usuario_actual.get("correo", "unknown")
                }
            }
        )
        
        # Obtener usuario actualizado
        usuario_actualizado = await collection.find_one({"_id": usuario_object_id})
        usuario_actualizado["_id"] = str(usuario_actualizado["_id"])
        usuario_actualizado["id"] = usuario_actualizado["_id"]
        
        # Remover contraseña
        if "contraseña" in usuario_actualizado:
            del usuario_actualizado["contraseña"]
        
        print(f"✅ [USUARIOS] Permisos actualizados para usuario: {usuario_id}")
        
        return {
            "message": "Permisos actualizados exitosamente",
            "usuario": usuario_actualizado
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [USUARIOS] Error actualizando permisos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/modificar-usuarios/{usuario_id}")
async def eliminar_usuario(
    usuario_id: str,
    usuario_actual: dict = Depends(get_current_user)
):
    """
    Elimina un usuario (marca como inactivo, no elimina físicamente).
    Requiere autenticación.
    """
    try:
        collection = get_collection("USUARIOS")
        
        try:
            usuario_object_id = ObjectId(usuario_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="ID de usuario inválido")
        
        # Verificar que el usuario existe
        usuario_existente = await collection.find_one({"_id": usuario_object_id})
        if not usuario_existente:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # Marcar como inactivo en lugar de eliminar físicamente
        await collection.update_one(
            {"_id": usuario_object_id},
            {
                "$set": {
                    "estado": "inactivo",
                    "fechaEliminacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "usuarioEliminacion": usuario_actual.get("correo", "unknown")
                }
            }
        )
        
        print(f"✅ [USUARIOS] Usuario marcado como inactivo: {usuario_id}")
        
        return {
            "message": "Usuario eliminado exitosamente",
            "id": usuario_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [USUARIOS] Error eliminando usuario: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/me")
async def get_current_user_info(usuario_actual: dict = Depends(get_current_user)):
    """
    Endpoint para obtener la información del usuario actual autenticado.
    """
    try:
        # Remover la contraseña por seguridad
        usuario_info = usuario_actual.copy()
        if "contraseña" in usuario_info:
            del usuario_info["contraseña"]
        
        return usuario_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/usuarios/me")
async def get_my_user_info(usuario_actual: dict = Depends(get_current_user)):
    """
    Endpoint alternativo para obtener la información del usuario actual.
    """
    try:
        # Remover la contraseña por seguridad
        usuario_info = usuario_actual.copy()
        if "contraseña" in usuario_info:
            del usuario_info["contraseña"]
        
        return usuario_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/auth/login")
async def login_user(data: LoginInput):
    try:
        print(f"[LOGIN] Intento de login - Correo: {data.correo}")
        
        # Limpiar datos de entrada
        correo = data.correo.strip().lower() if data.correo else ""
        contraseña = data.contraseña.strip() if data.contraseña else ""
        
        if not correo or not contraseña:
            print(f"[LOGIN] Correo o contraseña vacíos")
            raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
        
        result = await login_y_token(correo, contraseña, return_user=True)
        if result is None:
            print(f"[LOGIN] login_y_token retornó None")
            raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
        
        usuario, token = result
        if not token or not usuario:
            print(f"[LOGIN] Token o usuario faltante")
            raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
        
        # El usuario debe ser un dict con el campo 'farmacias'
        usuario["_id"] = str(usuario["_id"])
        
        # Asegurar que los permisos estén incluidos
        if "permisos" not in usuario:
            usuario["permisos"] = []
        
        # Remover la contraseña de la respuesta
        usuario_respuesta = usuario.copy()
        if "contraseña" in usuario_respuesta:
            del usuario_respuesta["contraseña"]
        
        print(f"[LOGIN] Login exitoso para: {correo}")
        print(f"[LOGIN] Permisos del usuario: {len(usuario_respuesta.get('permisos', []))}")
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "usuario": usuario_respuesta
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[LOGIN] Error en login: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@router.get("/cuadres")
async def obtener_cuadres(
    farmacia: Optional[str] = Query(None),
    fechaInicio: Optional[str] = Query(None),
    fechaFin: Optional[str] = Query(None)
):
    db = get_collection("CUADRES").database
    cuadres = []
    # Si no se especifica farmacia, buscar en todas las colecciones CUADRES-*
    if not farmacia:
        colecciones = await db.list_collection_names()
        for nombre in colecciones:
            if nombre.startswith("CUADRES-"):
                collection = db[nombre]
                filtro = {}
                if fechaInicio and fechaFin:
                    filtro["dia"] = {"$gte": fechaInicio, "$lte": fechaFin}
                docs = await collection.find(filtro).to_list(length=None)
                for r in docs:
                    r["_id"] = str(r["_id"])
                    r["codigoFarmacia"] = nombre.replace("CUADRES-", "")
                cuadres.extend(docs)
    else:
        nombre = f"CUADRES-{farmacia}"
        collection = db[nombre]
        filtro = {}
        if fechaInicio and fechaFin:
            filtro["dia"] = {"$gte": fechaInicio, "$lte": fechaFin}
        docs = await collection.find(filtro).to_list(length=None)
        for r in docs:
            r["_id"] = str(r["_id"])
            r["codigoFarmacia"] = farmacia
        cuadres.extend(docs)
    return cuadres

@router.get("/cuadres/all")
async def obtener_todos_los_cuadres():
    db = get_collection("CUADRES").database  # Obtener la instancia de la base de datos
    colecciones = await db.list_collection_names()
    cuadres = []
    for nombre in colecciones:
        if nombre.startswith("CUADRES-"):
            collection = db[nombre]
            docs = await collection.find({}).to_list(length=None)
            for r in docs:
                r["_id"] = str(r["_id"])
                # Extraer el código de farmacia del nombre de la colección
                r["codigoFarmacia"] = nombre.replace("CUADRES-", "")
            cuadres.extend(docs)
    return cuadres

@router.get("/cuadres/{farmacia_id}")
async def obtener_cuadres_farmacia(farmacia_id: str):
    try:
        collection = get_collection(f"CUADRES-{farmacia_id}")
        resultados = await collection.find({}).to_list(1000)
        for r in resultados:
            r["_id"] = str(r["_id"])
        return resultados
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agg/cuadre/{farmacia}")
async def agregar_cuadre(farmacia: str, cuadre: Cuadre):
    try:
        collection = get_collection(f"CUADRES-{farmacia}")
        cuadre_dict = cuadre.dict()
        # Forzar estado a 'wait' siempre
        cuadre_dict["estado"] = "wait"
        diferencia = cuadre_dict.get("diferenciaUsd", 0)
        cuadre_dict["sobranteUsd"] = diferencia if diferencia > 0 else 0
        cuadre_dict["faltanteUsd"] = abs(diferencia) if diferencia < 0 else 0
        cuadre_dict["cajeroId"] = cuadre.cajeroId
        # Agregar fecha y hora actual de Venezuela
        venezuela_tz = pytz.timezone("America/Caracas")
        now_ve = datetime.now(venezuela_tz)
        cuadre_dict["fecha"] = now_ve.strftime("%Y-%m-%d")
        cuadre_dict["hora"] = now_ve.strftime("%H:%M:%S")
        # Validar que valesUsd esté presente (si no, poner 0)
        if "valesUsd" not in cuadre_dict or cuadre_dict["valesUsd"] is None:
            cuadre_dict["valesUsd"] = 0
        # Eliminar campo imagenCuadre si existe (deprecated)
        if "imagenCuadre" in cuadre_dict:
            cuadre_dict.pop("imagenCuadre")
        # Limpieza robusta de imagenesCuadre antes de validar
        imagenes = cuadre_dict.get("imagenesCuadre", None)
        if isinstance(imagenes, list):
            imagenes = [x for x in imagenes if isinstance(x, str) and x.strip()]
            cuadre_dict["imagenesCuadre"] = imagenes
        if not isinstance(imagenes, list) or not (1 <= len(imagenes) <= 4):
            raise HTTPException(status_code=400, detail="El campo 'imagenesCuadre' debe ser un array de 1 a 3 strings no vacíos.")
        # ...existing code...
        result = collection.insert_one(cuadre_dict)
        return {"message": "Cuadre guardado", "result": str(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cuadres")
async def agregar_cuadre(cuadre: Cuadre):
    try:
        collection = get_collection("CUADRES")
        cuadre_dict = cuadre.dict()
        # Si viene 'dia' del frontend, guárdalo como 'fechaCajero', pero NO como 'dia' del cuadre
        if hasattr(cuadre, 'dia') and cuadre.dia:
            cuadre_dict["fechaCajero"] = cuadre.dia
        else:
            cuadre_dict["fechaCajero"] = None
        # El campo 'dia' real del cuadre es la fecha actual de Venezuela
        venezuela_tz = pytz.timezone("America/Caracas")
        now_ve = datetime.now(venezuela_tz)
        cuadre_dict["dia"] = now_ve.strftime("%Y-%m-%d")
        # Hora
        if hasattr(cuadre, 'hora') and cuadre.hora:
            cuadre_dict["hora"] = cuadre.hora
        else:
            cuadre_dict["hora"] = now_ve.strftime("%H:%M:%S")
        cuadre_dict["estado"] = "wait"
        # Eliminar el campo 'fecha' si existe para evitar duplicidad
        if "fecha" in cuadre_dict:
            cuadre_dict.pop("fecha")
        # Eliminar campo imagenCuadre si existe (deprecated)
        if "imagenCuadre" in cuadre_dict:
            cuadre_dict.pop("imagenCuadre")
        # Limpieza robusta de imagenesCuadre antes de validar
        imagenes = cuadre_dict.get("imagenesCuadre", None)
        if isinstance(imagenes, list):
            imagenes = [x for x in imagenes if isinstance(x, str) and x.strip()]
            cuadre_dict["imagenesCuadre"] = imagenes
        if not isinstance(imagenes, list) or not (1 <= len(imagenes) <= 4):
            raise HTTPException(status_code=400, detail="El campo 'imagenesCuadre' debe ser un array de 1 a 4 strings no vacíos.")
        result = await collection.insert_one(cuadre_dict)
        return {"message": "Cuadre agregado exitosamente", "id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/farmacias")
async def get_farmacias():
    collection = get_collection("FARMACIAS")
    # Obtener todos los documentos y construir un dict {id: nombre}
    docs = await collection.find({}, {"_id": 0}).to_list(length=None)
    # Si los docs son tipo [{id: '01', nombre: 'Santa Elena'}, ...], conviértelos a dict
    farmacias = {}
    for doc in docs:
        # Si el doc tiene 'id' y 'nombre', usa eso
        if 'id' in doc and 'nombre' in doc:
            farmacias[doc['id']] = doc['nombre']
        # Si el doc tiene otras claves, las agrega
        else:
            for k, v in doc.items():
                if k != '_id':
                    farmacias[k] = v
    return {"farmacias": farmacias}

@router.post("/cuadres/{farmacia_id}/{dia}/{cajaNumero}/estado")
async def actualizar_estado_cuadre(farmacia_id: str, dia: str, cajaNumero: int, estado: str = Body(..., embed=True)):
    try:
        collection = get_collection(f"CUADRES-{farmacia_id}")
        # Buscar por número (int) para cajaNumero
        result = await collection.update_one(
            {"dia": dia, "cajaNumero": int(cajaNumero)},
            {"$set": {"estado": estado}}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Cuadre no encontrado o sin cambios")
        return {"message": f"Estado actualizado a {estado}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/cuadres/{farmacia_id}/{cuadre_id}/estado")
async def actualizar_estado_cuadre_por_id(farmacia_id: str, cuadre_id: str, data: dict = Body(...)):
    try:
        estado = data.get("estado")
        costo = data.get("costo", None)
        update_fields = {"estado": estado}
        if costo is not None:
            update_fields["costo"] = float(costo)
        collection = get_collection(f"CUADRES-{farmacia_id}")
        result = await collection.update_one(
            {"_id": ObjectId(cuadre_id)},
            {"$set": update_fields}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Cuadre no encontrado o sin cambios")
        return {"message": f"Estado actualizado a {estado}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/cuadres/{farmacia_id}/{dia}/{cajaNumero}/cajero")
async def actualizar_cajero_cuadre(farmacia_id: str, dia: str, cajaNumero: int, cajero: str = Body(..., embed=True)):
    try:
        collection = get_collection(f"CUADRES-{farmacia_id}")
        result = await collection.update_one(
            {"dia": dia, "cajaNumero": int(cajaNumero)},
            {"$set": {"cajero": cajero}}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Cuadre no encontrado o sin cambios")
        return {"message": f"Cajero actualizado a {cajero}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cajeros")
async def get_cajeros():
    collection = get_collection("CAJERO")
    docs = await collection.find({}).to_list(length=None)
    # Convertir _id a string para el frontend
    for doc in docs:
        if '_id' in doc:
            doc['_id'] = str(doc['_id'])
    return docs

@router.post("/gastos")
async def agregar_gasto(gasto: Gasto):
    try:
        collection = get_collection("GASTOS")
        gasto_dict = gasto.dict()
        # Validación robusta de imagenesGasto
        imagenes = gasto_dict.get("imagenesGasto", None)
        if imagenes is not None:
            if isinstance(imagenes, list):
                imagenes = [x for x in imagenes if isinstance(x, str) and x.strip()]
            else:
                imagenes = []
            gasto_dict["imagenesGasto"] = imagenes
            if not (1 <= len(imagenes) <= 4):
                raise HTTPException(status_code=400, detail="El campo 'imagenesGasto' debe ser un array de 1 a 3 strings no vacíos.")
        else:
            gasto_dict["imagenesGasto"] = []
        # Guardar la fecha de registro (Venezuela) y la fecha enviada por el usuario
        venezuela_tz = pytz.timezone("America/Caracas")
        gasto_dict["fechaRegistro"] = datetime.now(venezuela_tz)
        # fecha ya viene como string ("2025-06-23")
        gasto_dict["estado"] = gasto_dict.get("estado", "wait")
        result = await collection.insert_one(gasto_dict)
        return {"message": "Gasto agregado exitosamente", "id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gastos")
async def obtener_gastos(
    localidad: Optional[str] = None,
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    estado: Optional[str] = None
):
    try:
        collection = get_collection("GASTOS")
        filtro = {}
        if localidad:
            filtro["localidad"] = localidad
        if fecha_inicio and fecha_fin:
            filtro["fecha"] = {"$gte": fecha_inicio, "$lte": fecha_fin}
        if estado:
            filtro["estado"] = estado
        resultados = await collection.find(filtro).to_list(1000)
        for r in resultados:
            r["_id"] = str(r["_id"])
        return resultados
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/gastos/estado")
async def actualizar_estado_gasto(data: dict = Body(...)):
    try:
        try:
            gasto_id = ObjectId(data.get("id"))
        except InvalidId:
            raise HTTPException(status_code=400, detail="ID inválido")

        nuevo_estado = data.get("estado")

        if not nuevo_estado:
            raise HTTPException(status_code=400, detail="Faltan campos obligatorios: estado")

        collection = get_collection("GASTOS")
        result = await collection.update_one(
            {"_id": gasto_id},
            {"$set": {"estado": nuevo_estado}}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Gasto no encontrado o sin cambios")

        return {"message": f"Estado del gasto actualizado a {nuevo_estado}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gastos/total")
async def obtener_total_gastos_por_farmacia():
    try:
        collection = get_collection("GASTOS")
        pipeline = [
            {"$match": {"monto": {"$gte": 0}}},  # Exclude negative values
            {"$group": {"_id": "$localidad", "totalGastos": {"$sum": "$monto"}}}
        ]
        resultados = await collection.aggregate(pipeline).to_list(length=None)
        # Convertir el resultado a un diccionario {localidad: totalGastos}
        gastos_por_farmacia = {r["_id"]: r["totalGastos"] for r in resultados}
        return gastos_por_farmacia
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cajeros")
async def crear_cajero(cajero: dict = Body(...)):
    try:
        collection = get_collection("CAJERO")
        # Procesar comision como float
        cajero["comision"] = float(cajero.get("comision", 0))  # Default commission
        cajero["estado"] = cajero.get("estado", "activo")  # Default state
        # Limpia tipocomision: elimina strings vacíos, pero si es lista vacía, la guarda como []
        if "tipocomision" in cajero:
            if isinstance(cajero["tipocomision"], list):
                cajero["tipocomision"] = [t for t in cajero["tipocomision"] if t]
                # Si queda vacía, se guarda como [] (no se elimina el campo)
            elif not cajero["tipocomision"]:
                cajero["tipocomision"] = []
        result = await collection.insert_one(cajero)
        return {"message": "Cajero creado exitosamente", "id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/cajeros/{cajero_id}")
async def actualizar_cajero(cajero_id: str, cajero: dict = Body(...)):
    try:
        collection = get_collection("CAJERO")
        print(f"Actualizando cajero con ID: {cajero_id} con datos: {cajero}")

        # Convert _id to ObjectId
        try:
            cajero["_id"] = ObjectId(cajero["_id"])
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid _id format")

        # Limpia tipocomision: elimina strings vacíos, pero si es lista vacía, la guarda como []
        if "tipocomision" in cajero:
            if isinstance(cajero["tipocomision"], list):
                cajero["tipocomision"] = [t for t in cajero["tipocomision"] if t]
                # Si queda vacía, se guarda como [] (no se elimina el campo)
            elif not cajero["tipocomision"]:
                cajero["tipocomision"] = []

        # Map field names to match database schema
        mapped_cajero = {
            "NOMBRE": cajero.get("nombre"),
            "ID": cajero.get("id"),
            "FARMACIAS": cajero.get("FARMACIAS"),
            "comision": float(cajero.get("comision", 0)),
            "estado": cajero.get("estado"),
            "tipocomision": cajero.get("tipocomision", None),
        }
        # Agrega campos extendidos si existen
        for campo in ["turno", "especial", "extra"]:
            if campo in cajero:
                mapped_cajero[campo] = cajero[campo]
        # Elimina campos None para no sobreescribir con null
        mapped_cajero = {k: v for k, v in mapped_cajero.items() if v is not None}

        # Perform the update
        result = await collection.update_one(
            {"_id": ObjectId(cajero_id)},
            {"$set": mapped_cajero}
        )
        print(f"Resultado de la actualización: {result.raw_result}")
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Cajero no encontrado o sin cambios")
        return {"message": "Cajero actualizado exitosamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/comisiones")
async def obtener_comisiones_por_turno(
    startDate: str = Query(...),
    endDate: str = Query(...)
): 
    try:
        db = get_collection("CUADRES").database
        colecciones = await db.list_collection_names()
        colecciones_farmacias = [nombre for nombre in colecciones if nombre.startswith("CUADRES-")]

        comisiones_planas = []

        for nombre_coleccion in colecciones_farmacias:
            collection = db[nombre_coleccion]
            pipeline = [
                {
                    "$match": {
                        "dia": {"$gte": startDate, "$lte": endDate},
                        "estado": "verified"
                    }
                },
                {
                    "$lookup": {
                        "from": "CAJERO",
                        "localField": "cajeroId",
                        "foreignField": "ID",
                        "as": "cajeroInfo",
                    }
                },
                {"$unwind": "$cajeroInfo"},
                {
                    "$project": {
                        "turno": 1,
                        "dia": 1,
                        "totalVentas": {"$divide": ["$totalCajaSistemaBs", {"$ifNull": ["$tasa", 1]}]},
                        "nombre": "$cajeroInfo.NOMBRE",
                        "cajeroId": "$cajeroId",
                        "farmacias": "$cajeroInfo.FARMACIAS",
                        "comisionPorcentaje": "$cajeroInfo.comision",
                        "tipocomision": "$cajeroInfo.tipocomision",
                        "sobrante": {"$ifNull": ["$sobranteUsd", 0]},
                        "faltante": {"$ifNull": ["$faltanteUsd", 0]}
                    }
                }
            ]
            resultados = await collection.aggregate(pipeline).to_list(length=None)
            # Agrupar por (turno, dia) para sumar ventas y obtener cajeros únicos
            agrupados = {}
            for r in resultados:
                if r.get("tipocomision") and ("Turno" in r["tipocomision"] if isinstance(r["tipocomision"], list) else r["tipocomision"] == "Turno"):
                    key = (r["turno"], r["dia"])
                    if key not in agrupados:
                        agrupados[key] = {"totalVentas": 0, "cajeros": []}
                    agrupados[key]["totalVentas"] += r["totalVentas"]
                    agrupados[key]["cajeros"].append({
                        "NOMBRE": r.get("nombre"),
                        "cajeroId": r.get("cajeroId"),
                        "farmacias": r.get("farmacias"),
                        "comisionPorcentaje": r.get("comisionPorcentaje"),
                        "turno": r.get("turno"),
                        "dia": r.get("dia"),
                        "sobrante": r.get("sobrante", 0),
                        "faltante": r.get("faltante", 0)
                    })
            # Para cada grupo, calcular la venta total del turno y aplicar el porcentaje de comisión INDIVIDUAL de cada cajero
            for (turno, dia), data in agrupados.items():
                total_ventas = data["totalVentas"]
                for cajero in data["cajeros"]:
                    comision_porcentaje = float(cajero.get("comisionPorcentaje") or 0)
                    comision = (total_ventas * comision_porcentaje) / 100
                    comisiones_planas.append({
                        "NOMBRE": cajero["NOMBRE"],
                        "cajeroId": cajero["cajeroId"],
                        "farmacias": cajero["farmacias"],
                        "comisionPorcentaje": cajero["comisionPorcentaje"],
                        "turno": cajero["turno"],
                        "dia": cajero["dia"],
                        "totalVentas": total_ventas,
                        "comision": comision,
                        "sobrante": cajero.get("sobrante", 0),
                        "faltante": cajero.get("faltante", 0)
                    })
        return comisiones_planas
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/comisiones/especial")
async def obtener_total_ventas_especial(
    startDate: str = Query(...),
    endDate: str = Query(...)
):
    try:
        db = get_collection("CUADRES").database
        colecciones = await db.list_collection_names()
        colecciones_farmacias = [nombre for nombre in colecciones if nombre.startswith("CUADRES-")]

        # Obtener todos los cajeros y mapear por farmacia
        cajeros_collection = get_collection("CAJERO")
        cajeros = await cajeros_collection.find({}).to_list(length=None)
        # Mapeo: {codigo_farmacia: [cajero, ...]}
        farmacias_cajeros = {}
        for cajero in cajeros:
            farmacias = cajero.get("FARMACIAS", {})
            if isinstance(farmacias, dict):
                for cod in farmacias.keys():
                    if cod not in farmacias_cajeros:
                        farmacias_cajeros[cod] = []
                    farmacias_cajeros[cod].append(cajero)
            elif isinstance(farmacias, list):
                for cod in farmacias:
                    if cod not in farmacias_cajeros:
                        farmacias_cajeros[cod] = []
                    farmacias_cajeros[cod].append(cajero)

        cajeros_especiales = []
        total_ventas_especial = 0

        for nombre_coleccion in colecciones_farmacias:
            codigo_farmacia = nombre_coleccion.replace("CUADRES-", "")
            collection = db[nombre_coleccion]
            pipeline = [
                {
                    "$match": {
                        "dia": {"$gte": startDate, "$lte": endDate},
                        "estado": "verified"
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "totalVentas": {"$sum": {"$divide": ["$totalCajaSistemaBs", {"$ifNull": ["$tasa", 0]}]}},
                    }
                }
            ]
            resultados = await collection.aggregate(pipeline).to_list(length=None)
            total_farmacia = resultados[0]["totalVentas"] if resultados else 0
            total_ventas_especial += total_farmacia

            # Buscar TODOS los cajeros especiales para esta farmacia
            cajeros_farmacia = farmacias_cajeros.get(codigo_farmacia, [])
            cajeros_especiales_farmacia = [
                c for c in cajeros_farmacia if "Especial" in (c.get("tipocomision") or [])
            ]
            for cajero_especial in cajeros_especiales_farmacia:
                cajeros_especiales.append({
                    "cajero": cajero_especial.get("NOMBRE"),
                    "cajeroId": cajero_especial.get("ID"),
                    "farmacias": cajero_especial.get("FARMACIAS", {}),
                    "totalVentas": total_farmacia,
                    "comisionPorcentaje": cajero_especial.get("comision", 0)
                })

        return {
            "totalVentasEspecial": total_ventas_especial,
            "cajeros": cajeros_especiales
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cuentas-por-pagar")
async def agregar_cuenta_por_pagar(cuenta: CuentaPorPagar,usuario: dict = Depends(get_current_user)):
    try:
        collection = get_collection("CUENTAS_POR_PAGAR")
        cuenta_dict = cuenta.dict()
        # Convertir fechas a datetime si es necesario
        cuenta_dict["fechaEmision"] = datetime.strptime(cuenta.fechaEmision, "%Y-%m-%d")
        if cuenta.fechaRecepcion:
            cuenta_dict["fechaRecepcion"] = datetime.strptime(cuenta.fechaRecepcion, "%Y-%m-%d")
        if cuenta.fechaVencimiento:
            cuenta_dict["fechaVencimiento"] = datetime.strptime(cuenta.fechaVencimiento, "%Y-%m-%d")
        # Fecha de registro: si viene, úsala, si no, pon la actual
        if cuenta.fechaRegistro:
            cuenta_dict["fechaRegistro"] = datetime.strptime(cuenta.fechaRegistro, "%Y-%m-%d")
        else:
            venezuela_tz = pytz.timezone("America/Caracas")
            cuenta_dict["fechaRegistro"] = datetime.now(venezuela_tz)
        cuenta_dict["estatus"] = "wait"
        cuenta_dict["usuarioCorreo"] = usuario.get("correo", "")
        # Validación robusta de imagenesCuentaPorPagar
        imagenes = cuenta_dict.get("imagenesCuentaPorPagar", None)
        if imagenes is not None:
            if isinstance(imagenes, list):
                imagenes = [x for x in imagenes if isinstance(x, str) and x.strip()]
            else:
                imagenes = []
            if len(imagenes) > 3:
                raise HTTPException(status_code=400, detail="El campo 'imagenesCuentaPorPagar' debe tener máximo 3 imágenes.")
            cuenta_dict["imagenesCuentaPorPagar"] = imagenes
        else:
            cuenta_dict["imagenesCuentaPorPagar"] = []
        result = await collection.insert_one(cuenta_dict)
        return {"message": "Cuenta por pagar registrada exitosamente", "id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cuentas-por-pagar")
async def listar_cuentas_por_pagar(usuario: dict = Depends(get_current_user)):
    print(usuario)
    try:
        collection = get_collection("CUENTAS_POR_PAGAR")
        cuentas = await collection.find({}).to_list(length=None)
        for c in cuentas:
            c["_id"] = str(c["_id"])
            if isinstance(c["fechaEmision"], datetime):
                c["fechaEmision"] = c["fechaEmision"].strftime("%Y-%m-%d")
            if "fechaRecepcion" in c and isinstance(c["fechaRecepcion"], datetime):
                c["fechaRecepcion"] = c["fechaRecepcion"].strftime("%Y-%m-%d")
            # Normaliza monto a USD
            if c.get("divisa") == "Bs":
                try:
                    tasa = float(c.get("tasa", 1)) or 1
                    c["montoUsd"] = float(c["monto"]) / tasa
                except Exception:
                    c["montoUsd"] = 0
            else:
                c["montoUsd"] = float(c["monto"])
        return cuentas
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/cuentas-por-pagar/{id}/estatus")
async def actualizar_estatus_cuenta_por_pagar(id: str, data: dict = Body(...)):
    try:
        nuevo_estatus = data.get("estatus")
        if not nuevo_estatus:
            raise HTTPException(status_code=400, detail="Falta el campo 'estatus'")
        collection = get_collection("CUENTAS_POR_PAGAR")
        result = await collection.update_one({"_id": ObjectId(id)}, {"$set": {"estatus": nuevo_estatus}})
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Cuenta por pagar no encontrada o sin cambios")
        return {"message": f"Estatus actualizado a {nuevo_estatus}"}
    except InvalidId:
        raise HTTPException(status_code=400, detail="ID inválido")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/inventarios")
async def agregar_inventario(data: Inventario, usuario: dict = Depends(get_current_user)):
    print(f"Usuario actual: {usuario}")
    print(f"Datos del inventario: {data}")
    try:
        collection = get_collection("INVENTARIOS")
        inventario_dict = data.dict()
        inventario_dict["usuarioCorreo"] = usuario.get("usuarioCorreo", data.usuarioCorreo)
        inventario_dict["fecha"] = datetime.now().strftime("%Y-%m-%d")
        inventario_dict["estado"] = "activo"  # Siempre activo al crear
        result = await collection.insert_one(inventario_dict)
        return {"message": "Inventario registrado exitosamente", "id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/inventarios")
async def listar_inventarios(
    farmacia: Optional[str] = Query(None, description="Filtrar por farmacia"),
    limit: Optional[int] = Query(500, description="Límite de resultados"),
    usuario: dict = Depends(get_current_user)
):
    """
    Lista inventarios (OPTIMIZADO).
    Puede filtrar por farmacia y limitar resultados.
    """
    try:
        collection = get_collection("INVENTARIOS")
        
        # IMPORTANTE: Filtrar solo productos activos (igual que /inventarios/items)
        filtro = {"estado": {"$ne": "inactivo"}}
        
        # Filtrar por farmacia si se especifica
        if farmacia and farmacia.strip():
            filtro["farmacia"] = farmacia.strip()
        
        # OPTIMIZACIÓN: Usar proyección y límite
        limit = min(limit or 500, 1000)  # Máximo 1000
        
        print(f"🔍 [INVENTARIOS] Listando inventarios - farmacia: {farmacia}, limit: {limit}")
        
        inventarios = await collection.find(
            filtro,
            projection={
                "_id": 1, "codigo": 1, "nombre": 1, "descripcion": 1,
                "precio_venta": 1, "precio": 1, "marca": 1, "cantidad": 1,
                "lotes": 1, "farmacia": 1, "costo": 1, "estado": 1, 
                "productoId": 1, "categoria": 1, "proveedor": 1,
                "utilidad": 1, "porcentaje_utilidad": 1
            }
        ).sort("nombre", 1).limit(limit).to_list(length=limit)
        
        for inv in inventarios:
            inv["_id"] = str(inv["_id"])
            if "productoId" in inv and isinstance(inv["productoId"], ObjectId):
                inv["productoId"] = str(inv["productoId"])
            
            # Calcular utilidad si no existe
            costo = float(inv.get("costo", 0))
            precio_venta = float(inv.get("precio_venta", 0))
            
            if costo > 0:
                if not precio_venta or precio_venta == 0:
                    precio_venta = costo / 0.60
                    inv["precio_venta"] = round(precio_venta, 2)
                
                if "utilidad" not in inv or not inv.get("utilidad"):
                    utilidad = precio_venta - costo
                    inv["utilidad"] = round(utilidad, 2)
                    inv["porcentaje_utilidad"] = 40.0
                elif "porcentaje_utilidad" not in inv:
                    inv["porcentaje_utilidad"] = 40.0
        
        return inventarios
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/inventarios/{id}/estado")
async def actualizar_estado_inventario(id: str, data: dict = Body(...), usuario: dict = Depends(get_current_user)):
    try:
        nuevo_estado = data.get("estado")
        if not nuevo_estado:
            raise HTTPException(status_code=400, detail="Falta el campo 'estado'")
        collection = get_collection("INVENTARIOS")
        result = await collection.update_one({"_id": ObjectId(id)}, {"$set": {"estado": nuevo_estado}})
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Inventario no encontrado o sin cambios")
        return {"message": f"Estado actualizado a {nuevo_estado}"}
    except InvalidId:
        raise HTTPException(status_code=400, detail="ID inválido")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# IMPORTANTE: Ruta específica sin ID debe ir ANTES de la ruta con {id}
@router.get("/inventarios/items")
async def obtener_items_inventario_sin_id(
    farmacia: Optional[str] = Query(None, description="Filtrar por farmacia"),
    limit: Optional[int] = Query(50, description="Límite de resultados (máximo 100, por defecto 50)"),
    skip: Optional[int] = Query(0, description="Número de resultados a saltar (para paginación)"),
    usuario: dict = Depends(get_current_user)
):
    """
    Obtiene items de inventario sin especificar ID de farmacia (ULTRA OPTIMIZADO CON PAGINACIÓN).
    Ruta específica para cuando el frontend llama /inventarios/items (después de normalización).
    
    OPTIMIZACIONES APLICADAS:
    - Proyección mínima (solo campos esenciales)
    - Solo productos activos
    - Paginación (limit y skip)
    - Límite inicial reducido a 50 para carga rápida
    - Usa índice en estado + nombre para ordenamiento rápido
    - Procesamiento mínimo
    
    Parámetros:
    - farmacia: ID de la farmacia (opcional)
    - limit: Límite de resultados (máximo 100, por defecto 50)
    - skip: Número de resultados a saltar (para paginación, por defecto 0)
    """
    try:
        collection = get_collection("INVENTARIOS")
        
        # OPTIMIZACIÓN: Proyección mínima (solo campos esenciales)
        # IMPORTANTE: Incluir existencia y stock para sincronización con punto de venta
        proyeccion_minima = {
            "_id": 1, "codigo": 1, "nombre": 1, "descripcion": 1,
            "precio_venta": 1, "precio": 1, "marca": 1, 
            "cantidad": 1, "existencia": 1, "stock": 1,  # Campos de stock
            "farmacia": 1, "costo": 1, "estado": 1, 
            "utilidad": 1, "porcentaje_utilidad": 1
        }
        
        # Construir filtro
        filtro = {"estado": {"$ne": "inactivo"}}
        if farmacia and farmacia.strip():
            filtro["farmacia"] = farmacia.strip()
        
        # OPTIMIZACIÓN CRÍTICA: Límite inicial reducido para carga rápida
        # Si no se especifica limit, usar 100 para carga inicial rápida
        # El frontend puede cargar más después si es necesario
        limit_val = min(limit or 100, 500)  # Por defecto 100, máximo 500
        skip_val = max(skip or 0, 0)
        
        print(f"🔍 [INVENTARIOS] Obteniendo items (sin ID - PAGINADO) - limit: {limit_val}, skip: {skip_val}, farmacia: {farmacia}")
        
        # OPTIMIZACIÓN MÁXIMA: Proyección mínima, solo activos, paginación, límite reducido
        # Usa índice compuesto (farmacia + estado + nombre) para ordenamiento ultra rápido
        # Este índice cubre exactamente la consulta: filtro por farmacia + estado + orden por nombre
        inventarios = await collection.find(
            filtro,
            projection=proyeccion_minima
        ).sort("nombre", 1).skip(skip_val).limit(limit_val).to_list(length=limit_val)
        
        # OPTIMIZACIÓN: Procesamiento rápido y mínimo
        resultados = []
        for inv in inventarios:
            # Convertir _id a string
            inv_id = str(inv["_id"])
            
            # Calcular valores si no existen (procesamiento mínimo)
            costo = float(inv.get("costo", 0))
            precio_venta = float(inv.get("precio_venta") or inv.get("precio", 0))
            
            # Calcular precio_venta y utilidad si no están definidos
            if costo > 0 and (precio_venta == 0 or "precio_venta" not in inv):
                precio_venta = costo / 0.60  # 40% de utilidad
            
            utilidad = precio_venta - costo if precio_venta > 0 and costo > 0 else float(inv.get("utilidad", 0))
            porcentaje_utilidad = float(inv.get("porcentaje_utilidad", 40.0)) if utilidad > 0 else 0.0
            
            # Obtener valores de stock (prioridad: existencia > cantidad > stock)
            # IMPORTANTE: Usar misma lógica que punto de venta para sincronización
            existencia = float(inv.get("existencia", 0))
            cantidad_val = float(inv.get("cantidad", 0))
            stock_val = float(inv.get("stock", 0))
            
            # Usar existencia como campo principal (igual que punto de venta)
            if existencia > 0:
                stock_disponible = existencia
            elif cantidad_val > 0:
                stock_disponible = cantidad_val
            else:
                stock_disponible = stock_val if stock_val > 0 else 0
            
            # Construir resultado optimizado
            resultado = {
                "_id": inv_id,
                "id": inv_id,
                "codigo": inv.get("codigo", ""),
                "nombre": inv.get("nombre", ""),
                "descripcion": inv.get("descripcion", ""),
                "marca": inv.get("marca", ""),
                "cantidad": float(stock_disponible),      # Usar existencia como valor
                "existencia": float(stock_disponible),    # Campo principal
                "stock": float(stock_disponible),         # Compatibilidad
                "costo": round(costo, 2),
                "precio_venta": round(precio_venta, 2),
                "precio": round(precio_venta, 2),
                "utilidad": round(utilidad, 2),
                "porcentaje_utilidad": round(porcentaje_utilidad, 2),
                "farmacia": inv.get("farmacia", ""),
                "estado": inv.get("estado", "activo")
            }
            
            resultados.append(resultado)
        
        # OPTIMIZACIÓN CRÍTICA: NO contar total para carga más rápida
        # El conteo puede ser muy lento con muchos productos (puede tomar varios segundos)
        # El frontend puede calcular el total si lo necesita, o cargar más productos con paginación
        total_count = None
        # if skip_val == 0:
        #     total_count = await collection.count_documents(filtro)
        
        print(f"✅ [INVENTARIOS] Retornando {len(resultados)} items (PAGINADO - sin ID) - Carga optimizada (sin conteo)")
        
        # IMPORTANTE: Retornar array directo para compatibilidad con frontend
        # Si el frontend necesita paginación, puede usar los parámetros limit y skip
        return resultados
        
    except Exception as e:
        print(f"❌ [INVENTARIOS] Error obteniendo items: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/inventarios/{id}/items")
async def obtener_items_inventario(
    id: str,
    limit: Optional[int] = Query(50, description="Límite de resultados (máximo 100, por defecto 50)"),
    skip: Optional[int] = Query(0, description="Número de resultados a saltar (para paginación)"),
    usuario: dict = Depends(get_current_user)
):
    """
    Obtiene los items de inventario (ULTRA OPTIMIZADO CON PAGINACIÓN).
    El {id} puede ser el ID de la farmacia o el ID de un inventario específico.
    Si es un ID de farmacia, retorna todos los items de esa farmacia.
    Si es un ID de inventario, retorna ese item específico.
    
    OPTIMIZACIONES APLICADAS:
    - Proyección mínima (solo campos esenciales)
    - Paginación (limit y skip)
    - Uso eficiente de índices
    - Procesamiento rápido de resultados
    - Límite inicial reducido a 50 para carga rápida
    """
    try:
        collection = get_collection("INVENTARIOS")
        
        # OPTIMIZACIÓN: Proyección mínima (solo campos esenciales)
        # IMPORTANTE: Incluir existencia y stock para sincronización con punto de venta
        proyeccion_minima = {
            "_id": 1, "codigo": 1, "nombre": 1, "descripcion": 1,
            "precio_venta": 1, "precio": 1, "marca": 1, 
            "cantidad": 1, "existencia": 1, "stock": 1,  # Campos de stock
            "farmacia": 1, "costo": 1, "estado": 1, 
            "utilidad": 1, "porcentaje_utilidad": 1
        }
        
        # Limitar el límite a máximo 100 para velocidad
        limit_val = min(limit or 50, 100)
        skip_val = max(skip or 0, 0)
        
        # Intentar primero como ObjectId (inventario específico) - MÁS RÁPIDO
        try:
            object_id = ObjectId(id)
            inventario = await collection.find_one(
                {"_id": object_id, "estado": {"$ne": "inactivo"}},
                projection=proyeccion_minima
            )
            if inventario:
                inventarios = [inventario]
            else:
                inventarios = []
        except (InvalidId, ValueError):
            # Si no es un ObjectId válido, tratar como ID de farmacia
            # OPTIMIZACIÓN: Buscar directamente por farmacia (usa índice) con paginación
            inventarios = await collection.find(
                {"farmacia": id.strip(), "estado": {"$ne": "inactivo"}},
                projection=proyeccion_minima
            ).sort("nombre", 1).skip(skip_val).limit(limit_val).to_list(length=limit_val)
        
        # OPTIMIZACIÓN: Procesamiento rápido y mínimo
        resultados = []
        for inv in inventarios:
            # Convertir _id a string
            inv_id = str(inv["_id"])
            
            # Calcular valores si no existen (procesamiento mínimo)
            costo = float(inv.get("costo", 0))
            precio_venta = float(inv.get("precio_venta") or inv.get("precio", 0))
            
            # Calcular precio_venta y utilidad si no están definidos
            if costo > 0 and (precio_venta == 0 or "precio_venta" not in inv):
                precio_venta = costo / 0.60  # 40% de utilidad
            
            utilidad = precio_venta - costo if precio_venta > 0 and costo > 0 else float(inv.get("utilidad", 0))
            porcentaje_utilidad = float(inv.get("porcentaje_utilidad", 40.0)) if utilidad > 0 else 0.0
            
            # Obtener valores de stock (prioridad: existencia > cantidad > stock)
            # IMPORTANTE: Usar misma lógica que punto de venta para sincronización
            existencia = float(inv.get("existencia", 0))
            cantidad_val = float(inv.get("cantidad", 0))
            stock_val = float(inv.get("stock", 0))
            
            # Usar existencia como campo principal (igual que punto de venta)
            if existencia > 0:
                stock_disponible = existencia
            elif cantidad_val > 0:
                stock_disponible = cantidad_val
            else:
                stock_disponible = stock_val if stock_val > 0 else 0
            
            # Construir resultado optimizado
            resultado = {
                "_id": inv_id,
                "id": inv_id,
                "codigo": inv.get("codigo", ""),
                "nombre": inv.get("nombre", ""),
                "descripcion": inv.get("descripcion", ""),
                "marca": inv.get("marca", ""),
                "cantidad": float(stock_disponible),      # Usar existencia como valor
                "existencia": float(stock_disponible),    # Campo principal
                "stock": float(stock_disponible),         # Compatibilidad
                "costo": round(costo, 2),
                "precio_venta": round(precio_venta, 2),
                "precio": round(precio_venta, 2),
                "utilidad": round(utilidad, 2),
                "porcentaje_utilidad": round(porcentaje_utilidad, 2),
                "farmacia": inv.get("farmacia", ""),
                "estado": inv.get("estado", "activo")
            }
            
            resultados.append(resultado)
        
        # OPTIMIZACIÓN CRÍTICA: NO contar total para carga más rápida
        # El conteo puede ser muy lento con muchos productos (puede tomar varios segundos)
        # El frontend puede calcular el total si lo necesita, o cargar más productos con paginación
        total_count = None
        # try:
        #     ObjectId(id)  # Si es ObjectId, no contar
        # except (InvalidId, ValueError):
        #     if skip_val == 0:
        #         total_count = await collection.count_documents({"farmacia": id.strip(), "estado": {"$ne": "inactivo"}})
        
        print(f"✅ [INVENTARIOS] Retornando {len(resultados)} items (PAGINADO - con ID) - Carga optimizada (sin conteo)")
        
        # IMPORTANTE: Retornar array directo para compatibilidad con frontend
        return resultados
        
    except Exception as e:
        print(f"❌ [INVENTARIOS] Error obteniendo items: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/inventarios/{id}")
async def obtener_inventario(id: str, usuario: dict = Depends(get_current_user)):
    """
    Obtiene un inventario específico por su ID.
    """
    try:
        try:
            object_id = ObjectId(id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="ID de inventario inválido")
        
        collection = get_collection("INVENTARIOS")
        inventario = await collection.find_one({"_id": object_id})
        
        if not inventario:
            raise HTTPException(status_code=404, detail="Inventario no encontrado")
        
        inventario["_id"] = str(inventario["_id"])
        if "productoId" in inventario and isinstance(inventario["productoId"], ObjectId):
            inventario["productoId"] = str(inventario["productoId"])
        
        # Calcular utilidad si no existe
        costo = float(inventario.get("costo", 0))
        precio_venta = float(inventario.get("precio_venta", 0))
        
        if costo > 0:
            if not precio_venta or precio_venta == 0:
                precio_venta = costo / 0.60
                inventario["precio_venta"] = round(precio_venta, 2)
            
            if "utilidad" not in inventario or not inventario.get("utilidad"):
                utilidad = precio_venta - costo
                inventario["utilidad"] = round(utilidad, 2)
                inventario["porcentaje_utilidad"] = 40.0
            elif "porcentaje_utilidad" not in inventario:
                inventario["porcentaje_utilidad"] = 40.0
        
        return inventario
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/inventarios/{id}/items/{item_id}")
async def eliminar_item_inventario(
    id: str, 
    item_id: str, 
    usuario: dict = Depends(get_current_user)
):
    """
    Elimina un item de inventario.
    El {id} es el ID de la farmacia o inventario padre.
    El {item_id} es el ID del item a eliminar (puede tener formato especial como "id_codigo").
    """
    try:
        print(f"🗑️ [INVENTARIOS] Eliminando item: {item_id} de inventario: {id}")
        collection = get_collection("INVENTARIOS")
        
        # El item_id puede venir en formato "id_codigo" o solo "id"
        # Intentar extraer el ID real (antes del guion bajo si existe)
        item_id_real = item_id.split("_")[0] if "_" in item_id else item_id
        
        try:
            item_object_id = ObjectId(item_id_real)
        except (InvalidId, ValueError):
            # Si no es ObjectId válido, intentar buscar por código
            # El formato puede ser "id_codigo", extraer el código
            if "_" in item_id:
                codigo = "_".join(item_id.split("_")[1:])  # Todo después del primer _
                filtro = {"codigo": codigo}
                if id and id.strip():
                    filtro["farmacia"] = id.strip()
            else:
                # Intentar buscar por código directamente
                filtro = {"codigo": item_id}
                if id and id.strip():
                    filtro["farmacia"] = id.strip()
            
            resultado = await collection.delete_one(filtro)
            if resultado.deleted_count == 0:
                raise HTTPException(status_code=404, detail="Item de inventario no encontrado")
            
            print(f"✅ [INVENTARIOS] Item eliminado por código: {item_id}")
            return {"message": "Item de inventario eliminado exitosamente", "id": item_id}
        
        # Buscar y eliminar por ObjectId
        item = await collection.find_one({"_id": item_object_id})
        
        if not item:
            raise HTTPException(status_code=404, detail="Item de inventario no encontrado")
        
        # Verificar que pertenece a la farmacia/inventario correcto si se especifica
        if id and id.strip():
            farmacia_item = item.get("farmacia", "")
            if farmacia_item != id.strip():
                # Si no coincide, puede ser que el id sea el ID del inventario padre
                # En ese caso, verificar que el item_id sea el correcto
                pass
        
        resultado = await collection.delete_one({"_id": item_object_id})
        
        if resultado.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Item de inventario no encontrado")
        
        print(f"✅ [INVENTARIOS] Item eliminado: {item_id_real}")
        return {"message": "Item de inventario eliminado exitosamente", "id": item_id_real}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [INVENTARIOS] Error eliminando item: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

async def _actualizar_item_inventario_internal(
    item_id: str,
    data: dict,
    id_clean: str,
    usuario: dict
):
    """
    Función interna para actualizar un item de inventario.
    """
    collection = get_collection("INVENTARIOS")
    
    # DEBUG: Log de datos recibidos
    print(f"📝 [INVENTARIOS] Datos recibidos para actualizar item {item_id}: {data}")
    
    # El item_id puede venir en formato "id_codigo" o solo "id"
    item_id_real = item_id.split("_")[0] if "_" in item_id else item_id
    
    # Determinar el ID de farmacia correcto
    farmacia_id = None
    if id_clean:
        # Verificar si id_clean es un ObjectId (ID del inventario)
        try:
            inventario_object_id = ObjectId(id_clean)
            # Si es ObjectId, buscar el inventario para obtener su farmacia
            inventario = await collection.find_one({"_id": inventario_object_id})
            if inventario:
                farmacia_id = inventario.get("farmacia")
                print(f"🔍 [INVENTARIOS] ID de inventario detectado, farmacia encontrada: {farmacia_id}")
        except (InvalidId, ValueError):
            # Si no es ObjectId, asumir que es el ID de la farmacia directamente
            farmacia_id = id_clean
            print(f"🔍 [INVENTARIOS] ID de farmacia detectado: {farmacia_id}")
    
    try:
        item_object_id = ObjectId(item_id_real)
    except (InvalidId, ValueError):
        # Si no es ObjectId válido, intentar buscar por código
        if "_" in item_id:
            codigo = "_".join(item_id.split("_")[1:])
            filtro = {"codigo": codigo}
            if farmacia_id:
                filtro["farmacia"] = farmacia_id
        else:
            filtro = {"codigo": item_id}
            if farmacia_id:
                filtro["farmacia"] = farmacia_id
        
        print(f"🔍 [INVENTARIOS] Buscando item por código con filtro: {filtro}")
        
        # Buscar el item
        item = await collection.find_one(filtro)
        if not item:
            # Si no se encuentra con filtro de farmacia, intentar sin filtro
            if farmacia_id:
                filtro_sin_farmacia = {"codigo": item_id if not "_" in item_id else "_".join(item_id.split("_")[1:])}
                print(f"🔍 [INVENTARIOS] No encontrado con filtro de farmacia, intentando sin filtro: {filtro_sin_farmacia}")
                item = await collection.find_one(filtro_sin_farmacia)
            
            if not item:
                raise HTTPException(status_code=404, detail=f"Item de inventario no encontrado (código: {item_id}, farmacia: {farmacia_id})")
        
        item_object_id = item["_id"]
        print(f"✅ [INVENTARIOS] Item encontrado: {item_object_id}")
    
    # No permitir actualizar el _id
    if "_id" in data:
        del data["_id"]
    
    # Obtener el item actual para calcular utilidad si es necesario
    item_actual = await collection.find_one({"_id": item_object_id})
    if not item_actual:
        raise HTTPException(status_code=404, detail="Item de inventario no encontrado")
    
    costo_actual = float(item_actual.get("costo", 0)) if item_actual else 0
    precio_venta_actual = float(item_actual.get("precio_venta", 0)) if item_actual else 0
    
    print(f"📊 [INVENTARIOS] Valores actuales - Costo: {costo_actual}, Precio venta: {precio_venta_actual}")
    
    # Si se actualiza el costo, recalcular precio_venta y utilidad con 40%
    if "costo" in data:
        nuevo_costo = float(data["costo"])
        # Si no viene precio_venta explícito, calcular con 40% de utilidad
        if "precio_venta" not in data or not data.get("precio_venta"):
            data["precio_venta"] = nuevo_costo / 0.60
            data["utilidad"] = round(data["precio_venta"] - nuevo_costo, 2)
            data["porcentaje_utilidad"] = 40.0
        else:
            # Si viene precio_venta, calcular utilidad basada en ese precio
            nuevo_precio_venta = float(data["precio_venta"])
            data["utilidad"] = round(nuevo_precio_venta - nuevo_costo, 2)
            if nuevo_costo > 0:
                data["porcentaje_utilidad"] = round((data["utilidad"] / nuevo_costo) * 100, 2)
            else:
                data["porcentaje_utilidad"] = 0.0
    
    # Si solo se actualiza precio_venta (sin costo), recalcular utilidad
    elif "precio_venta" in data and "costo" not in data:
        nuevo_precio_venta = float(data["precio_venta"])
        print(f"💰 [INVENTARIOS] Actualizando precio_venta: {precio_venta_actual} -> {nuevo_precio_venta}")
        if costo_actual > 0:
            data["utilidad"] = round(nuevo_precio_venta - costo_actual, 2)
            data["porcentaje_utilidad"] = round((data["utilidad"] / costo_actual) * 100, 2)
        else:
            data["utilidad"] = 0.0
            data["porcentaje_utilidad"] = 0.0
        # Asegurar que también se actualice el campo "precio" si existe
        if "precio" not in data:
            data["precio"] = nuevo_precio_venta
    
    # Si no se actualiza ni costo ni precio_venta, pero faltan campos de utilidad, calcularlos
    elif "costo" not in data and "precio_venta" not in data:
        if costo_actual > 0 and precio_venta_actual > 0:
            # Recalcular utilidad con los valores actuales
            utilidad_calculada = precio_venta_actual - costo_actual
            porcentaje_calculado = (utilidad_calculada / costo_actual) * 100 if costo_actual > 0 else 0
            data["utilidad"] = round(utilidad_calculada, 2)
            data["porcentaje_utilidad"] = round(porcentaje_calculado, 2)
        elif costo_actual > 0 and (not precio_venta_actual or precio_venta_actual == 0):
            # Si hay costo pero no precio_venta, calcular con 40%
            data["precio_venta"] = costo_actual / 0.60
            data["utilidad"] = round(data["precio_venta"] - costo_actual, 2)
            data["porcentaje_utilidad"] = 40.0
    
    # Agregar información de actualización
    data["usuarioActualizacion"] = usuario.get("correo", "unknown")
    data["fechaActualizacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # DEBUG: Log de datos que se van a guardar
    print(f"💾 [INVENTARIOS] Guardando datos: {data}")
    
    resultado = await collection.update_one(
        {"_id": item_object_id},
        {"$set": data}
    )
    
    if resultado.modified_count == 0:
        raise HTTPException(status_code=404, detail="Item de inventario no encontrado o sin cambios")
    
    print(f"✅ [INVENTARIOS] Item actualizado exitosamente. Modified count: {resultado.modified_count}")
    
    # Obtener el item actualizado
    item_actualizado = await collection.find_one({"_id": item_object_id})
    item_actualizado["_id"] = str(item_actualizado["_id"])
    if "productoId" in item_actualizado and isinstance(item_actualizado["productoId"], ObjectId):
        item_actualizado["productoId"] = str(item_actualizado["productoId"])
    
    print(f"✅ [INVENTARIOS] Item actualizado: {item_id_real}")
    return {
        "message": "Item de inventario actualizado exitosamente",
        "item": item_actualizado
    }

# IMPORTANTE: Las rutas más específicas deben ir ANTES que las más generales
# FastAPI procesa las rutas en orden y la primera que haga match es la que se usa

@router.put("/inventarios/items/{item_id}")
@router.patch("/inventarios/items/{item_id}")
async def actualizar_item_inventario_sin_id(
    item_id: str,
    data: dict = Body(...),
    usuario: dict = Depends(get_current_user)
):
    """
    Actualiza un item de inventario sin especificar el ID de farmacia.
    Ruta específica para cuando el frontend llama /inventarios/items/{item_id}
    (después de normalización del middleware: /inventarios//items/{item_id} -> /inventarios/items/{item_id})
    """
    try:
        print(f"✏️ [INVENTARIOS] Actualizando item: {item_id} (sin ID de farmacia - ruta específica)")
        
        return await _actualizar_item_inventario_internal(item_id, data, "", usuario)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [INVENTARIOS] Error actualizando item: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/inventarios/{id}/items/{item_id}")
@router.patch("/inventarios/{id}/items/{item_id}")
async def actualizar_item_inventario(
    id: str,
    item_id: str,
    data: dict = Body(...),
    usuario: dict = Depends(get_current_user)
):
    """
    Actualiza un item de inventario.
    El {id} es el ID de la farmacia o inventario padre (puede estar vacío).
    El {item_id} es el ID del item a actualizar.
    Ruta general que captura cualquier ID de farmacia.
    """
    try:
        # Manejar caso cuando id está vacío (doble barra //)
        id_clean = id.strip() if id else ""
        print(f"✏️ [INVENTARIOS] Actualizando item: {item_id} de inventario: '{id_clean}' (vacío: {not id_clean})")
        
        return await _actualizar_item_inventario_internal(item_id, data, id_clean, usuario)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [INVENTARIOS] Error actualizando item: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/inventarios/{inventario_id}/items/{item_id}")
async def eliminar_item_inventario_por_id(
    inventario_id: str,
    item_id: str,
    usuario: dict = Depends(get_current_user)
):
    """
    Elimina un item del inventario por su ID.
    
    Args:
        inventario_id: ID de la farmacia o inventario (puede estar vacío)
        item_id: ID del item a eliminar
        usuario: Usuario autenticado
    
    Returns:
        Mensaje de confirmación de eliminación
    """
    try:
        collection = get_collection("INVENTARIOS")
        
        # Limpiar inventario_id si está vacío
        inventario_id_clean = inventario_id.strip() if inventario_id else ""
        
        print(f"🗑️ [INVENTARIOS] Eliminando item por ID: {item_id} de inventario: '{inventario_id_clean}'")
        
        # Validar que item_id sea un ObjectId válido
        try:
            item_object_id = ObjectId(item_id)
        except (InvalidId, ValueError):
            raise HTTPException(
                status_code=400,
                detail=f"ID de item inválido: {item_id}"
            )
        
        # Buscar el item antes de eliminarlo
        item = await collection.find_one({"_id": item_object_id})
        
        if not item:
            raise HTTPException(
                status_code=404,
                detail=f"Item con ID {item_id} no encontrado"
            )
        
        # IMPORTANTE: No validar farmacia - permitir eliminar cualquier producto
        # El usuario puede eliminar productos de cualquier farmacia sin restricciones
        codigo_item = item.get("codigo", "N/A")
        nombre_item = item.get("nombre", "N/A")
        farmacia_item = item.get("farmacia", "N/A")
        
        print(f"   Item encontrado: {codigo_item} - {nombre_item} (Farmacia: {farmacia_item}) - Eliminando sin restricciones")
        
        # Eliminar el item
        resultado = await collection.delete_one({"_id": item_object_id})
        
        if resultado.deleted_count == 0:
            raise HTTPException(
                status_code=500,
                detail="No se pudo eliminar el item (deleted_count = 0)"
            )
        
        print(f"✅ [INVENTARIOS] Item eliminado exitosamente: {item_id} ({codigo_item})")
        
        return {
            "message": "Item eliminado exitosamente",
            "item_id": item_id,
            "codigo": codigo_item,
            "nombre": nombre_item,
            "deleted": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [INVENTARIOS] Error eliminando item por ID: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/inventarios/{inventario_id}/items/codigo/{codigo}")
async def eliminar_item_inventario_por_codigo(
    inventario_id: str,
    codigo: str,
    usuario: dict = Depends(get_current_user)
):
    """
    Elimina un item del inventario por su código.
    
    Args:
        inventario_id: ID de la farmacia o inventario (puede estar vacío)
        codigo: Código del item a eliminar
        usuario: Usuario autenticado
    
    Returns:
        Mensaje de confirmación de eliminación
    """
    try:
        collection = get_collection("INVENTARIOS")
        
        # Limpiar inventario_id si está vacío
        inventario_id_clean = inventario_id.strip() if inventario_id else ""
        
        print(f"🗑️ [INVENTARIOS] Eliminando item por código: {codigo} (sin restricciones de farmacia)")
        
        # IMPORTANTE: Buscar el producto por código SIN filtrar por farmacia
        # Esto permite eliminar cualquier producto sin importar a qué farmacia pertenezca
        filtro = {
            "codigo": {"$regex": f"^{re.escape(codigo)}$", "$options": "i"}  # Case insensitive
        }
        
        # Buscar el item antes de eliminarlo (sin restricción de farmacia)
        item = await collection.find_one(filtro)
        
        if not item:
            raise HTTPException(
                status_code=404,
                detail=f"Item con código '{codigo}' no encontrado"
            )
        
        # Información del item antes de eliminar
        item_id = str(item["_id"])
        codigo_item = item.get("codigo", "N/A")
        nombre_item = item.get("nombre", "N/A")
        farmacia_item = item.get("farmacia", "N/A")
        
        print(f"   Item encontrado: {codigo_item} - {nombre_item} (ID: {item_id}, Farmacia: {farmacia_item})")
        
        # Eliminar el item
        resultado = await collection.delete_one({"_id": item["_id"]})
        
        if resultado.deleted_count == 0:
            raise HTTPException(
                status_code=500,
                detail="No se pudo eliminar el item (deleted_count = 0)"
            )
        
        print(f"✅ [INVENTARIOS] Item eliminado exitosamente por código: {codigo} (ID: {item_id})")
        
        return {
            "message": "Item eliminado exitosamente",
            "item_id": item_id,
            "codigo": codigo_item,
            "nombre": nombre_item,
            "deleted": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [INVENTARIOS] Error eliminando item por código: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/inventarios/buscar")
async def buscar_productos_inventario_modal(
    q: Optional[str] = Query(None, description="Término de búsqueda (código, nombre, descripción)"),
    farmacia: Optional[str] = Query(None, description="ID de la farmacia"),
    limit: Optional[int] = Query(50, description="Límite de resultados (máximo 50)"),
    usuario: dict = Depends(get_current_user)
):
    """
    Búsqueda ULTRA RÁPIDA de productos en inventario para modal de carga masiva.
    Optimizado para responder en menos de 5 segundos.
    
    OPTIMIZACIONES:
    - Búsqueda exacta por código primero (instantánea con índice)
    - Búsqueda por prefijo en código y nombre (campos indexados)
    - Búsqueda parcial en descripción si no hay resultados
    - Proyección mínima (solo campos esenciales)
    - Límite máximo de 50 resultados
    - Solo productos activos
    - Sin procesamiento pesado
    
    Parámetros:
    - q: Término de búsqueda (código, nombre o descripción) - opcional
    - farmacia: ID de la farmacia (opcional)
    - limit: Límite de resultados (máximo 50, por defecto 50)
    
    Response: Array de productos con campos mínimos
    """
    try:
        # Manejar parámetro q que puede ser None o string vacío
        if q is None:
            return []
        query_term = str(q).strip() if q else ""
        if not query_term:
            return []
        
        # Limitar el límite a máximo 50 para velocidad
        limit = min(limit or 50, 50)
        
        print(f"🔍 [INVENTARIOS-MODAL] Búsqueda rápida: '{query_term}' (límite: {limit})")
        
        collection = get_collection("INVENTARIOS")
        
        # Construir filtro base (solo activos)
        filtro = {"estado": {"$ne": "inactivo"}}
        
        # Filtrar por farmacia si se especifica
        if farmacia and farmacia.strip():
            filtro["farmacia"] = farmacia.strip()
        
        # PROYECCIÓN MÍNIMA (solo campos esenciales para el modal)
        # IMPORTANTE: Incluir "cantidad" para mostrar existencia actualizada
        proyeccion_minima = {
            "_id": 1, "codigo": 1, "nombre": 1, "descripcion": 1,
            "cantidad": 1, "costo": 1, "precio_venta": 1, "precio": 1,
            "farmacia": 1, "marca": 1, "utilidad": 1, "porcentaje_utilidad": 1
        }
        
        # OPTIMIZACIÓN 1: Búsqueda exacta por código primero (MUY RÁPIDA con índice)
        # IMPORTANTE: Consultar directamente de la BD sin caché para obtener datos actualizados
        codigo_filtro = {**filtro, "codigo": query_term.upper()}
        producto_exacto = await collection.find_one(
            codigo_filtro,
            projection=proyeccion_minima
        )
        
        # Si no encontramos por código exacto, buscar por nombre/descripción
        if not producto_exacto:
            # Buscar también por nombre exacto (sin regex para más velocidad)
            nombre_filtro = {**filtro, "nombre": {"$regex": f"^{re.escape(query_term)}", "$options": "i"}}
            producto_exacto = await collection.find_one(
                nombre_filtro,
                projection=proyeccion_minima
            )
        
        resultados = []
        
        if producto_exacto:
            # Si encontramos coincidencia exacta, agregarla primero
            producto_exacto["_id"] = str(producto_exacto["_id"])
            # Calcular valores si faltan
            costo = float(producto_exacto.get("costo", 0))
            precio_venta = float(producto_exacto.get("precio_venta") or producto_exacto.get("precio", 0))
            if costo > 0 and precio_venta == 0:
                precio_venta = costo / 0.60
            utilidad = precio_venta - costo if precio_venta > 0 and costo > 0 else float(producto_exacto.get("utilidad", 0))
            porcentaje_utilidad = float(producto_exacto.get("porcentaje_utilidad", 40.0)) if utilidad > 0 else 0.0
            
            # IMPORTANTE: Obtener cantidad directamente de la BD (sin redondeo para mostrar valor exacto)
            cantidad_actual_exacto = float(producto_exacto.get("cantidad", 0))
            
            resultados.append({
                "id": producto_exacto["_id"],
                "_id": producto_exacto["_id"],
                "codigo": producto_exacto.get("codigo", ""),
                "nombre": producto_exacto.get("nombre", ""),
                "descripcion": producto_exacto.get("descripcion", ""),
                "marca": producto_exacto.get("marca", ""),
                "cantidad": cantidad_actual_exacto,  # Valor exacto sin redondeo
                "costo": round(costo, 2),
                "precio_venta": round(precio_venta, 2),
                "precio": round(precio_venta, 2),
                "utilidad": round(utilidad, 2),
                "porcentaje_utilidad": round(porcentaje_utilidad, 2),
                "farmacia": producto_exacto.get("farmacia", "")
            })
        
        # OPTIMIZACIÓN 2: Búsqueda por término en nombre y descripción (SOLO busca el término específico)
        # Solo si no encontramos coincidencia exacta o queremos más resultados
        if len(resultados) < limit:
            # Escapar caracteres especiales del término de búsqueda
            query_escaped = re.escape(query_term)
            
            # Buscar SOLO productos que contengan el término (no todos los productos)
            busqueda_filtro = {
                **filtro,
                "$or": [
                    {"codigo": {"$regex": query_escaped, "$options": "i"}},
                    {"nombre": {"$regex": query_escaped, "$options": "i"}},
                    {"descripcion": {"$regex": query_escaped, "$options": "i"}}
                ]
            }
            
            # Excluir el producto exacto si ya lo agregamos
            if producto_exacto:
                busqueda_filtro["_id"] = {"$ne": ObjectId(producto_exacto["_id"])}
            
            # Buscar con límite reducido - SOLO productos que coincidan con el término
            productos_busqueda = await collection.find(
                busqueda_filtro,
                projection=proyeccion_minima
            ).sort("nombre", 1).limit(limit - len(resultados)).to_list(length=limit - len(resultados))
            
            # Procesar resultados (mínimo procesamiento)
            for inv in productos_busqueda:
                inv_id = str(inv["_id"])
                costo = float(inv.get("costo", 0))
                precio_venta = float(inv.get("precio_venta") or inv.get("precio", 0))
                if costo > 0 and precio_venta == 0:
                    precio_venta = costo / 0.60
                utilidad = precio_venta - costo if precio_venta > 0 and costo > 0 else float(inv.get("utilidad", 0))
                porcentaje_utilidad = float(inv.get("porcentaje_utilidad", 40.0)) if utilidad > 0 else 0.0
                
                # IMPORTANTE: Obtener cantidad directamente de la BD (sin redondeo para mostrar valor exacto)
                cantidad_actual = float(inv.get("cantidad", 0))
                
                resultados.append({
                    "id": inv_id,
                    "_id": inv_id,
                    "codigo": inv.get("codigo", ""),
                    "nombre": inv.get("nombre", ""),
                    "descripcion": inv.get("descripcion", ""),
                    "marca": inv.get("marca", ""),
                    "cantidad": cantidad_actual,  # Valor exacto sin redondeo
                    "costo": round(costo, 2),
                    "precio_venta": round(precio_venta, 2),
                    "precio": round(precio_venta, 2),
                    "utilidad": round(utilidad, 2),
                    "porcentaje_utilidad": round(porcentaje_utilidad, 2),
                    "farmacia": inv.get("farmacia", "")
                })
        
        print(f"✅ [INVENTARIOS-MODAL] Búsqueda completada: {len(resultados)} resultados en <5s")
        return resultados
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [INVENTARIOS-MODAL] Error en búsqueda: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al buscar productos: {str(e)}")

@router.post("/inventarios/crear-producto")
async def crear_producto_inventario(
    datos_producto: dict = Body(...),
    usuario: dict = Depends(get_current_user)
):
    """
    Crea un nuevo producto en el inventario desde el modal de carga masiva.
    
    Body:
    {
      "farmacia": "01",           // ID de la farmacia (requerido)
      "codigo": "PROD-001",       // Código del producto (opcional)
      "nombre": "Producto Nuevo", // Nombre del producto (requerido)
      "descripcion": "...",       // Descripción (opcional)
      "marca": "Marca X",         // Marca (opcional)
      "cantidad": 0,              // Cantidad inicial (opcional, default 0)
      "costo": 100.00,            // Costo unitario (requerido)
      "utilidad": 66.67,          // Utilidad en dinero (opcional)
      "porcentaje_utilidad": 40.0, // Porcentaje de utilidad (opcional, default 40%)
      "precio_venta": 166.67      // Precio de venta (opcional, se calcula si no se envía)
    }
    
    Response:
    {
      "message": "Producto creado exitosamente",
      "producto": {
        "id": "...",
        "codigo": "...",
        "nombre": "...",
        // ... resto de campos
      }
    }
    """
    try:
        collection = get_collection("INVENTARIOS")
        usuario_correo = usuario.get("correo", "unknown")
        
        # Validar datos requeridos
        farmacia = datos_producto.get("farmacia")
        if not farmacia:
            raise HTTPException(status_code=400, detail="El campo 'farmacia' es requerido")
        
        nombre = datos_producto.get("nombre", "").strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="El campo 'nombre' es requerido")
        
        costo = float(datos_producto.get("costo", 0))
        if costo <= 0:
            raise HTTPException(status_code=400, detail="El campo 'costo' debe ser mayor a 0")
        
        # Verificar si ya existe un producto con el mismo código en esta farmacia
        codigo = datos_producto.get("codigo", "").strip()
        if codigo:
            producto_existente = await collection.find_one({
                "farmacia": farmacia,
                "codigo": codigo.upper(),
                "estado": {"$ne": "inactivo"}
            })
            if producto_existente:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Ya existe un producto con el código '{codigo}' en esta farmacia"
                )
        
        # Calcular precio_venta y utilidad
        precio_venta_enviado = datos_producto.get("precio_venta")
        utilidad_enviada = datos_producto.get("utilidad")
        porcentaje_utilidad_enviado = datos_producto.get("porcentaje_utilidad", 40.0)
        
        if precio_venta_enviado and precio_venta_enviado > 0:
            # Si viene precio_venta explícito, usarlo
            precio_venta_final = float(precio_venta_enviado)
            if utilidad_enviada is not None:
                utilidad_final = float(utilidad_enviada)
            else:
                utilidad_final = precio_venta_final - costo
            porcentaje_utilidad_final = porcentaje_utilidad_enviado
        elif utilidad_enviada is not None and utilidad_enviada > 0:
            # Si viene utilidad, calcular precio_venta
            utilidad_final = float(utilidad_enviada)
            precio_venta_final = costo + utilidad_final
            porcentaje_utilidad_final = (utilidad_final / costo) * 100 if costo > 0 else 0
        else:
            # Calcular automáticamente con porcentaje de utilidad (default 40%)
            porcentaje_utilidad_final = float(porcentaje_utilidad_enviado)
            precio_venta_final = costo / (1 - (porcentaje_utilidad_final / 100))
            utilidad_final = precio_venta_final - costo
        
        # Obtener fecha actual
        venezuela_tz = pytz.timezone("America/Caracas")
        now_ve = datetime.now(venezuela_tz)
        fecha_actual = now_ve.strftime("%Y-%m-%d")
        
        # Crear nuevo producto
        # IMPORTANTE: Asegurar que el estado sea "activo" explícitamente
        # IMPORTANTE: Inicializar cantidad, existencia y stock con el mismo valor para sincronización
        cantidad_inicial = float(datos_producto.get("cantidad", 0))
        nuevo_producto = {
            "farmacia": str(farmacia).strip(),
            "nombre": nombre,
            "descripcion": datos_producto.get("descripcion", "").strip(),
            "marca": datos_producto.get("marca", "").strip(),
            "cantidad": cantidad_inicial,
            "existencia": cantidad_inicial,  # IMPORTANTE: Sincronizar con cantidad
            "stock": cantidad_inicial,      # IMPORTANTE: Sincronizar con cantidad
            "costo": round(costo, 2),
            "precio_venta": round(precio_venta_final, 2),
            "precio": round(precio_venta_final, 2),
            "utilidad": round(utilidad_final, 2),
            "porcentaje_utilidad": round(porcentaje_utilidad_final, 2),
            "usuarioCorreo": usuario_correo,
            "fecha": fecha_actual,
            "fechaCreacion": fecha_actual,
            "estado": "activo"  # IMPORTANTE: Estado activo explícito
        }
        
        print(f"📝 [INVENTARIOS] Datos del producto a crear: {nuevo_producto}")
        
        if codigo:
            nuevo_producto["codigo"] = codigo.upper()
        
        # Insertar en la base de datos
        print(f"📝 [INVENTARIOS] Insertando producto: {nombre} en farmacia {farmacia}")
        result = await collection.insert_one(nuevo_producto)
        producto_id = str(result.inserted_id)
        print(f"✅ [INVENTARIOS] Producto insertado con ID: {producto_id}")
        
        # Obtener el producto creado para retornarlo (consultar directamente de BD)
        producto_creado = await collection.find_one({"_id": result.inserted_id})
        if not producto_creado:
            raise HTTPException(status_code=500, detail="Error: Producto creado pero no se pudo recuperar")
        
        producto_creado["_id"] = producto_id
        print(f"✅ [INVENTARIOS] Producto recuperado de BD: {producto_creado.get('nombre', 'N/A')}")
        
        # Formatear respuesta
        # IMPORTANTE: Incluir existencia y stock en la respuesta para sincronización
        cantidad_respuesta = float(producto_creado.get("cantidad", 0))
        existencia_respuesta = float(producto_creado.get("existencia", cantidad_respuesta))
        stock_respuesta = float(producto_creado.get("stock", cantidad_respuesta))
        
        producto_formateado = {
            "id": producto_id,
            "_id": producto_id,
            "codigo": producto_creado.get("codigo", ""),
            "nombre": producto_creado.get("nombre", ""),
            "descripcion": producto_creado.get("descripcion", ""),
            "marca": producto_creado.get("marca", ""),
            "cantidad": cantidad_respuesta,
            "existencia": existencia_respuesta,  # IMPORTANTE: Incluir existencia
            "stock": stock_respuesta,            # IMPORTANTE: Incluir stock
            "costo": round(float(producto_creado.get("costo", 0)), 2),
            "precio_venta": round(float(producto_creado.get("precio_venta", 0)), 2),
            "precio": round(float(producto_creado.get("precio_venta", 0)), 2),
            "utilidad": round(float(producto_creado.get("utilidad", 0)), 2),
            "porcentaje_utilidad": round(float(producto_creado.get("porcentaje_utilidad", 0)), 2),
            "farmacia": producto_creado.get("farmacia", ""),
            "estado": producto_creado.get("estado", "activo")
        }
        
        print(f"✅ [INVENTARIOS] Producto creado: {nombre} - ID: {producto_id}")
        
        return {
            "message": "Producto creado exitosamente",
            "producto": producto_formateado
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [INVENTARIOS] Error creando producto: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al crear producto: {str(e)}")

@router.post("/inventarios/cargar-existencia")
async def cargar_existencia_masiva(
    datos_carga: dict = Body(...),
    usuario: dict = Depends(get_current_user)
):
    """
    Carga existencia masiva al inventario.
    Suma las cantidades a los productos existentes (no reemplaza).
    Permite cargar múltiples productos a la vez.
    
    Body:
    {
      "farmacia": "01",  // ID de la farmacia (requerido)
      "productos": [     // Array de productos a cargar
        {
          "producto_id": "id_del_producto",  // ID del producto en inventario
          "cantidad": 10,                     // Cantidad a sumar
          "costo": 100.00,                    // Costo unitario (opcional, usa el actual si no se envía)
          "utilidad": 66.67,                  // Utilidad en dinero (opcional)
          "porcentaje_utilidad": 40.0,        // Porcentaje de utilidad (opcional, default 40%)
          "precio_venta": 166.67              // Precio de venta (opcional, se calcula si no se envía)
        }
      ]
    }
    
    Response:
    {
      "message": "Existencia cargada exitosamente",
      "productos_procesados": 5,
      "productos_exitosos": 5,
      "productos_con_error": 0,
      "detalle": {
        "exitosos": [...],
        "errores": [...]
      }
    }
    """
    try:
        collection = get_collection("INVENTARIOS")
        usuario_correo = usuario.get("correo", "unknown")
        
        # Validar datos
        farmacia = datos_carga.get("farmacia")
        if not farmacia:
            raise HTTPException(status_code=400, detail="El campo 'farmacia' es requerido")
        
        productos = datos_carga.get("productos", [])
        if not productos or len(productos) == 0:
            raise HTTPException(status_code=400, detail="Debe enviar al menos un producto")
        
        print(f"📦 [INVENTARIOS] Cargando existencia masiva: {len(productos)} productos en farmacia {farmacia}")
        
        venezuela_tz = pytz.timezone("America/Caracas")
        now_ve = datetime.now(venezuela_tz)
        fecha_actual = now_ve.strftime("%Y-%m-%d")
        
        productos_exitosos = []
        productos_con_error = []
        
        # Procesar cada producto
        for producto_carga in productos:
            try:
                producto_id = producto_carga.get("producto_id")
                if not producto_id:
                    raise ValueError("El campo 'producto_id' es requerido")
                
                cantidad_a_sumar = float(producto_carga.get("cantidad", 0))
                if cantidad_a_sumar <= 0:
                    raise ValueError("La cantidad debe ser mayor a 0")
                
                # Buscar el producto en el inventario
                try:
                    producto_object_id = ObjectId(producto_id)
                except (InvalidId, ValueError):
                    raise ValueError(f"ID de producto inválido: {producto_id}")
                
                producto_actual = await collection.find_one({"_id": producto_object_id})
                if not producto_actual:
                    raise ValueError(f"Producto no encontrado: {producto_id}")
                
                # Verificar que pertenece a la farmacia correcta
                if producto_actual.get("farmacia") != farmacia:
                    raise ValueError(f"El producto no pertenece a la farmacia {farmacia}")
                
                # Obtener valores actuales
                cantidad_actual = float(producto_actual.get("cantidad", 0))
                costo_actual = float(producto_actual.get("costo", 0))
                
                # Calcular nueva cantidad (SUMAR, no reemplazar)
                cantidad_nueva = cantidad_actual + cantidad_a_sumar
                
                # Obtener nuevo costo (si viene en la carga, usarlo; sino usar el actual)
                nuevo_costo_unitario = float(producto_carga.get("costo", costo_actual))
                if nuevo_costo_unitario <= 0:
                    nuevo_costo_unitario = costo_actual
                
                # Calcular costo promedio ponderado
                if cantidad_actual > 0 and nuevo_costo_unitario != costo_actual:
                    costo_total_actual = cantidad_actual * costo_actual
                    costo_total_nuevo = cantidad_a_sumar * nuevo_costo_unitario
                    costo_promedio = (costo_total_actual + costo_total_nuevo) / cantidad_nueva
                else:
                    costo_promedio = nuevo_costo_unitario if nuevo_costo_unitario > 0 else costo_actual
                
                # Calcular precio_venta y utilidad
                precio_venta_enviado = producto_carga.get("precio_venta")
                utilidad_enviada = producto_carga.get("utilidad")
                porcentaje_utilidad_enviado = producto_carga.get("porcentaje_utilidad", 40.0)
                
                if precio_venta_enviado and precio_venta_enviado > 0:
                    # Si viene precio_venta explícito, usarlo
                    precio_venta_final = float(precio_venta_enviado)
                    if utilidad_enviada is not None:
                        utilidad_final = float(utilidad_enviada)
                    else:
                        utilidad_final = precio_venta_final - costo_promedio
                    porcentaje_utilidad_final = porcentaje_utilidad_enviado
                elif utilidad_enviada is not None and utilidad_enviada > 0:
                    # Si viene utilidad, calcular precio_venta
                    utilidad_final = float(utilidad_enviada)
                    precio_venta_final = costo_promedio + utilidad_final
                    porcentaje_utilidad_final = (utilidad_final / costo_promedio) * 100 if costo_promedio > 0 else 0
                else:
                    # Calcular automáticamente con porcentaje de utilidad (default 40%)
                    porcentaje_utilidad_final = float(porcentaje_utilidad_enviado)
                    precio_venta_final = costo_promedio / (1 - (porcentaje_utilidad_final / 100))
                    utilidad_final = precio_venta_final - costo_promedio
                
                # Actualizar inventario
                update_data = {
                    "cantidad": cantidad_nueva,
                    "costo": round(costo_promedio, 2),
                    "precio_venta": round(precio_venta_final, 2),
                    "precio": round(precio_venta_final, 2),
                    "utilidad": round(utilidad_final, 2),
                    "porcentaje_utilidad": round(porcentaje_utilidad_final, 2),
                    "fechaActualizacion": fecha_actual,
                    "usuarioActualizacion": usuario_correo
                }
                
                await collection.update_one(
                    {"_id": producto_object_id},
                    {"$set": update_data}
                )
                
                # Obtener el producto actualizado completo para retornarlo
                producto_actualizado = await collection.find_one({"_id": producto_object_id})
                
                # Formatear producto actualizado para el frontend
                producto_formateado = {
                    "id": producto_id,
                    "_id": producto_id,
                    "codigo": producto_actualizado.get("codigo", ""),
                    "nombre": producto_actualizado.get("nombre", ""),
                    "descripcion": producto_actualizado.get("descripcion", ""),
                    "marca": producto_actualizado.get("marca", ""),
                    "cantidad": float(producto_actualizado.get("cantidad", 0)),
                    "costo": round(float(producto_actualizado.get("costo", 0)), 2),
                    "precio_venta": round(float(producto_actualizado.get("precio_venta") or producto_actualizado.get("precio", 0)), 2),
                    "precio": round(float(producto_actualizado.get("precio_venta") or producto_actualizado.get("precio", 0)), 2),
                    "utilidad": round(float(producto_actualizado.get("utilidad", 0)), 2),
                    "porcentaje_utilidad": round(float(producto_actualizado.get("porcentaje_utilidad", 0)), 2),
                    "farmacia": producto_actualizado.get("farmacia", ""),
                    "estado": producto_actualizado.get("estado", "activo"),
                    # Información adicional para el frontend
                    "cantidad_anterior": cantidad_actual,
                    "cantidad_suma": cantidad_a_sumar,
                    "cantidad_nueva": cantidad_nueva
                }
                
                productos_exitosos.append(producto_formateado)
                
                print(f"✅ [INVENTARIOS] Existencia cargada: {producto_actual.get('nombre', '')} - {cantidad_actual} + {cantidad_a_sumar} = {cantidad_nueva}")
                
            except Exception as e:
                error_msg = str(e)
                print(f"❌ [INVENTARIOS] Error cargando existencia para producto {producto_carga.get('producto_id', 'unknown')}: {error_msg}")
                productos_con_error.append({
                    "producto_id": producto_carga.get("producto_id", "unknown"),
                    "error": error_msg
                })
        
        print(f"✅ [INVENTARIOS] Carga masiva completada: {len(productos_exitosos)} exitosos, {len(productos_con_error)} con error")
        
        return {
            "message": "Existencia cargada exitosamente",
            "productos_procesados": len(productos),
            "productos_exitosos": len(productos_exitosos),
            "productos_con_error": len(productos_con_error),
            "detalle": {
                "exitosos": productos_exitosos,
                "errores": productos_con_error
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [INVENTARIOS] Error en carga masiva: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bancos")
async def obtener_bancos(usuario: dict = Depends(get_current_user)):
    """
    Obtiene todos los bancos disponibles.
    Requiere autenticación.
    """
    try:
        print(f"🏦 [BANCOS] Obteniendo bancos")
        collection = get_collection("BANCOS")
        bancos = await collection.find({}).to_list(length=None)
        
        # Convertir _id a string
        for banco in bancos:
            banco["_id"] = str(banco["_id"])
        
        print(f"🏦 [BANCOS] Encontrados {len(bancos)} bancos")
        return bancos
    except Exception as e:
        print(f"❌ [BANCOS] Error obteniendo bancos: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bancos")
async def crear_banco(
    banco_data: dict = Body(...),
    usuario: dict = Depends(get_current_user)
):
    """
    Crea un nuevo banco.
    Requiere autenticación.
    """
    try:
        print(f"🏦 [BANCOS] Creando banco - Usuario: {usuario.get('correo', 'unknown')}")
        collection = get_collection("BANCOS")
        
        # Agregar información de creación
        banco_dict = banco_data.copy()
        banco_dict["usuarioCreacion"] = usuario.get("correo", "unknown")
        banco_dict["fechaCreacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Inicializar campos si no existen
        if "saldo" not in banco_dict:
            banco_dict["saldo"] = 0.0
        if "movimientos" not in banco_dict:
            banco_dict["movimientos"] = []
        
        # Insertar banco
        resultado = await collection.insert_one(banco_dict)
        banco_id = str(resultado.inserted_id)
        
        # Convertir _id a string en la respuesta
        banco_dict["_id"] = banco_id
        
        print(f"✅ [BANCOS] Banco creado: {banco_id}")
        
        return {
            "message": "Banco creado exitosamente",
            "id": banco_id,
            "banco": banco_dict
        }
        
    except Exception as e:
        print(f"❌ [BANCOS] Error creando banco: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bancos/movimientos")
async def crear_movimiento_banco(
    movimiento_data: dict = Body(...),
    usuario: dict = Depends(get_current_user)
):
    """
    Crea un movimiento bancario (depósito, retiro, transferencia, etc.).
    Actualiza el saldo del banco y agrega el movimiento al historial.
    Requiere autenticación.
    """
    try:
        print(f"💸 [BANCOS] Creando movimiento - Usuario: {usuario.get('correo', 'unknown')}")
        
        bancos_collection = get_collection("BANCOS")
        
        # Validar campos requeridos
        banco_id = movimiento_data.get("banco_id")
        if not banco_id:
            raise HTTPException(status_code=400, detail="El campo 'banco_id' es requerido")
        
        tipo = movimiento_data.get("tipo", "").lower()
        if not tipo:
            raise HTTPException(status_code=400, detail="El campo 'tipo' es requerido")
        
        monto = float(movimiento_data.get("monto", 0))
        if monto <= 0:
            raise HTTPException(status_code=400, detail="El monto debe ser mayor a 0")
        
        # Validar banco_id
        try:
            banco_object_id = ObjectId(banco_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="ID de banco inválido")
        
        # Obtener el banco
        banco = await bancos_collection.find_one({"_id": banco_object_id})
        if not banco:
            raise HTTPException(status_code=404, detail="Banco no encontrado")
        
        saldo_actual = float(banco.get("saldo", 0))
        
        # Determinar si es entrada o salida de dinero
        tipos_entrada = ["deposito", "ingreso", "transferencia_entrada", "abono", "pago_recibido"]
        tipos_salida = ["retiro", "egreso", "transferencia_salida", "pago", "pago_compra", "gasto"]
        
        es_entrada = tipo in tipos_entrada
        es_salida = tipo in tipos_salida
        
        if not es_entrada and not es_salida:
            # Si no está en ninguna lista, asumir que es salida por defecto
            es_salida = True
        
        # Calcular nuevo saldo
        if es_entrada:
            nuevo_saldo = saldo_actual + monto
        else:  # es_salida
            # Validar que haya saldo suficiente para retiros
            if saldo_actual < monto:
                raise HTTPException(
                    status_code=400,
                    detail=f"Saldo insuficiente. Saldo disponible: {saldo_actual}, Monto requerido: {monto}"
                )
            nuevo_saldo = saldo_actual - monto
        
        # Crear el movimiento
        movimiento = {
            "tipo": tipo,
            "monto": monto,
            "fecha": movimiento_data.get("fecha", datetime.now().strftime("%Y-%m-%d")),
            "referencia": movimiento_data.get("referencia", ""),
            "descripcion": movimiento_data.get("descripcion", ""),
            "notas": movimiento_data.get("notas", ""),
            "usuario": usuario.get("correo", "unknown"),
            "fechaCreacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "saldo_anterior": saldo_actual,
            "saldo_nuevo": nuevo_saldo
        }
        
        # Agregar campos opcionales
        if movimiento_data.get("comprobante"):
            movimiento["comprobante"] = movimiento_data.get("comprobante")
        
        if movimiento_data.get("compra_id"):
            movimiento["compra_id"] = movimiento_data.get("compra_id")
        
        if movimiento_data.get("cliente_id"):
            movimiento["cliente_id"] = movimiento_data.get("cliente_id")
        
        # Obtener movimientos existentes
        movimientos = banco.get("movimientos", [])
        movimientos.append(movimiento)
        
        # Actualizar el banco
        await bancos_collection.update_one(
            {"_id": banco_object_id},
            {
                "$set": {
                    "saldo": nuevo_saldo,
                    "movimientos": movimientos,
                    "fechaActualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "usuarioActualizacion": usuario.get("correo", "unknown")
                }
            }
        )
        
        # Obtener el banco actualizado
        banco_actualizado = await bancos_collection.find_one({"_id": banco_object_id})
        banco_actualizado["_id"] = str(banco_actualizado["_id"])
        
        # Convertir ObjectIds en movimientos
        for mov in banco_actualizado.get("movimientos", []):
            if "compra_id" in mov and isinstance(mov["compra_id"], ObjectId):
                mov["compra_id"] = str(mov["compra_id"])
            if "cliente_id" in mov and isinstance(mov["cliente_id"], ObjectId):
                mov["cliente_id"] = str(mov["cliente_id"])
        
        print(f"✅ [BANCOS] Movimiento creado: {tipo} - {monto} - Saldo: {saldo_actual} -> {nuevo_saldo}")
        
        return {
            "message": "Movimiento creado exitosamente",
            "movimiento": movimiento,
            "banco": banco_actualizado
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [BANCOS] Error creando movimiento: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bancos/{banco_id}/movimientos")
async def obtener_movimientos_banco(
    banco_id: str,
    fecha_inicio: Optional[str] = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin: Optional[str] = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    usuario: dict = Depends(get_current_user)
):
    """
    Obtiene el historial de movimientos de un banco.
    Puede filtrar por rango de fechas.
    Requiere autenticación.
    """
    try:
        try:
            banco_object_id = ObjectId(banco_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="ID de banco inválido")
        
        bancos_collection = get_collection("BANCOS")
        banco = await bancos_collection.find_one({"_id": banco_object_id})
        
        if not banco:
            raise HTTPException(status_code=404, detail="Banco no encontrado")
        
        movimientos = banco.get("movimientos", [])
        
        # Filtrar por fecha si se especifica
        if fecha_inicio or fecha_fin:
            movimientos_filtrados = []
            for mov in movimientos:
                fecha_mov = mov.get("fecha", "")
                if fecha_inicio and fecha_fin:
                    if fecha_inicio <= fecha_mov <= fecha_fin:
                        movimientos_filtrados.append(mov)
                elif fecha_inicio:
                    if fecha_mov >= fecha_inicio:
                        movimientos_filtrados.append(mov)
                elif fecha_fin:
                    if fecha_mov <= fecha_fin:
                        movimientos_filtrados.append(mov)
            movimientos = movimientos_filtrados
        
        # Ordenar por fecha más reciente primero
        movimientos.sort(key=lambda x: x.get("fechaCreacion", ""), reverse=True)
        
        # Convertir ObjectIds a strings
        for mov in movimientos:
            if "compra_id" in mov and isinstance(mov["compra_id"], ObjectId):
                mov["compra_id"] = str(mov["compra_id"])
            if "cliente_id" in mov and isinstance(mov["cliente_id"], ObjectId):
                mov["cliente_id"] = str(mov["cliente_id"])
        
        return {
            "banco_id": banco_id,
            "banco_nombre": banco.get("nombre", ""),
            "saldo_actual": banco.get("saldo", 0),
            "total_movimientos": len(movimientos),
            "movimientos": movimientos
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/presigned-url")
async def get_presigned_url(request: Request):
    """
    Endpoint para generar una URL prefirmada para Cloudflare R2.
    """
    data = await request.json()
    object_name = data.get('object_name')
    operation = data.get('operation', 'get_object')
    expires_in = data.get('expires_in', 3600)
    content_type = data.get('content_type')

    if not object_name:
        return JSONResponse(status_code=400, content={"error": "Missing 'object_name' in request body"})

    try:
        if operation == 'get_object':
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': R2_BUCKET,
                    'Key': object_name
                },
                ExpiresIn=expires_in
            )
        elif operation == 'put_object':
            if not content_type:
                return JSONResponse(status_code=400, content={"error": "For 'put_object' operation, 'content_type' is required."})
            presigned_url = s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': R2_BUCKET,
                    'Key': object_name,
                    'ContentType': content_type
                },
                ExpiresIn=expires_in
            )
        else:
            return JSONResponse(status_code=400, content={"error": "Invalid 'operation'. Must be 'get_object' or 'put_object'."})
        return {"presigned_url": presigned_url}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to generate presigned URL: {str(e)}"})

