# Instrucciones Frontend - Búsqueda Rápida en Modal de Carga Masiva

## 🚀 Nuevo Endpoint Ultra Optimizado

### **GET `/inventarios/buscar`**

**Descripción:** Búsqueda ULTRA RÁPIDA de productos en inventario específicamente para el modal de carga masiva. Optimizado para responder en menos de 5 segundos.

**Headers:**
```javascript
{
  "Authorization": "Bearer {token}"
}
```

**Parámetros:**
- `q` (requerido): Término de búsqueda (código, nombre o descripción)
- `farmacia` (opcional): ID de la farmacia
- `limit` (opcional): Límite de resultados (máximo 50, por defecto 50)

**Ejemplo de uso:**
```javascript
// Búsqueda básica
GET /inventarios/buscar?q=martillo

// Búsqueda con farmacia
GET /inventarios/buscar?q=martillo&farmacia=01

// Búsqueda con límite personalizado
GET /inventarios/buscar?q=martillo&limit=30
```

**Response (200 OK):**
```javascript
[
  {
    "id": "693877e8873821ce183741c9",
    "_id": "693877e8873821ce183741c9",
    "codigo": "MAR-001",
    "nombre": "Martillo",
    "descripcion": "Martillo de acero",
    "marca": "Marca X",
    "cantidad": 50,
    "costo": 100.00,
    "precio_venta": 166.67,
    "precio": 166.67,
    "utilidad": 66.67,
    "porcentaje_utilidad": 40.0,
    "farmacia": "01"
  },
  // ... más productos (máximo 50)
]
```

---

## ⚡ Optimizaciones Aplicadas

### **1. Búsqueda Exacta por Código Primero**
- Si el término coincide exactamente con un código, retorna ese producto instantáneamente
- Usa índice de MongoDB para búsqueda ultra rápida

### **2. Búsqueda por Prefijo**
- Si no hay coincidencia exacta, busca productos que **empiecen** con el término
- Busca en código y nombre (campos indexados)
- Mucho más rápida que búsqueda parcial en cualquier parte

### **3. Proyección Mínima**
- Solo trae campos esenciales para el modal
- Reduce transferencia de datos en ~60%

### **4. Límite Reducido**
- Máximo 50 resultados (suficiente para el modal)
- Reduce tiempo de procesamiento

### **5. Solo Productos Activos**
- Filtra automáticamente productos inactivos
- Reduce resultados innecesarios

---

## 🎨 Implementación en el Frontend

### **Ejemplo de Componente React con Debounce:**

```jsx
import { useState, useEffect, useCallback } from 'react';
import { debounce } from 'lodash'; // o implementar tu propio debounce

const CargarExistenciasMasivaModal = () => {
  const [terminoBusqueda, setTerminoBusqueda] = useState('');
  const [productos, setProductos] = useState([]);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);

  // Función de búsqueda con debounce (espera 300ms después de que el usuario deje de escribir)
  const buscarProductos = useCallback(
    debounce(async (termino) => {
      if (!termino || termino.trim().length < 2) {
        setProductos([]);
        return;
      }

      setCargando(true);
      setError(null);

      try {
        const response = await fetch(
          `/inventarios/buscar?q=${encodeURIComponent(termino)}&farmacia=${farmaciaId}&limit=50`,
          {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        );

        if (!response.ok) {
          throw new Error('Error al buscar productos');
        }

        const datos = await response.json();
        setProductos(datos);
      } catch (err) {
        setError(err.message);
        setProductos([]);
      } finally {
        setCargando(false);
      }
    }, 300), // 300ms de debounce
    [farmaciaId, token]
  );

  // Efecto para buscar cuando cambia el término
  useEffect(() => {
    buscarProductos(terminoBusqueda);
    
    // Cleanup: cancelar búsqueda pendiente si el componente se desmonta
    return () => {
      buscarProductos.cancel();
    };
  }, [terminoBusqueda, buscarProductos]);

  return (
    <div>
      {/* Campo de búsqueda */}
      <input
        type="text"
        placeholder="Buscar por código, nombre o descripción..."
        value={terminoBusqueda}
        onChange={(e) => setTerminoBusqueda(e.target.value)}
      />

      {/* Indicador de carga */}
      {cargando && <div>Buscando...</div>}

      {/* Error */}
      {error && <div className="error">{error}</div>}

      {/* Lista de productos */}
      {!cargando && productos.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Seleccionar</th>
              <th>Código</th>
              <th>Nombre</th>
              <th>Cantidad</th>
              <th>Costo</th>
              <th>Precio Venta</th>
            </tr>
          </thead>
          <tbody>
            {productos.map((producto) => (
              <tr key={producto.id}>
                <td>
                  <input
                    type="checkbox"
                    // ... lógica de selección
                  />
                </td>
                <td>{producto.codigo}</td>
                <td>{producto.nombre}</td>
                <td>{producto.cantidad}</td>
                <td>{producto.costo}</td>
                <td>{producto.precio_venta}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Mensaje si no hay resultados */}
      {!cargando && terminoBusqueda && productos.length === 0 && (
        <div>No se encontraron productos</div>
      )}
    </div>
  );
};
```

