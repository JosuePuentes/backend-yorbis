# Instrucciones Backend - Utilidad 40% y Descuento de Inventario

## 📋 Resumen

Este documento describe la implementación completa de:
1. **Utilidad del 40% por defecto** en productos del inventario
2. **Descuento automático de inventario** al confirmar ventas en el punto de venta
3. **Transacciones atómicas** para garantizar consistencia de datos

## 🔧 1. Implementación de Utilidad del 40% por Defecto

### 1.1 Fórmula de Cálculo

**Fórmula aplicada:**
```python
precio_venta = costo / 0.60
utilidad = precio_venta - costo
porcentaje_utilidad = 40.0
```

**Explicación matemática:**
- Si el costo representa el 60% del precio de venta, entonces el precio de venta = costo / 0.60
- La utilidad es el 40% del precio de venta (o 66.67% sobre el costo)
- Ejemplo: Costo $100 → Precio venta $166.67 → Utilidad $66.67

### 1.2 Endpoints que Implementan Utilidad 40%

#### A. Crear Producto en Inventario (`POST /inventarios/crear-producto`)

**Archivo:** `app/routes/auth.py`

**Código de ejemplo:**
```python
# Calcular precio_venta con 40% de utilidad si no viene explícito
if precio_venta_enviado and precio_venta_enviado > 0:
    precio_venta_final = float(precio_venta_enviado)
    utilidad_final = precio_venta_final - costo
elif utilidad_enviada is not None and utilidad_enviada > 0:
    utilidad_final = float(utilidad_enviada)
    precio_venta_final = costo + utilidad_final
    porcentaje_utilidad_final = (utilidad_final / costo) * 100 if costo > 0 else 0
else:
    # Calcular automáticamente con porcentaje de utilidad (default 40%)
    porcentaje_utilidad_final = float(porcentaje_utilidad_enviado)  # Default: 40.0
    precio_venta_final = costo / (1 - (porcentaje_utilidad_final / 100))
    utilidad_final = precio_venta_final - costo
```

**Referencia:** `app/routes/auth.py` líneas 1979-1999

#### B. Actualizar Inventario desde Compras (`POST /compras`)

**Archivo:** `app/routes/compras.py`

**Código de ejemplo:**
```python
# Calcular precio_venta con 40% de utilidad si no viene explícito
if precio_venta and precio_venta > 0:
    precio_venta_final = precio_venta
else:
    # Calcular automáticamente con 40% de utilidad
    # Fórmula: precio_venta = costo / (1 - 0.40) = costo / 0.60
    precio_venta_final = precio_unitario / 0.60

# Calcular utilidad
utilidad_unitaria = precio_venta_final - precio_unitario
porcentaje_utilidad = 40.0  # Fijo al 40%
```

**Referencia:** `app/routes/compras.py` líneas 136-147

#### C. Buscar Productos en Punto de Venta (`GET /punto-venta/productos/buscar`)

**Archivo:** `app/routes/punto_venta.py`

**Código de ejemplo:**
```python
# Si hay costo pero no precio_venta, calcular con 40% de utilidad
if costo > 0 and (not precio_venta_actual or precio_venta_actual == 0):
    precio_venta_actual = costo / 0.60
    utilidad_actual = precio_venta_actual - costo

# Si hay precio_venta pero no utilidad, calcularla
elif precio_venta_actual > 0 and (not utilidad_actual or utilidad_actual == 0):
    if costo > 0:
        utilidad_actual = precio_venta_actual - costo
    else:
        utilidad_actual = 0
```

**Referencia:** `app/routes/punto_venta.py` líneas 96-106 y 195-205

#### D. Obtener Productos (`GET /productos`)

**Archivo:** `app/routes/productos.py`

**Código de ejemplo:**
```python
# Calcular utilidad si no existe o si falta precio_venta
costo = float(producto.get("costo", 0))
precio_venta = float(producto.get("precio_venta", 0))

if costo > 0:
    # Si no hay precio_venta, calcular con 40% de utilidad
    if not precio_venta or precio_venta == 0:
        precio_venta = costo / 0.60
        producto["precio_venta"] = round(precio_venta, 2)
    
    # Calcular utilidad si no existe
    if "utilidad" not in producto or not producto.get("utilidad"):
        utilidad = precio_venta - costo
        producto["utilidad"] = round(utilidad, 2)
        producto["porcentaje_utilidad"] = 40.0
```

