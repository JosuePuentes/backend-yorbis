# Instrucciones Frontend - Actualización de UI después de Cargar Existencia

## 🎯 Problema Resuelto

Después de cargar existencia masiva, el frontend debe actualizar la UI **sin recargar toda la página**. El backend ahora retorna los productos completos actualizados para facilitar esto.

---

## ✅ Cambios en el Backend

### **POST `/inventarios/cargar-existencia` - Respuesta Mejorada**

El endpoint ahora retorna los productos **completos y actualizados** en el campo `detalle.exitosos`:

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
        "id": "693877e8873821ce183741c9",
        "_id": "693877e8873821ce183741c9",
        "codigo": "MAR-001",
        "nombre": "Martillo",
        "descripcion": "Martillo de acero",
        "marca": "Marca X",
        "cantidad": 30,              // ← CANTIDAD ACTUALIZADA
        "costo": 100.00,
        "precio_venta": 166.67,
        "precio": 166.67,
        "utilidad": 66.67,
        "porcentaje_utilidad": 40.0,
        "farmacia": "01",
        "estado": "activo",
        // Información adicional
        "cantidad_anterior": 20,     // ← Cantidad antes de cargar
        "cantidad_suma": 10,         // ← Cantidad que se sumó
        "cantidad_nueva": 30         // ← Cantidad nueva (igual a cantidad)
      }
    ],
    "errores": []
  }
}
```

---

## 🎨 Implementación en el Frontend

### **Actualizar UI sin Recargar Página**

Después de cargar existencia, actualiza **solo los productos modificados** en el estado local:

```jsx
const handleCargarExistencia = async () => {
  setCargando(true);
  
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
          utilidad: datosCarga[productoId]?.utilidad ? parseFloat(datosCarga[productoId].utilidad) : undefined,
          porcentaje_utilidad: datosCarga[productoId]?.porcentaje_utilidad || 40.0
        })).filter(p => p.cantidad > 0)
      })
    });

    const resultado = await response.json();

    if (response.ok) {
      // ✅ Éxito - Actualizar UI sin recargar página
      console.log(`✅ ${resultado.productos_exitosos} productos actualizados`);
      
      // ACTUALIZAR SOLO LOS PRODUCTOS MODIFICADOS
      resultado.detalle.exitosos.forEach(productoActualizado => {
        // Opción 1: Actualizar en el estado de la lista principal
        setProductos(prevProductos => 
          prevProductos.map(producto => 
            producto.id === productoActualizado.id 
              ? { ...producto, ...productoActualizado }  // Reemplazar con datos actualizados
              : producto
          )
        );
        
        // Opción 2: Si usas un mapa/diccionario
        setProductosMap(prev => ({
          ...prev,
          [productoActualizado.id]: productoActualizado
        }));
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
```

---

## 🔧 Ejemplo Completo con React

```jsx
import { useState } from 'react';

const VisualizarInventariosPage = () => {
  const [productos, setProductos] = useState([]);
  const [productosSeleccionados, setProductosSeleccionados] = useState([]);
  const [datosCarga, setDatosCarga] = useState({});

  // Función para cargar existencia masiva
  const cargarExistenciaMasiva = async () => {
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
        // ✅ ACTUALIZAR UI SIN RECARGAR PÁGINA
        // Actualizar solo los productos modificados
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
            } else {
              // Si no existe en la lista, agregarlo (por si acaso)
              productosActualizados.push(productoActualizado);
            }
          });
          
          return productosActualizados;
        });

        // Mostrar mensaje de éxito
        toast.success(`✅ ${resultado.productos_exitosos} productos actualizados`);
        
        // Limpiar selección
        setProductosSeleccionados([]);
        setDatosCarga({});
      } else {
        toast.error(`Error: ${resultado.detail || 'Error al cargar existencia'}`);
      }
    } catch (error) {
      console.error('Error:', error);
      toast.error('Error al cargar existencia');
    }
  };

  return (
    <div>
      {/* Tabla de productos */}
      <table>
        <thead>
          <tr>
            <th>Código</th>
            <th>Nombre</th>
            <th>Cantidad</th>
            <th>Costo</th>
            <th>Precio Venta</th>
          </tr>
        </thead>
        <tbody>
          {productos.map(producto => (
            <tr key={producto.id}>
              <td>{producto.codigo}</td>
              <td>{producto.nombre}</td>
              <td>{producto.cantidad}</td>  {/* ← Se actualiza automáticamente */}
              <td>{producto.costo}</td>
              <td>{producto.precio_venta}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
```

---

## ⚡ Optimizaciones Aplicadas

### **1. Actualización Selectiva**
- Solo actualiza los productos que fueron modificados
- No recarga toda la lista
- Mantiene el estado de la UI (scroll, selecciones, etc.)

### **2. Datos Completos**
- El backend retorna el producto completo actualizado
- El frontend puede reemplazar directamente el producto en el estado
- No necesita hacer otra petición para obtener los datos actualizados

### **3. Información Adicional**
- Incluye `cantidad_anterior`, `cantidad_suma`, `cantidad_nueva`
- Útil para mostrar mensajes informativos al usuario
- Facilita el debugging

---

## ✅ Checklist de Implementación

- [ ] Actualizar función `handleCargarExistencia` para usar los productos retornados
- [ ] Actualizar estado local solo con productos modificados
- [ ] No recargar toda la página después de cargar
- [ ] Mostrar mensajes de éxito/error
- [ ] Limpiar selección después de cargar exitosamente
- [ ] Probar que la cantidad se actualiza correctamente en la UI
- [ ] Verificar que no se pierde el estado de la UI (scroll, etc.)

---

## 🐛 Troubleshooting

### **Problema: La cantidad no se actualiza en la UI**

**Solución:**
1. Verificar que estás actualizando el estado correctamente
2. Verificar que el `id` del producto coincide
3. Verificar que estás usando los datos del campo `detalle.exitosos`
4. Agregar logs para ver qué productos se están actualizando

```javascript
resultado.detalle.exitosos.forEach(productoActualizado => {
  console.log('Actualizando producto:', productoActualizado.id, productoActualizado.cantidad);
  // ... código de actualización
});
```

### **Problema: Se recarga toda la página**

**Solución:**
1. Asegurarse de que NO estás llamando a `window.location.reload()` o similar
2. Asegurarse de que NO estás recargando la lista completa después de cargar
3. Solo actualizar los productos específicos que fueron modificados

---

**Última actualización:** 2025-12-11


