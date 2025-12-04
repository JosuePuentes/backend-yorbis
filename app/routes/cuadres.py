from fastapi import APIRouter, HTTPException, Query, Body
from app.db.mongo import get_collection, db
from bson import ObjectId
from typing import Optional, List

router = APIRouter()

# Endpoint 1: Resumen de cuadres por fecha
@router.get("/cuadres/lista")
async def resumen_cuadres(fecha: str = Query(...)):
    print(f"Obteniendo resumen de cuadres para la fecha: {fecha}")
    try:
        colecciones = [f"CUADRES-0{i}" for i in range(1, 8)]
        total = 0
        suma_montos = 0.0
        todos_cuadres = []
        for nombre in colecciones:
            collection = db[nombre]
            filtro = {"dia": fecha}
            cuadres = await collection.find(filtro).to_list(length=None)
            for c in cuadres:
                c["_id"] = str(c["_id"])
            total += len(cuadres)
            suma_montos += sum(c.get("totalCajaSistemaBs", 0) for c in cuadres)
            todos_cuadres.extend(cuadres)
        print(f"Procesada colección {nombre}: {len(cuadres)} cuadres")
        return {
            "fecha": fecha,
            "cantidad": total,
            "suma_montos": suma_montos,
            "cuadres": todos_cuadres
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Endpoint 2: Detalle de cuadres por fecha o rango
@router.get("/cuadres/detalle")
async def detalle_cuadres(
    id: Optional[str] = Query(None),
    fecha: Optional[str] = Query(None),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None)
):
    try:
        colecciones = [f"CUADRES-0{i}" for i in range(1, 8)]
        # Si se pasa id, buscar por id en todas las colecciones
        if id:
            for nombre in colecciones:
                collection = db[nombre]
                cuadre = await collection.find_one({"_id": ObjectId(id)})
                if cuadre:
                    cuadre["_id"] = str(cuadre["_id"])
                    return [cuadre]
            raise HTTPException(status_code=404, detail="Cuadre no encontrado")
        filtro = {}
        if fecha:
            filtro["dia"] = fecha
        elif fecha_inicio and fecha_fin:
            filtro["dia"] = {"$gte": fecha_inicio, "$lte": fecha_fin}
        resultado = []
        for nombre in colecciones:
            collection = db[nombre]
            cuadres = await collection.find(filtro).to_list(length=None)
            for c in cuadres:
                c["_id"] = str(c["_id"])
            resultado.extend(cuadres)
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Endpoint 3: Modificar cuadre por ID
@router.patch("/cuadres/{id}")
async def modificar_cuadre(id: str, data: dict = Body(...)):
    try:
        colecciones = [f"CUADRES-0{i}" for i in range(1, 8)]
        for nombre in colecciones:
            collection = db[nombre]
            result = await collection.update_one({"_id": ObjectId(id)}, {"$set": data})
            if result.modified_count > 0:
                return {"message": "Cuadre modificado exitosamente"}
        raise HTTPException(status_code=404, detail="Cuadre no encontrado o sin cambios")
    except Exception as e:
        print(str(e))
        raise HTTPException(status_code=500, detail=str(e))