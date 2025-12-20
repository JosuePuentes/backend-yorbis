# Instrucciones Frontend - Carga Masiva de Existencia en Inventarios

## 📋 Resumen

El backend ahora incluye un endpoint optimizado para cargar existencia masiva al inventario. Permite seleccionar múltiples productos, especificar cantidad, costo y utilidad, y luego cargar todo de una vez sin actualizar la página.

---

## 🚀 Nuevo Endpoint: Carga Masiva

### **POST `/inventarios/cargar-existencia`**

**Descripción:** Carga existencia masiva al inventario. Suma las cantidades a los productos existentes (no reemplaza).

**Headers:**
```javascript
{
  "Content-Type": "application/json",
  "Authorization": "Bearer {token}"
}
```

**Body:**
```javascript
{
  "farmacia": "01",  // ID de la farmacia (requerido)
  "productos": [     // Array de productos a cargar
    {
      "producto_id": "693877e8873821ce183741c9",  // ID del producto en inventario (requerido)
      "cantidad": 10,                              // Cantidad a SUMAR (requerido, > 0)
      "costo": 100.00,                             // Costo unitario (opcional, usa el actual si no se envía)
      "utilidad": 66.67,                          // Utilidad en dinero (opcional)
      "porcentaje_utilidad": 40.0,                // Porcentaje de utilidad (opcional, default 40%)
      "precio_venta": 166.67                      // Precio de venta (opcional, se calcula si no se envía)
    },
    {
      "producto_id": "693877e8873821ce183741ca",
      "cantidad": 5,
      "costo": 50.00,
      "porcentaje_utilidad": 40.0
    }
  ]
}
```

**Response (200 OK):**
```javascript
{
  "message": "Existencia cargada exitosamente",
  "productos_procesados": 2,
  "productos_exitosos": 2,
  "productos_con_error": 0,
  "detalle": {
    "exitosos": [
      {
        "producto_id": "693877e8873821ce183741c9",
        "nombre": "Producto 1",
        "cantidad_anterior": 20,
        "cantidad_suma": 10,
        "cantidad_nueva": 30,
        "costo": 100.00,
        "precio_venta": 166.67
      },
      {
        "producto_id": "693877e8873821ce183741ca",
        "nombre": "Producto 2",
        "cantidad_anterior": 15,
        "cantidad_suma": 5,
        "cantidad_nueva": 20,
        "costo": 50.00,
        "precio_venta": 83.33
      }
    ],
    "errores": []
  }
}
```

---

## 🎨 Implementación en el Frontend

### **Flujo Recomendado:**

1. **Seleccionar productos** (checkbox o similar)
2. **Ingresar datos** para cada producto seleccionado:
   - Cantidad a sumar
   - Costo (opcional)
   - Utilidad o porcentaje de utilidad (opcional)
3. **Totalizar** - Validar y preparar datos
4. **Cargar** - Enviar al endpoint
5. **Actualizar UI** - Sin recargar página, actualizar solo los productos modificados

### **Ejemplo de Componente React:**

