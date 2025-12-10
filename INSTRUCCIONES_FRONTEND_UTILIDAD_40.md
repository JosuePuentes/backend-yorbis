# Instrucciones Frontend - Utilidad 40% en Inventario

## 📋 Resumen

El backend ahora calcula automáticamente el **precio de venta con 40% de utilidad** y guarda los siguientes campos en el inventario:
- `costo`: Costo del producto
- `utilidad`: Utilidad en dinero (precio_venta - costo)
- `porcentaje_utilidad`: Siempre 40%
- `precio_venta`: Precio de venta calculado automáticamente

## 🔧 Cambios en el Backend

### Cálculo Automático de Precio de Venta

**Fórmula aplicada:**
```
precio_venta = costo / 0.60
utilidad = precio_venta - costo
porcentaje_utilidad = 40%
```

**Ejemplo:**
- Costo: $100
- Precio de venta: $100 / 0.60 = $166.67
- Utilidad: $166.67 - $100 = $66.67
- Porcentaje: 40%

### Campos en el Inventario

Cuando se obtiene un producto del inventario (endpoints `/productos`, `/inventarios`, etc.), cada producto incluye:

```json
{
  "_id": "producto_id",
  "codigo": "ABC123",
  "nombre": "Producto Ejemplo",
  "cantidad": 10,
  "costo": 100.00,
  "precio_venta": 166.67,
  "utilidad": 66.67,
  "porcentaje_utilidad": 40.0,
  "farmacia": "01",
  "estado": "activo"
}
```

## 🎨 Instrucciones para el Frontend

### 1. Mostrar Campos en la Tabla de Inventario

En la tabla de inventario, debes mostrar las siguientes columnas:

#### Columnas Requeridas:
1. **Código** - `producto.codigo`
2. **Nombre** - `producto.nombre`
3. **Cantidad/Stock** - `producto.cantidad`
4. **Costo** - `producto.costo` (formateado como moneda)
5. **Utilidad** - `producto.utilidad` (formateado como moneda)
6. **Precio de Venta** - `producto.precio_venta` (formateado como moneda)

#### Ejemplo de Implementación (React/Vue):

```jsx
// React Example
const InventarioTable = ({ productos }) => {
  const formatCurrency = (value) => {
    return new Intl.NumberFormat('es-VE', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(value);
  };

  return (
    <table>
      <thead>
        <tr>
          <th>Código</th>
          <th>Nombre</th>
          <th>Cantidad</th>
          <th>Costo</th>
          <th>Utilidad</th>
          <th>Precio Venta</th>
        </tr>
      </thead>
      <tbody>
        {productos.map((producto) => (
          <tr key={producto._id}>
            <td>{producto.codigo}</td>
            <td>{producto.nombre}</td>
            <td>{producto.cantidad}</td>
            <td>{formatCurrency(producto.costo || 0)}</td>
            <td className="text-success">
              {formatCurrency(producto.utilidad || 0)}
            </td>
            <td className="text-primary font-weight-bold">
              {formatCurrency(producto.precio_venta || 0)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};
```

### 2. Formato de Moneda

**Importante:** Formatea todos los valores monetarios con 2 decimales:

```javascript
// Función helper para formatear moneda
const formatCurrency = (value) => {
  if (!value && value !== 0) return '$0.00';
  
  return new Intl.NumberFormat('es-VE', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(value);
};

// Uso:
formatCurrency(producto.costo)      // "$100.00"
formatCurrency(producto.utilidad)   // "$66.67"
formatCurrency(producto.precio_venta) // "$166.67"
```

### 3. Mostrar Porcentaje de Utilidad (Opcional)

Si quieres mostrar el porcentaje de utilidad, puedes agregar una columna adicional:

```jsx
<th>% Utilidad</th>
// ...
<td>{producto.porcentaje_utilidad || 40}%</td>
```

**Nota:** El porcentaje siempre será 40%, pero puedes mostrarlo para referencia.

### 4. Validación de Datos

Siempre valida que los campos existan antes de mostrarlos:

```javascript
// Validación segura
const costo = producto.costo || 0;
const utilidad = producto.utilidad || 0;
const precioVenta = producto.precio_venta || 0;
```

### 5. Ordenamiento y Filtros

Puedes permitir ordenar por:
- Costo (ascendente/descendente)
- Utilidad (ascendente/descendente)
- Precio de venta (ascendente/descendente)

### 6. Edición Manual de Precio de Venta (Opcional)

Si el usuario quiere editar manualmente el precio de venta:

**Endpoint:** `PUT /inventarios/{id}/items/{item_id}`

**Body:**
```json
{
  "precio_venta": 180.00
}
```