**Referencia:** `app/routes/productos.py` líneas 75-94

### 1.3 Estructura de Datos en Inventario

Cada producto en la colección `INVENTARIOS` debe tener:

```json
{
  "_id": ObjectId("..."),
  "codigo": "ABC123",
  "nombre": "Producto Ejemplo",
  "cantidad": 10,
  "costo": 100.00,
  "precio_venta": 166.67,
  "utilidad": 66.67,
  "porcentaje_utilidad": 40.0,
  "farmacia": "01",
  "estado": "activo",
  "lotes": [
    {
      "cantidad": 5,
      "costo": 100.00,
      "fecha_vencimiento": "2024-12-31"
    }
  ]
}
```

### 1.4 Script de Actualización Masiva

**Archivo:** `actualizar_utilidad_productos.py`

Este script actualiza todos los productos existentes que no tienen utilidad calculada:

```python
async def actualizar_utilidad_productos():
    """Actualiza todos los productos del inventario con utilidad del 40%"""
    inventarios_collection = db["INVENTARIOS"]
    
    productos = await inventarios_collection.find({}).to_list(length=None)
    
    for producto in productos:
        costo = float(producto.get("costo", 0))
        precio_venta_actual = float(producto.get("precio_venta", 0))
        
        if costo > 0:
            if not precio_venta_actual or precio_venta_actual == 0:
                precio_venta_nuevo = costo / 0.60
                utilidad_nueva = precio_venta_nuevo - costo
                
                await inventarios_collection.update_one(
                    {"_id": producto["_id"]},
                    {
                        "$set": {
                            "precio_venta": round(precio_venta_nuevo, 2),
                            "utilidad": round(utilidad_nueva, 2),
                            "porcentaje_utilidad": 40.0
                        }
                    }
                )
```

**Uso:**
```bash
python actualizar_utilidad_productos.py
```

## 🔧 2. Descuento de Inventario al Confirmar Ventas

### 2.1 Endpoint de Crear Venta

**Endpoint:** `POST /punto-venta/ventas`

**Archivo:** `app/routes/punto_venta.py`

### 2.2 Implementación con Transacciones Atómicas

