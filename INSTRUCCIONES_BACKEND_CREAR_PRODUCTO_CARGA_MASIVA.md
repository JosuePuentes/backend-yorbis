# Instrucciones Backend - Crear Producto desde Carga Masiva

## 📋 Resumen

Este documento describe la implementación del endpoint para crear productos nuevos en el inventario desde el modal de carga masiva del frontend.

## 🔧 Endpoint Principal

**Endpoint:** `POST /inventarios/crear-producto`

**Archivo:** `app/routes/auth.py`

**Líneas:** 1939-2101

## ⚙️ Implementación

### 1. Endpoint de Creación

```python
@router.post("/inventarios/crear-producto")
async def crear_producto_inventario(
    datos_producto: dict = Body(...),
    usuario: dict = Depends(get_current_user)
):
    """
    Crea un nuevo producto en el inventario desde el modal de carga masiva.
    """
    collection = get_collection("INVENTARIOS")
    usuario_correo = usuario.get("correo", "unknown")
    
    # Validar datos requeridos
    farmacia = datos_producto.get("farmacia")
    if not farmacia:
        raise HTTPException(status_code=400, detail="El campo 'farmacia' es requerido")
    
    nombre = datos_producto.get("nombre", "").strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El campo 'nombre' es requerido")
    
    costo = float(datos_producto.get("costo", 0))
    if costo <= 0:
        raise HTTPException(status_code=400, detail="El campo 'costo' debe ser mayor a 0")
    
    # Verificar si ya existe un producto con el mismo código
    codigo = datos_producto.get("codigo", "").strip()
    if codigo:
        producto_existente = await collection.find_one({
            "farmacia": farmacia,
            "codigo": codigo.upper(),
            "estado": {"$ne": "inactivo"}
        })
        if producto_existente:
            raise HTTPException(
                status_code=400, 
                detail=f"Ya existe un producto con el código '{codigo}' en esta farmacia"
            )
    
    # Calcular precio_venta y utilidad (40% por defecto)
    # ... lógica de cálculo ...
    
    # Crear nuevo producto
    nuevo_producto = {
        "farmacia": str(farmacia).strip(),
        "nombre": nombre,
        "descripcion": datos_producto.get("descripcion", "").strip(),
        "marca": datos_producto.get("marca", "").strip(),
        "cantidad": float(datos_producto.get("cantidad", 0)),
        "costo": round(costo, 2),
        "precio_venta": round(precio_venta_final, 2),
        "precio": round(precio_venta_final, 2),
        "utilidad": round(utilidad_final, 2),
        "porcentaje_utilidad": round(porcentaje_utilidad_final, 2),
        "usuarioCorreo": usuario_correo,
        "fecha": fecha_actual,
        "fechaCreacion": fecha_actual,
        "estado": "activo"  # IMPORTANTE: Estado activo explícito
    }
    
    if codigo:
        nuevo_producto["codigo"] = codigo.upper()
    
    # Insertar en la base de datos
    result = await collection.insert_one(nuevo_producto)
    producto_id = str(result.inserted_id)
    
    # Retornar producto creado
    return {
        "message": "Producto creado exitosamente",
        "producto": producto_formateado
    }
```

**Referencia:** `app/routes/auth.py` líneas 1939-2101

### 2. Cálculo de Utilidad y Precio de Venta

El sistema calcula automáticamente el precio de venta con 40% de utilidad por defecto:

```python
# Calcular precio_venta y utilidad
precio_venta_enviado = datos_producto.get("precio_venta")
utilidad_enviada = datos_producto.get("utilidad")
porcentaje_utilidad_enviado = datos_producto.get("porcentaje_utilidad", 40.0)

if precio_venta_enviado and precio_venta_enviado > 0:
    # Si viene precio_venta explícito, usarlo
    precio_venta_final = float(precio_venta_enviado)
    if utilidad_enviada is not None:
        utilidad_final = float(utilidad_enviada)
    else:
        utilidad_final = precio_venta_final - costo
    porcentaje_utilidad_final = porcentaje_utilidad_enviado
elif utilidad_enviada is not None and utilidad_enviada > 0:
    # Si viene utilidad, calcular precio_venta
    utilidad_final = float(utilidad_enviada)
    precio_venta_final = costo + utilidad_final
    porcentaje_utilidad_final = (utilidad_final / costo) * 100 if costo > 0 else 0
else:
    # Calcular automáticamente con porcentaje de utilidad (default 40%)
    porcentaje_utilidad_final = float(porcentaje_utilidad_enviado)
    precio_venta_final = costo / (1 - (porcentaje_utilidad_final / 100))
    utilidad_final = precio_venta_final - costo
```

**Fórmula aplicada:**
- Si no se envía precio_venta ni utilidad: `precio_venta = costo / 0.60` (40% de utilidad)
- Si se envía precio_venta: se usa ese precio y se calcula la utilidad
- Si se envía utilidad: se calcula precio_venta = costo + utilidad

