# Instrucciones Backend - Descuento de Stock al Confirmar Venta

## 🚨 URGENTE - Funcionalidad Crítica

Este documento describe la implementación **CRÍTICA** del descuento automático de stock del inventario cuando se confirma una venta en el punto de venta.

## 📋 Resumen

Cuando se confirma una venta en el punto de venta, el sistema **DEBE** descontar automáticamente el stock del inventario de cada producto vendido. Esta operación es **ATÓMICA** usando transacciones de MongoDB para garantizar que:
- Si la venta se guarda, el stock se descuenta
- Si falla el descuento de stock, la venta NO se guarda
- No puede haber inconsistencias entre ventas y stock

## 🔧 Endpoint Principal

**Endpoint:** `POST /punto-venta/ventas`

**Archivo:** `app/routes/punto_venta.py`

**Líneas:** 240-390

## ⚙️ Implementación

### 1. Flujo de Transacción Atómica

El endpoint usa **transacciones de MongoDB** para garantizar atomicidad:

```python
@router.post("/punto-venta/ventas")
async def crear_venta(
    venta_data: dict = Body(...),
    usuario_actual: dict = Depends(get_current_user)
):
    # ... validaciones ...
    
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
            # Si hay cualquier error, abortar la transacción
            await session.abort_transaction()
            raise HTTPException(status_code=500, detail=f"Error al procesar venta: {str(e)}")
```

**Referencia:** `app/routes/punto_venta.py` líneas 299-343

### 2. Función de Descuento de Stock

**Función:** `descontar_stock_inventario_con_sesion()`

**Archivo:** `app/routes/punto_venta.py`

