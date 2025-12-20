# Instrucciones Frontend - Stock y Existencia en Punto de Venta

## 🚨 CRÍTICO - Corrección de Inconsistencia de Stock

Este documento describe los cambios **CRÍTICOS** en el endpoint de búsqueda de productos del punto de venta para corregir la inconsistencia entre el stock mostrado en punto de venta y verinventario.

---

## 📋 Resumen del Problema

**Antes:**
- Punto de venta mostraba: `Stock disponible: 2` (usaba campo `cantidad`)
- Verinventario mostraba: `Existencia: 1` (usaba campo `existencia`)
- **Inconsistencia:** Valores diferentes causaban confusión y errores al confirmar ventas

**Ahora:**
- Punto de venta muestra: `Stock disponible: 1` (usa campo `existencia`)
- Verinventario muestra: `Existencia: 1` (usa campo `existencia`)
- **Consistencia:** Ambos sistemas muestran el mismo valor

---

## 🔧 Cambios en el Backend

### Endpoint: `GET /punto-venta/productos/buscar`

**Cambio principal:** Ahora usa `existencia` como campo principal para mostrar el stock disponible.

**Prioridad de campos:**
1. `existencia` (campo principal)
2. `cantidad` (si no hay existencia)
3. `stock` (si no hay existencia ni cantidad)

### Estructura de Respuesta Actualizada

```json
{
  "id": "69349598873821ce1837413d",
  "codigo": "TT1135",
  "nombre": "ESMERIL ANGULAR 4-1/2 710W",
  "costo": 22.00,
  "utilidad": 8.80,
  "porcentaje_utilidad": 40.0,
  "precio": 30.80,
  "precio_venta": 30.80,
  "cantidad": 1,          // ← AHORA usa existencia como valor
  "stock": 1,              // ← AHORA usa existencia como valor
  "existencia": 1,         // ← NUEVO: Campo explícito con el valor real
  "sucursal": "01",
  "estado": "activo",
  "marca": ""
}
```

**Campos importantes:**
- `cantidad`: Stock disponible (usa `existencia` como fuente)
- `stock`: Stock disponible (usa `existencia` como fuente) - **para compatibilidad**
- `existencia`: Existencia disponible (campo principal) - **USAR ESTE**

---

## 🎨 Instrucciones para el Frontend

### 1. Mostrar Stock Disponible en Punto de Venta

**IMPORTANTE:** Usar el campo `existencia` para mostrar el stock disponible.

#### ❌ INCORRECTO (Antes):
```jsx
// NO usar cantidad directamente
<div>Stock disponible: {producto.cantidad}</div>
```

#### ✅ CORRECTO (Ahora):
```jsx
// Usar existencia como campo principal
<div>Stock disponible: {producto.existencia ?? producto.cantidad ?? producto.stock ?? 0}</div>

// O más simple si el backend ya normaliza:
<div>Stock disponible: {producto.existencia || producto.cantidad || 0}</div>
```

### 2. Ejemplo Completo - Componente de Búsqueda

```jsx
import { useState, useEffect } from 'react';

const BuscarProducto = () => {
  const [productos, setProductos] = useState([]);
  const [busqueda, setBusqueda] = useState('');

  const buscarProductos = async (query) => {
    try {
      const response = await fetch(
        `${API_URL}/punto-venta/productos/buscar?q=${encodeURIComponent(query)}&sucursal=01`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      const data = await response.json();
      setProductos(data);
    } catch (error) {
      console.error('Error buscando productos:', error);
    }
  };

  return (
    <div>
      <input
        type="text"
        value={busqueda}
        onChange={(e) => {
          setBusqueda(e.target.value);
          buscarProductos(e.target.value);
        }}
        placeholder="Buscar producto..."
      />
      
      <div className="productos-lista">
        {productos.map((producto) => (
          <div key={producto.id} className="producto-item">
            <h3>{producto.nombre}</h3>
            <p>Código: {producto.codigo}</p>
            <p>Precio: ${producto.precio.toFixed(2)}</p>
            
            {/* ✅ USAR EXISTENCIA */}
            <p className="stock-disponible">
              Stock disponible: {producto.existencia ?? producto.cantidad ?? 0}
            </p>
            
            {/* Validar stock antes de agregar */}
            {producto.existencia > 0 ? (
              <button onClick={() => agregarAlCarrito(producto)}>
                Agregar al carrito
              </button>
            ) : (
              <button disabled>Sin stock</button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
```