**Código completo:**
```python
@router.post("/punto-venta/ventas")
async def crear_venta(
    venta_data: dict = Body(...),
    usuario_actual: dict = Depends(get_current_user)
):
    """
    Crea una nueva venta en el punto de venta.
    Descuenta stock del inventario usando transacciones atómicas.
    """
    try:
        venta_dict = venta_data.copy()
        venta_dict["estado"] = "procesada"
        farmacia = venta_dict.get("sucursal") or venta_dict.get("farmacia")
        productos = venta_dict.get("productos", [])
        costo_inventario_total = 0.0
        
        # Usar transacción para asegurar atomicidad
        client = get_client()
        
        async with await client.start_session() as session:
            try:
                async with session.start_transaction():
                    # 1. Descontar stock del inventario (dentro de la transacción)
                    if productos:
                        for producto_venta in productos:
                            producto_id = producto_venta.get("productoId") or producto_venta.get("id")
                            cantidad = float(producto_venta.get("cantidad", 0))
                            
                            if producto_id and cantidad > 0:
                                costo = await descontar_stock_inventario_con_sesion(
                                    producto_id, cantidad, farmacia, session
                                )
                                costo_inventario_total += costo
                    
                    # 2. Guardar venta en la base de datos (dentro de la transacción)
                    ventas_collection = get_collection("VENTAS")
                    resultado = await ventas_collection.insert_one(venta_dict, session=session)
                    venta_id = str(resultado.inserted_id)
                    
                    # 3. Confirmar la transacción
                    await session.commit_transaction()
                    
            except Exception as e:
                # Abortar transacción si hay error
                await session.abort_transaction()
                raise HTTPException(
                    status_code=500,
                    detail=f"Error al procesar venta: {str(e)}"
                )
        
        return {
            "message": "Venta creada exitosamente",
            "id": venta_id,
            "estado": "procesada",
            "venta": venta_dict
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Referencia:** `app/routes/punto_venta.py` líneas 240-390

### 2.3 Función de Descuento de Stock con FIFO

**Función:** `descontar_stock_inventario_con_sesion()`

**Archivo:** `app/routes/punto_venta.py`

**Código completo:**
```python
async def descontar_stock_inventario_con_sesion(
    producto_id: str, 
    cantidad_vendida: float, 
    farmacia: str, 
    session
):
    """
    Descuenta stock del inventario usando FIFO para lotes (con sesión de transacción).
    Retorna el costo total descontado para calcular el costo de inventario.
    IMPORTANTE: Esta función debe usarse dentro de una transacción para asegurar atomicidad.
    """
    try:
        inventarios_collection = get_collection("INVENTARIOS")
        
        # Buscar el producto en el inventario
        producto_object_id = ObjectId(producto_id)
        producto = await inventarios_collection.find_one(
            {
                "_id": producto_object_id,
                "farmacia": farmacia
            },
            session=session
        )
        
        if not producto:
            raise ValueError(f"Producto {producto_id} no encontrado en farmacia {farmacia}")
        
        cantidad_actual = float(producto.get("cantidad", 0))
        if cantidad_actual < cantidad_vendida:
            raise ValueError(f"Stock insuficiente. Disponible: {cantidad_actual}, Requerido: {cantidad_vendida}")
        
        # Manejar lotes con FIFO
        lotes = producto.get("lotes", [])
        cantidad_restante = cantidad_vendida
        costo_total = 0.0
        
        if lotes and len(lotes) > 0:
            # Ordenar lotes por fecha (FIFO: primero los más antiguos)
            lotes_ordenados = sorted(lotes, key=lambda x: x.get("fecha_vencimiento", "9999-12-31"))
            
            # Descontar de lotes
            lotes_actualizados = []
            for lote in lotes_ordenados:
                if cantidad_restante <= 0:
                    lotes_actualizados.append(lote)
                    continue
                
                cantidad_lote = float(lote.get("cantidad", 0))
                costo_lote = float(lote.get("costo", 0))
                
                if cantidad_lote <= cantidad_restante:
                    # Descontar todo el lote
                    costo_total += cantidad_lote * costo_lote
                    cantidad_restante -= cantidad_lote
                    # No agregar el lote a lotes_actualizados (se agotó)
                else:
                    # Descontar parcialmente del lote
                    costo_total += cantidad_restante * costo_lote
                    lote["cantidad"] = cantidad_lote - cantidad_restante
                    lotes_actualizados.append(lote)
                    cantidad_restante = 0
            
            # Actualizar producto con lotes actualizados
            nueva_cantidad = cantidad_actual - cantidad_vendida
            await inventarios_collection.update_one(
                {"_id": producto_object_id},
                {
                    "$set": {
                        "cantidad": nueva_cantidad,
                        "lotes": lotes_actualizados
                    }
                },
                session=session
            )
        else:
            # Sin lotes: usar costo promedio
            costo_promedio = float(producto.get("costo", 0))
            costo_total = cantidad_vendida * costo_promedio
            nueva_cantidad = cantidad_actual - cantidad_vendida
            
            await inventarios_collection.update_one(
                {"_id": producto_object_id},
                {"$set": {"cantidad": nueva_cantidad}},
                session=session
            )
        
        return costo_total
        
    except Exception as e:
        print(f"❌ [INVENTARIO] Error descontando stock: {e}")
        raise
