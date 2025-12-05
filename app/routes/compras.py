"""
Rutas para gestión de compras
Cuando se crea una compra, los productos se suman automáticamente al inventario
"""
from fastapi import APIRouter, HTTPException, Body, Query, Depends
from app.db.mongo import get_collection
from app.core.get_current_user import get_current_user
from typing import List, Optional, Dict, Any
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime
import pytz
from pydantic import BaseModel

router = APIRouter()

class ProductoCompra(BaseModel):
    """Modelo para un producto en una compra"""
    productoId: Optional[str] = None
    nombre: str
    cantidad: float
    precioUnitario: float
    precioTotal: float
    codigo: Optional[str] = None

class Compra(BaseModel):
    """Modelo para una compra"""
    proveedorId: str
    proveedorNombre: Optional[str] = None
    fecha: str
    productos: List[ProductoCompra]
    total: float
    farmacia: str
    observaciones: Optional[str] = None
    numeroFactura: Optional[str] = None

async def actualizar_inventario(producto_data: dict, farmacia: str, usuario_correo: str):
    """
    Actualiza el inventario sumando los productos de la compra.
    Si el producto existe, suma la cantidad. Si no existe, lo crea.
    Acepta un dict directamente para mayor flexibilidad.
    """
    try:
        inventarios_collection = get_collection("INVENTARIOS")
        
        # Extraer datos del producto (acepta dict directamente)
        nombre = producto_data.get("nombre", "")
        cantidad = float(producto_data.get("cantidad", 0))
        precio_unitario = float(producto_data.get("precioUnitario", 0))
        precio_total = float(producto_data.get("precioTotal", 0))
        codigo = producto_data.get("codigo")
        producto_id = producto_data.get("productoId")
        
        if not nombre:
            raise ValueError("El producto debe tener un nombre")
        
        # Buscar si ya existe un inventario para este producto en esta farmacia
        # Buscar por código si existe, o por nombre
        filtro = {"farmacia": farmacia}
        
        if codigo:
            filtro["codigo"] = codigo
        else:
            filtro["nombre"] = nombre
        
        inventario_existente = await inventarios_collection.find_one(filtro)
        
        venezuela_tz = pytz.timezone("America/Caracas")
        now_ve = datetime.now(venezuela_tz)
        fecha_actual = now_ve.strftime("%Y-%m-%d")
        
        if inventario_existente:
            # Producto existe: sumar cantidad y actualizar costo promedio
            cantidad_actual = float(inventario_existente.get("cantidad", 0))
            costo_actual = float(inventario_existente.get("costo", 0))
            cantidad_nueva = cantidad_actual + cantidad
            
            # Calcular nuevo costo promedio ponderado
            if cantidad_actual > 0:
                costo_total_actual = cantidad_actual * costo_actual
                costo_total_nuevo = precio_total
                costo_promedio = (costo_total_actual + costo_total_nuevo) / cantidad_nueva
            else:
                costo_promedio = precio_unitario
            
            # Actualizar inventario
            await inventarios_collection.update_one(
                {"_id": inventario_existente["_id"]},
                {
                    "$set": {
                        "cantidad": cantidad_nueva,
                        "costo": costo_promedio,
                        "fechaActualizacion": fecha_actual,
                        "usuarioActualizacion": usuario_correo
                    }
                }
            )
            print(f"✅ Inventario actualizado: {nombre} - Cantidad: {cantidad_actual} + {cantidad} = {cantidad_nueva}")
        else:
            # Producto no existe: crear nuevo registro de inventario
            nuevo_inventario = {
                "farmacia": farmacia,
                "nombre": nombre,
                "cantidad": cantidad,
                "costo": precio_unitario,
                "usuarioCorreo": usuario_correo,
                "fecha": fecha_actual,
                "estado": "activo"
            }
            
            if codigo:
                nuevo_inventario["codigo"] = codigo
            
            if producto_id:
                nuevo_inventario["productoId"] = producto_id
            
            await inventarios_collection.insert_one(nuevo_inventario)
            print(f"✅ Nuevo producto agregado al inventario: {nombre} - Cantidad: {cantidad}")
        
        return True
    except Exception as e:
        nombre_producto = producto_data.get("nombre", "Desconocido") if isinstance(producto_data, dict) else "Desconocido"
        print(f"❌ Error actualizando inventario para {nombre_producto}: {e}")
        import traceback
        traceback.print_exc()
        raise

