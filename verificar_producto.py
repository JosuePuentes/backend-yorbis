"""
Script para verificar información completa de un producto en la base de datos
"""
import asyncio
import sys
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

# Cargar variables de entorno
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME") or "ferreteria_los_puentes"

async def verificar_producto(codigo: str):
    """
    Verifica toda la información de un producto por su código
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
        inventarios_collection = db["INVENTARIOS"]
        
        # Buscar el producto por código (case insensitive)
        producto = await inventarios_collection.find_one({
            "codigo": {"$regex": f"^{codigo}$", "$options": "i"}
        })
        
        if not producto:
            print(f"ERROR: Producto con codigo '{codigo}' no encontrado en la base de datos")
            return
        
        print("=" * 80)
        print(f"INFORMACION COMPLETA DEL PRODUCTO: {codigo.upper()}")
        print("=" * 80)
        
        # Información básica
        print("\nINFORMACION BASICA:")
        print(f"   ID: {producto.get('_id')}")
        print(f"   Código: {producto.get('codigo', 'N/A')}")
        print(f"   Nombre: {producto.get('nombre', 'N/A')}")
        print(f"   Descripción: {producto.get('descripcion', 'N/A')}")
        print(f"   Marca: {producto.get('marca', 'N/A') or producto.get('marca_producto', 'N/A')}")
        print(f"   Estado: {producto.get('estado', 'N/A')}")
        print(f"   Farmacia/Sucursal: {producto.get('farmacia', 'N/A')}")
        
        # Información de stock/existencia
        print("\nINFORMACION DE STOCK/EXISTENCIA:")
        cantidad = producto.get("cantidad", 0)
        existencia = producto.get("existencia", 0)
        stock = producto.get("stock", 0)
        
        print(f"   Cantidad: {cantidad}")
        print(f"   Existencia: {existencia}")
        print(f"   Stock: {stock}")
        
        # Determinar valor principal según lógica del sistema
        if existencia > 0:
            valor_principal = existencia
            campo_principal = "existencia"
        elif cantidad > 0:
            valor_principal = cantidad
            campo_principal = "cantidad"
        else:
            valor_principal = stock if stock > 0 else 0
            campo_principal = "stock"
        
        print(f"\n   >>> Valor principal (usado por el sistema): {valor_principal} (campo: {campo_principal})")
        
        # Información de precios
        print("\nINFORMACION DE PRECIOS:")
        costo = producto.get("costo", 0)
        precio_venta = producto.get("precio_venta", 0) or producto.get("precio", 0)
        utilidad = producto.get("utilidad", 0)
        porcentaje_utilidad = producto.get("porcentaje_utilidad", 0)
        
        print(f"   Costo: ${costo:.2f}")
        print(f"   Precio de venta: ${precio_venta:.2f}")
        print(f"   Utilidad: ${utilidad:.2f}")
        print(f"   Porcentaje de utilidad: {porcentaje_utilidad}%")
        
        # Calcular precio si no existe
        if costo > 0 and (not precio_venta or precio_venta == 0):
            precio_calculado = costo / 0.60
            utilidad_calculada = precio_calculado - costo
            print(f"\n   >>> Precio no definido, se calcularia automaticamente:")
            print(f"      Precio calculado (40% utilidad): ${precio_calculado:.2f}")
            print(f"      Utilidad calculada: ${utilidad_calculada:.2f}")
        
        # Información de lotes
        lotes = producto.get("lotes", [])
        if lotes:
            print(f"\nLOTES ({len(lotes)} lote(s)):")
            for i, lote in enumerate(lotes, 1):
                print(f"   Lote {i}:")
                print(f"      Cantidad: {lote.get('cantidad', 0)}")
                print(f"      Costo: ${lote.get('costo', 0):.2f}")
                print(f"      Fecha vencimiento: {lote.get('fecha_vencimiento', 'N/A')}")
        else:
            print("\nLOTES: Sin lotes (producto sin control de lotes)")
        
        # Información adicional
        print("\nINFORMACION ADICIONAL:")
        if producto.get("categoria"):
            print(f"   Categoría: {producto.get('categoria')}")
        if producto.get("proveedor"):
            print(f"   Proveedor: {producto.get('proveedor')}")
        if producto.get("productoId"):
            print(f"   Producto ID: {producto.get('productoId')}")
        if producto.get("fechaCreacion"):
            print(f"   Fecha creación: {producto.get('fechaCreacion')}")
        if producto.get("fechaActualizacion"):
            print(f"   Fecha actualización: {producto.get('fechaActualizacion')}")
        if producto.get("usuarioCreacion"):
            print(f"   Usuario creación: {producto.get('usuarioCreacion')}")
        
        # Todos los campos disponibles
        print("\nTODOS LOS CAMPOS DISPONIBLES:")
        for key, value in sorted(producto.items()):
            if key != "_id":
                print(f"   {key}: {value}")
        
        print("\n" + "=" * 80)
        print("Verificacion completada")
        print("=" * 80)
        
        # Cerrar conexión
        client.close()
        
    except Exception as e:
        print(f"ERROR verificando producto: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    codigo = sys.argv[1] if len(sys.argv) > 1 else "pppp1"
    print(f"Buscando producto con codigo: {codigo}")
    asyncio.run(verificar_producto(codigo))

