"""
Rutas para gestión de proveedores
"""
from fastapi import APIRouter, HTTPException, Body, Query, Depends
from app.db.mongo import get_collection
from app.core.get_current_user import get_current_user
from typing import List, Optional
from bson import ObjectId
from bson.errors import InvalidId

router = APIRouter()

@router.get("/proveedores")
async def obtener_proveedores(usuario_actual: dict = Depends(get_current_user)):
    """
    Obtiene todos los proveedores.
    Requiere autenticación.
    """
    try:
        collection = get_collection("PROVEEDORES")
        proveedores = await collection.find({}).to_list(length=None)
        
        # Convertir _id a string
        for proveedor in proveedores:
            proveedor["_id"] = str(proveedor["_id"])
        
        return proveedores
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/proveedores")
async def crear_proveedor(proveedor: dict = Body(...), usuario_actual: dict = Depends(get_current_user)):
    """
    Crea un nuevo proveedor.
    Requiere autenticación.
    """
    try:
        collection = get_collection("PROVEEDORES")
        
        # Validar campos requeridos
        if "nombre" not in proveedor or not proveedor["nombre"]:
            raise HTTPException(status_code=400, detail="El campo 'nombre' es requerido")
        
        # Agregar información del usuario que crea
        proveedor["usuarioCreacion"] = usuario_actual.get("correo", "unknown")
        
        resultado = await collection.insert_one(proveedor)
        proveedor["_id"] = str(resultado.inserted_id)
        
        return {
            "message": "Proveedor creado exitosamente",
            "id": str(resultado.inserted_id),
            "proveedor": proveedor
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/proveedores/{proveedor_id}")
async def obtener_proveedor(proveedor_id: str, usuario_actual: dict = Depends(get_current_user)):
    """
    Obtiene un proveedor por su ID.
    Requiere autenticación.
    """
    try:
        try:
            object_id = ObjectId(proveedor_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="ID de proveedor inválido")
        
        collection = get_collection("PROVEEDORES")
        proveedor = await collection.find_one({"_id": object_id})
        
        if not proveedor:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
        proveedor["_id"] = str(proveedor["_id"])
        return proveedor
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/proveedores/{proveedor_id}")
async def actualizar_proveedor(proveedor_id: str, proveedor: dict = Body(...), usuario_actual: dict = Depends(get_current_user)):
    """
    Actualiza un proveedor existente.
    Requiere autenticación.
    """
    try:
        try:
            object_id = ObjectId(proveedor_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="ID de proveedor inválido")
        
        collection = get_collection("PROVEEDORES")
        
        # Verificar que el proveedor existe
        proveedor_existente = await collection.find_one({"_id": object_id})
        if not proveedor_existente:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
        # No permitir actualizar el _id
        if "_id" in proveedor:
            del proveedor["_id"]
        
        # Agregar información de actualización
        proveedor["usuarioActualizacion"] = usuario_actual.get("correo", "unknown")
        
        resultado = await collection.update_one(
            {"_id": object_id},
            {"$set": proveedor}
        )
        
        if resultado.modified_count == 0:
            raise HTTPException(status_code=400, detail="No se pudo actualizar el proveedor")
        
        # Obtener el proveedor actualizado
        proveedor_actualizado = await collection.find_one({"_id": object_id})
        proveedor_actualizado["_id"] = str(proveedor_actualizado["_id"])
        
        return {
            "message": "Proveedor actualizado exitosamente",
            "proveedor": proveedor_actualizado
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/proveedores/{proveedor_id}")
async def eliminar_proveedor(proveedor_id: str, usuario_actual: dict = Depends(get_current_user)):
    """
    Elimina un proveedor.
    Requiere autenticación.
    """
    try:
        try:
            object_id = ObjectId(proveedor_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="ID de proveedor inválido")
        
        collection = get_collection("PROVEEDORES")
        
        # Verificar que el proveedor existe
        proveedor = await collection.find_one({"_id": object_id})
        if not proveedor:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
        resultado = await collection.delete_one({"_id": object_id})
        
        if resultado.deleted_count == 0:
            raise HTTPException(status_code=400, detail="No se pudo eliminar el proveedor")
        
        return {
            "message": "Proveedor eliminado exitosamente",
            "id": proveedor_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

