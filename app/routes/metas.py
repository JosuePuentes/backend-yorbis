from pydantic import BaseModel
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Body, Depends, Query
from fastapi.responses import JSONResponse
from app.db.mongo import get_collection
from bson import ObjectId
from datetime import datetime

router = APIRouter()

class Meta(BaseModel):
    _id: Optional[str] = None
    nombre: str
    descripcion: Optional[str] = None
    fechaInicio: str
    fechaFin: str
    monto: float
    farmaciaId: Optional[str] = None
    usuario: Optional[str] = None
    cumplida: Optional[bool] = False

def meta_to_dict(meta):
    d = dict(meta)
    if '_id' in d and isinstance(d['_id'], ObjectId):
        d['_id'] = str(d['_id'])
    return d

# Crear meta
@router.post("/metas")
async def crear_meta(meta: Meta):
    try:
        collection = get_collection("metas")
        meta_dict = meta.dict()
        meta_dict["fechaRegistro"] = datetime.now().strftime("%Y-%m-%d")
        result = await collection.insert_one(meta_dict)
        return {"message": "Meta registrada exitosamente", "id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Listar metas (por farmacia opcional)
@router.get("/metas")
async def listar_metas(farmaciaId: Optional[str] = Query(None)):
    try:
        collection = get_collection("metas")
        query = {"farmaciaId": farmaciaId} if farmaciaId else {}
        metas = await collection.find(query).to_list(length=100)
        metas = [meta_to_dict(m) for m in metas]
        return metas
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Actualizar meta
@router.patch("/metas/{meta_id}")
async def actualizar_meta(meta_id: str, meta: Meta):
    try:
        collection = get_collection("metas")
        meta_dict = meta.dict(exclude_unset=True)
        result = await collection.update_one({"_id": ObjectId(meta_id)}, {"$set": meta_dict})
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Meta no encontrada o sin cambios")
        return {"message": "Meta actualizada correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Eliminar meta
@router.delete("/metas/{meta_id}")
async def eliminar_meta(meta_id: str):
    try:
        collection = get_collection("metas")
        result = await collection.delete_one({"_id": ObjectId(meta_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Meta no encontrada")
        return {"message": "Meta eliminada correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

