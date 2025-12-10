"""
Script para otorgar todos los permisos al usuario ferreterialospuentes@gmail.com
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

MONGO_URI = "mongodb+srv://rapifarma:w1Y7HoezUiMtfrWt@cluster0.9nirn5t.mongodb.net/?appName=Cluster0"
DATABASE_NAME = "ferreteria_los_puentes"

# Lista completa de permisos basada en los módulos del sistema
TODOS_LOS_PERMISOS = [
    # Permisos generales
    "ver_inicio",
    "ver_about",
    
    # Permisos de cuadres
    "agregar_cuadre",
    "verificar_cuadres",
    "ver_cuadres_dia",
    "editar_cuadre",
    "eliminar_cuadre",
    "ver_cuadres",
    "aprobar_cuadre",
    "rechazar_cuadre",
    
    # Permisos de gastos
    "verificar_gastos",
    "agregar_gasto",
    "editar_gasto",
    "eliminar_gasto",
    "ver_gastos",
    "aprobar_gasto",
    "rechazar_gasto",
    
    # Permisos de cuentas por pagar
    "ver_cuentas_por_pagar",
    "agregar_cuenta_por_pagar",
    "editar_cuenta_por_pagar",
    "eliminar_cuenta_por_pagar",
    "pagar_cuenta_por_pagar",
    "verificar_cuenta_por_pagar",
    
    # Permisos de pagos CPP
    "ver_pagos_cpp",
    "agregar_pago_cpp",
    "editar_pago_cpp",
    "eliminar_pago_cpp",
    
    # Permisos de inventarios
    "ver_inventarios",
    "agregar_inventario",
    "editar_inventario",
    "eliminar_inventario",
    "actualizar_estado_inventario",
    
    # Permisos de compras
    "ver_compras",
    "agregar_compra",
    "editar_compra",
    "eliminar_compra",
    
    # Permisos de ventas
    "ver_ventas",
    "agregar_venta",
    "editar_venta",
    "eliminar_venta",
    
    # Permisos de productos
    "ver_productos",
    "agregar_producto",
    "editar_producto",
    "eliminar_producto",
    
    # Permisos de clientes
    "ver_clientes",
    "agregar_cliente",
    "editar_cliente",
    "eliminar_cliente",
    
    # Permisos de proveedores
    "ver_proveedores",
    "agregar_proveedor",
    "editar_proveedor",
    "eliminar_proveedor",
    
    # Permisos de usuarios
    "ver_usuarios",
    "agregar_usuario",
    "editar_usuario",
    "eliminar_usuario",
    "editar_permisos_usuario",
    
    # Permisos de farmacias
    "ver_farmacias",
    "agregar_farmacia",
    "editar_farmacia",
    "eliminar_farmacia",
    
    # Permisos de bancos
    "ver_bancos",
    "agregar_banco",
    "editar_banco",
    "eliminar_banco",
    
    # Permisos de movimientos bancarios
    "ver_movimientos_bancos",
    "agregar_movimiento_banco",
    "editar_movimiento_banco",
    "eliminar_movimiento_banco",
    
    # Permisos de cajeros
    "ver_cajeros",
    "agregar_cajero",
    "editar_cajero",
    "eliminar_cajero",
    
    # Permisos de metas
    "ver_metas",
    "agregar_meta",
    "editar_meta",
    "eliminar_meta",
    "marcar_meta_cumplida",
    
    # Permisos de configuración
    "ver_configuracion",
    "editar_configuracion",
    
    # Permisos administrativos
    "admin",
    "super_admin",
    "acceso_total",
]

async def grant_all_permissions():
    """Otorga todos los permisos al usuario"""
    client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client[DATABASE_NAME]
    usuarios_collection = db["USUARIOS"]
    
    correo = "ferreterialospuentes@gmail.com"
    
    try:
        print("=" * 60)
        print("🔐 Otorgando todos los permisos al usuario")
        print("=" * 60)
        print(f"📧 Usuario: {correo}")
        print(f"📋 Total de permisos: {len(TODOS_LOS_PERMISOS)}")
        print("=" * 60)
        
        # Buscar usuario
        usuario = await usuarios_collection.find_one({"correo": correo})
        
        if not usuario:
            print(f"❌ Usuario '{correo}' no encontrado")
            return
        
        print(f"✅ Usuario encontrado: {usuario.get('correo')}")
        
        # Actualizar permisos
        await usuarios_collection.update_one(
            {"correo": correo},
            {"$set": {"permisos": TODOS_LOS_PERMISOS}}
        )
        
        print(f"\n✅ Permisos actualizados exitosamente!")
        print(f"   Total de permisos otorgados: {len(TODOS_LOS_PERMISOS)}")
        
        # Verificar
        usuario_actualizado = await usuarios_collection.find_one({"correo": correo})
        permisos_actuales = usuario_actualizado.get("permisos", [])
        
        print(f"\n📋 Permisos otorgados ({len(permisos_actuales)}):")
        for i, permiso in enumerate(permisos_actuales, 1):
            print(f"   {i}. {permiso}")
        
        print("\n" + "=" * 60)
        print("✅ Proceso completado")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(grant_all_permissions())