## 📊 Estructura de Datos

### Request Body

```json
{
  "farmacia": "01",                    // ID de la farmacia (REQUERIDO)
  "codigo": "PROD-001",                // Código del producto (opcional)
  "nombre": "Producto Nuevo",          // Nombre del producto (REQUERIDO)
  "descripcion": "Descripción...",     // Descripción (opcional)
  "marca": "Marca X",                  // Marca (opcional)
  "cantidad": 0,                        // Cantidad inicial (opcional, default 0)
  "costo": 100.00,                     // Costo unitario (REQUERIDO, debe ser > 0)
  "utilidad": 66.67,                    // Utilidad en dinero (opcional)
  "porcentaje_utilidad": 40.0,         // Porcentaje de utilidad (opcional, default 40%)
  "precio_venta": 166.67               // Precio de venta (opcional, se calcula si no se envía)
}
```

### Response

```json
{
  "message": "Producto creado exitosamente",
  "producto": {
    "id": "507f1f77bcf86cd799439011",
    "_id": "507f1f77bcf86cd799439011",
    "codigo": "PROD-001",
    "nombre": "Producto Nuevo",
    "descripcion": "Descripción...",
    "marca": "Marca X",
    "cantidad": 0.0,
    "costo": 100.00,
    "precio_venta": 166.67,
    "precio": 166.67,
    "utilidad": 66.67,
    "porcentaje_utilidad": 40.0,
    "farmacia": "01",
    "estado": "activo"
  }
}
```

## 🔑 Validaciones

### 1. Campos Requeridos

- ✅ `farmacia`: ID de la farmacia (requerido)
- ✅ `nombre`: Nombre del producto (requerido, no puede estar vacío)
- ✅ `costo`: Costo unitario (requerido, debe ser > 0)

### 2. Validación de Código Duplicado

- Si se envía un `codigo`, se verifica que no exista otro producto activo con el mismo código en la misma farmacia
- El código se convierte a mayúsculas automáticamente
- Si existe un producto con el mismo código, se retorna error 400

### 3. Cálculo Automático

- Si no se envía `precio_venta` ni `utilidad`, se calcula automáticamente con 40% de utilidad
- Si se envía `precio_venta`, se usa ese precio y se calcula la utilidad
- Si se envía `utilidad`, se calcula `precio_venta = costo + utilidad`

## 📝 Campos del Producto Creado

El producto creado incluye los siguientes campos:

```json
{
  "_id": ObjectId("..."),
  "farmacia": "01",
  "codigo": "PROD-001",              // Si se proporcionó
  "nombre": "Producto Nuevo",
  "descripcion": "Descripción...",   // Si se proporcionó
  "marca": "Marca X",                // Si se proporcionó
  "cantidad": 0.0,
  "costo": 100.00,
  "precio_venta": 166.67,
  "precio": 166.67,
  "utilidad": 66.67,
  "porcentaje_utilidad": 40.0,
  "usuarioCorreo": "usuario@example.com",
  "fecha": "2024-01-15",
  "fechaCreacion": "2024-01-15",
  "estado": "activo"                 // Siempre "activo" al crear
}
```

## ⚠️ Errores Comunes

### Error 1: Campo Farmacia Faltante

**Mensaje:** `"El campo 'farmacia' es requerido"`

**Causa:** No se envió el campo `farmacia` en el request

**Solución:** Incluir `farmacia` en el body del request

### Error 2: Campo Nombre Faltante

**Mensaje:** `"El campo 'nombre' es requerido"`

**Causa:** No se envió el campo `nombre` o está vacío

**Solución:** Incluir `nombre` con un valor no vacío

### Error 3: Costo Inválido

**Mensaje:** `"El campo 'costo' debe ser mayor a 0"`

**Causa:** El costo es 0 o negativo

**Solución:** Enviar un costo mayor a 0

### Error 4: Código Duplicado

**Mensaje:** `"Ya existe un producto con el código 'XXX' en esta farmacia"`

**Causa:** Ya existe un producto activo con el mismo código en la misma farmacia

**Solución:** Usar un código diferente o actualizar el producto existente

## 🧪 Ejemplos de Pruebas

### Prueba 1: Crear Producto Básico

**Request:**
```json
POST /inventarios/crear-producto
{
  "farmacia": "01",
  "nombre": "Producto Test",
  "costo": 100.00
}
```

**Response esperada:**
```json
{
  "message": "Producto creado exitosamente",
  "producto": {
    "id": "...",
    "nombre": "Producto Test",
    "costo": 100.00,
    "precio_venta": 166.67,
    "utilidad": 66.67,
    "porcentaje_utilidad": 40.0,
    "cantidad": 0.0,
    "estado": "activo"
  }
}
```