**Nota:** Si se edita manualmente, el backend NO recalculará la utilidad automáticamente. Si quieres que siempre sea 40%, debes recalcular:

```javascript
// Recalcular precio_venta con 40% de utilidad
const nuevoPrecioVenta = costo / 0.60;
const nuevaUtilidad = nuevoPrecioVenta - costo;
```

### 7. Endpoints que Retornan estos Campos

Los siguientes endpoints ya incluyen los campos de utilidad:

- `GET /productos` - Lista de productos
- `GET /productos/{id}` - Producto específico
- `GET /inventarios` - Lista de inventarios
- `GET /inventarios/{id}/items` - Items de inventario
- `GET /productos/buscar` - Búsqueda de productos

### 8. Ejemplo Completo de Componente

```jsx
import React, { useState, useEffect } from 'react';

const InventarioView = () => {
  const [productos, setProductos] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProductos();
  }, []);

  const fetchProductos = async () => {
    try {
      const response = await fetch('/api/productos', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const data = await response.json();
      setProductos(data);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('es-VE', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(value || 0);
  };

  if (loading) return <div>Cargando...</div>;

  return (
    <div className="inventario-container">
      <h2>Inventario</h2>
      <table className="table">
        <thead>
          <tr>
            <th>Código</th>
            <th>Nombre</th>
            <th>Stock</th>
            <th>Costo</th>
            <th>Utilidad</th>
            <th>Precio Venta</th>
            <th>% Utilidad</th>
          </tr>
        </thead>
        <tbody>
          {productos.map((producto) => (
            <tr key={producto._id}>
              <td>{producto.codigo || '-'}</td>
              <td>{producto.nombre || '-'}</td>
              <td>{producto.cantidad || 0}</td>
              <td>{formatCurrency(producto.costo)}</td>
              <td className="text-success">
                {formatCurrency(producto.utilidad)}
              </td>
              <td className="text-primary font-weight-bold">
                {formatCurrency(producto.precio_venta)}
              </td>
              <td>{producto.porcentaje_utilidad || 40}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default InventarioView;
```

## ✅ Checklist de Implementación

- [ ] Agregar columna "Costo" en la tabla de inventario
- [ ] Agregar columna "Utilidad" en la tabla de inventario
- [ ] Agregar columna "Precio de Venta" en la tabla de inventario
- [ ] Formatear todos los valores monetarios con 2 decimales
- [ ] Validar que los campos existan antes de mostrarlos
- [ ] Agregar estilos visuales (utilidad en verde, precio venta destacado)
- [ ] Probar con datos reales del backend
- [ ] Verificar que los cálculos sean correctos

## 🎨 Sugerencias de Estilos

```css
/* Estilos sugeridos */
.costo {
  color: #666;
}

.utilidad {
  color: #28a745; /* Verde para ganancia */
  font-weight: 500;
}

.precio-venta {
  color: #007bff; /* Azul para precio */
  font-weight: bold;
}

.porcentaje-utilidad {
  color: #6c757d;
  font-size: 0.9em;
}
```

## 🔄 Actualizar Productos Existentes

Si tienes productos existentes que no tienen utilidad calculada, ejecuta el script:

```bash
python actualizar_utilidad_productos.py
```

Este script:
- Busca todos los productos del inventario
- Calcula precio_venta con 40% de utilidad para productos sin precio_venta
- Calcula utilidad para productos que no la tengan
- Muestra un resumen de productos actualizados

## 📝 Notas Importantes

1. **Cálculo Automático:** El backend calcula automáticamente el precio de venta con 40% de utilidad cuando se crea o actualiza un producto en una compra.

2. **Edición Manual:** Si el usuario edita manualmente el precio de venta, la utilidad se recalcula automáticamente, pero el porcentaje puede cambiar.

3. **Consistencia:** Todos los productos nuevos tendrán automáticamente 40% de utilidad.

4. **Formato:** Siempre muestra los valores monetarios con 2 decimales para mantener consistencia.

5. **Productos Existentes:** Los productos existentes se actualizan automáticamente cuando se consultan, pero puedes ejecutar el script para actualizarlos todos de una vez.

## 🔍 Verificación

Para verificar que todo funciona:

1. Crea una compra con productos
2. Verifica que en el inventario aparezcan:
   - Costo correcto
   - Utilidad calculada (precio_venta - costo)
   - Precio de venta = costo / 0.60
   - Porcentaje de utilidad = 40%

## 📞 Soporte

Si tienes dudas sobre la implementación, revisa:
- Los endpoints de productos e inventarios
- La estructura de datos retornada
- Los ejemplos de código proporcionados

