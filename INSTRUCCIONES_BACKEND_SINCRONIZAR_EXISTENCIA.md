# Instrucciones Backend - Sincronizar Existencia entre Endpoints

## 🚨 CRÍTICO - Sincronización de Datos

Este documento describe los requisitos **CRÍTICOS** para que los endpoints de inventario y punto de venta devuelvan la misma existencia y se mantengan sincronizados.

---

## 📋 Resumen del Problema

**Problema anterior:**
- Endpoint `/punto-venta/productos/buscar` mostraba: `cantidad = 2`
- Endpoint `/inventarios/{id}/items` mostraba: `existencia = 1`
- **Inconsistencia:** Valores diferentes causaban confusión y errores

**Solución implementada:**
- Ambos endpoints ahora usan `existencia` como campo principal
- Prioridad: `existencia` > `cantidad` > `stock`
- Todos los campos (`cantidad`, `existencia`, `stock`) tienen el mismo valor en la respuesta

---

## ✅ Requisitos Implementados

### 1. Endpoint `/punto-venta/productos/buscar`

**Archivo:** `app/routes/punto_venta.py`

**Líneas:** 15-238

**Requisitos:**
- ✅ Incluir `existencia` y `stock` en la proyección de MongoDB
- ✅ Usar `existencia` como campo principal
- ✅ Retornar `cantidad`, `existencia` y `stock` con el mismo valor
- ✅ Prioridad: `existencia` > `cantidad` > `stock`

**Código implementado:**
```python
# Proyección incluye existencia y stock
projection={
    "_id": 1, "codigo": 1, "nombre": 1,
    "precio_venta": 1, "precio": 1, 
    "cantidad": 1, "existencia": 1, "stock": 1,  # ← Campos de stock
    "costo": 1, "utilidad": 1, "porcentaje_utilidad": 1,
    "farmacia": 1, "estado": 1, "marca": 1, "marca_producto": 1
}

# Lógica de prioridad
existencia = float(producto.get("existencia", 0))
cantidad = float(producto.get("cantidad", 0))
stock = float(producto.get("stock", 0))

if existencia > 0:
    stock_disponible = existencia
elif cantidad > 0:
    stock_disponible = cantidad
else:
    stock_disponible = stock if stock > 0 else 0

# Respuesta con mismo valor en los tres campos
resultado = {
    "cantidad": float(stock_disponible),      # Usar existencia
    "existencia": float(stock_disponible),    # Campo principal
    "stock": float(stock_disponible),         # Compatibilidad
    # ... otros campos
}
```

### 2. Endpoint `/inventarios/items` y `/inventarios/{id}/items`

**Archivo:** `app/routes/auth.py`

**Líneas:** 1225-1432

**Requisitos:**
- ✅ Incluir `existencia` y `stock` en la proyección de MongoDB
- ✅ Usar `existencia` como campo principal (misma lógica que punto de venta)
- ✅ Retornar `cantidad`, `existencia` y `stock` con el mismo valor
- ✅ Prioridad: `existencia` > `cantidad` > `stock`

**Código implementado:**
```python
# Proyección incluye existencia y stock
proyeccion_minima = {
    "_id": 1, "codigo": 1, "nombre": 1, "descripcion": 1,
    "precio_venta": 1, "precio": 1, "marca": 1, 
    "cantidad": 1, "existencia": 1, "stock": 1,  # ← Campos de stock
    "farmacia": 1, "costo": 1, "estado": 1, 
    "utilidad": 1, "porcentaje_utilidad": 1
}

# Lógica de prioridad (igual que punto de venta)
existencia = float(inv.get("existencia", 0))
cantidad_val = float(inv.get("cantidad", 0))
stock_val = float(inv.get("stock", 0))

if existencia > 0:
    stock_disponible = existencia
elif cantidad_val > 0:
    stock_disponible = cantidad_val
else:
    stock_disponible = stock_val if stock_val > 0 else 0

# Respuesta con mismo valor en los tres campos
resultado = {
    "cantidad": float(stock_disponible),      # Usar existencia
    "existencia": float(stock_disponible),    # Campo principal
    "stock": float(stock_disponible),         # Compatibilidad
    # ... otros campos
}
```

### 3. Endpoint `/punto-venta/ventas` (POST)

**Archivo:** `app/routes/punto_venta.py`

**Líneas:** 240-390

**Requisitos:**
- ✅ Descontar la misma cantidad de `cantidad`, `existencia` y `stock`
- ✅ Usar `existencia` como campo principal para validar stock
- ✅ Actualizar los tres campos con el mismo valor
- ✅ Usar transacciones para garantizar atomicidad

