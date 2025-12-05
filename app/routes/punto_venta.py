"""
Rutas para punto de venta
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from app.db.mongo import get_collection
from app.core.get_current_user import get_current_user
from typing import Optional, List, Dict, Any
from bson import ObjectId
from bson.errors import InvalidId
import re

router = APIRouter()

@router.get("/punto-venta/productos/buscar")
async def buscar_productos_punto_venta(
    q: str = Query(..., description="Término de búsqueda"),
    sucursal: Optional[str] = Query(None, description="ID de la sucursal (farmacia)"),
    usuario_actual: dict = Depends(get_current_user)
):
    """
    Busca productos para el punto de venta.
    Busca en código, nombre/descripción y marca.
    Búsqueda case-insensitive y coincidencia parcial.
    
    Campos requeridos en respuesta:
    - id: ID del producto
    - codigo: Código del producto
    - nombre/descripcion: Nombre o descripción
    - precio: Precio de venta
    
    Campos opcionales:
    - marca: Marca del producto
    - cantidad/stock: Stock disponible
    - lotes: Información de lotes
    - sucursal: ID de la sucursal
    """
    try:
        print(f"🔍 [PUNTO_VENTA] Búsqueda: '{q}' en sucursal: {sucursal}")
        
        inventarios_collection = get_collection("INVENTARIOS")
        
        # Construir filtro de búsqueda
        filtro = {}
        
        # Filtrar por sucursal si se especifica
        if sucursal and sucursal.strip():
            filtro["farmacia"] = sucursal.strip()
        
        # Solo productos activos
        filtro["estado"] = {"$ne": "inactivo"}
        
        # Construir búsqueda en código, nombre y marca (case-insensitive, coincidencia parcial)
        if q and q.strip():
            query_term = q.strip()
            # Escapar caracteres especiales de regex
            escaped_query = re.escape(query_term)
            # Crear regex para búsqueda case-insensitive
            regex_pattern = re.compile(escaped_query, re.IGNORECASE)
            
            filtro["$or"] = [
                {"codigo": regex_pattern},
                {"nombre": regex_pattern},
                {"descripcion": regex_pattern},
                {"marca": regex_pattern}
            ]
        else:
            # Si no hay término de búsqueda, retornar todos los productos de la sucursal
            pass
        
        # Buscar productos
        productos = await inventarios_collection.find(filtro).to_list(length=100)  # Limitar a 100 resultados
        
        print(f"🔍 [PUNTO_VENTA] Encontrados {len(productos)} productos")
        
        # Normalizar y formatear respuesta
        resultados = []
        for producto in productos:
            # Convertir _id a string
            producto_id = str(producto.get("_id", ""))
            
            # Obtener campos requeridos
            codigo = producto.get("codigo", "")
            nombre = producto.get("nombre", "")
            descripcion = producto.get("descripcion", nombre)  # Usar descripcion si existe, sino nombre
            precio = float(producto.get("precio_venta", producto.get("precio", 0)))
            
            # Obtener campos opcionales
            marca = producto.get("marca", "")
            cantidad = float(producto.get("cantidad", 0))
            stock = cantidad  # Alias para compatibilidad
            lotes = producto.get("lotes", [])
            sucursal_id = producto.get("farmacia", sucursal or "")
            
            # Construir objeto de respuesta normalizado
            resultado = {
                # Campos requeridos
                "id": producto_id,
                "codigo": codigo,
                "nombre": nombre,
                "descripcion": descripcion,
                "precio": precio,
                
                # Campos opcionales
                "marca": marca if marca else None,
                "cantidad": cantidad,
                "stock": stock,
                "lotes": lotes if lotes else [],
                "sucursal": sucursal_id,
                
                # Campos adicionales para compatibilidad
                "precio_venta": precio,
                "costo": float(producto.get("costo", 0)),
                "estado": producto.get("estado", "activo"),
                "productoId": str(producto.get("productoId", "")) if producto.get("productoId") else None
            }
            
            # Remover campos None para limpiar la respuesta
            resultado = {k: v for k, v in resultado.items() if v is not None or k in ["id", "codigo", "nombre", "descripcion", "precio"]}
            
            resultados.append(resultado)
        
        print(f"🔍 [PUNTO_VENTA] Retornando {len(resultados)} productos normalizados")
        return resultados
        
    except Exception as e:
        print(f"❌ [PUNTO_VENTA] Error buscando productos: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

