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
        filtro = {}
        
        # Filtrar por farmacia si se especifica
        if farmacia and farmacia.strip():
            filtro["farmacia"] = farmacia.strip()
        
        # OPTIMIZACIÓN: Usar proyección y límite
        limit = min(limit or 500, 1000)  # Máximo 1000
        
        inventarios = await collection.find(
            filtro,
            projection={
                "_id": 1, "codigo": 1, "nombre": 1, "descripcion": 1,
                "precio_venta": 1, "precio": 1, "marca": 1, "cantidad": 1,
                "lotes": 1, "farmacia": 1, "costo": 1, "estado": 1, 
                "productoId": 1, "categoria": 1, "proveedor": 1
            }
        ).sort("nombre", 1).limit(limit).to_list(length=limit)
        
        for inv in inventarios:
            inv["_id"] = str(inv["_id"])
            if "productoId" in inv and isinstance(inv["productoId"], ObjectId):
                inv["productoId"] = str(inv["productoId"])
        
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

@router.get("/inventarios/{id}/items")
async def obtener_items_inventario(id: str, usuario: dict = Depends(get_current_user)):
    """
    Obtiene los items de inventario.
    El {id} puede ser el ID de la farmacia o el ID de un inventario específico.
    Si es un ID de farmacia, retorna todos los items de esa farmacia.
    Si es un ID de inventario, retorna ese item específico.
    Si el ID está vacío, retorna todos los inventarios.
    """
    try:
        collection = get_collection("INVENTARIOS")
        
        # Si el ID está vacío, retornar todos los inventarios
        if not id or id.strip() == "":
            print("🔍 [INVENTARIOS] ID vacío, retornando todos los inventarios")
            # OPTIMIZACIÓN: Usar proyección y límite
            inventarios = await collection.find(
                {},
                projection={
                    "_id": 1, "codigo": 1, "nombre": 1, "descripcion": 1,
                    "precio_venta": 1, "precio": 1, "marca": 1, "cantidad": 1,
                    "lotes": 1, "farmacia": 1, "costo": 1, "estado": 1, 
                    "productoId": 1, "categoria": 1, "proveedor": 1
                }
            ).sort("nombre", 1).limit(500).to_list(length=500)
            for inv in inventarios:
                inv["_id"] = str(inv["_id"])
                if "productoId" in inv and isinstance(inv["productoId"], ObjectId):
                    inv["productoId"] = str(inv["productoId"])
            return inventarios
        
        # Intentar primero como ObjectId (inventario específico)
        try:
            object_id = ObjectId(id)
            inventario = await collection.find_one(
                {"_id": object_id},
                projection={
                    "_id": 1, "codigo": 1, "nombre": 1, "descripcion": 1,
                    "precio_venta": 1, "precio": 1, "marca": 1, "cantidad": 1,
                    "lotes": 1, "farmacia": 1, "costo": 1, "estado": 1, 
                    "productoId": 1, "categoria": 1, "proveedor": 1
                }
            )
            if inventario:
                inventario["_id"] = str(inventario["_id"])
                if "productoId" in inventario and isinstance(inventario["productoId"], ObjectId):
                    inventario["productoId"] = str(inventario["productoId"])
                return [inventario]  # Retornar como lista para consistencia
        except (InvalidId, ValueError):
            # Si no es un ObjectId válido, tratar como ID de farmacia
            pass
        
        # OPTIMIZACIÓN: Buscar por farmacia con proyección y límite
        inventarios = await collection.find(
            {"farmacia": id},
            projection={
                "_id": 1, "codigo": 1, "nombre": 1, "descripcion": 1,
                "precio_venta": 1, "precio": 1, "marca": 1, "cantidad": 1,
                "lotes": 1, "farmacia": 1, "costo": 1, "estado": 1, 
                "productoId": 1, "categoria": 1, "proveedor": 1
            }
        ).sort("nombre", 1).limit(500).to_list(length=500)
        
        # Si no se encontró nada, intentar buscar por cualquier campo que contenga el ID
        if len(inventarios) == 0:
            # Buscar en todos los campos posibles
            inventarios = await collection.find(
                {
                    "$or": [
                        {"farmacia": id},
                        {"_id": id},
                        {"productoId": id}
                    ]
                },
                projection={
                    "_id": 1, "codigo": 1, "nombre": 1, "descripcion": 1,
                    "precio_venta": 1, "precio": 1, "marca": 1, "cantidad": 1,
                    "lotes": 1, "farmacia": 1, "costo": 1, "estado": 1, 
                    "productoId": 1, "categoria": 1, "proveedor": 1
                }
            ).limit(500).to_list(length=500)
        
        # Convertir _id a string
        for inv in inventarios:
            inv["_id"] = str(inv["_id"])
            if "productoId" in inv and isinstance(inv["productoId"], ObjectId):
                inv["productoId"] = str(inv["productoId"])
        
        return inventarios
    except Exception as e:
        print(f"❌ Error obteniendo items de inventario: {e}")
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

@router.put("/inventarios/{id}/items/{item_id}")
async def actualizar_item_inventario(
    id: str,
    item_id: str,
    data: dict = Body(...),
    usuario: dict = Depends(get_current_user)
):
    """
    Actualiza un item de inventario.
    El {id} es el ID de la farmacia o inventario padre.
    El {item_id} es el ID del item a actualizar.
    """
    try:
        print(f"✏️ [INVENTARIOS] Actualizando item: {item_id} de inventario: {id}")
        collection = get_collection("INVENTARIOS")
        
        # El item_id puede venir en formato "id_codigo" o solo "id"
        item_id_real = item_id.split("_")[0] if "_" in item_id else item_id
        
        try:
            item_object_id = ObjectId(item_id_real)
        except (InvalidId, ValueError):
            # Si no es ObjectId válido, intentar buscar por código
            if "_" in item_id:
                codigo = "_".join(item_id.split("_")[1:])
                filtro = {"codigo": codigo}
                if id and id.strip():
                    filtro["farmacia"] = id.strip()
            else:
                filtro = {"codigo": item_id}
                if id and id.strip():
                    filtro["farmacia"] = id.strip()
            
            # Buscar el item
            item = await collection.find_one(filtro)
            if not item:
                raise HTTPException(status_code=404, detail="Item de inventario no encontrado")
            
            item_object_id = item["_id"]
        
        # No permitir actualizar el _id
        if "_id" in data:
            del data["_id"]
        
        # Agregar información de actualización
        data["usuarioActualizacion"] = usuario.get("correo", "unknown")
        data["fechaActualizacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        resultado = await collection.update_one(
            {"_id": item_object_id},
            {"$set": data}
        )
        
        if resultado.modified_count == 0:
            raise HTTPException(status_code=404, detail="Item de inventario no encontrado o sin cambios")
        
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
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [INVENTARIOS] Error actualizando item: {e}")
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

