# Cambios Necesarios en el Frontend - Módulo de Inventarios

## ⚠️ IMPORTANTE: Cambios en la Estructura de Respuesta

### **GET `/inventarios/items` - Cambio de Estructura**

**ANTES (objeto con paginación):**
```javascript
{
  "productos": [...],
  "total": 500,
  "limit": 50,
  "skip": 0,
  "has_more": true
}
```

**AHORA (array directo):**
```javascript
[
  {
    "_id": "...",
    "id": "...",
    "codigo": "...",
    "nombre": "...",
    "cantidad": 50,
    // ... resto de campos
  },
  // ... más productos
]
```

**⚠️ ACCIÓN REQUERIDA:** Si el frontend estaba accediendo a `response.productos`, debe cambiarse a usar `response` directamente.

---

## 🔧 Cambios Necesarios en el Frontend

### **1. Actualizar Carga de Lista de Inventarios**

**Antes:**
```javascript
const response = await fetch('/inventarios/items?farmacia=01');
const data = await response.json();
const productos = data.productos; // ❌ Ya no existe
```

**Ahora:**
```javascript
const response = await fetch('/inventarios/items?farmacia=01');
const productos = await response.json(); // ✅ Array directo
```

**O si necesitas paginación:**
```javascript
const response = await fetch('/inventarios/items?farmacia=01&limit=500&skip=0');
const productos = await response.json(); // ✅ Array directo
```

---

### **2. Después de Crear Producto Nuevo**

**El frontend debe:**
1. Agregar el producto a la lista actual (sin recargar toda la página)
2. Seleccionar automáticamente el producto recién creado
3. Mostrar mensaje de éxito

**Ejemplo:**
```javascript
const handleCrearProducto = async () => {
  try {
    const response = await fetch('/inventarios/crear-producto', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        farmacia: farmaciaId,
        nombre: nuevoProducto.nombre,
        codigo: nuevoProducto.codigo,
        descripcion: nuevoProducto.descripcion,
        marca: nuevoProducto.marca,
        costo: nuevoProducto.costo,
        porcentaje_utilidad: nuevoProducto.porcentaje_utilidad || 40.0
      })
    });

    const resultado = await response.json();

    if (response.ok) {
      // ✅ Agregar producto a la lista actual
      setProductos(prevProductos => [...prevProductos, resultado.producto]);
      
      // ✅ Seleccionar automáticamente el producto
      seleccionarProducto(resultado.producto.id);
      
      // ✅ Mostrar mensaje de éxito
      toast.success('Producto creado exitosamente');
      
      // ✅ Cerrar modal de crear producto
      setMostrarCrearProducto(false);
    } else {
      toast.error(`Error: ${resultado.detail}`);
    }
  } catch (error) {
    console.error('Error:', error);
    toast.error('Error al crear producto');
  }
};
```

---

### **3. Después de Cargar Existencia**

**El frontend debe:**
1. Actualizar solo los productos modificados (no recargar toda la página)
2. Actualizar las cantidades en la lista actual

**Ejemplo:**
```javascript
const handleCargarExistencia = async () => {
  try {
    const response = await fetch('/inventarios/cargar-existencia', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        farmacia: farmaciaId,
        productos: productosSeleccionados.map(productoId => ({
          producto_id: productoId,
          cantidad: parseFloat(datosCarga[productoId]?.cantidad || 0),
          costo: datosCarga[productoId]?.costo ? parseFloat(datosCarga[productoId].costo) : undefined,
          porcentaje_utilidad: datosCarga[productoId]?.porcentaje_utilidad || 40.0
        })).filter(p => p.cantidad > 0)
      })
    });

    const resultado = await response.json();

    if (response.ok) {
      // ✅ Actualizar solo los productos modificados
      setProductos(prevProductos => {
        const productosActualizados = [...prevProductos];
        
        resultado.detalle.exitosos.forEach(productoActualizado => {
          const index = productosActualizados.findIndex(p => p.id === productoActualizado.id);
          if (index !== -1) {
            // Reemplazar el producto con los datos actualizados
            productosActualizados[index] = {
              ...productosActualizados[index],
              ...productoActualizado
            };
          }
        });
        
        return productosActualizados;
      });

      toast.success(`✅ ${resultado.productos_exitosos} productos actualizados`);
      
      // Limpiar selección
      setProductosSeleccionados([]);
      setDatosCarga({});
    } else {
      toast.error(`Error: ${resultado.detail}`);
    }
  } catch (error) {
    console.error('Error:', error);
    toast.error('Error al cargar existencia');
  }
};
```

---

### **4. Verificar Endpoint de Carga Inicial**

**Asegurar que el frontend use el endpoint correcto:**

```javascript
// ✅ CORRECTO - Array directo
const cargarInventario = async () => {
  setCargando(true);
  try {
    const response = await fetch(`/inventarios/items?farmacia=${farmaciaId}&limit=500`);
    const productos = await response.json(); // Array directo
    
    setProductos(productos);
  } catch (error) {
    console.error('Error:', error);
    toast.error('Error al cargar inventario');
  } finally {
    setCargando(false);
  }
};
```

---

## ✅ Checklist de Cambios en el Frontend

- [ ] **Actualizar carga de lista:** Cambiar `response.productos` a `response` directamente
- [ ] **Después de crear producto:** Agregar producto a la lista sin recargar
- [ ] **Después de cargar existencia:** Actualizar solo productos modificados
- [ ] **Verificar endpoint:** Usar `/inventarios/items?farmacia=01&limit=500`
- [ ] **Probar creación de producto:** Verificar que aparece inmediatamente
- [ ] **Probar carga de existencia:** Verificar que las cantidades se actualizan

---

## 🐛 Troubleshooting

### **Problema: Los productos no aparecen después de crearlos**

**Solución:**
1. Verificar que estés agregando el producto a la lista después de crearlo
2. Verificar que el endpoint de carga inicial esté usando el formato correcto (array directo)
3. Verificar que no haya caché en el frontend

### **Problema: Las cantidades no se actualizan después de cargar existencia**

**Solución:**
1. Verificar que estés actualizando el estado local con los productos retornados
2. Verificar que estés usando `resultado.detalle.exitosos` para actualizar
3. Verificar que el `id` del producto coincida

### **Problema: Error "Cannot read property 'productos' of undefined"**

**Solución:**
- El endpoint ahora retorna un array directo, no un objeto con `productos`
- Cambiar `response.productos` a `response` directamente

---

## 📝 Resumen de Cambios

| Endpoint | Cambio | Acción Frontend |
|----------|--------|-----------------|
| `GET /inventarios/items` | Retorna array directo (no objeto) | Usar `response` directamente, no `response.productos` |
| `POST /inventarios/crear-producto` | Retorna producto completo | Agregar a lista sin recargar |
| `POST /inventarios/cargar-existencia` | Retorna productos actualizados | Actualizar solo productos modificados |

---

**Última actualización:** 2025-12-12