@router.get("/compras")
async def obtener_compras(
    farmacia: Optional[str] = Query(None),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    usuario_actual: dict = Depends(get_current_user)
):
    """
    Obtiene todas las compras.
    Puede filtrar por farmacia y rango de fechas.
    Requiere autenticación.
    """
    try:
        collection = get_collection("COMPRAS")
        filtro = {}
        
        if farmacia:
            filtro["farmacia"] = farmacia
        
        if fecha_inicio and fecha_fin:
            filtro["fecha"] = {"$gte": fecha_inicio, "$lte": fecha_fin}
        elif fecha_inicio:
            filtro["fecha"] = {"$gte": fecha_inicio}
        elif fecha_fin:
            filtro["fecha"] = {"$lte": fecha_fin}
        
        compras = await collection.find(filtro).sort("fecha", -1).to_list(length=None)
        
        # Convertir _id a string
        for compra in compras:
            compra["_id"] = str(compra["_id"])
            if "proveedorId" in compra and isinstance(compra["proveedorId"], ObjectId):
                compra["proveedorId"] = str(compra["proveedorId"])
        
        return compras
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/compras")
async def crear_compra(compra_data: dict = Body(...), usuario_actual: dict = Depends(get_current_user)):
    """
    Crea una nueva compra.
    IMPORTANTE: Al crear una compra, los productos se suman automáticamente al inventario.
    Requiere autenticación.
    """
    try:
        print(f"[COMPRAS] Datos recibidos: {compra_data}")
        
        collection = get_collection("COMPRAS")
        usuario_correo = usuario_actual.get("correo", "unknown")
        
        # Validar campos requeridos
        if "productos" not in compra_data:
            raise HTTPException(status_code=400, detail="El campo 'productos' es requerido")
        
        if not compra_data["productos"] or len(compra_data["productos"]) == 0:
            raise HTTPException(status_code=400, detail="La compra debe tener al menos un producto")
        
        if "farmacia" not in compra_data:
            raise HTTPException(status_code=400, detail="El campo 'farmacia' es requerido")
        
        if "proveedorId" not in compra_data:
            raise HTTPException(status_code=400, detail="El campo 'proveedorId' es requerido")
        
        # Validar estructura de productos
        for i, producto in enumerate(compra_data["productos"]):
            if not isinstance(producto, dict):
                raise HTTPException(status_code=400, detail=f"El producto en la posición {i} debe ser un objeto")
            
            if "nombre" not in producto:
                raise HTTPException(status_code=400, detail=f"El producto en la posición {i} debe tener el campo 'nombre'")
            
            if "cantidad" not in producto:
                raise HTTPException(status_code=400, detail=f"El producto en la posición {i} debe tener el campo 'cantidad'")
            
            if "precioUnitario" not in producto:
                raise HTTPException(status_code=400, detail=f"El producto en la posición {i} debe tener el campo 'precioUnitario'")
            
            if "precioTotal" not in producto:
                raise HTTPException(status_code=400, detail=f"El producto en la posición {i} debe tener el campo 'precioTotal'")
        
        # Crear el documento de compra
        compra_dict = compra_data.copy()
        compra_dict["usuarioCreacion"] = usuario_correo
        compra_dict["fechaCreacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Convertir proveedorId a ObjectId si es necesario
        if compra_dict.get("proveedorId"):
            try:
                compra_dict["proveedorId"] = ObjectId(compra_dict["proveedorId"])
            except:
                # Si no es un ObjectId válido, dejarlo como string
                pass
        
        # Insertar la compra
        resultado = await collection.insert_one(compra_dict)
        compra_id = str(resultado.inserted_id)
        
        # ACTUALIZAR INVENTARIO: Sumar cada producto al inventario
        print(f"\n🔄 Actualizando inventario para compra {compra_id}...")
        productos_actualizados = []
        productos_con_error = []
        
        farmacia = compra_dict["farmacia"]
        productos = compra_dict["productos"]
        
        for producto_data in productos:
            try:
                # Asegurar que producto_data es un dict
                if not isinstance(producto_data, dict):
                    raise ValueError(f"El producto debe ser un objeto/dict, recibido: {type(producto_data)}")
                
                # Validar campos mínimos requeridos
                if "nombre" not in producto_data:
                    raise ValueError("El producto debe tener el campo 'nombre'")
                if "cantidad" not in producto_data:
                    raise ValueError("El producto debe tener el campo 'cantidad'")
                if "precioUnitario" not in producto_data:
                    raise ValueError("El producto debe tener el campo 'precioUnitario'")
                if "precioTotal" not in producto_data:
                    raise ValueError("El producto debe tener el campo 'precioTotal'")
                
                # Actualizar inventario directamente con el dict
                await actualizar_inventario(producto_data, farmacia, usuario_correo)
                nombre_producto = producto_data.get('nombre', 'Desconocido')
                productos_actualizados.append(nombre_producto)
            except Exception as e:
                print(f"❌ Error actualizando producto: {e}")
                import traceback
                traceback.print_exc()
                nombre_producto = producto_data.get('nombre', 'Desconocido') if isinstance(producto_data, dict) else 'Desconocido'
                productos_con_error.append(f"{nombre_producto} ({str(e)})")
        
        # Respuesta
        respuesta = {
            "message": "Compra creada exitosamente",
            "id": compra_id,
            "compra": compra_dict,
            "inventario_actualizado": {
                "productos_actualizados": len(productos_actualizados),
                "productos_con_error": len(productos_con_error),
                "detalle": {
                    "exitosos": productos_actualizados,
                    "errores": productos_con_error
                }
            }
        }
        
        if productos_con_error:
            respuesta["warning"] = f"Algunos productos no se pudieron actualizar en el inventario: {', '.join(productos_con_error)}"
        
        print(f"✅ Compra creada: {compra_id} - {len(productos_actualizados)} productos actualizados en inventario")
        
        return respuesta
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error creando compra: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/compras/{compra_id}")
async def obtener_compra(compra_id: str, usuario_actual: dict = Depends(get_current_user)):
    """
    Obtiene una compra por su ID.
    Requiere autenticación.
    """
    try:
        try:
            object_id = ObjectId(compra_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="ID de compra inválido")
        
        collection = get_collection("COMPRAS")
        compra = await collection.find_one({"_id": object_id})
        
        if not compra:
            raise HTTPException(status_code=404, detail="Compra no encontrada")
        
        compra["_id"] = str(compra["_id"])
        if "proveedorId" in compra and isinstance(compra["proveedorId"], ObjectId):
            compra["proveedorId"] = str(compra["proveedorId"])
        
        return compra
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/compras/{compra_id}")
async def actualizar_compra(compra_id: str, compra: dict = Body(...), usuario_actual: dict = Depends(get_current_user)):
    """
    Actualiza una compra existente.
    NOTA: Si se actualizan productos, el inventario NO se actualiza automáticamente.
    Requiere autenticación.
    """
    try:
        try:
            object_id = ObjectId(compra_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="ID de compra inválido")
        
        collection = get_collection("COMPRAS")
        
        # Verificar que la compra existe
        compra_existente = await collection.find_one({"_id": object_id})
        if not compra_existente:
            raise HTTPException(status_code=404, detail="Compra no encontrada")
        
        # No permitir actualizar el _id
        if "_id" in compra:
            del compra["_id"]
        
        # Agregar información de actualización
        compra["usuarioActualizacion"] = usuario_actual.get("correo", "unknown")
        compra["fechaActualizacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        resultado = await collection.update_one(
            {"_id": object_id},
            {"$set": compra}
        )
        
        if resultado.modified_count == 0:
            raise HTTPException(status_code=400, detail="No se pudo actualizar la compra")
        
        # Obtener la compra actualizada
        compra_actualizada = await collection.find_one({"_id": object_id})
        compra_actualizada["_id"] = str(compra_actualizada["_id"])
        
        return {
            "message": "Compra actualizada exitosamente",
            "compra": compra_actualizada
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/compras/{compra_id}")
async def eliminar_compra(compra_id: str, usuario_actual: dict = Depends(get_current_user)):
    """
    Elimina una compra.
    NOTA: Al eliminar una compra, el inventario NO se actualiza automáticamente.
    Requiere autenticación.
    """
    try:
        try:
            object_id = ObjectId(compra_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="ID de compra inválido")
        
        collection = get_collection("COMPRAS")
        
        # Verificar que la compra existe
        compra = await collection.find_one({"_id": object_id})
        if not compra:
            raise HTTPException(status_code=404, detail="Compra no encontrada")
        
        resultado = await collection.delete_one({"_id": object_id})
        
        if resultado.deleted_count == 0:
            raise HTTPException(status_code=400, detail="No se pudo eliminar la compra")
        
        return {
            "message": "Compra eliminada exitosamente",
            "id": compra_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