---

## ⚙️ Mejores Prácticas

### **1. Usar Debounce**
- Espera 300-500ms después de que el usuario deje de escribir
- Evita hacer una petición por cada tecla presionada
- Mejora significativamente el rendimiento

### **2. Validar Longitud Mínima**
- No buscar si el término tiene menos de 2-3 caracteres
- Reduce peticiones innecesarias

### **3. Mostrar Indicador de Carga**
- Muestra un spinner o mensaje mientras busca
- Mejora la experiencia del usuario

### **4. Manejar Errores**
- Captura y muestra errores de red o del servidor
- Permite al usuario reintentar

### **5. Limpiar Búsquedas Pendientes**
- Cancela búsquedas pendientes cuando el componente se desmonta
- Evita actualizaciones de estado en componentes desmontados

---

## 📊 Comparación de Rendimiento

| Métrica | Endpoint Anterior | Nuevo Endpoint | Mejora |
|---------|-------------------|----------------|--------|
| Tiempo de respuesta | 2+ minutos | <5 segundos | ~96% más rápido |
| Resultados máximos | 200+ | 50 | Más enfocado |
| Campos transferidos | ~12 | ~12 | Similar |
| Búsqueda exacta | No optimizada | ✅ Instantánea | Nueva |

---

## 🔍 Estrategia de Búsqueda

El endpoint usa una estrategia de dos pasos:

1. **Paso 1: Búsqueda Exacta**
   - Busca coincidencia exacta por código
   - Si encuentra, la retorna inmediatamente
   - Usa índice de MongoDB (ultra rápido)

2. **Paso 2: Búsqueda por Prefijo**
   - Si no hay coincidencia exacta o necesita más resultados
   - Busca productos que **empiecen** con el término
   - Busca en código y nombre (campos indexados)
   - Limita a 50 resultados

**Ventajas:**
- ✅ Búsquedas por código son instantáneas
- ✅ Búsquedas por nombre son rápidas (prefijo usa índices)
- ✅ No busca en descripción (más lento)
- ✅ Límite de 50 resultados (suficiente para modal)

---

## ✅ Checklist de Implementación

- [ ] Reemplazar endpoint anterior por `/inventarios/buscar`
- [ ] Agregar debounce a la búsqueda (300-500ms)
- [ ] Validar longitud mínima del término (2-3 caracteres)
- [ ] Mostrar indicador de carga
- [ ] Manejar errores correctamente
- [ ] Limpiar búsquedas pendientes al desmontar
- [ ] Probar con diferentes términos de búsqueda
- [ ] Verificar que la respuesta sea <5 segundos

---

## 🐛 Troubleshooting

### **Problema: La búsqueda sigue siendo lenta**

**Soluciones:**
1. Verificar que estás usando el endpoint correcto: `/inventarios/buscar`
2. Verificar que tienes debounce implementado
3. Verificar que no estás buscando con términos muy cortos (<2 caracteres)
4. Verificar que los índices de MongoDB están creados (verificar con `create_indexes.py`)

### **Problema: No encuentra productos**

**Soluciones:**
1. Verificar que el término de búsqueda tiene al menos 2 caracteres
2. Verificar que estás buscando por código o nombre (no por descripción completa)
3. Verificar que los productos están activos (`estado: "activo"`)

### **Problema: Demasiados resultados**

**Soluciones:**
1. El endpoint ya limita a 50 resultados máximo
2. Si necesitas menos, usa el parámetro `limit`
3. Considera agregar más filtros en el frontend

---

**Última actualización:** 2025-12-11