```jsx
import { useState } from 'react';

const CargaMasivaInventario = () => {
  const [productosSeleccionados, setProductosSeleccionados] = useState([]);
  const [datosCarga, setDatosCarga] = useState({});
  const [cargando, setCargando] = useState(false);

  // Estructura de datosCarga:
  // {
  //   "producto_id_1": { cantidad: 10, costo: 100, utilidad: 66.67 },
  //   "producto_id_2": { cantidad: 5, costo: 50, porcentaje_utilidad: 40 }
  // }

  const handleCargarExistencia = async () => {
    setCargando(true);
    
    try {
      // Preparar array de productos
      const productos = productosSeleccionados.map(productoId => ({
        producto_id: productoId,
        cantidad: parseFloat(datosCarga[productoId]?.cantidad || 0),
        costo: datosCarga[productoId]?.costo ? parseFloat(datosCarga[productoId].costo) : undefined,
        utilidad: datosCarga[productoId]?.utilidad ? parseFloat(datosCarga[productoId].utilidad) : undefined,
        porcentaje_utilidad: datosCarga[productoId]?.porcentaje_utilidad ? parseFloat(datosCarga[productoId].porcentaje_utilidad) : undefined,
        precio_venta: datosCarga[productoId]?.precio_venta ? parseFloat(datosCarga[productoId].precio_venta) : undefined
      })).filter(p => p.cantidad > 0); // Filtrar productos con cantidad > 0

      if (productos.length === 0) {
        alert("Debe seleccionar al menos un producto con cantidad > 0");
        setCargando(false);
        return;
      }

      const response = await fetch('/inventarios/cargar-existencia', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          farmacia: farmaciaId, // ID de la farmacia actual
          productos: productos
        })
      });

      const resultado = await response.json();

      if (response.ok) {
        // ✅ Éxito - Actualizar UI sin recargar página
        console.log(`✅ ${resultado.productos_exitosos} productos actualizados`);
        
        // Actualizar solo los productos modificados en el estado local
        resultado.detalle.exitosos.forEach(producto => {
          // Actualizar el producto en el estado local
          actualizarProductoEnEstado(producto.producto_id, {
            cantidad: producto.cantidad_nueva,
            costo: producto.costo,
            precio_venta: producto.precio_venta
          });
        });

        // Mostrar mensaje de éxito
        alert(`✅ Existencia cargada: ${resultado.productos_exitosos} productos actualizados`);
        
        // Limpiar selección
        setProductosSeleccionados([]);
        setDatosCarga({});
      } else {
        // ❌ Error
        console.error('Error:', resultado);
        alert(`Error: ${resultado.detail || 'Error al cargar existencia'}`);
      }
    } catch (error) {
      console.error('Error:', error);
      alert('Error al cargar existencia');
    } finally {
      setCargando(false);
    }
  };

  return (
    <div>
      {/* Tabla de productos con checkboxes */}
      <table>
        <thead>
          <tr>
            <th>Seleccionar</th>
            <th>Producto</th>
            <th>Cantidad Actual</th>
            <th>Cantidad a Sumar</th>
            <th>Costo</th>
            <th>Utilidad</th>
            <th>% Utilidad</th>
          </tr>
        </thead>
        <tbody>
          {productos.map(producto => (
            <tr key={producto.id}>
              <td>
                <input
                  type="checkbox"
                  checked={productosSeleccionados.includes(producto.id)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setProductosSeleccionados([...productosSeleccionados, producto.id]);
                    } else {
                      setProductosSeleccionados(productosSeleccionados.filter(id => id !== producto.id));
                      // Limpiar datos de este producto
                      const nuevosDatos = { ...datosCarga };
                      delete nuevosDatos[producto.id];
                      setDatosCarga(nuevosDatos);
                    }
                  }}
                />
              </td>
              <td>{producto.nombre}</td>
              <td>{producto.cantidad}</td>
              <td>
                {productosSeleccionados.includes(producto.id) && (
                  <input
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={datosCarga[producto.id]?.cantidad || ''}
                    onChange={(e) => {
                      setDatosCarga({
                        ...datosCarga,
                        [producto.id]: {
                          ...datosCarga[producto.id],
                          cantidad: e.target.value
                        }
                      });
                    }}
                  />
                )}
              </td>
              <td>
                {productosSeleccionados.includes(producto.id) && (
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    placeholder={producto.costo}
                    value={datosCarga[producto.id]?.costo || ''}
                    onChange={(e) => {
                      setDatosCarga({
                        ...datosCarga,
                        [producto.id]: {
                          ...datosCarga[producto.id],
                          costo: e.target.value
                        }
                      });
                    }}
                  />
                )}
              </td>
              <td>
                {productosSeleccionados.includes(producto.id) && (
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={datosCarga[producto.id]?.utilidad || ''}
                    onChange={(e) => {
                      setDatosCarga({
                        ...datosCarga,
                        [producto.id]: {
                          ...datosCarga[producto.id],
                          utilidad: e.target.value
                        }
                      });
                    }}
                  />
                )}
              </td>
              <td>
                {productosSeleccionados.includes(producto.id) && (
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="0.1"
                    placeholder="40"
                    value={datosCarga[producto.id]?.porcentaje_utilidad || ''}
                    onChange={(e) => {
                      setDatosCarga({
                        ...datosCarga,
                        [producto.id]: {
                          ...datosCarga[producto.id],
                          porcentaje_utilidad: e.target.value
                        }
                      });
                    }}
                  />
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Botón de cargar */}
      <button
        onClick={handleCargarExistencia}
        disabled={cargando || productosSeleccionados.length === 0}
      >
        {cargando ? 'Cargando...' : 'Totalizar y Cargar Existencia'}
      </button>
    </div>
  );
};
```