**Código implementado:**
```python
# Función: descontar_stock_inventario_con_sesion()
# Líneas: 579-733

# Validar stock usando existencia como principal
existencia_actual = float(producto.get("existencia", 0))
cantidad_actual = float(producto.get("cantidad", 0))
stock_actual = float(producto.get("stock", 0))

if existencia_actual > 0:
    cantidad_disponible = existencia_actual
elif cantidad_actual > 0:
    cantidad_disponible = cantidad_actual
else:
    cantidad_disponible = stock_actual if stock_actual > 0 else 0

# Descontar y actualizar los tres campos
nueva_cantidad = cantidad_disponible - cantidad_vendida
update_data = {
    "cantidad": nueva_cantidad,
    "existencia": nueva_cantidad,  # Siempre actualizar
    "stock": nueva_cantidad,       # Siempre actualizar
    # ... otros campos
}
```

---

## 🔍 Validaciones Críticas

### 1. Verificar Proyección de MongoDB

**Requisito:** Ambos endpoints deben incluir `existencia` y `stock` en la proyección.

**Verificación:**
```python
# ✅ CORRECTO
projection={
    "cantidad": 1, 
    "existencia": 1,  # ← Debe estar presente
    "stock": 1       # ← Debe estar presente
}

# ❌ INCORRECTO
projection={
    "cantidad": 1
    # Faltan existencia y stock
}
```

### 2. Verificar Lógica de Prioridad

**Requisito:** Ambos endpoints deben usar la misma lógica de prioridad.

**Verificación:**
```python
# ✅ CORRECTO (misma lógica en ambos endpoints)
if existencia > 0:
    stock_disponible = existencia
elif cantidad > 0:
    stock_disponible = cantidad
else:
    stock_disponible = stock if stock > 0 else 0

# ❌ INCORRECTO (lógica diferente)
# Un endpoint usa cantidad, otro usa existencia
```

### 3. Verificar Respuesta del API

**Requisito:** Los tres campos deben tener el mismo valor.

**Verificación:**
```python
# ✅ CORRECTO
resultado = {
    "cantidad": 1,
    "existencia": 1,  # Mismo valor
    "stock": 1        # Mismo valor
}

# ❌ INCORRECTO
resultado = {
    "cantidad": 2,
    "existencia": 1,  # Valores diferentes
    "stock": 1
}
```

### 4. Verificar Descuento de Inventario

**Requisito:** Al descontar, los tres campos deben actualizarse con el mismo valor.

**Verificación:**
```python
# ✅ CORRECTO
update_data = {
    "cantidad": nueva_cantidad,
    "existencia": nueva_cantidad,  # Mismo valor
    "stock": nueva_cantidad         # Mismo valor
}

# ❌ INCORRECTO
update_data = {
    "cantidad": nueva_cantidad
    # Faltan existencia y stock
}
```

---

## 📊 Estructura de Datos Esperada

### Respuesta de `/punto-venta/productos/buscar`

```json
{
  "id": "69349598873821ce1837413d",
  "codigo": "TT1135",
  "nombre": "ESMERIL ANGULAR 4-1/2 710W",
  "cantidad": 1,          // ← Mismo valor
  "existencia": 1,        // ← Campo principal
  "stock": 1,             // ← Mismo valor
  "precio": 30.80,
  "costo": 22.00,
  "sucursal": "01"
}
```

### Respuesta de `/inventarios/{id}/items`

```json
{
  "id": "69349598873821ce1837413d",
  "codigo": "TT1135",
  "nombre": "ESMERIL ANGULAR 4-1/2 710W",
  "cantidad": 1,          // ← Mismo valor
  "existencia": 1,        // ← Campo principal
  "stock": 1,             // ← Mismo valor
  "precio_venta": 30.80,
  "costo": 22.00,
  "farmacia": "01"
}
```

**IMPORTANTE:** Ambos endpoints deben retornar los mismos valores para `cantidad`, `existencia` y `stock`.

---

## 🔧 Logs de Depuración

### Logs en Búsqueda de Productos

**Endpoint:** `/punto-venta/productos/buscar`

```python
# Logs automáticos (ya implementados)
print(f"✅ [INVENTARIO] Producto encontrado por código: {codigo_busqueda}")
```

### Logs en Confirmación de Venta

**Endpoint:** `/punto-venta/ventas` (POST)

**Logs implementados:**
```python
# Logs de datos recibidos
print(f"📋 [PUNTO_VENTA] Datos de la venta:")
print(f"   - Farmacia/Sucursal: {farmacia}")
print(f"   - Total productos: {len(productos)}")
for idx, producto_venta in enumerate(productos):
    print(f"   📦 Producto {idx + 1}: ID={producto_id}, Código={codigo}, Cantidad={cantidad}")

# Logs de valores antes del descuento
print(f"📊 [INVENTARIO] Valores ANTES del descuento:")
print(f"      - existencia: {existencia_actual}")
print(f"      - cantidad: {cantidad_actual}")
print(f"      - stock: {stock_actual}")

# Logs de valores después del descuento
print(f"📊 [INVENTARIO] Valores DESPUÉS del descuento:")
print(f"      - existencia: {nueva_cantidad}")
print(f"      - cantidad: {nueva_cantidad}")
print(f"      - stock: {nueva_cantidad}")
```

