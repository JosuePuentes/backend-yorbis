"""
Rutas para gestión de clientes
"""
from fastapi import APIRouter, HTTPException, Body, Query, Depends
from app.db.mongo import get_collection
from app.core.get_current_user import get_current_user
from typing import Optional, List, Dict, Any
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime

router = APIRouter()

@router.post("/clientes")
async def crear_cliente(
    cliente_data: dict = Body(...),
    usuario_actual: dict = Depends(get_current_user)
):
    """
    Crea un nuevo cliente.
    Requiere autenticación.
    """
    try:
        print(f"👤 [CLIENTES] Creando cliente - Usuario: {usuario_actual.get('correo', 'unknown')}")
        
        clientes_collection = get_collection("CLIENTES")
        
        # Agregar información de creación
        cliente_dict = cliente_data.copy()
        cliente_dict["usuarioCreacion"] = usuario_actual.get("correo", "unknown")
        cliente_dict["fechaCreacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Insertar cliente
        resultado = await clientes_collection.insert_one(cliente_dict)
        cliente_id = str(resultado.inserted_id)
        
        # Convertir _id a string en la respuesta
        cliente_dict["_id"] = cliente_id
        
        print(f"✅ [CLIENTES] Cliente creado: {cliente_id}")
        
        return {
            "message": "Cliente creado exitosamente",
            "id": cliente_id,
            "cliente": cliente_dict
        }
        
    except Exception as e:
        print(f"❌ [CLIENTES] Error creando cliente: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clientes")
async def obtener_clientes(
    usuario_actual: dict = Depends(get_current_user)
):
    """
    Obtiene todos los clientes.
    Requiere autenticación.
    """
    try:
        print(f"📋 [CLIENTES] Obteniendo clientes")
        
        clientes_collection = get_collection("CLIENTES")
        clientes = await clientes_collection.find({}).to_list(length=None)
        
        # Convertir _id a string
        for cliente in clientes:
            cliente["_id"] = str(cliente["_id"])
        
        print(f"📋 [CLIENTES] Encontrados {len(clientes)} clientes")
        return clientes
        
    except Exception as e:
        print(f"❌ [CLIENTES] Error obteniendo clientes: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clientes/{cliente_id}")
async def obtener_cliente(
    cliente_id: str,
    usuario_actual: dict = Depends(get_current_user)
):
    """
    Obtiene un cliente específico por su ID.
    Requiere autenticación.
    """
    try:
        try:
            object_id = ObjectId(cliente_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="ID de cliente inválido")
        
        clientes_collection = get_collection("CLIENTES")
        cliente = await clientes_collection.find_one({"_id": object_id})
        
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
        cliente["_id"] = str(cliente["_id"])
        return cliente
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/clientes/{cliente_id}")
async def actualizar_cliente(
    cliente_id: str,
    cliente_data: dict = Body(...),
    usuario_actual: dict = Depends(get_current_user)
):
    """
    Actualiza un cliente existente.
    Requiere autenticación.
    """
    try:
        try:
            object_id = ObjectId(cliente_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="ID de cliente inválido")
        
        clientes_collection = get_collection("CLIENTES")
        
        # Verificar que el cliente existe
        cliente_existente = await clientes_collection.find_one({"_id": object_id})
        if not cliente_existente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
        # No permitir actualizar el _id
        if "_id" in cliente_data:
            del cliente_data["_id"]
        
        # Agregar información de actualización
        cliente_data["usuarioActualizacion"] = usuario_actual.get("correo", "unknown")
        cliente_data["fechaActualizacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Actualizar cliente
        resultado = await clientes_collection.update_one(
            {"_id": object_id},
            {"$set": cliente_data}
        )
        
        if resultado.modified_count == 0:
            raise HTTPException(status_code=400, detail="No se pudo actualizar el cliente")
        
        # Obtener el cliente actualizado
        cliente_actualizado = await clientes_collection.find_one({"_id": object_id})
        cliente_actualizado["_id"] = str(cliente_actualizado["_id"])
        
        return {
            "message": "Cliente actualizado exitosamente",
            "cliente": cliente_actualizado
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/clientes/{cliente_id}")
async def eliminar_cliente(
    cliente_id: str,
    usuario_actual: dict = Depends(get_current_user)
):
    """
    Elimina un cliente.
    Requiere autenticación.
    """
    try:
        try:
            object_id = ObjectId(cliente_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="ID de cliente inválido")
        
        clientes_collection = get_collection("CLIENTES")
        
        # Verificar que el cliente existe
        cliente = await clientes_collection.find_one({"_id": object_id})
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
        # Eliminar cliente
        resultado = await clientes_collection.delete_one({"_id": object_id})
        
        if resultado.deleted_count == 0:
            raise HTTPException(status_code=400, detail="No se pudo eliminar el cliente")
        
        return {
            "message": "Cliente eliminado exitosamente",
            "id": cliente_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