### 3. Validación de Stock al Agregar Producto

```jsx
const agregarAlCarrito = (producto) => {
  // Validar stock usando existencia
  const stockDisponible = producto.existencia ?? producto.cantidad ?? 0;
  
  if (stockDisponible <= 0) {
    alert('Producto sin stock disponible');
    return;
  }
  
  // Verificar si ya está en el carrito
  const itemExistente = carrito.find(item => item.id === producto.id);
  const cantidadEnCarrito = itemExistente ? itemExistente.cantidad : 0;
  
  if (cantidadEnCarrito >= stockDisponible) {
    alert(`Stock insuficiente. Disponible: ${stockDisponible}`);
    return;
  }
  
  // Agregar al carrito
  // ...
};
```

### 4. Mostrar Stock en Modal de Confirmación

```jsx
const ModalConfirmarVenta = ({ productos }) => {
  return (
    <div className="modal">
      <h2>Confirmar Venta</h2>
      
      <table>
        <thead>
          <tr>
            <th>Producto</th>
            <th>Cantidad</th>
            <th>Stock Disponible</th>
            <th>Precio</th>
          </tr>
        </thead>
        <tbody>
          {productos.map((item) => {
            // ✅ Usar existencia para mostrar stock
            const stockDisponible = item.existencia ?? item.cantidad ?? 0;
            const tieneStock = stockDisponible >= item.cantidad;
            
            return (
              <tr key={item.id} className={!tieneStock ? 'sin-stock' : ''}>
                <td>{item.nombre}</td>
                <td>{item.cantidad}</td>
                <td>
                  {/* Mostrar stock disponible */}
                  <span className={!tieneStock ? 'error' : ''}>
                    {stockDisponible}
                  </span>
                  {!tieneStock && (
                    <span className="error-message">
                      ⚠️ Stock insuficiente
                    </span>
                  )}
                </td>
                <td>${item.precio.toFixed(2)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      
      <button 
        onClick={confirmarVenta}
        disabled={!todosTienenStock()}
      >
        Confirmar e Imprimir
      </button>
    </div>
  );
};
```

### 5. Función de Validación de Stock

```jsx
const validarStockDisponible = (productos) => {
  return productos.every((item) => {
    // ✅ Usar existencia como campo principal
    const stockDisponible = item.existencia ?? item.cantidad ?? 0;
    return stockDisponible >= item.cantidad;
  });
};

const todosTienenStock = () => {
  return carrito.every((item) => {
    // Buscar el producto original para obtener stock actualizado
    const producto = productos.find(p => p.id === item.id);
    if (!producto) return false;
    
    // ✅ Usar existencia
    const stockDisponible = producto.existencia ?? producto.cantidad ?? 0;
    return stockDisponible >= item.cantidad;
  });
};
```

---

## 🔄 Flujo Completo de Venta

### Paso 1: Búsqueda de Producto
```jsx
// El backend retorna:
{
  "id": "...",
  "codigo": "TT1135",
  "nombre": "ESMERIL ANGULAR 4-1/2 710W",
  "existencia": 1,  // ← USAR ESTE VALOR
  "cantidad": 1,    // ← Compatibilidad (mismo valor)
  "stock": 1        // ← Compatibilidad (mismo valor)
}
```

### Paso 2: Mostrar en UI
```jsx
// Mostrar stock disponible
<p>Stock disponible: {producto.existencia}</p>
```

### Paso 3: Validar al Agregar
```jsx
if (producto.existencia < cantidadSolicitada) {
  alert('Stock insuficiente');
  return;
}
```

### Paso 4: Confirmar Venta
```jsx
// Al confirmar, el backend descuenta automáticamente:
// - existencia
// - cantidad  
// - stock
// Todos se actualizan con el mismo valor
```