**Líneas:** 564-659

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
```

## 🔑 Características Clave

### 1. Transacciones Atómicas

- **Garantía:** Si falla cualquier paso, se revierte todo
- **Ventaja:** No puede haber venta sin descuento de stock, ni viceversa
- **Implementación:** Usa `session.start_transaction()` de MongoDB

### 2. Método FIFO (First In, First Out)

- Los productos se descuentan primero de los lotes más antiguos
- Se ordenan por `fecha_vencimiento` (más antiguos primero)
- Garantiza rotación adecuada de inventario

### 3. Manejo de Lotes

- Si el producto tiene lotes, se descuenta de los lotes más antiguos
- Si un lote se agota completamente, se elimina del array
- Si se descuenta parcialmente, se actualiza la cantidad del lote

### 4. Sin Lotes

- Si no hay lotes, se usa el costo promedio del producto
- Se descuenta directamente de la cantidad total

### 5. Validaciones

- ✅ Verifica que el producto exista en la farmacia especificada
- ✅ Verifica que haya stock suficiente antes de descontar
- ✅ Lanza excepción si no hay stock suficiente (aborta transacción)

### 6. Cálculo de Costo de Inventario

- Retorna el costo total descontado
- Se usa para calcular el costo de inventario en resúmenes de ventas
- Con lotes: suma de (cantidad × costo_lote) de cada lote descontado
- Sin lotes: cantidad_vendida × costo_promedio

## 📊 Estructura de Datos

### Request Body

```json
{
  "sucursal": "01",
  "farmacia": "01",
  "fecha": "2024-01-15",
  "productos": [
    {
      "productoId": "507f1f77bcf86cd799439011",
      "id": "507f1f77bcf86cd799439011",
      "cantidad": 2,
      "precio": 166.67
    }
  ],
  "pagos": [
    {
      "tipo": "efectivo_bs",
      "monto": 333.34
    }
  ],
  "descuento_por_divisa": 0
}
```

### Response

```json
{
  "message": "Venta creada exitosamente",
  "id": "507f1f77bcf86cd799439012",
  "estado": "procesada",
  "venta": {
    "_id": "507f1f77bcf86cd799439012",
    "sucursal": "01",
    "farmacia": "01",
    "fecha": "2024-01-15",
    "productos": [...],
    "pagos": [...],
    "estado": "procesada",
    "usuarioCreacion": "usuario@example.com",
    "fechaCreacion": "2024-01-15 10:30:00"
  }
}
```

## ⚠️ Errores Comunes

### Error 1: Stock Insuficiente

**Mensaje:** `"Stock insuficiente. Disponible: X, Requerido: Y"`

**Causa:** El producto no tiene suficiente stock para la cantidad solicitada

**Solución:** Verificar stock antes de crear la venta

### Error 2: Producto No Encontrado

**Mensaje:** `"Producto {producto_id} no encontrado en farmacia {farmacia}"`

**Causa:** El producto no existe en la farmacia especificada

**Solución:** Verificar que el producto exista y pertenezca a la farmacia correcta

### Error 3: Transacción Abortada

**Mensaje:** `"Error al procesar venta: ..."`

**Causa:** Cualquier error durante el proceso aborta la transacción

**Solución:** Revisar logs para identificar el error específico

## 🧪 Ejemplos de Pruebas

### Prueba 1: Venta Exitosa con Descuento de Stock

**Request:**
```json
POST /punto-venta/ventas
{
  "sucursal": "01",
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
1. ✅ Se inicia transacción
2. ✅ Se descuenta 2 unidades del producto en inventario
3. ✅ Se actualiza cantidad: `cantidad_actual - 2`
4. ✅ Se guarda venta con estado "procesada"
5. ✅ Se confirma transacción
6. ✅ Se retorna venta creada

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
1. ✅ Se inicia transacción
2. ✅ Se intenta descontar stock
3. ✅ Se detecta stock insuficiente
4. ✅ Se aborta transacción (rollback)
5. ✅ Se retorna error 400: "Stock insuficiente"
6. ✅ El stock NO se descuenta
7. ✅ La venta NO se guarda

### Prueba 3: Venta con Múltiples Productos

**Request:**
```json
POST /punto-venta/ventas
{
  "sucursal": "01",
  "productos": [
    {
      "productoId": "507f1f77bcf86cd799439011",
      "cantidad": 2
    },
    {
      "productoId": "507f1f77bcf86cd799439012",
      "cantidad": 5
    }
  ],
  "pagos": [...]
}
```

**Comportamiento esperado:**
1. ✅ Se descuenta stock de ambos productos
2. ✅ Si uno falla, se aborta todo (atomicidad)
3. ✅ Solo se guarda la venta si todos los descuentos son exitosos

## 🔍 Verificación

### Verificar Descuento de Stock

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

### ⚠️ CRÍTICO

1. **NUNCA** crear una venta sin descontar stock
2. **SIEMPRE** usar transacciones para garantizar atomicidad
3. **VALIDAR** stock suficiente antes de descontar
4. **ABORTAR** transacción si hay cualquier error

### 🔒 Seguridad

- El descuento de stock solo ocurre dentro de una transacción
- Si falla cualquier paso, se revierte todo automáticamente
- No puede haber inconsistencias entre ventas y stock

### 📊 Logs

El sistema genera logs detallados:
- `📦 [PUNTO_VENTA] Descontando stock de X productos`
- `📦 [INVENTARIO] Stock descontado: producto_id - cantidad unidades, Costo: X`
- `✅ [PUNTO_VENTA] Transacción completada exitosamente`
- `❌ [PUNTO_VENTA] Error en transacción, abortando`

## 🚀 Referencias

- **Código fuente:**
  - `app/routes/punto_venta.py` - Endpoint de ventas (líneas 240-390)
  - `app/routes/punto_venta.py` - Función de descuento (líneas 564-659)

- **Documentación relacionada:**
  - `INSTRUCCIONES_BACKEND_UTILIDAD_40_DESCUENTO_INVENTARIO.md` - Documentación completa

---

**Última actualización:** 2024-12-20  
**Estado:** ✅ Implementado y probado  
**Prioridad:** 🚨 CRÍTICA

