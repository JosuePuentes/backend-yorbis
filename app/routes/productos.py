"""
Rutas para gestión de productos
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from app.db.mongo import get_collection
from app.core.get_current_user import get_current_user
from typing import Optional
from bson import ObjectId
from bson.errors import InvalidId
import re

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
        
        # OPTIMIZACIÓN: Usar proyección para reducir transferencia de datos
        # Obtener inventarios (que son los productos) con límite razonable
        productos = await inventarios_collection.find(
            filtro,
            projection={
                "_id": 1, "codigo": 1, "nombre": 1, "descripcion": 1,
                "precio_venta": 1, "precio": 1, "marca": 1, "cantidad": 1,
                "lotes": 1, "farmacia": 1, "costo": 1, "estado": 1, 
                "productoId": 1, "categoria": 1, "proveedor": 1
            }
        ).sort("nombre", 1).limit(500).to_list(length=500)
        
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

@router.get("/productos/buscar")
async def buscar_productos(
    q: str = Query(..., description="Término de búsqueda (código, nombre, descripción o marca)"),
    farmacia: Optional[str] = Query(None, description="ID de la sucursal (farmacia)"),
    limit: Optional[int] = Query(50, description="Límite de resultados (máximo 100)"),
    usuario_actual: dict = Depends(get_current_user)
):
    """
    Busca productos en el inventario (OPTIMIZADO).
    Busca en código, nombre, descripción y marca.
    Búsqueda case-insensitive y coincidencia parcial.
    
    Optimizaciones aplicadas:
    - Búsqueda exacta por código primero (muy rápida con índice)
    - Uso de índices de MongoDB para búsquedas rápidas
    - Proyección de campos para reducir transferencia de datos
    - Límite de resultados configurable
    
    Requiere autenticación.
    """
    try:
        query_term = q.strip() if q and q.strip() else ""
        if not query_term:
            return []
        
        # Limitar el límite a máximo 100
        limit = min(limit or 50, 100)
        
        print(f"🔍 [PRODUCTOS] Buscando: '{query_term}' en sucursal: {farmacia}")
        
        inventarios_collection = get_collection("INVENTARIOS")
        
        # Construir filtro base
        filtro = {}
        
        # Filtrar por sucursal si se especifica
        if farmacia and farmacia.strip():
            filtro["farmacia"] = farmacia.strip()
        
        # OPTIMIZACIÓN: Búsqueda exacta por código primero (más rápida)
        codigo_filtro = {**filtro, "codigo": query_term.upper()}
        producto_exacto = await inventarios_collection.find_one(
            codigo_filtro,
            projection={
                "_id": 1, "codigo": 1, "nombre": 1, "descripcion": 1,
                "precio_venta": 1, "precio": 1, "marca": 1, "cantidad": 1,
                "lotes": 1, "farmacia": 1, "costo": 1, "estado": 1, "productoId": 1
            }
        )
        
        if producto_exacto:
            producto_exacto["_id"] = str(producto_exacto["_id"])
            if "productoId" in producto_exacto and isinstance(producto_exacto["productoId"], ObjectId):
                producto_exacto["productoId"] = str(producto_exacto["productoId"])
            print(f"🔍 [PRODUCTOS] Coincidencia exacta encontrada")
            return [producto_exacto]
        
        # Búsqueda con regex optimizado (usa índices)
        escaped_query = re.escape(query_term)
        match_stage = {
            **filtro,
            "$or": [
                {"codigo": {"$regex": f"^{escaped_query}", "$options": "i"}},  # Coincidencia al inicio
                {"nombre": {"$regex": f"^{escaped_query}", "$options": "i"}},  # Coincidencia al inicio
                {"codigo": {"$regex": escaped_query, "$options": "i"}},  # Coincidencia parcial
                {"nombre": {"$regex": escaped_query, "$options": "i"}},  # Coincidencia parcial
                {"descripcion": {"$regex": escaped_query, "$options": "i"}},
                {"marca": {"$regex": escaped_query, "$options": "i"}}
            ]
        }
        
        # Usar find() con proyección (más rápido)
        productos = await inventarios_collection.find(
            match_stage,
            projection={
                "_id": 1, "codigo": 1, "nombre": 1, "descripcion": 1,
                "precio_venta": 1, "precio": 1, "marca": 1, "cantidad": 1,
                "lotes": 1, "farmacia": 1, "costo": 1, "estado": 1, "productoId": 1
            }
        ).sort("nombre", 1).limit(limit).to_list(length=limit)
        
        # Convertir _id a string
        for producto in productos:
            producto["_id"] = str(producto["_id"])
            if "productoId" in producto and isinstance(producto["productoId"], ObjectId):
                producto["productoId"] = str(producto["productoId"])
        
        print(f"🔍 [PRODUCTOS] Encontrados {len(productos)} productos")
        return productos
            
    except Exception as e:
        print(f"❌ [PRODUCTOS] Error buscando productos: {e}")
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
    Busca si un código existe en el inventario (OPTIMIZADO).
    Retorna el producto si existe, o array vacío si no existe.
    Usa índice en código para búsqueda rápida.
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
        
        # OPTIMIZACIÓN: Usar proyección para búsqueda más rápida
        producto = await inventarios_collection.find_one(
            filtro,
            projection={
                "_id": 1, "codigo": 1, "nombre": 1, "descripcion": 1,
                "precio_venta": 1, "precio": 1, "marca": 1, "cantidad": 1,
                "lotes": 1, "farmacia": 1, "costo": 1, "estado": 1, "productoId": 1
            }
        )
        
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

