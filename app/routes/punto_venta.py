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
    Busca productos para el punto de venta (OPTIMIZADO).
    Busca en código, nombre/descripción y marca.
    Búsqueda case-insensitive y coincidencia parcial.
    
    Optimizaciones aplicadas:
    - Uso de índice de texto de MongoDB para búsquedas rápidas
    - Proyección de campos para reducir transferencia de datos
    - Agregación de MongoDB para formateo eficiente
    
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
        print(f"🔍 [PUNTO_VENTA] Búsqueda optimizada: '{q}' en sucursal: {sucursal}")
        
        inventarios_collection = get_collection("INVENTARIOS")
        
        # Construir filtro de búsqueda
        filtro = {}
        
        # Filtrar por sucursal si se especifica
        if sucursal and sucursal.strip():
            filtro["farmacia"] = sucursal.strip()
        
        # Solo productos activos
        filtro["estado"] = {"$ne": "inactivo"}
        
        # OPTIMIZACIÓN: Usar agregación de MongoDB para formatear resultados directamente
        query_term = q.strip() if q and q.strip() else ""
        sucursal_value = sucursal.strip() if sucursal and sucursal.strip() else ""
        
        # Construir pipeline de agregación optimizado que formatea los resultados en MongoDB
        pipeline = []
        
        # Paso 1: Match - Filtrar documentos
        match_stage = {**filtro}
        use_text_search = False
        
        if query_term:
            # Intentar usar búsqueda de texto primero (requiere índice de texto)
            # Verificar si existe índice de texto probando la búsqueda
            try:
                # Probar si existe índice de texto ejecutando una búsqueda de prueba
                test_match = {**filtro, "$text": {"$search": query_term}}
                test_pipeline = [{"$match": test_match}, {"$limit": 1}]
                test_result = await inventarios_collection.aggregate(test_pipeline).to_list(length=1)
                
                if test_result:
                    match_stage["$text"] = {"$search": query_term}
                    use_text_search = True
                else:
                    raise ValueError("No text index or no results")
            except Exception:
                # FALLBACK: Usar regex optimizado
                use_text_search = False
                escaped_query = re.escape(query_term)
                regex_pattern = re.compile(escaped_query, re.IGNORECASE)
                regex_start = re.compile(f"^{escaped_query}", re.IGNORECASE)
                
                # Priorizar coincidencias al inicio (más rápidas con índices)
                match_stage["$or"] = [
                    {"codigo": regex_start},
                    {"nombre": regex_start},
                    {"codigo": regex_pattern},
                    {"nombre": regex_pattern},
                    {"descripcion": regex_pattern},
                    {"marca": regex_pattern}
                ]
        
        pipeline.append({"$match": match_stage})
        
        # Paso 2: Project - Formatear campos directamente en MongoDB
        project_stage = {
            "id": {"$toString": "$_id"},
            "codigo": {"$ifNull": ["$codigo", ""]},
            "nombre": {"$ifNull": ["$nombre", ""]},
            "descripcion": {
                "$cond": {
                    "if": {"$and": [{"$ne": ["$descripcion", None]}, {"$ne": ["$descripcion", ""]}]},
                    "then": "$descripcion",
                    "else": {"$ifNull": ["$nombre", ""]}
                }
            },
            "precio": {
                "$cond": {
                    "if": {"$and": [{"$ne": ["$precio_venta", None]}, {"$ne": ["$precio_venta", ""]}]},
                    "then": {"$toDouble": "$precio_venta"},
                    "else": {
                        "$cond": {
                            "if": {"$and": [{"$ne": ["$precio", None]}, {"$ne": ["$precio", ""]}]},
                            "then": {"$toDouble": "$precio"},
                            "else": 0.0
                        }
                    }
                }
            },
            "marca": {"$ifNull": ["$marca", None]},
            "cantidad": {"$toDouble": {"$ifNull": ["$cantidad", 0]}},
            "lotes": {"$ifNull": ["$lotes", []]},
            "sucursal": {
                "$cond": {
                    "if": {"$ne": ["$farmacia", None]},
                    "then": "$farmacia",
                    "else": {"$literal": sucursal_value}
                }
            },
            "costo": {"$toDouble": {"$ifNull": ["$costo", 0]}},
            "estado": {"$ifNull": ["$estado", "activo"]},
            "productoId": {
                "$cond": {
                    "if": {"$ne": ["$productoId", None]},
                    "then": {"$toString": "$productoId"},
                    "else": None
                }
            }
        }
        
        # Agregar score solo si se usa búsqueda de texto
        if use_text_search:
            project_stage["score"] = {"$meta": "textScore"}
        
        pipeline.append({"$project": project_stage})
        
        # Paso 3: AddFields - Agregar campos calculados
        pipeline.append({
            "$addFields": {
                "stock": "$cantidad",
                "precio_venta": "$precio"
            }
        })
        
        # Paso 4: Sort - Ordenar por relevancia (si hay búsqueda de texto) o por nombre
        if use_text_search:
            pipeline.append({"$sort": {"score": {"$meta": "textScore"}}})
        else:
            pipeline.append({"$sort": {"nombre": 1}})
        
        # Paso 5: Limit - Limitar resultados
        pipeline.append({"$limit": 100})
        
        # Ejecutar agregación
        productos_cursor = inventarios_collection.aggregate(pipeline)
        resultados = await productos_cursor.to_list(length=100)
        
        # Limpiar campos None (MongoDB no puede hacer esto fácilmente en agregación)
        for i, resultado in enumerate(resultados):
            # Remover campos None excepto los requeridos
            resultados[i] = {k: v for k, v in resultado.items() if v is not None or k in ["id", "codigo", "nombre", "descripcion", "precio"]}
        
        if use_text_search:
            print(f"🔍 [PUNTO_VENTA] Encontrados {len(resultados)} productos usando índice de texto")
        else:
            print(f"🔍 [PUNTO_VENTA] Encontrados {len(resultados)} productos usando búsqueda optimizada")
        
        print(f"🔍 [PUNTO_VENTA] Retornando {len(resultados)} productos normalizados")
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