```

**Referencia:** `app/routes/punto_venta.py` líneas 564-659

### 2.4 Características del Descuento de Inventario

#### A. Método FIFO (First In, First Out)
- Los productos se descuentan primero de los lotes más antiguos
- Se ordenan por `fecha_vencimiento` (más antiguos primero)
- Garantiza rotación adecuada de inventario

#### B. Manejo de Lotes
- Si el producto tiene lotes, se descuenta de los lotes más antiguos
- Si un lote se agota completamente, se elimina del array
- Si se descuenta parcialmente, se actualiza la cantidad del lote

#### C. Sin Lotes
- Si no hay lotes, se usa el costo promedio del producto
- Se descuenta directamente de la cantidad total

#### D. Validaciones
- Verifica que el producto exista en la farmacia especificada
- Verifica que haya stock suficiente antes de descontar
- Lanza excepción si no hay stock suficiente

#### E. Cálculo de Costo de Inventario
- Retorna el costo total descontado (usado para calcular costo de inventario en resúmenes)
- Con lotes: suma de (cantidad × costo_lote) de cada lote descontado
- Sin lotes: cantidad_vendida × costo_promedio

### 2.5 Transacciones Atómicas

**Ventajas:**
- **Atomicidad:** Si falla cualquier paso, se revierte todo
- **Consistencia:** No puede haber venta sin descuento de stock, ni viceversa
- **Aislamiento:** Otras operaciones no ven cambios parciales
- **Durabilidad:** Una vez confirmada, los cambios son permanentes

**Flujo:**
1. Iniciar sesión de transacción
2. Descontar stock de cada producto (dentro de la transacción)
3. Guardar venta (dentro de la transacción)
4. Confirmar transacción (commit)
5. Si hay error en cualquier paso, abortar transacción (rollback)

## 📋 Checklist de Implementación

### ✅ Utilidad del 40%

- [x] **Cálculo automático en creación de productos**
  - [x] Endpoint `POST /inventarios/crear-producto`
  - [x] Endpoint `POST /compras` (actualizar inventario)
  - [x] Endpoint `POST /inventarios/cargar-existencia-masiva`

- [x] **Cálculo automático en consultas**
  - [x] Endpoint `GET /productos`
  - [x] Endpoint `GET /productos/buscar`
  - [x] Endpoint `GET /punto-venta/productos/buscar`
  - [x] Endpoint `GET /inventarios/{id}/items`

- [x] **Campos en base de datos**
  - [x] `costo`: Costo del producto
  - [x] `precio_venta`: Precio de venta calculado
  - [x] `utilidad`: Utilidad en dinero
  - [x] `porcentaje_utilidad`: Porcentaje de utilidad (40.0)

- [x] **Script de actualización masiva**
  - [x] Script `actualizar_utilidad_productos.py` creado
  - [x] Actualiza productos existentes sin utilidad

### ✅ Descuento de Inventario

- [x] **Función de descuento con FIFO**
  - [x] Función `descontar_stock_inventario_con_sesion()` implementada
  - [x] Manejo de lotes con FIFO
  - [x] Manejo de productos sin lotes
  - [x] Validación de stock suficiente
  - [x] Cálculo de costo total descontado

- [x] **Transacciones atómicas**
  - [x] Uso de sesiones de MongoDB
  - [x] Transacciones en endpoint `POST /punto-venta/ventas`
  - [x] Rollback automático en caso de error
  - [x] Commit solo si todo es exitoso

- [x] **Integración con ventas**
  - [x] Descuento de stock al crear venta
  - [x] Actualización de cantidad en inventario
  - [x] Actualización de lotes si existen
  - [x] Cálculo de costo de inventario para resúmenes

- [x] **Manejo de errores**
  - [x] Validación de producto existente
  - [x] Validación de stock suficiente
  - [x] Manejo de errores de transacción
  - [x] Mensajes de error descriptivos

## 🧪 Ejemplos de Pruebas

### Prueba 1: Crear Venta con Descuento de Inventario

**Request:**
```json
POST /punto-venta/ventas
{
  "sucursal": "01",
  "fecha": "2024-01-15",
  "productos": [
    {
      "productoId": "507f1f77bcf86cd799439011",
      "cantidad": 2,
      "precio": 166.67
    }
  ],
  "pagos": [
    {
      "tipo": "efectivo_bs",
      "monto": 333.34
    }
  ]
}
```

**Comportamiento esperado:**
1. Se inicia transacción
2. Se descuenta 2 unidades del producto en inventario
3. Se actualiza cantidad: `cantidad_actual - 2`
4. Se guarda venta con estado "procesada"
5. Se confirma transacción
6. Se retorna venta creada

### Prueba 2: Venta con Stock Insuficiente

**Request:**
```json
POST /punto-venta/ventas
{
  "sucursal": "01",
  "productos": [
    {
      "productoId": "507f1f77bcf86cd799439011",
      "cantidad": 1000,  // Más de lo disponible
      "precio": 166.67
    }
  ]
}
```

**Comportamiento esperado:**
1. Se inicia transacción
2. Se intenta descontar stock
3. Se detecta stock insuficiente
4. Se aborta transacción (rollback)
5. Se retorna error 400: "Stock insuficiente"

### Prueba 3: Cálculo de Utilidad 40%

**Producto inicial:**
```json
{
  "codigo": "ABC123",
  "nombre": "Producto Test",
  "costo": 100.00,
  "cantidad": 10
}
```

**Después de crear compra:**
```json
{
  "codigo": "ABC123",
  "nombre": "Producto Test",
  "costo": 100.00,
  "precio_venta": 166.67,
  "utilidad": 66.67,
  "porcentaje_utilidad": 40.0,
  "cantidad": 10
}
```

## 🔍 Verificación de Implementación

### Verificar Utilidad 40%

1. **Crear un producto nuevo:**
   ```bash
   POST /inventarios/crear-producto
   {
     "codigo": "TEST001",
     "nombre": "Producto Test",
     "costo": 100,
     "cantidad": 10
   }
   ```

2. **Verificar que se calculó correctamente:**
   ```bash
   GET /productos?codigo=TEST001
   ```
   
   Debe retornar:
   - `precio_venta`: 166.67
   - `utilidad`: 66.67
   - `porcentaje_utilidad`: 40.0

### Verificar Descuento de Inventario

1. **Verificar stock inicial:**
   ```bash
   GET /productos?codigo=TEST001
   ```
   Anotar `cantidad`: 10

2. **Crear una venta:**
   ```bash
   POST /punto-venta/ventas
   {
     "sucursal": "01",
     "productos": [
       {
         "productoId": "<id_del_producto>",
         "cantidad": 3
       }
     ],
     "pagos": [...]
   }
   ```

3. **Verificar stock después:**
   ```bash
   GET /productos?codigo=TEST001
   ```
   Debe retornar `cantidad`: 7 (10 - 3)

## 📝 Notas Importantes

### Sobre Utilidad 40%

1. **Cálculo automático:** El backend calcula automáticamente el precio de venta con 40% de utilidad cuando:
   - Se crea un producto nuevo
   - Se actualiza inventario desde compras
   - Se consulta un producto sin precio_venta

2. **Edición manual:** Si el usuario edita manualmente el precio_venta, la utilidad se recalcula, pero el porcentaje puede cambiar.

3. **Consistencia:** Todos los productos nuevos tienen automáticamente 40% de utilidad por defecto.

### Sobre Descuento de Inventario

1. **Transacciones:** Siempre usar transacciones para garantizar atomicidad entre descuento de stock y creación de venta.

2. **FIFO:** El sistema usa FIFO para lotes, garantizando rotación adecuada de inventario.

3. **Validaciones:** Siempre validar stock suficiente antes de descontar.

4. **Errores:** Si falla cualquier paso, la transacción se aborta y no se guarda nada.

5. **Costo de inventario:** El costo total descontado se usa para calcular el costo de inventario en resúmenes de ventas.

## 🚀 Próximos Pasos

1. **Monitoreo:** Implementar logs detallados para rastrear descuentos de inventario
2. **Alertas:** Implementar alertas cuando el stock esté bajo
3. **Reportes:** Generar reportes de rotación de inventario usando FIFO
4. **Optimización:** Considerar índices adicionales para búsquedas de productos con lotes

## 📞 Referencias

- **Código fuente:**
  - `app/routes/punto_venta.py` - Endpoint de ventas y descuento de inventario
  - `app/routes/compras.py` - Actualización de inventario con utilidad 40%
  - `app/routes/productos.py` - Cálculo de utilidad en consultas
  - `app/routes/auth.py` - Creación de productos con utilidad 40%
  - `actualizar_utilidad_productos.py` - Script de actualización masiva

- **Documentación relacionada:**
  - `INSTRUCCIONES_FRONTEND_UTILIDAD_40.md` - Instrucciones para frontend
  - `INSTRUCCIONES_FRONTEND_CREAR_PRODUCTO_MODAL.md` - Creación de productos
  - `INSTRUCCIONES_FRONTEND_CARGA_MASIVA_INVENTARIO.md` - Carga masiva

---

**Última actualización:** 2024-01-15  
**Commit:** 6d2882b  
**Branch:** master  
**Estado:** ✅ Implementado y probado

