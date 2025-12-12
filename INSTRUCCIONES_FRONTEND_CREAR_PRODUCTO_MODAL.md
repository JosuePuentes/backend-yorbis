# Instrucciones Frontend - Crear Producto Nuevo en Modal de Carga Masiva

## 🚀 Nuevo Endpoint: Crear Producto

### **POST `/inventarios/crear-producto`**

**Descripción:** Crea un nuevo producto en el inventario desde el modal de carga masiva.

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
  "farmacia": "01",                    // ID de la farmacia (requerido)
  "codigo": "PROD-001",                // Código del producto (opcional)
  "nombre": "Producto Nuevo",          // Nombre del producto (requerido)
  "descripcion": "Descripción...",     // Descripción (opcional)
  "marca": "Marca X",                  // Marca (opcional)
  "cantidad": 0,                       // Cantidad inicial (opcional, default 0)
  "costo": 100.00,                     // Costo unitario (requerido, > 0)
  "utilidad": 66.67,                   // Utilidad en dinero (opcional)
  "porcentaje_utilidad": 40.0,         // Porcentaje de utilidad (opcional, default 40%)
  "precio_venta": 166.67               // Precio de venta (opcional, se calcula si no se envía)
}
```

**Response (200 OK):**
```javascript
{
  "message": "Producto creado exitosamente",
  "producto": {
    "id": "693877e8873821ce183741c9",
    "_id": "693877e8873821ce183741c9",
    "codigo": "PROD-001",
    "nombre": "Producto Nuevo",
    "descripcion": "Descripción...",
    "marca": "Marca X",
    "cantidad": 0,
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

**Errores posibles:**
- `400`: Campo requerido faltante o inválido
- `400`: Ya existe un producto con el mismo código en esta farmacia
- `500`: Error del servidor

---

## 🎨 Implementación en el Frontend

### **Ejemplo de Componente React:**

```jsx
import { useState } from 'react';

const CargarExistenciasMasivaModal = () => {
  const [mostrarCrearProducto, setMostrarCrearProducto] = useState(false);
  const [nuevoProducto, setNuevoProducto] = useState({
    codigo: '',
    nombre: '',
    descripcion: '',
    marca: '',
    cantidad: 0,
    costo: '',
    utilidad: '',
    porcentaje_utilidad: 40.0
  });

  const handleCrearProducto = async () => {
    // Validar campos requeridos
    if (!nuevoProducto.nombre.trim()) {
      alert('El nombre del producto es requerido');
      return;
    }

    if (!nuevoProducto.costo || parseFloat(nuevoProducto.costo) <= 0) {
      alert('El costo debe ser mayor a 0');
      return;
    }

    try {
      const response = await fetch('/inventarios/crear-producto', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          farmacia: farmaciaId,
          codigo: nuevoProducto.codigo.trim() || undefined,
          nombre: nuevoProducto.nombre.trim(),
          descripcion: nuevoProducto.descripcion.trim() || undefined,
          marca: nuevoProducto.marca.trim() || undefined,
          cantidad: parseFloat(nuevoProducto.cantidad) || 0,
          costo: parseFloat(nuevoProducto.costo),
          utilidad: nuevoProducto.utilidad ? parseFloat(nuevoProducto.utilidad) : undefined,
          porcentaje_utilidad: parseFloat(nuevoProducto.porcentaje_utilidad) || 40.0
        })
      });

      const resultado = await response.json();

      if (response.ok) {
        // ✅ Producto creado exitosamente
        console.log('Producto creado:', resultado.producto);
        
        // Agregar el producto a la lista de productos disponibles
        // (para que aparezca en la búsqueda inmediatamente)
        agregarProductoALista(resultado.producto);
        
        // Seleccionar automáticamente el producto recién creado
        seleccionarProducto(resultado.producto.id);
        
        // Limpiar formulario
        setNuevoProducto({
          codigo: '',
          nombre: '',
          descripcion: '',
          marca: '',
          cantidad: 0,
          costo: '',
          utilidad: '',
          porcentaje_utilidad: 40.0
        });
        
        // Cerrar modal de crear producto
        setMostrarCrearProducto(false);
        
        // Mostrar mensaje de éxito
        toast.success('Producto creado exitosamente');
      } else {
        // ❌ Error
        console.error('Error:', resultado);
        alert(`Error: ${resultado.detail || 'Error al crear producto'}`);
      }
    } catch (error) {
      console.error('Error:', error);
      alert('Error al crear producto');
    }
  };

  return (
    <div>
      {/* Botón para abrir modal de crear producto */}
      <button onClick={() => setMostrarCrearProducto(true)}>
        + Crear Producto Nuevo
      </button>

      {/* Modal de crear producto */}
      {mostrarCrearProducto && (
        <div className="modal">
          <div className="modal-content">
            <h2>Crear Producto Nuevo</h2>
            
            <div className="form-group">
              <label>Código (opcional)</label>
              <input
                type="text"
                value={nuevoProducto.codigo}
                onChange={(e) => setNuevoProducto({...nuevoProducto, codigo: e.target.value})}
                placeholder="PROD-001"
              />
            </div>

            <div className="form-group">
              <label>Nombre *</label>
              <input
                type="text"
                value={nuevoProducto.nombre}
                onChange={(e) => setNuevoProducto({...nuevoProducto, nombre: e.target.value})}
                placeholder="Nombre del producto"
                required
              />
            </div>

            <div className="form-group">
              <label>Descripción (opcional)</label>
              <textarea
                value={nuevoProducto.descripcion}
                onChange={(e) => setNuevoProducto({...nuevoProducto, descripcion: e.target.value})}
                placeholder="Descripción del producto"
              />
            </div>

            <div className="form-group">
              <label>Marca (opcional)</label>
              <input
                type="text"
                value={nuevoProducto.marca}
                onChange={(e) => setNuevoProducto({...nuevoProducto, marca: e.target.value})}
                placeholder="Marca del producto"
              />
            </div>

            <div className="form-group">
              <label>Cantidad Inicial (opcional)</label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={nuevoProducto.cantidad}
                onChange={(e) => setNuevoProducto({...nuevoProducto, cantidad: e.target.value})}
                placeholder="0"
              />
            </div>

            <div className="form-group">
              <label>Costo *</label>
              <input
                type="number"
                min="0.01"
                step="0.01"
                value={nuevoProducto.costo}
                onChange={(e) => setNuevoProducto({...nuevoProducto, costo: e.target.value})}
                placeholder="100.00"
                required
              />
            </div>

            <div className="form-group">
              <label>% Utilidad (opcional, default 40%)</label>
              <input
                type="number"
                min="0"
                max="100"
                step="0.1"
                value={nuevoProducto.porcentaje_utilidad}
                onChange={(e) => setNuevoProducto({...nuevoProducto, porcentaje_utilidad: e.target.value})}
                placeholder="40.0"
              />
            </div>

            <div className="form-group">
              <label>Utilidad en $ (opcional)</label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={nuevoProducto.utilidad}
                onChange={(e) => setNuevoProducto({...nuevoProducto, utilidad: e.target.value})}
                placeholder="66.67"
              />
              <small>Si se especifica, se usará en lugar del % utilidad</small>
            </div>

            <div className="modal-actions">
              <button onClick={handleCrearProducto}>
                Crear Producto
              </button>
              <button onClick={() => setMostrarCrearProducto(false)}>
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
```

---

## ⚙️ Comportamiento del Backend

### **Validaciones:**

1. **Campos requeridos:**
   - `farmacia`: Debe estar presente
   - `nombre`: Debe estar presente y no estar vacío
   - `costo`: Debe ser mayor a 0

2. **Validación de código único:**
   - Si se proporciona un código, verifica que no exista otro producto activo con el mismo código en la misma farmacia
   - Si existe, retorna error 400

3. **Cálculo de precio de venta:**
   - Si se envía `precio_venta`: Se usa ese precio
   - Si se envía `utilidad`: Se calcula `precio_venta = costo + utilidad`
   - Si se envía `porcentaje_utilidad`: Se calcula `precio_venta = costo / (1 - porcentaje/100)`
   - Si no se envía nada: Se calcula con 40% de utilidad por defecto

### **Campos opcionales:**
- `codigo`: Si no se proporciona, el producto se crea sin código
- `descripcion`: Si no se proporciona, se guarda como string vacío
- `marca`: Si no se proporciona, se guarda como string vacío
- `cantidad`: Si no se proporciona, se guarda como 0
- `utilidad` o `porcentaje_utilidad`: Si no se proporcionan, se calculan automáticamente

---

## ✅ Checklist de Implementación

- [ ] Agregar botón "Crear Producto Nuevo" en el modal de carga masiva
- [ ] Crear modal/formulario para ingresar datos del producto
- [ ] Implementar función `handleCrearProducto`
- [ ] Validar campos requeridos (nombre, costo)
- [ ] Manejar errores (código duplicado, etc.)
- [ ] Agregar producto creado a la lista de productos disponibles
- [ ] Seleccionar automáticamente el producto recién creado
- [ ] Mostrar mensaje de éxito/error
- [ ] Limpiar formulario después de crear

---

## 🎯 Flujo Recomendado

1. Usuario hace clic en "Crear Producto Nuevo"
2. Se abre modal con formulario
3. Usuario ingresa datos (código, nombre, descripción, marca, costo, utilidad)
4. Usuario hace clic en "Crear Producto"
5. Backend valida y crea el producto
6. Frontend:
   - Agrega el producto a la lista
   - Selecciona automáticamente el producto
   - Cierra el modal de crear producto
   - Muestra mensaje de éxito
7. Usuario puede continuar con la carga de existencia normalmente

---

**Última actualización:** 2025-12-12

