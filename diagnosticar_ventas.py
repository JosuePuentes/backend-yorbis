"""
Script para diagnosticar ventas en la base de datos
Verifica si las ventas se guardan correctamente con estado "procesada"
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import certifi
from bson import ObjectId
from datetime import datetime

# Cargar variables de entorno
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME") or "ferreteria_los_puentes"

async def diagnosticar_ventas(sucursal: str = "01"):
    """
    Diagnostica las ventas en la base de datos
    """
    try:
        if not MONGO_URI:
            print("=" * 80)
            print("ERROR: MONGO_URI no esta configurada")
            print("=" * 80)
            print("\nPara usar este script, necesitas:")
            print("1. Crear un archivo .env en la raiz del proyecto con:")
            print("   MONGO_URI=mongodb+srv://usuario:password@cluster.mongodb.net/")
            print("   DATABASE_NAME=ferreteria_los_puentes")
            print("\n2. O configurar las variables de entorno del sistema")
            print("=" * 80)
            return
        
        # Conectar a MongoDB
        client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
        db = client[DATABASE_NAME]
        ventas_collection = db["VENTAS"]
        
        print("=" * 80)
        print("DIAGNOSTICO DE VENTAS EN LA BASE DE DATOS")
        print("=" * 80)
        
        # 1. Contar total de ventas
        total_ventas = await ventas_collection.count_documents({})
        print(f"\n1. TOTAL DE VENTAS EN LA BD: {total_ventas}")
        
        # 2. Contar ventas con estado "procesada"
        ventas_procesadas = await ventas_collection.count_documents({"estado": "procesada"})
        print(f"2. VENTAS CON ESTADO 'procesada': {ventas_procesadas}")
        
        # 3. Ver estados distintos
        estados_distintos = await ventas_collection.distinct("estado")
        print(f"3. ESTADOS DISTINTOS EN LA BD: {estados_distintos}")
        
        # 4. Contar ventas por estado
        print(f"\n4. VENTAS POR ESTADO:")
        for estado in estados_distintos:
            count = await ventas_collection.count_documents({"estado": estado})
            print(f"   - '{estado}': {count} ventas")
        
        # 5. Contar ventas de la sucursal
        ventas_sucursal = await ventas_collection.count_documents({
            "$or": [
                {"sucursal": sucursal},
                {"farmacia": sucursal}
            ]
        })
        print(f"\n5. VENTAS DE LA SUCURSAL '{sucursal}': {ventas_sucursal}")
        
        # 6. Contar ventas con estado "procesada" de la sucursal
        ventas_procesadas_sucursal = await ventas_collection.count_documents({
            "estado": "procesada",
            "$or": [
                {"sucursal": sucursal},
                {"farmacia": sucursal}
            ]
        })
        print(f"6. VENTAS CON ESTADO 'procesada' DE LA SUCURSAL '{sucursal}': {ventas_procesadas_sucursal}")
        
        # 7. Ver las últimas 5 ventas
        print(f"\n7. ULTIMAS 5 VENTAS CREADAS:")
        ultimas_ventas = await ventas_collection.find({}).sort("fechaCreacion", -1).limit(5).to_list(length=5)
        if ultimas_ventas:
            for i, venta in enumerate(ultimas_ventas, 1):
                print(f"\n   Venta {i}:")
                print(f"      ID: {venta.get('_id')}")
                print(f"      Estado: '{venta.get('estado', 'N/A')}'")
                print(f"      Sucursal: {venta.get('sucursal', venta.get('farmacia', 'N/A'))}")
                print(f"      Fecha: {venta.get('fecha', 'N/A')}")
                print(f"      Fecha creacion: {venta.get('fechaCreacion', 'N/A')}")
                print(f"      Numero factura: {venta.get('numeroFactura', venta.get('numero_factura', 'N/A'))}")
                print(f"      Productos: {len(venta.get('productos', []))} items")
        else:
            print("   No hay ventas en la base de datos")
        
        # 8. Ver ventas con estado "procesada" de la sucursal
        print(f"\n8. VENTAS CON ESTADO 'procesada' DE LA SUCURSAL '{sucursal}':")
        ventas_filtradas = await ventas_collection.find({
            "estado": "procesada",
            "$or": [
                {"sucursal": sucursal},
                {"farmacia": sucursal}
            ]
        }).sort("fechaCreacion", -1).limit(5).to_list(length=5)
        
        if ventas_filtradas:
            for i, venta in enumerate(ventas_filtradas, 1):
                print(f"\n   Venta {i}:")
                print(f"      ID: {venta.get('_id')}")
                print(f"      Estado: '{venta.get('estado')}'")
                print(f"      Numero factura: {venta.get('numeroFactura', venta.get('numero_factura', 'N/A'))}")
                print(f"      Fecha: {venta.get('fecha', 'N/A')}")
                print(f"      Productos: {len(venta.get('productos', []))} items")
                if venta.get('productos'):
                    print(f"      Primer producto: {venta['productos'][0].get('codigo', 'N/A')} - {venta['productos'][0].get('nombre', 'N/A')}")
        else:
            print(f"   No se encontraron ventas con estado 'procesada' de la sucursal '{sucursal}'")
            print(f"   Esto explica por que el endpoint retorna un array vacio")
        
        # 9. Verificar si hay ventas de la sucursal con otros estados
        print(f"\n9. VENTAS DE LA SUCURSAL '{sucursal}' CON OTROS ESTADOS:")
        ventas_otras_estados = await ventas_collection.find({
            "$or": [
                {"sucursal": sucursal},
                {"farmacia": sucursal}
            ],
            "estado": {"$ne": "procesada"}
        }).limit(5).to_list(length=5)
        
        if ventas_otras_estados:
            print(f"   Se encontraron {len(ventas_otras_estados)} ventas con otros estados:")
            for venta in ventas_otras_estados:
                print(f"      - ID: {venta.get('_id')}, Estado: '{venta.get('estado', 'N/A')}'")
        else:
            print(f"   No hay ventas de la sucursal con otros estados")
        
        # 10. Resumen y recomendaciones
        print(f"\n" + "=" * 80)
        print("RESUMEN Y RECOMENDACIONES")
        print("=" * 80)
        
        if total_ventas == 0:
            print("❌ PROBLEMA: No hay ventas en la base de datos")
            print("   SOLUCION: Crear una venta desde el punto de venta")
        elif ventas_procesadas == 0:
            print("❌ PROBLEMA: No hay ventas con estado 'procesada'")
            print(f"   Estados encontrados: {estados_distintos}")
            print("   SOLUCION: Verificar que el endpoint POST /punto-venta/ventas")
            print("            establezca el estado como 'procesada' exactamente")
        elif ventas_procesadas_sucursal == 0:
            print(f"❌ PROBLEMA: No hay ventas con estado 'procesada' de la sucursal '{sucursal}'")
            print(f"   Total ventas procesadas: {ventas_procesadas}")
            print(f"   Total ventas de la sucursal: {ventas_sucursal}")
            print("   SOLUCION: Verificar que las ventas se guarden con la sucursal correcta")
        else:
            print(f"✅ OK: Se encontraron {ventas_procesadas_sucursal} ventas con estado 'procesada'")
            print("   El endpoint deberia retornar estas ventas")
            print("   Si el endpoint retorna vacio, verificar los logs del servidor")
        
        print("\n" + "=" * 80)
        print("Diagnostico completado")
        print("=" * 80)
        
        # Cerrar conexión
        client.close()
        
    except Exception as e:
        print(f"Error en diagnostico: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    sucursal = sys.argv[1] if len(sys.argv) > 1 else "01"
    print(f"Diagnosticando ventas para sucursal: {sucursal}")
    asyncio.run(diagnosticar_ventas(sucursal))

