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
        marca = producto_data.get("marca") or producto_data.get("marca_producto") or ""
        
        # Obtener precio_venta si existe, sino usar precio_unitario como fallback
        precio_venta = producto_data.get("precio_venta")
        if precio_venta is None:
            precio_venta = producto_data.get("precioVenta")
        if precio_venta is None:
            # Si no hay precio_venta explícito, usar precio_unitario como referencia
            precio_venta = precio_unitario
        
        # Convertir a float si es necesario
        if precio_venta is not None:
            precio_venta = float(precio_venta)
        else:
            precio_venta = precio_unitario
        
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
            
            # Calcular precio_venta con 40% de utilidad si no viene explícito
            if precio_venta and precio_venta > 0:
                # Si viene precio_venta explícito, usarlo
                precio_venta_final = precio_venta
            else:
                # Calcular automáticamente con 40% de utilidad
                # Fórmula: precio_venta = costo / (1 - 0.40) = costo / 0.60
                precio_venta_final = costo_promedio / 0.60
            
            # Calcular utilidad
            utilidad_unitaria = precio_venta_final - costo_promedio
            porcentaje_utilidad = 40.0  # Fijo al 40%
            
            # Actualizar inventario
            update_data = {
                "cantidad": cantidad_nueva,
                "costo": costo_promedio,
                "precio_venta": precio_venta_final,
                "utilidad": round(utilidad_unitaria, 2),
                "porcentaje_utilidad": porcentaje_utilidad,
                "fechaActualizacion": fecha_actual,
                "usuarioActualizacion": usuario_correo
            }
            
            # Actualizar marca si viene en el producto
            if marca:
                update_data["marca"] = marca
            
            await inventarios_collection.update_one(
                {"_id": inventario_existente["_id"]},
                {"$set": update_data}
            )
            print(f"✅ Inventario actualizado: {nombre} - Cantidad: {cantidad_actual} + {cantidad} = {cantidad_nueva}, Precio venta: {precio_venta}")
        else:
            # Producto no existe: crear nuevo registro de inventario
            # Calcular precio_venta con 40% de utilidad si no viene explícito
            if precio_venta and precio_venta > 0:
                # Si viene precio_venta explícito, usarlo
                precio_venta_final = precio_venta
            else:
                # Calcular automáticamente con 40% de utilidad
                # Fórmula: precio_venta = costo / (1 - 0.40) = costo / 0.60
                precio_venta_final = precio_unitario / 0.60
            
            # Calcular utilidad
            utilidad_unitaria = precio_venta_final - precio_unitario
            porcentaje_utilidad = 40.0  # Fijo al 40%
            
            nuevo_inventario = {
                "farmacia": farmacia,
                "nombre": nombre,
                "cantidad": cantidad,
                "costo": precio_unitario,
                "precio_venta": precio_venta_final,
                "utilidad": round(utilidad_unitaria, 2),
                "porcentaje_utilidad": porcentaje_utilidad,
                "usuarioCorreo": usuario_correo,
                "fecha": fecha_actual,
                "estado": "activo"
            }
            
            if codigo:
                nuevo_inventario["codigo"] = codigo
            
            if producto_id:
                nuevo_inventario["productoId"] = producto_id
            
            if marca:
                nuevo_inventario["marca"] = marca
            
            await inventarios_collection.insert_one(nuevo_inventario)
            print(f"✅ Nuevo producto agregado al inventario: {nombre} - Cantidad: {cantidad}, Costo: {precio_unitario}, Utilidad: {utilidad_unitaria}, Precio venta: {precio_venta_final}")
        
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
    Obtiene todas las compras con el objeto proveedor completo poblado.
    Puede filtrar por farmacia y rango de fechas.
    Requiere autenticación.
    """
    try:
        print("🔍 [COMPRAS] Obteniendo compras...")
        collection = get_collection("COMPRAS")
        proveedores_collection = get_collection("PROVEEDORES")
        
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
        
        print(f"🔍 [COMPRAS] Encontradas {len(compras)} compras")
        
        # Obtener colección de inventarios para buscar precios de venta
        inventarios_collection = get_collection("INVENTARIOS")
        
        # Poblar el objeto proveedor completo y agregar utilidad a cada producto
        for compra in compras:
            # Convertir _id a string
            compra["_id"] = str(compra["_id"])
            
            # Obtener proveedorId (puede ser ObjectId o string)
            proveedor_id = compra.get("proveedorId")
            
            if proveedor_id:
                try:
                    # Intentar convertir a ObjectId si es string
                    if isinstance(proveedor_id, str):
                        # Verificar si es un ObjectId válido
                        if len(proveedor_id) == 24:
                            proveedor_id_obj = ObjectId(proveedor_id)
                        else:
                            # Si no es ObjectId válido, buscar por otro campo
                            proveedor = await proveedores_collection.find_one({"nombre": proveedor_id})
                            if proveedor:
                                proveedor["_id"] = str(proveedor["_id"])
                                compra["proveedor"] = proveedor
                                compra["proveedorId"] = str(proveedor["_id"])
                            else:
                                print(f"⚠️ [COMPRAS] Proveedor no encontrado para ID: {proveedor_id}")
                                compra["proveedor"] = None
                            continue
                    else:
                        proveedor_id_obj = proveedor_id
                    
                    # Buscar el proveedor en la colección PROVEEDORES
                    proveedor = await proveedores_collection.find_one({"_id": proveedor_id_obj})
                    
                    if proveedor:
                        # Convertir _id a string
                        proveedor["_id"] = str(proveedor["_id"])
                        # Agregar el objeto proveedor completo a la compra
                        compra["proveedor"] = proveedor
                        # Mantener también el proveedorId como string para compatibilidad
                        compra["proveedorId"] = str(proveedor["_id"])
                        print(f"🔍 [COMPRAS] Proveedor poblado: {proveedor.get('nombre', 'Sin nombre')}")
                    else:
                        print(f"⚠️ [COMPRAS] Proveedor no encontrado para ID: {proveedor_id}")
                        compra["proveedor"] = None
                except (InvalidId, ValueError) as e:
                    print(f"⚠️ [COMPRAS] Error al convertir proveedorId {proveedor_id}: {e}")
                    compra["proveedor"] = None
                except Exception as e:
                    print(f"⚠️ [COMPRAS] Error al buscar proveedor: {e}")
                    compra["proveedor"] = None
            else:
                print(f"⚠️ [COMPRAS] Compra sin proveedorId")
                compra["proveedor"] = None
            
            # Agregar utilidad a cada producto en la compra
            productos = compra.get("productos", [])
            farmacia_compra = compra.get("farmacia", "")
            
            for producto in productos:
                try:
                    # Obtener precio de compra (precioUnitario)
                    precio_compra = float(producto.get("precioUnitario", 0))
                    cantidad = float(producto.get("cantidad", 1))
                    
                    # Buscar el producto en el inventario para obtener precio_venta
                    nombre_producto = producto.get("nombre", "")
                    codigo_producto = producto.get("codigo")
                    
                    filtro_inventario = {"farmacia": farmacia_compra}
                    if codigo_producto:
                        filtro_inventario["codigo"] = codigo_producto
                    else:
                        filtro_inventario["nombre"] = nombre_producto
                    
                    inventario = await inventarios_collection.find_one(filtro_inventario)
                    
                    if inventario:
                        # Obtener precio_venta del inventario
                        precio_venta = float(inventario.get("precio_venta", 0))
                        
                        if precio_venta > 0:
                            # Calcular utilidad en dinero
                            utilidad_unitaria = precio_venta - precio_compra
                            utilidad_total = utilidad_unitaria * cantidad
                            
                            # Calcular porcentaje de ganancia
                            if precio_compra > 0:
                                porcentaje_ganancia = (utilidad_unitaria / precio_compra) * 100
                            else:
                                porcentaje_ganancia = 0
                            
                            # Agregar campos de utilidad al producto
                            producto["precio_venta"] = precio_venta
                            producto["utilidad"] = round(utilidad_unitaria, 2)
                            producto["utilidad_contable"] = round(utilidad_total, 2)
                            producto["porcentaje_ganancia"] = round(porcentaje_ganancia, 2)
                        else:
                            # Si no hay precio_venta, verificar si viene en el producto
                            precio_venta_producto = producto.get("precio_venta", 0)
                            if precio_venta_producto and precio_venta_producto > 0:
                                precio_venta = float(precio_venta_producto)
                                utilidad_unitaria = precio_venta - precio_compra
                                utilidad_total = utilidad_unitaria * cantidad
                                
                                if precio_compra > 0:
                                    porcentaje_ganancia = (utilidad_unitaria / precio_compra) * 100
                                else:
                                    porcentaje_ganancia = 0
                                
                                producto["precio_venta"] = precio_venta
                                producto["utilidad"] = round(utilidad_unitaria, 2)
                                producto["utilidad_contable"] = round(utilidad_total, 2)
                                producto["porcentaje_ganancia"] = round(porcentaje_ganancia, 2)
                            else:
                                # No hay precio_venta disponible
                                producto["precio_venta"] = 0
                                producto["utilidad"] = 0
                                producto["utilidad_contable"] = 0
                                producto["porcentaje_ganancia"] = 0
                    else:
                        # Producto no encontrado en inventario, verificar si viene utilidad en el producto
                        if "utilidad" in producto or "precio_venta" in producto:
                            # Ya tiene utilidad, mantenerla
                            pass
                        else:
                            # No hay información de utilidad
                            producto["precio_venta"] = 0
                            producto["utilidad"] = 0
                            producto["utilidad_contable"] = 0
                            producto["porcentaje_ganancia"] = 0
                except Exception as e:
                    print(f"⚠️ [COMPRAS] Error calculando utilidad para producto {producto.get('nombre', 'Desconocido')}: {e}")
                    # Asegurar que los campos existan aunque haya error
                    if "precio_venta" not in producto:
                        producto["precio_venta"] = producto.get("precio_venta", 0)
                    if "utilidad" not in producto:
                        producto["utilidad"] = producto.get("utilidad", 0)
                    if "utilidad_contable" not in producto:
                        producto["utilidad_contable"] = producto.get("utilidad_contable", 0)
                    if "porcentaje_ganancia" not in producto:
                        producto["porcentaje_ganancia"] = producto.get("porcentaje_ganancia", 0)
        
        # Incluir pagos en cada compra
        for compra in compras:
            pagos = compra.get("pagos", [])
            for pago in pagos:
                if "_id" in pago and isinstance(pago["_id"], ObjectId):
                    pago["_id"] = str(pago["_id"])
                if "banco_id" in pago and isinstance(pago["banco_id"], ObjectId):
                    pago["banco_id"] = str(pago["banco_id"])
            compra["pagos"] = pagos
        
        print(f"🔍 [COMPRAS] Compras procesadas: {len(compras)}")
        print(f"🔍 [INVENTARIOS] Compras obtenidas: {len(compras)} compras con productos y utilidad calculada")
        return compras
    except Exception as e:
        print(f"❌ [COMPRAS] Error obteniendo compras: {e}")
        import traceback
        traceback.print_exc()
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
        productos = compra_data["productos"]
        farmacia = compra_data["farmacia"]
        
        for i, producto in enumerate(productos):
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
        
        # VALIDACIÓN 1: Validar códigos duplicados dentro de la misma compra
        codigos_vistos = set()
        for i, producto in enumerate(productos):
            codigo = producto.get("codigo")
            if codigo:
                codigo_normalizado = str(codigo).strip().upper()
                if codigo_normalizado in codigos_vistos:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"El código '{codigo_normalizado}' está duplicado en la compra. Cada producto debe tener un código único."
                    )
                codigos_vistos.add(codigo_normalizado)
        
        # VALIDACIÓN 2: Validar que productos nuevos no tengan códigos que ya existen en inventario
        inventarios_collection = get_collection("INVENTARIOS")
        for i, producto in enumerate(productos):
            es_nuevo = producto.get("es_nuevo", False)
            codigo = producto.get("codigo")
            
            if es_nuevo and codigo:
                codigo_normalizado = str(codigo).strip().upper()
                
                # Buscar si el código ya existe en el inventario de esta farmacia
                filtro_codigo = {
                    "codigo": codigo_normalizado,
                    "farmacia": farmacia
                }
                producto_existente = await inventarios_collection.find_one(filtro_codigo)
                
                if producto_existente:
                    nombre_existente = producto_existente.get("nombre", "Desconocido")
                    raise HTTPException(
                        status_code=400,
                        detail=f"El código '{codigo_normalizado}' ya existe en el inventario para el producto '{nombre_existente}'. Los productos nuevos no pueden usar códigos existentes."
                    )
        
        print(f"✅ [COMPRAS] Validaciones de códigos pasadas correctamente")
        
        # Crear el documento de compra
        compra_dict = compra_data.copy()
        compra_dict["usuarioCreacion"] = usuario_correo
        compra_dict["fechaCreacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Convertir proveedorId a ObjectId si es necesario
        if compra_dict.get("proveedorId"):
            try:
                # Intentar convertir a ObjectId solo si es un string válido de 24 caracteres hex
                proveedor_id = str(compra_dict["proveedorId"]).strip()
                if len(proveedor_id) == 24:
                    compra_dict["proveedorId"] = ObjectId(proveedor_id)
                else:
                    # Si no es un ObjectId válido, dejarlo como string
                    compra_dict["proveedorId"] = proveedor_id
            except (InvalidId, ValueError, TypeError) as e:
                # Si no es un ObjectId válido, dejarlo como string
                print(f"[COMPRAS] No se pudo convertir proveedorId a ObjectId: {e}. Se guardará como string.")
                compra_dict["proveedorId"] = str(compra_dict["proveedorId"])
        
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
        
        # Convertir ObjectId a string en la respuesta
        if "_id" in compra_dict:
            compra_dict["_id"] = str(compra_dict["_id"])
        if "proveedorId" in compra_dict and isinstance(compra_dict["proveedorId"], ObjectId):
            compra_dict["proveedorId"] = str(compra_dict["proveedorId"])
        
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
        error_trace = traceback.format_exc()
        print(f"❌ Traceback completo:\n{error_trace}")
        # Asegurar que el error se propaga con información útil
        error_message = f"Error al crear compra: {str(e)}"
        raise HTTPException(status_code=500, detail=error_message)

@router.get("/compras/{compra_id}")
async def obtener_compra(compra_id: str, usuario_actual: dict = Depends(get_current_user)):
    """
    Obtiene una compra por su ID con el objeto proveedor completo poblado.
    Requiere autenticación.
    """
    try:
        try:
            object_id = ObjectId(compra_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="ID de compra inválido")
        
        collection = get_collection("COMPRAS")
        proveedores_collection = get_collection("PROVEEDORES")
        inventarios_collection = get_collection("INVENTARIOS")
        
        compra = await collection.find_one({"_id": object_id})
        
        if not compra:
            raise HTTPException(status_code=404, detail="Compra no encontrada")
        
        compra["_id"] = str(compra["_id"])
        
        # Poblar el objeto proveedor completo
        proveedor_id = compra.get("proveedorId")
        
        if proveedor_id:
            try:
                # Intentar convertir a ObjectId si es string
                if isinstance(proveedor_id, str):
                    if len(proveedor_id) == 24:
                        proveedor_id_obj = ObjectId(proveedor_id)
                    else:
                        # Buscar por nombre u otro campo
                        proveedor = await proveedores_collection.find_one({"nombre": proveedor_id})
                        if proveedor:
                            proveedor["_id"] = str(proveedor["_id"])
                            compra["proveedor"] = proveedor
                            compra["proveedorId"] = str(proveedor["_id"])
                        else:
                            compra["proveedor"] = None
                        return compra
                else:
                    proveedor_id_obj = proveedor_id
                
                # Buscar el proveedor
                proveedor = await proveedores_collection.find_one({"_id": proveedor_id_obj})
                
                if proveedor:
                    proveedor["_id"] = str(proveedor["_id"])
                    compra["proveedor"] = proveedor
                    compra["proveedorId"] = str(proveedor["_id"])
                else:
                    compra["proveedor"] = None
            except (InvalidId, ValueError):
                compra["proveedor"] = None
            except Exception as e:
                print(f"⚠️ [COMPRAS] Error al buscar proveedor: {e}")
                compra["proveedor"] = None
        else:
            compra["proveedor"] = None
        
        # Agregar utilidad a cada producto en la compra
        productos = compra.get("productos", [])
        farmacia_compra = compra.get("farmacia", "")
        
        for producto in productos:
            try:
                # Obtener precio de compra (precioUnitario)
                precio_compra = float(producto.get("precioUnitario", 0))
                cantidad = float(producto.get("cantidad", 1))
                
                # Buscar el producto en el inventario para obtener precio_venta
                nombre_producto = producto.get("nombre", "")
                codigo_producto = producto.get("codigo")
                
                filtro_inventario = {"farmacia": farmacia_compra}
                if codigo_producto:
                    filtro_inventario["codigo"] = codigo_producto
                else:
                    filtro_inventario["nombre"] = nombre_producto
                
                inventario = await inventarios_collection.find_one(filtro_inventario)
                
                if inventario:
                    # Obtener precio_venta del inventario
                    precio_venta = float(inventario.get("precio_venta", 0))
                    
                    if precio_venta > 0:
                        # Calcular utilidad en dinero
                        utilidad_unitaria = precio_venta - precio_compra
                        utilidad_total = utilidad_unitaria * cantidad
                        
                        # Calcular porcentaje de ganancia
                        if precio_compra > 0:
                            porcentaje_ganancia = (utilidad_unitaria / precio_compra) * 100
                        else:
                            porcentaje_ganancia = 0
                        
                        # Agregar campos de utilidad al producto
                        producto["precio_venta"] = precio_venta
                        producto["utilidad"] = round(utilidad_unitaria, 2)
                        producto["utilidad_contable"] = round(utilidad_total, 2)
                        producto["porcentaje_ganancia"] = round(porcentaje_ganancia, 2)
                    else:
                        # Si no hay precio_venta, verificar si viene en el producto
                        precio_venta_producto = producto.get("precio_venta", 0)
                        if precio_venta_producto and precio_venta_producto > 0:
                            precio_venta = float(precio_venta_producto)
                            utilidad_unitaria = precio_venta - precio_compra
                            utilidad_total = utilidad_unitaria * cantidad
                            
                            if precio_compra > 0:
                                porcentaje_ganancia = (utilidad_unitaria / precio_compra) * 100
                            else:
                                porcentaje_ganancia = 0
                            
                            producto["precio_venta"] = precio_venta
                            producto["utilidad"] = round(utilidad_unitaria, 2)
                            producto["utilidad_contable"] = round(utilidad_total, 2)
                            producto["porcentaje_ganancia"] = round(porcentaje_ganancia, 2)
                        else:
                            # No hay precio_venta disponible
                            producto["precio_venta"] = 0
                            producto["utilidad"] = 0
                            producto["utilidad_contable"] = 0
                            producto["porcentaje_ganancia"] = 0
                else:
                    # Producto no encontrado en inventario, verificar si viene utilidad en el producto
                    if "utilidad" in producto or "precio_venta" in producto:
                        # Ya tiene utilidad, mantenerla
                        pass
                    else:
                        # No hay información de utilidad
                        producto["precio_venta"] = 0
                        producto["utilidad"] = 0
                        producto["utilidad_contable"] = 0
                        producto["porcentaje_ganancia"] = 0
            except Exception as e:
                print(f"⚠️ [COMPRAS] Error calculando utilidad para producto {producto.get('nombre', 'Desconocido')}: {e}")
                # Asegurar que los campos existan aunque haya error
                if "precio_venta" not in producto:
                    producto["precio_venta"] = producto.get("precio_venta", 0)
                if "utilidad" not in producto:
                    producto["utilidad"] = producto.get("utilidad", 0)
                if "utilidad_contable" not in producto:
                    producto["utilidad_contable"] = producto.get("utilidad_contable", 0)
                if "porcentaje_ganancia" not in producto:
                    producto["porcentaje_ganancia"] = producto.get("porcentaje_ganancia", 0)
        
        # Incluir pagos en la respuesta
        pagos = compra.get("pagos", [])
        for pago in pagos:
            if "_id" in pago and isinstance(pago["_id"], ObjectId):
                pago["_id"] = str(pago["_id"])
            if "banco_id" in pago and isinstance(pago["banco_id"], ObjectId):
                pago["banco_id"] = str(pago["banco_id"])
        
        compra["pagos"] = pagos
        
        return compra
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/compras/{compra_id}/pagos")
async def crear_pago_compra(
    compra_id: str,
    pago_data: dict = Body(...),
    usuario_actual: dict = Depends(get_current_user)
):
    """
    Crea un pago para una compra.
    Actualiza el monto_abonado, monto_restante y estado de la compra.
    Actualiza el saldo del banco (resta el monto).
    Crea un movimiento en el historial del banco.
    Requiere autenticación.
    """
    try:
        print(f"💳 [COMPRAS] Creando pago para compra: {compra_id}")
        
        compras_collection = get_collection("COMPRAS")
        bancos_collection = get_collection("BANCOS")
        
        # Validar compra_id
        try:
            compra_object_id = ObjectId(compra_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="ID de compra inválido")
        
        # Obtener la compra
        compra = await compras_collection.find_one({"_id": compra_object_id})
        if not compra:
            raise HTTPException(status_code=404, detail="Compra no encontrada")
        
        # Validar que la compra no esté completamente pagada
        estado_actual = compra.get("estado", "sin_pago")
        if estado_actual == "pagada":
            raise HTTPException(status_code=400, detail="La compra ya está completamente pagada")
        
        # Validar datos del pago
        monto = float(pago_data.get("monto", 0))
        if monto <= 0:
            raise HTTPException(status_code=400, detail="El monto debe ser mayor a 0")
        
        metodo_pago = pago_data.get("metodo_pago", "")
        banco_id = pago_data.get("banco_id")
        fecha_pago = pago_data.get("fecha_pago", datetime.now().strftime("%Y-%m-%d"))
        referencia = pago_data.get("referencia", "")
        notas = pago_data.get("notas", "")
        comprobante = pago_data.get("comprobante", "")  # Nombre del archivo del comprobante
        
        # Calcular montos actuales
        total_factura = float(compra.get("total", 0))
        pagos_existentes = compra.get("pagos", [])
        
        # Validar que pagos_existentes sea una lista
        if not isinstance(pagos_existentes, list):
            print(f"⚠️ [COMPRAS] pagos_existentes no es una lista, tipo: {type(pagos_existentes)}, valor: {pagos_existentes}")
            pagos_existentes = []
        
        # Convertir ObjectIds en pagos existentes si es necesario
        pagos_procesados = []
        for p in pagos_existentes:
            if isinstance(p, dict):
                pago_procesado = p.copy()
                # Convertir ObjectId a string si existe
                if "banco_id" in pago_procesado and isinstance(pago_procesado["banco_id"], ObjectId):
                    pago_procesado["banco_id"] = str(pago_procesado["banco_id"])
                pagos_procesados.append(pago_procesado)
            else:
                print(f"⚠️ [COMPRAS] Pago no es un diccionario: {type(p)}, valor: {p}")
        
        monto_abonado_actual = sum(float(p.get("monto", 0)) for p in pagos_procesados)
        monto_restante_actual = total_factura - monto_abonado_actual
        
        # Validar que el monto no exceda el monto restante
        if monto > monto_restante_actual:
            raise HTTPException(
                status_code=400,
                detail=f"El monto del pago ({monto}) excede el monto restante ({monto_restante_actual})"
            )
        
        # Si el método de pago es banco, validar y actualizar el banco
        if metodo_pago == "banco" and banco_id:
            try:
                banco_object_id = ObjectId(banco_id)
            except InvalidId:
                raise HTTPException(status_code=400, detail="ID de banco inválido")
            
            banco = await bancos_collection.find_one({"_id": banco_object_id})
            if not banco:
                raise HTTPException(status_code=404, detail="Banco no encontrado")
            
            # Validar que el banco tenga saldo suficiente
            saldo_actual = float(banco.get("saldo", 0))
            if saldo_actual < monto:
                raise HTTPException(
                    status_code=400,
                    detail=f"El banco no tiene saldo suficiente. Saldo disponible: {saldo_actual}, Monto requerido: {monto}"
                )
            
            # Actualizar saldo del banco (restar porque es un pago saliente)
            nuevo_saldo = saldo_actual - monto
            await bancos_collection.update_one(
                {"_id": banco_object_id},
                {"$set": {"saldo": nuevo_saldo}}
            )
            
            # Crear movimiento en el historial del banco
            movimientos = banco.get("movimientos", [])
            nuevo_movimiento = {
                "tipo": "pago_compra",
                "monto": monto,
                "fecha": fecha_pago,
                "referencia": referencia,
                "compra_id": compra_id,
                "notas": notas,
                "usuario": usuario_actual.get("correo", "unknown"),
                "fechaCreacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            movimientos.append(nuevo_movimiento)
            
            await bancos_collection.update_one(
                {"_id": banco_object_id},
                {"$set": {"movimientos": movimientos}}
            )
            
            print(f"🏦 [COMPRAS] Saldo del banco actualizado: {saldo_actual} -> {nuevo_saldo}")
        
        # Crear el pago
        nuevo_pago = {
            "monto": monto,
            "fecha_pago": fecha_pago,
            "metodo_pago": metodo_pago,
            "referencia": referencia,
            "notas": notas,
            "comprobante": comprobante,  # Guardar nombre del archivo
            "usuarioCreacion": usuario_actual.get("correo", "unknown"),
            "fechaCreacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if banco_id:
            nuevo_pago["banco_id"] = ObjectId(banco_id)
        
        # Agregar el pago a la compra
        if "pagos" not in compra or not isinstance(compra["pagos"], list):
            compra["pagos"] = []
        
        compra["pagos"].append(nuevo_pago)
        
        # Calcular nuevos montos
        monto_abonado_nuevo = monto_abonado_actual + monto
        monto_restante_nuevo = total_factura - monto_abonado_nuevo
        
        # Determinar nuevo estado
        if monto_restante_nuevo <= 0:
            nuevo_estado = "pagada"
        elif monto_abonado_nuevo > 0:
            nuevo_estado = "abonado"
        else:
            nuevo_estado = "sin_pago"
        
        # Actualizar la compra
        await compras_collection.update_one(
            {"_id": compra_object_id},
            {
                "$set": {
                    "pagos": compra["pagos"],
                    "monto_abonado": monto_abonado_nuevo,
                    "monto_restante": monto_restante_nuevo,
                    "estado": nuevo_estado,
                    "fechaActualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "usuarioActualizacion": usuario_actual.get("correo", "unknown")
                }
            }
        )
        
        # Obtener la compra actualizada
        compra_actualizada = await compras_collection.find_one({"_id": compra_object_id})
        
        if compra_actualizada:
            # Convertir _id a string
            compra_actualizada["_id"] = str(compra_actualizada["_id"])
            
            # Convertir ObjectIds en pagos
            pagos_compra = compra_actualizada.get("pagos", [])
            if isinstance(pagos_compra, list):
                for pago in pagos_compra:
                    if isinstance(pago, dict):
                        if "banco_id" in pago and isinstance(pago["banco_id"], ObjectId):
                            pago["banco_id"] = str(pago["banco_id"])
                        if "_id" in pago and isinstance(pago["_id"], ObjectId):
                            pago["_id"] = str(pago["_id"])
            
            # Convertir banco_id en nuevo_pago a string para la respuesta
            nuevo_pago_respuesta = nuevo_pago.copy()
            if "banco_id" in nuevo_pago_respuesta and isinstance(nuevo_pago_respuesta["banco_id"], ObjectId):
                nuevo_pago_respuesta["banco_id"] = str(nuevo_pago_respuesta["banco_id"])
        else:
            compra_actualizada = compra.copy()
            compra_actualizada["_id"] = str(compra_actualizada["_id"])
            nuevo_pago_respuesta = nuevo_pago.copy()
            if "banco_id" in nuevo_pago_respuesta and isinstance(nuevo_pago_respuesta["banco_id"], ObjectId):
                nuevo_pago_respuesta["banco_id"] = str(nuevo_pago_respuesta["banco_id"])
        
        print(f"✅ [COMPRAS] Pago creado: {monto} - Estado: {nuevo_estado}")
        
        return {
            "message": "Pago creado exitosamente",
            "pago": nuevo_pago_respuesta,
            "compra": compra_actualizada
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [COMPRAS] Error creando pago: {e}")
        import traceback
        traceback.print_exc()
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