---

## ⚙️ Comportamiento del Backend

### **Suma de Cantidades (NO Reemplaza)**

- ✅ Si el producto tiene 20 unidades y cargas 10 → Resultado: 30 unidades
- ❌ NO reemplaza la cantidad existente

### **Cálculo de Costo Promedio**

- Si el producto tiene costo actual y cargas con nuevo costo:
  - Se calcula costo promedio ponderado
  - Ejemplo: 20 unidades a $100 + 10 unidades a $120 = 30 unidades a $106.67

### **Cálculo de Precio de Venta**

El backend calcula el precio de venta según lo que envíes:

1. **Si envías `precio_venta`**: Se usa ese precio
2. **Si envías `utilidad`**: Se calcula `precio_venta = costo + utilidad`
3. **Si envías `porcentaje_utilidad`**: Se calcula `precio_venta = costo / (1 - porcentaje/100)`
4. **Si no envías nada**: Se calcula con 40% de utilidad por defecto

---

## 📊 Optimizaciones Aplicadas

### **GET `/inventarios/items`**

- ✅ Límite reducido a 200 productos (antes 300)
- ✅ Proyección mínima (solo campos esenciales)
- ✅ Solo productos activos
- ✅ Procesamiento optimizado

### **POST `/inventarios/cargar-existencia`**

- ✅ Procesamiento en batch (múltiples productos a la vez)
- ✅ Validación de cada producto
- ✅ Manejo de errores individual por producto
- ✅ Respuesta detallada con éxito/errores

---

## ✅ Checklist de Implementación

- [ ] Crear componente de carga masiva
- [ ] Agregar checkboxes para seleccionar productos
- [ ] Agregar campos de entrada (cantidad, costo, utilidad)
- [ ] Implementar función `handleCargarExistencia`
- [ ] Actualizar UI sin recargar página después de cargar
- [ ] Mostrar mensajes de éxito/error
- [ ] Validar que cantidad > 0 antes de enviar
- [ ] Manejar errores individuales por producto

---

## 🐛 Manejo de Errores

El endpoint retorna errores individuales por producto:

```javascript
{
  "productos_exitosos": 3,
  "productos_con_error": 1,
  "detalle": {
    "exitosos": [...],
    "errores": [
      {
        "producto_id": "id_invalido",
        "error": "Producto no encontrado: id_invalido"
      }
    ]
  }
}
```

**Recomendación:** Mostrar los errores al usuario para que pueda corregirlos.

---

## 🚀 Ventajas de la Carga Masiva

1. **Rapidez**: Carga múltiples productos en una sola petición
2. **Sin recarga**: Actualiza solo los productos modificados
3. **Flexibilidad**: Permite especificar costo y utilidad por producto
4. **Validación**: Valida cada producto individualmente
5. **Feedback**: Retorna detalle de éxitos y errores

---

**Última actualización:** 2025-12-11


