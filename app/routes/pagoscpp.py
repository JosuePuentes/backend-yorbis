from fastapi import APIRouter, HTTPException, Body, Depends, Query
from fastapi import Request
from datetime import datetime
from fastapi import Query
from fastapi.responses import JSONResponse
from dateutil.parser import parse as parse_date
from app.db.mongo import get_collection
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List
import pytz
from bson import ObjectId

router = APIRouter()

class ImagenCuentaPorPagar(BaseModel):
    url: str
    descripcion: Optional[str] = None

class PagoCPP(BaseModel):
    _id: Optional[str] = None
    fecha: str
    referencia: str
    usuario: str
    bancoEmisor: str
    bancoReceptor: str
    imagenPago: Optional[str] = None
    farmaciaId: str
    estado: str
    cuentaPorPagarId: str
    fechaEmision: Optional[str] = None
    fechaRecepcion: Optional[str] = None
    fechaVencimiento: Optional[str] = None
    fechaRegistro: Optional[str] = None
    diasCredito: Optional[int] = None
    numeroFactura: Optional[str] = None
    numeroControl: Optional[str] = None
    proveedor: Optional[str] = None
    descripcion: Optional[str] = None
    montoOriginal: Optional[float] = None
    retencion: Optional[float] = None
    monedaOriginal: Optional[str] = None
    tasaOriginal: Optional[float] = None
    tasaDePago: Optional[float] = None
    estatus: Optional[str] = None
    usuarioCorreoCuenta: Optional[str] = None
    imagenesCuentaPorPagar: Optional[List[ImagenCuentaPorPagar]] = None
    montoDePago: Optional[float] = None
    monedaDePago: Optional[str] = None
    abono: Optional[bool] = None
    horaRegistro: Optional[str] = None
    hora: Optional[str] = None  # ya estaba en tu modelo

class EstadoUpdate(BaseModel):
    estado: str

def pago_to_dict(pago):
    d = dict(pago)
    if '_id' in d and isinstance(d['_id'], ObjectId):
        d['_id'] = str(d['_id'])
    return d

@router.post("/pagoscpp")
async def crear_pago_cpp(pago: PagoCPP):
    try:
        venezuela_tz = pytz.timezone("America/Caracas")
        now_ve = datetime.now(venezuela_tz)
        pago_dict = pago.dict()
        pago_dict["fechaRegistro"] = now_ve.strftime("%Y-%m-%d")
        pago_dict["horaRegistro"] = now_ve.strftime("%H:%M:%S")
        collection = get_collection("PAGOSCPP")
        result = await collection.insert_one(pago_dict)
        return {"message": "Pago registrado exitosamente", "id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pagoscpp")
async def listar_pagos_cpp(cuentaPorPagarId: str = Query(...)):
    try:
        collection = get_collection("PAGOSCPP")
        pagos = await collection.find({"cuentaPorPagarId": cuentaPorPagarId}).to_list(length=100)
        pagos = [pago_to_dict(p) for p in pagos]
        return pagos
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/pagoscpp/{pago_id}/estado")
async def actualizar_estado_pago_cpp(pago_id: str, body: EstadoUpdate):
    try:
        collection = get_collection("PAGOSCPP")
        result = await collection.update_one(
            {"_id": ObjectId(pago_id)},
            {"$set": {"estado": body.estado}}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Pago no encontrado o estado sin cambios")
        return {"message": "Estado actualizado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pagoscpp/masivo")
async def crear_pagos_cpp_masivo(pagos: List[dict]):
    try:
        venezuela_tz = pytz.timezone("America/Caracas")
        now_ve = datetime.now(venezuela_tz)
        pagos_dicts = []
        collection = get_collection("PAGOSCPP")
        cuentas_collection = get_collection("CUENTAS_POR_PAGAR")
        for pago in pagos:
            # Compatibilidad: si solo viene _id, usarlo como cuentaPorPagarId
            if not pago.get("cuentaPorPagarId") and pago.get("_id"):
                pago["cuentaPorPagarId"] = str(pago["_id"])
            cuenta_id = pago.get("cuentaPorPagarId")
            # Eliminar campo _id del pago para evitar conflictos
            if "_id" in pago:
                del pago["_id"]
            # Si abono es True, forzar estado a 'abonada' en el pago y la cuenta
            if pago.get("abono") is True:
                pago["estado"] = "abonada"
                if cuenta_id:
                    await cuentas_collection.update_one({"_id": ObjectId(cuenta_id)}, {"$set": {"estatus": "abonada"}})
            else:
                pago["estado"] = "pagada"
                if cuenta_id:
                    await cuentas_collection.update_one({"_id": ObjectId(cuenta_id)}, {"$set": {"estatus": "pagada"}})
            pago["fechaRegistro"] = now_ve.strftime("%Y-%m-%d")
            pago["horaRegistro"] = now_ve.strftime("%H:%M:%S")
            pagos_dicts.append(pago)
        result = await collection.insert_many(pagos_dicts)
        return {"message": "Pagos masivos registrados exitosamente", "ids": [str(_id) for _id in result.inserted_ids]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pagoscpp/all")
async def listar_todos_los_pagos_cpp():
    try:
        collection = get_collection("PAGOSCPP")
        pagos = await collection.find({}).to_list(length=1000)
        pagos = [pago_to_dict(p) for p in pagos]
        return pagos
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pagoscpp/rango-fechas")
async def obtener_pagos_por_rango_fechas(
    fechaInicio: str = Query(..., description="Fecha de inicio en formato YYYY-MM-DD"),
    fechaFin: str = Query(..., description="Fecha de fin en formato YYYY-MM-DD")
):
    """
    Devuelve todos los pagos cuyo campo 'fecha' esté en el rango [fechaInicio, fechaFin] (ambos inclusive).
    """
    try:
        collection = get_collection("PAGOSCPP")
        # Validar formato de fecha
        try:
            fecha_inicio_dt = datetime.strptime(fechaInicio, "%Y-%m-%d")
            fecha_fin_dt = datetime.strptime(fechaFin, "%Y-%m-%d")
        except Exception:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD.")

        pagos = await collection.find({
            "fecha": {
                "$gte": fechaInicio,
                "$lte": fechaFin
            }
        }).to_list(length=1000)
        pagos = [pago_to_dict(p) for p in pagos]
        return pagos
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))