---

## 🧪 Casos de Prueba

### Prueba 1: Verificar Sincronización

**Pasos:**
1. Buscar producto en punto de venta: `GET /punto-venta/productos/buscar?q=TT1135`
2. Buscar mismo producto en inventarios: `GET /inventarios/01/items` (filtrar por código)
3. Comparar valores de `existencia`

**Resultado esperado:**
- Ambos endpoints retornan el mismo valor para `existencia`
- Los tres campos (`cantidad`, `existencia`, `stock`) tienen el mismo valor

### Prueba 2: Verificar Descuento

**Pasos:**
1. Anotar `existencia` inicial del producto
2. Crear venta con ese producto: `POST /punto-venta/ventas`
3. Verificar que `existencia` se descontó correctamente
4. Buscar producto nuevamente y verificar nuevo valor

**Resultado esperado:**
- `existencia` se descuenta correctamente
- Los tres campos se actualizan con el mismo valor
- El nuevo valor coincide en ambos endpoints

### Prueba 3: Verificar Prioridad de Campos

**Pasos:**
1. Crear producto con:
   - `existencia = 5`
   - `cantidad = 10`
   - `stock = 15`
2. Buscar producto en ambos endpoints
3. Verificar que ambos usan `existencia = 5` (campo principal)

**Resultado esperado:**
- Ambos endpoints retornan `existencia = 5`
- Los tres campos tienen valor `5` en la respuesta

---

## ⚠️ Puntos Críticos

### 1. Nunca Usar Solo `cantidad`

**❌ INCORRECTO:**
```python
cantidad = producto.get("cantidad", 0)
# Esto puede mostrar valor diferente a existencia
```

**✅ CORRECTO:**
```python
existencia = float(producto.get("existencia", 0))
cantidad = float(producto.get("cantidad", 0))
stock = float(producto.get("stock", 0))

if existencia > 0:
    stock_disponible = existencia
elif cantidad > 0:
    stock_disponible = cantidad
else:
    stock_disponible = stock if stock > 0 else 0
```

### 2. Siempre Actualizar los Tres Campos

**❌ INCORRECTO:**
```python
update_data = {"cantidad": nueva_cantidad}
# Faltan existencia y stock
```

**✅ CORRECTO:**
```python
update_data = {
    "cantidad": nueva_cantidad,
    "existencia": nueva_cantidad,  # Siempre actualizar
    "stock": nueva_cantidad         # Siempre actualizar
}
```

### 3. Usar Misma Lógica en Ambos Endpoints

**Requisito:** La lógica de prioridad debe ser **idéntica** en:
- `/punto-venta/productos/buscar`
- `/inventarios/items`
- `/inventarios/{id}/items`

---

## 📝 Checklist de Implementación

- [x] Endpoint `/punto-venta/productos/buscar` incluye `existencia` y `stock` en proyección
- [x] Endpoint `/punto-venta/productos/buscar` usa `existencia` como campo principal
- [x] Endpoint `/inventarios/items` incluye `existencia` y `stock` en proyección
- [x] Endpoint `/inventarios/items` usa `existencia` como campo principal
- [x] Endpoint `/inventarios/{id}/items` incluye `existencia` y `stock` en proyección
- [x] Endpoint `/inventarios/{id}/items` usa `existencia` como campo principal
- [x] Endpoint `/punto-venta/ventas` descuenta los tres campos
- [x] Endpoint `/punto-venta/ventas` usa `existencia` para validar stock
- [x] Logs de depuración implementados
- [x] Lógica de prioridad idéntica en todos los endpoints

---

## 🚀 Referencias

- **Código fuente:**
  - `app/routes/punto_venta.py` - Endpoint de búsqueda (líneas 15-238)
  - `app/routes/punto_venta.py` - Endpoint de ventas (líneas 240-390)
  - `app/routes/punto_venta.py` - Función de descuento (líneas 579-733)
  - `app/routes/auth.py` - Endpoints de inventarios (líneas 1225-1432)

- **Documentación relacionada:**
  - `INSTRUCCIONES_BACKEND_URGENTE_DESCUENTO_STOCK.md` - Descuento de inventario
  - `INSTRUCCIONES_FRONTEND_STOCK_EXISTENCIA.md` - Instrucciones frontend

---

**Última actualización:** 2024-12-20  
**Estado:** ✅ Implementado  
**Prioridad:** 🚨 CRÍTICA