---

## ⚠️ Puntos Críticos

### 1. Siempre Usar `existencia` como Campo Principal

```jsx
// ✅ CORRECTO
const stock = producto.existencia ?? producto.cantidad ?? 0;

// ❌ INCORRECTO (puede mostrar valor incorrecto)
const stock = producto.cantidad;
```

### 2. Validar Stock Antes de Confirmar

```jsx
// ✅ Validar antes de enviar venta
const puedeConfirmar = productos.every(item => {
  const stock = item.existencia ?? 0;
  return stock >= item.cantidad;
});

if (!puedeConfirmar) {
  alert('Algunos productos no tienen stock suficiente');
  return;
}
```

### 3. Actualizar Stock Después de Búsqueda

```jsx
// Si el usuario busca el mismo producto varias veces,
// el stock puede cambiar. Siempre usar el valor más reciente.
const buscarProducto = async (codigo) => {
  const response = await fetch(`/punto-venta/productos/buscar?q=${codigo}`);
  const productos = await response.json();
  const producto = productos[0];
  
  // ✅ Usar existencia del resultado más reciente
  setStockDisponible(producto.existencia);
};
```

---

## 🧪 Casos de Prueba

### Caso 1: Producto con Existencia
```json
// Respuesta del backend:
{
  "existencia": 1,
  "cantidad": 1,
  "stock": 1
}
```
**Resultado esperado:** Mostrar "Stock disponible: 1"

### Caso 2: Producto sin Existencia pero con Cantidad
```json
// Respuesta del backend:
{
  "existencia": 0,
  "cantidad": 5,
  "stock": 5
}
```
**Resultado esperado:** Mostrar "Stock disponible: 5" (usa cantidad como fallback)

### Caso 3: Producto sin Stock
```json
// Respuesta del backend:
{
  "existencia": 0,
  "cantidad": 0,
  "stock": 0
}
```
**Resultado esperado:** Mostrar "Sin stock" y deshabilitar botón de agregar

---

## 📊 Comparación: Antes vs Ahora

| Escenario | Antes | Ahora |
|-----------|-------|-------|
| Campo usado | `cantidad` | `existencia` |
| Valor mostrado | Podía ser diferente | Siempre igual a verinventario |
| Consistencia | ❌ Inconsistente | ✅ Consistente |
| Validación | Podía fallar | ✅ Funciona correctamente |

---

## 🔍 Verificación

### Checklist de Implementación

- [ ] Cambiar todas las referencias de `producto.cantidad` a `producto.existencia`
- [ ] Actualizar validaciones de stock para usar `existencia`
- [ ] Actualizar mensajes de "Stock disponible" para usar `existencia`
- [ ] Probar que el stock mostrado coincide con verinventario
- [ ] Probar que las ventas descuentan correctamente el inventario
- [ ] Probar validación de stock insuficiente

---

## 📝 Notas Adicionales

### Compatibilidad

El backend mantiene compatibilidad retornando:
- `cantidad`: Mismo valor que `existencia` (para compatibilidad)
- `stock`: Mismo valor que `existencia` (para compatibilidad)
- `existencia`: Valor real del campo (usar este)

### Migración Gradual

Si tienes código existente que usa `cantidad` o `stock`, puedes migrar gradualmente:

```jsx
// Fase 1: Agregar fallback
const stock = producto.existencia ?? producto.cantidad ?? 0;

// Fase 2: Cambiar a existencia como principal
const stock = producto.existencia ?? 0;
```

---

## 🚀 Referencias

- **Endpoint:** `GET /punto-venta/productos/buscar`
- **Archivo backend:** `app/routes/punto_venta.py`
- **Documentación relacionada:**
  - `INSTRUCCIONES_BACKEND_URGENTE_DESCUENTO_STOCK.md` - Descuento de inventario
  - `INSTRUCCIONES_FRONTEND_UTILIDAD_40.md` - Utilidad 40%

---

**Última actualización:** 2024-12-20  
**Estado:** ✅ Implementado  
**Prioridad:** 🚨 CRÍTICA

