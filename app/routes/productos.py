"""
Rutas para gestión de productos
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from app.db.mongo import get_collection
from app.core.get_current_user import get_current_user
from typing import Optional
from bson import ObjectId
from bson.errors import InvalidId

router = APIRouter()

@router.get("/productos")
async def obtener_productos(
    inventario_id: Optional[str] = Query(None),
    farmacia: Optional[str] = Query(None),
    usuario_actual: dict = Depends(get_current_user)
):
    """
    Obtiene productos.
    Puede filtrar por inventario_id o farmacia.
    Si no se especifica filtro, retorna todos los productos del inventario.
    Requiere autenticación.
    """
    try:
        print(f"🔍 [PRODUCTOS] Obteniendo productos - inventario_id: {inventario_id}, farmacia: {farmacia}")
        
        inventarios_collection = get_collection("INVENTARIOS")
        filtro = {}
        
        # Si se especifica inventario_id, buscar ese inventario específico
        if inventario_id and inventario_id.strip():
            try:
                object_id = ObjectId(inventario_id)
                inventario = await inventarios_collection.find_one({"_id": object_id})
                if inventario:
                    inventario["_id"] = str(inventario["_id"])
                    if "productoId" in inventario and isinstance(inventario["productoId"], ObjectId):
                        inventario["productoId"] = str(inventario["productoId"])
                    return [inventario]
                else:
                    return []
            except (InvalidId, ValueError):
                # Si no es ObjectId válido, buscar por otros campos
                pass
        
        # Filtrar por farmacia si se especifica
        if farmacia and farmacia.strip():
            filtro["farmacia"] = farmacia
        
        # Si hay inventario_id pero no es ObjectId válido, buscar por productoId
        if inventario_id and inventario_id.strip():
            filtro["productoId"] = inventario_id
        
        # Obtener inventarios (que son los productos)
        productos = await inventarios_collection.find(filtro).to_list(length=None)
        
        # Convertir _id a string
        for producto in productos:
            producto["_id"] = str(producto["_id"])
            if "productoId" in producto and isinstance(producto["productoId"], ObjectId):
                producto["productoId"] = str(producto["productoId"])
        
        print(f"🔍 [PRODUCTOS] Encontrados {len(productos)} productos")
        return productos
    except Exception as e:
        print(f"❌ [PRODUCTOS] Error obteniendo productos: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/productos/buscar-codigo")
async def buscar_codigo_producto(
    codigo: str = Query(..., description="Código del producto a buscar"),
    sucursal: Optional[str] = Query(None, description="ID de la sucursal (farmacia)"),
    usuario_actual: dict = Depends(get_current_user)
):
    """
    Busca si un código existe en el inventario.
    Retorna el producto si existe, o array vacío si no existe.
    Requiere autenticación.
    """
    try:
        print(f"🔍 [PRODUCTOS] Buscando código: '{codigo}' en sucursal: {sucursal}")
        
        inventarios_collection = get_collection("INVENTARIOS")
        
        # Construir filtro
        filtro = {"codigo": codigo.strip().upper()}
        
        # Filtrar por sucursal si se especifica
        if sucursal and sucursal.strip():
            filtro["farmacia"] = sucursal.strip()
        
        # Buscar producto
        producto = await inventarios_collection.find_one(filtro)
        
        if producto:
            producto["_id"] = str(producto["_id"])
            if "productoId" in producto and isinstance(producto["productoId"], ObjectId):
                producto["productoId"] = str(producto["productoId"])
            print(f"🔍 [PRODUCTOS] Código '{codigo}' encontrado")
            return [producto]
        else:
            print(f"🔍 [PRODUCTOS] Código '{codigo}' no encontrado")
            return []
            
    except Exception as e:
        print(f"❌ [PRODUCTOS] Error buscando código: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/productos/{producto_id}")
async def obtener_producto(producto_id: str, usuario_actual: dict = Depends(get_current_user)):
    """
    Obtiene un producto específico por su ID.
    Requiere autenticación.
    """
    try:
        inventarios_collection = get_collection("INVENTARIOS")
        
        try:
            object_id = ObjectId(producto_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="ID de producto inválido")
        
        producto = await inventarios_collection.find_one({"_id": object_id})
        
        if not producto:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        
        producto["_id"] = str(producto["_id"])
        if "productoId" in producto and isinstance(producto["productoId"], ObjectId):
            producto["productoId"] = str(producto["productoId"])
        
        return producto
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

