# Instrucciones Frontend - Campo Marca en Productos

## 📋 Resumen

El backend ahora incluye el campo `marca` en todas las respuestas de productos e inventarios. Este documento explica cómo mostrar la marca en el frontend.

---

## 🔍 Endpoints que Incluyen Marca

### 1. **GET `/punto-venta/productos/buscar`**

**Respuesta:**
```json
{
  "id": "producto_id",
  "codigo": "ABC123",
  "nombre": "Producto Ejemplo",
  "marca": "Marca Ejemplo",  // ← NUEVO CAMPO
  "costo": 100.00,
  "utilidad": 66.67,
  "porcentaje_utilidad": 40.0,
  "precio": 166.67,
  "precio_venta": 166.67,
  "cantidad": 10,
  "stock": 10,
  "sucursal": "01",
  "estado": "activo"
}
```

### 2. **GET `/inventarios/{id}/items`**

**Respuesta:**
```json
[
  {
    "_id": "item_id",
    "id": "item_id",
    "codigo": "ABC123",
    "nombre": "Producto Ejemplo",
    "descripcion": "Descripción del producto",
    "marca": "Marca Ejemplo",  // ← NUEVO CAMPO
    "cantidad": 10,
    "costo": 100.00,
    "precio_venta": 166.67,
    "precio": 166.67,
    "utilidad": 66.67,
    "porcentaje_utilidad": 40.0,
    "farmacia": "01",
    "estado": "activo"
  }
]
```

---

## 🎨 Implementación en el Frontend

### **Punto de Venta - Tabla de Productos**

```jsx
// Ejemplo en React/Next.js
const ProductoRow = ({ producto }) => {
  return (
    <tr>
      <td>{producto.codigo}</td>
      <td>{producto.nombre}</td>
      <td>{producto.marca || 'Sin marca'}</td>  {/* ← AGREGAR ESTA COLUMNA */}
      <td>${producto.precio.toFixed(2)}</td>
      <td>{producto.cantidad}</td>
    </tr>
  );
};
```

### **Inventarios - Tabla de Items**

```jsx
// Ejemplo en React/Next.js
const InventarioRow = ({ item }) => {
  return (
    <tr>
      <td>{item.codigo}</td>
      <td>{item.nombre}</td>
      <td>{item.marca || 'Sin marca'}</td>  {/* ← AGREGAR ESTA COLUMNA */}
      <td>{item.descripcion}</td>
      <td>${item.costo.toFixed(2)}</td>
      <td>${item.precio_venta.toFixed(2)}</td>
      <td>{item.cantidad}</td>
    </tr>
  );
};
```

---

## 📊 Estructura de Tabla Recomendada

### **Punto de Venta**

| Código | Nombre | **Marca** | Precio | Stock |
|--------|--------|-----------|--------|-------|
| ABC123 | Producto 1 | Marca X | $166.67 | 10 |

### **Inventarios**

| Código | Nombre | **Marca** | Descripción | Costo | Precio Venta | Cantidad |
|--------|--------|-----------|-------------|-------|-------------|----------|
| ABC123 | Producto 1 | Marca X | Desc... | $100.00 | $166.67 | 10 |

---

## 🔧 Manejo de Valores Vacíos

El campo `marca` puede estar vacío (`""`) o ser `null`. Siempre mostrar un valor por defecto:

```jsx
// Opción 1: Mostrar "Sin marca"
{producto.marca || 'Sin marca'}

// Opción 2: Mostrar guión
{producto.marca || '-'}

// Opción 3: Ocultar si está vacío
{producto.marca && <span>{producto.marca}</span>}
```

---

## ✅ Checklist de Implementación

- [ ] Agregar columna "Marca" en tabla de productos del punto de venta
- [ ] Agregar columna "Marca" en tabla de items de inventarios
- [ ] Manejar valores vacíos de marca (mostrar "Sin marca" o "-")
- [ ] Verificar que la marca se muestre correctamente en búsquedas
- [ ] Probar con productos que tienen marca y sin marca

---

## 🐛 Solución de Problemas

### **La marca no aparece en punto de venta**

1. Verificar que el endpoint `/punto-venta/productos/buscar` retorna el campo `marca`
2. Verificar en la consola del navegador la respuesta del API
3. Asegurarse de que el componente está accediendo a `producto.marca`

### **La marca aparece como `undefined`**

- Usar el operador de coalescencia nula: `producto.marca ?? 'Sin marca'`
- O verificar: `producto.marca || 'Sin marca'`

---

## 📝 Notas Importantes

1. **El campo `marca` puede venir vacío**: Siempre manejar el caso cuando no hay marca
2. **Compatibilidad**: El backend acepta tanto `marca` como `marca_producto` al guardar
3. **Búsqueda**: La marca se incluye en las búsquedas amplias del punto de venta
4. **Actualización**: Al actualizar un producto desde compras, la marca se guarda automáticamente

---

## 🚀 Optimizaciones Aplicadas

El endpoint `/inventarios/{id}/items` ha sido optimizado para mejor rendimiento:
- Proyección mínima de campos
- Uso eficiente de índices
- Procesamiento rápido de resultados
- Límite de 500 resultados

El endpoint `/punto-venta/productos/buscar` ya estaba optimizado y ahora incluye la marca.

---

**Última actualización:** 2025-12-10


