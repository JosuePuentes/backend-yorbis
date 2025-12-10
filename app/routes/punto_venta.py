"""
Rutas para punto de venta
"""
from fastapi import APIRouter, HTTPException, Query, Depends, Body
from app.db.mongo import get_collection
from app.core.get_current_user import get_current_user
from typing import Optional, List, Dict, Any
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime
import re

router = APIRouter()

@router.get("/punto-venta/productos/buscar")
async def buscar_productos_punto_venta(
    q: str = Query(..., description="Término de búsqueda"),
    sucursal: Optional[str] = Query(None, description="ID de la sucursal (farmacia)"),
    usuario_actual: dict = Depends(get_current_user)
):
    """
    Busca productos para el punto de venta (ULTRA OPTIMIZADO).
    
    MODOS DE BÚSQUEDA:
    1. Búsqueda RÁPIDA (con * al final): "esmalte*"
       - Solo busca coincidencias que EMPIECEN con el término
       - Busca solo en código y nombre (campos indexados)
       - MUY RÁPIDA - usa índices de manera óptima
       - Ejemplo: "esmalte*" → encuentra "esmalte rojo", "esmalte azul", etc.
    
    2. Búsqueda AMPLIA (sin *): "esmalte"
       - Busca en todos los campos (código, nombre, descripción, marca)
       - Coincidencias parciales en cualquier parte
       - Más lenta pero más flexible
       - Ejemplo: "esmalte" → encuentra "esmalte rojo", "pintura esmalte", etc.
    
    Optimizaciones aplicadas:
    - Búsqueda exacta por código primero (instantánea)
    - Búsqueda rápida con * solo en campos indexados
    - Proyección de campos para reducir transferencia
    - Uso eficiente de índices de MongoDB
    
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
        inventarios_collection = get_collection("INVENTARIOS")
        
        # Construir filtro base
        filtro = {"estado": {"$ne": "inactivo"}}
        
        # Filtrar por sucursal si se especifica
        if sucursal and sucursal.strip():
            filtro["farmacia"] = sucursal.strip()
        
        query_term = q.strip() if q and q.strip() else ""
        
        # Detectar modo de búsqueda: rápida (*) o amplia (sin *)
        busqueda_rapida = query_term.endswith("*")
        if busqueda_rapida:
            # Remover el * del término
            query_term = query_term[:-1].strip()
        
        # OPTIMIZACIÓN MÁXIMA: Búsqueda por código exacto primero (más rápida)
        if query_term:
            # 1. Intentar búsqueda exacta por código (MUY RÁPIDA con índice)
            codigo_filtro = {**filtro, "codigo": query_term.upper()}
            # OPTIMIZACIÓN: Proyección mínima para búsqueda exacta
            producto_exacto = await inventarios_collection.find_one(
                codigo_filtro,
                projection={
                    "_id": 1, "codigo": 1, "nombre": 1,
                    "precio_venta": 1, "precio": 1, "cantidad": 1,
                    "farmacia": 1, "estado": 1
                }
            )
            
            if producto_exacto:
                # Si encontramos coincidencia exacta, retornar solo ese resultado
                # OPTIMIZACIÓN: Solo campos esenciales para respuesta rápida
                precio_venta = producto_exacto.get("precio_venta") or producto_exacto.get("precio", 0)
                cantidad = producto_exacto.get("cantidad", 0)
                
                resultado = {
                    "id": str(producto_exacto["_id"]),
                    "codigo": producto_exacto.get("codigo", ""),
                    "nombre": producto_exacto.get("nombre", ""),
                    "precio": float(precio_venta),
                    "precio_venta": float(precio_venta),
                    "cantidad": float(cantidad),
                    "stock": float(cantidad),
                    "sucursal": producto_exacto.get("farmacia", sucursal or ""),
                    "estado": producto_exacto.get("estado", "activo")
                }
                return [resultado]
        
        # 2. Si no hay término de búsqueda, retornar productos de la sucursal
        if not query_term:
            # OPTIMIZACIÓN: Proyección mínima cuando no hay búsqueda
            productos = await inventarios_collection.find(
                filtro,
                projection={
                    "_id": 1, "codigo": 1, "nombre": 1,
                    "precio_venta": 1, "precio": 1, "cantidad": 1,
                    "farmacia": 1, "estado": 1
                }
            ).sort("nombre", 1).limit(30).to_list(length=30)
        else:
            # Escapar el término para regex
            escaped_query = re.escape(query_term)
            
            if busqueda_rapida:
                # BÚSQUEDA RÁPIDA: Solo coincidencias al INICIO en código y nombre (campos indexados)
                # OPTIMIZACIÓN MÁXIMA: Priorizar código primero (índice más rápido)
                match_stage = {
                    **filtro,
                    "$or": [
                        {"codigo": {"$regex": f"^{escaped_query}", "$options": "i"}},  # Coincidencia al inicio en código (MÁS RÁPIDO)
                        {"nombre": {"$regex": f"^{escaped_query}", "$options": "i"}}   # Coincidencia al inicio en nombre
                    ]
                }
                print(f"⚡ [PUNTO_VENTA] Búsqueda RÁPIDA (con *): '{query_term}' - Solo código y nombre")
            else:
                # BÚSQUEDA AMPLIA: Busca en todos los campos pero prioriza código y nombre
                # OPTIMIZACIÓN: Priorizar coincidencias al inicio primero
                match_stage = {
                    **filtro,
                    "$or": [
                        {"codigo": {"$regex": f"^{escaped_query}", "$options": "i"}},  # Coincidencia al inicio en código (MÁS RÁPIDO)
                        {"nombre": {"$regex": f"^{escaped_query}", "$options": "i"}},  # Coincidencia al inicio en nombre
                        {"codigo": {"$regex": escaped_query, "$options": "i"}},  # Coincidencia parcial en código
                        {"nombre": {"$regex": escaped_query, "$options": "i"}},  # Coincidencia parcial en nombre
                        {"descripcion": {"$regex": escaped_query, "$options": "i"}},  # Último recurso: descripción
                        {"marca": {"$regex": escaped_query, "$options": "i"}}  # Último recurso: marca
                    ]
                }
                print(f"🔍 [PUNTO_VENTA] Búsqueda AMPLIA (sin *): '{query_term}' - Todos los campos")
            
            # OPTIMIZACIÓN MÁXIMA: Proyección mínima (solo campos esenciales) y límite reducido
            # Reducir límite a 30 para mejor rendimiento
            productos = await inventarios_collection.find(
                match_stage,
                projection={
                    "_id": 1, "codigo": 1, "nombre": 1, 
                    "precio_venta": 1, "precio": 1, "cantidad": 1,
                    "farmacia": 1, "estado": 1
                }
            ).sort("nombre", 1).limit(30).to_list(length=30)
        
        # OPTIMIZACIÓN MÁXIMA: Formateo ultra-rápido (solo campos esenciales)
        # Reducir procesamiento al mínimo absoluto
        resultados = []
        for producto in productos:
            precio_venta = producto.get("precio_venta") or producto.get("precio", 0)
            cantidad = producto.get("cantidad", 0)
            
            # Solo campos esenciales para punto de venta
            resultado = {
                "id": str(producto["_id"]),
                "codigo": producto.get("codigo", ""),
                "nombre": producto.get("nombre", ""),
                "precio": float(precio_venta),
                "precio_venta": float(precio_venta),
                "cantidad": float(cantidad),
                "stock": float(cantidad),
                "sucursal": producto.get("farmacia", sucursal or ""),
                "estado": producto.get("estado", "activo")
            }
            
            resultados.append(resultado)
        
        return resultados
        
    except Exception as e:
        print(f"❌ [PUNTO_VENTA] Error buscando productos: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/punto-venta/ventas")
async def crear_venta(
    venta_data: dict = Body(...),
    usuario_actual: dict = Depends(get_current_user)
):
    """
    Crea una nueva venta en el punto de venta.
    Incluye el campo descuento_por_divisa (opcional, 0-100).
    Requiere autenticación.
    """
    try:
        print(f"💰 [PUNTO_VENTA] Creando venta - Usuario: {usuario_actual.get('correo', 'unknown')}")
        
        # Validar y procesar descuento_por_divisa
        descuento_por_divisa = venta_data.get("descuento_por_divisa", 0)
        
        # Convertir a float si es necesario
        if descuento_por_divisa is None:
            descuento_por_divisa = 0
        else:
            try:
                descuento_por_divisa = float(descuento_por_divisa)
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=400,
                    detail="El campo 'descuento_por_divisa' debe ser un número"
                )
        
        # Validar rango 0-100
        if descuento_por_divisa < 0 or descuento_por_divisa > 100:
            raise HTTPException(
                status_code=400,
                detail="El campo 'descuento_por_divisa' debe estar entre 0 y 100"
            )
        
        # Agregar el campo al documento de venta
        venta_dict = venta_data.copy()
        venta_dict["descuento_por_divisa"] = descuento_por_divisa
        
        # Agregar información de creación
        venta_dict["usuarioCreacion"] = usuario_actual.get("correo", "unknown")
        venta_dict["fechaCreacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Guardar en la base de datos
        ventas_collection = get_collection("VENTAS")
        resultado = await ventas_collection.insert_one(venta_dict)
        venta_id = str(resultado.inserted_id)
        
        # Convertir _id a string en la respuesta
        venta_dict["_id"] = venta_id
        
        print(f"✅ [PUNTO_VENTA] Venta creada: {venta_id} - Descuento por divisa: {descuento_por_divisa}%")
        
        return {
            "message": "Venta creada exitosamente",
            "id": venta_id,
            "venta": venta_dict
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [PUNTO_VENTA] Error creando venta: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/punto-venta/ventas")
async def obtener_ventas(
    sucursal: Optional[str] = Query(None, description="ID de la sucursal (farmacia)"),
    fecha_inicio: Optional[str] = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin: Optional[str] = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    usuario_actual: dict = Depends(get_current_user)
):
    """
    Obtiene todas las ventas del punto de venta.
    Puede filtrar por sucursal y rango de fechas.
    Incluye el campo descuento_por_divisa en cada venta.
    Requiere autenticación.
    """
    try:
        print(f"📋 [PUNTO_VENTA] Obteniendo ventas - Sucursal: {sucursal}")
        
        ventas_collection = get_collection("VENTAS")
        filtro = {}
        
        # Filtrar por sucursal si se especifica
        if sucursal and sucursal.strip():
            filtro["sucursal"] = sucursal.strip()
            # También buscar por farmacia (compatibilidad)
            filtro = {"$or": [{"sucursal": sucursal.strip()}, {"farmacia": sucursal.strip()}]}
        
        # Filtrar por rango de fechas
        if fecha_inicio and fecha_fin:
            filtro["fecha"] = {"$gte": fecha_inicio, "$lte": fecha_fin}
        elif fecha_inicio:
            filtro["fecha"] = {"$gte": fecha_inicio}
        elif fecha_fin:
            filtro["fecha"] = {"$lte": fecha_fin}
        
        ventas = await ventas_collection.find(filtro).sort("fechaCreacion", -1).to_list(length=None)
        
        # Convertir _id a string y asegurar que descuento_por_divisa esté presente
        for venta in ventas:
            venta["_id"] = str(venta["_id"])
            # Asegurar que descuento_por_divisa esté presente (por defecto 0)
            if "descuento_por_divisa" not in venta:
                venta["descuento_por_divisa"] = 0
        
        print(f"📋 [PUNTO_VENTA] Encontradas {len(ventas)} ventas")
        return ventas
        
    except Exception as e:
        print(f"❌ [PUNTO_VENTA] Error obteniendo ventas: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/punto-venta/ventas/usuario")
async def obtener_ventas_usuario(
    usuario_actual: dict = Depends(get_current_user)
):
    """
    Obtiene las ventas del usuario actual.
    Incluye el campo descuento_por_divisa en cada venta.
    Requiere autenticación.
    """
    try:
        usuario_correo = usuario_actual.get("correo", "unknown")
        print(f"📋 [PUNTO_VENTA] Obteniendo ventas del usuario: {usuario_correo}")
        
        ventas_collection = get_collection("VENTAS")
        
        # Buscar ventas del usuario actual
        filtro = {
            "$or": [
                {"usuarioCreacion": usuario_correo},
                {"usuario": usuario_correo},
                {"vendedor": usuario_correo}
            ]
        }
        
        ventas = await ventas_collection.find(filtro).sort("fechaCreacion", -1).to_list(length=None)
        
        # Convertir _id a string y asegurar que descuento_por_divisa esté presente
        for venta in ventas:
            venta["_id"] = str(venta["_id"])
            # Asegurar que descuento_por_divisa esté presente (por defecto 0)
            if "descuento_por_divisa" not in venta:
                venta["descuento_por_divisa"] = 0
        
        print(f"📋 [PUNTO_VENTA] Encontradas {len(ventas)} ventas del usuario")
        return ventas
        
    except Exception as e:
        print(f"❌ [PUNTO_VENTA] Error obteniendo ventas del usuario: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/punto-venta/tasa-del-dia")
async def obtener_tasa_del_dia(
    fecha: Optional[str] = Query(None, description="Fecha en formato YYYY-MM-DD (opcional, por defecto hoy)"),
    usuario_actual: dict = Depends(get_current_user)
):
    """
    Obtiene la tasa de cambio del día.
    Si no se especifica fecha, retorna la tasa del día actual.
    Requiere autenticación.
    """
    try:
        # Si no se especifica fecha, usar la fecha actual
        if not fecha:
            fecha = datetime.now().strftime("%Y-%m-%d")
        
        print(f"💱 [PUNTO_VENTA] Obteniendo tasa del día: {fecha}")
        
        # Buscar en la colección de cuadres o tasas
        cuadres_collection = get_collection("CUADRES")
        
        # Buscar cuadre de esa fecha
        cuadre = await cuadres_collection.find_one({"dia": fecha})
        
        if cuadre and "tasa" in cuadre:
            tasa = float(cuadre["tasa"])
            print(f"💱 [PUNTO_VENTA] Tasa encontrada: {tasa} para fecha: {fecha}")
            return {
                "fecha": fecha,
                "tasa": tasa
            }
        
        # Si no se encuentra en cuadres, buscar en una colección de tasas si existe
        tasas_collection = get_collection("TASAS")
        tasa_doc = await tasas_collection.find_one({"fecha": fecha})
        
        if tasa_doc and "tasa" in tasa_doc:
            tasa = float(tasa_doc["tasa"])
            print(f"💱 [PUNTO_VENTA] Tasa encontrada en colección TASAS: {tasa}")
            return {
                "fecha": fecha,
                "tasa": tasa
            }
        
        # Si no se encuentra, retornar tasa por defecto (1.0) o la última tasa conocida
        # Buscar la última tasa disponible
        ultima_tasa = await cuadres_collection.find_one(
            {"tasa": {"$exists": True, "$ne": None}},
            sort=[("dia", -1)]
        )
        
        if ultima_tasa and "tasa" in ultima_tasa:
            tasa = float(ultima_tasa["tasa"])
            print(f"💱 [PUNTO_VENTA] Usando última tasa conocida: {tasa} del día {ultima_tasa.get('dia', 'desconocido')}")
            return {
                "fecha": fecha,
                "tasa": tasa,
                "nota": "Tasa de fecha anterior (no se encontró tasa para esta fecha)"
            }
        
        # Si no hay ninguna tasa, retornar 1.0 por defecto
        print(f"⚠️ [PUNTO_VENTA] No se encontró tasa, usando valor por defecto: 1.0")
        return {
            "fecha": fecha,
            "tasa": 1.0,
            "nota": "Tasa por defecto (no se encontró tasa en el sistema)"
        }
        
    except Exception as e:
        print(f"❌ [PUNTO_VENTA] Error obteniendo tasa del día: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