### Prueba 2: Crear Producto Completo

**Request:**
```json
POST /inventarios/crear-producto
{
  "farmacia": "01",
  "codigo": "TEST-001",
  "nombre": "Producto Completo",
  "descripcion": "Descripción del producto",
  "marca": "Marca Test",
  "cantidad": 10,
  "costo": 50.00,
  "porcentaje_utilidad": 40.0
}
```

**Response esperada:**
```json
{
  "message": "Producto creado exitosamente",
  "producto": {
    "id": "...",
    "codigo": "TEST-001",
    "nombre": "Producto Completo",
    "descripcion": "Descripción del producto",
    "marca": "Marca Test",
    "cantidad": 10.0,
    "costo": 50.00,
    "precio_venta": 83.33,
    "utilidad": 33.33,
    "porcentaje_utilidad": 40.0,
    "estado": "activo"
  }
}
```

### Prueba 3: Crear Producto con Precio de Venta Explícito

**Request:**
```json
POST /inventarios/crear-producto
{
  "farmacia": "01",
  "nombre": "Producto con Precio",
  "costo": 100.00,
  "precio_venta": 200.00
}
```

**Response esperada:**
```json
{
  "message": "Producto creado exitosamente",
  "producto": {
    "id": "...",
    "nombre": "Producto con Precio",
    "costo": 100.00,
    "precio_venta": 200.00,
    "utilidad": 100.00,
    "porcentaje_utilidad": 40.0,
    "estado": "activo"
  }
}
```

### Prueba 4: Error - Código Duplicado

**Request:**
```json
POST /inventarios/crear-producto
{
  "farmacia": "01",
  "codigo": "EXISTENTE-001",
  "nombre": "Producto Nuevo",
  "costo": 100.00
}
```

**Response esperada (si ya existe un producto con código "EXISTENTE-001"):**
```json
{
  "detail": "Ya existe un producto con el código 'EXISTENTE-001' en esta farmacia"
}
```

**Status Code:** 400

## 🔍 Verificación

### Verificar Producto Creado

1. **Crear un producto:**
   ```bash
   POST /inventarios/crear-producto
   {
     "farmacia": "01",
     "codigo": "VERIFY-001",
     "nombre": "Producto Verificación",
     "costo": 100.00
   }
   ```

2. **Verificar que se creó:**
   ```bash
   GET /productos?codigo=VERIFY-001
   ```
   
   Debe retornar el producto con:
   - `codigo`: "VERIFY-001"
   - `nombre`: "Producto Verificación"
   - `costo`: 100.00
   - `precio_venta`: 166.67 (calculado automáticamente)
   - `utilidad`: 66.67
   - `porcentaje_utilidad`: 40.0
   - `estado`: "activo"

## 📝 Notas Importantes

### ⚠️ CRÍTICO

1. **Estado:** Todos los productos creados tienen estado "activo" por defecto
2. **Código:** Se convierte a mayúsculas automáticamente
3. **Utilidad:** Se calcula automáticamente con 40% por defecto si no se especifica
4. **Validación:** Se valida que no exista un producto activo con el mismo código en la misma farmacia

### 🔒 Seguridad

- Requiere autenticación (token JWT)
- Valida permisos del usuario
- Registra el usuario que crea el producto (`usuarioCorreo`)

### 📊 Logs

El sistema genera logs detallados:
- `📝 [INVENTARIOS] Datos del producto a crear: {...}`
- `📝 [INVENTARIOS] Insertando producto: {nombre} en farmacia {farmacia}`
- `✅ [INVENTARIOS] Producto insertado con ID: {producto_id}`
- `✅ [INVENTARIOS] Producto recuperado de BD: {nombre}`
- `✅ [INVENTARIOS] Producto creado: {nombre} - ID: {producto_id}`

## 🚀 Referencias

- **Código fuente:**
  - `app/routes/auth.py` - Endpoint de creación (líneas 1939-2101)

- **Documentación relacionada:**
  - `INSTRUCCIONES_FRONTEND_CREAR_PRODUCTO_MODAL.md` - Instrucciones para frontend
  - `INSTRUCCIONES_BACKEND_UTILIDAD_40_DESCUENTO_INVENTARIO.md` - Utilidad 40%

## 🔗 Integración con Carga Masiva

Este endpoint se usa desde el modal de carga masiva del frontend:

1. El usuario hace clic en "Carga Masiva"
2. Se abre el modal donde puede crear productos nuevos
3. Al crear un producto, se llama a `POST /inventarios/crear-producto`
4. El producto se crea con estado "activo" y utilidad del 40% por defecto
5. Luego se puede cargar existencia usando `POST /inventarios/cargar-existencia`

---

**Última actualización:** 2024-12-20  
**Estado:** ✅ Implementado y probado  
**Prioridad:** 🔴 ALTA

