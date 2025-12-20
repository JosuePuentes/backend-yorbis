# Instrucciones Frontend - Eliminar Items del Inventario

## 🗑️ Nuevos Endpoints: Eliminación de Items

El backend ahora incluye dos endpoints para eliminar items del inventario:

### 1. **DELETE `/inventarios/{inventario_id}/items/{item_id}`**

Elimina un item por su ID.

**Headers:**
```javascript
{
  "Authorization": "Bearer {token}"
}
```

**Parámetros de URL:**
- `inventario_id`: ID de la farmacia o inventario (puede estar vacío)
- `item_id`: ID del item a eliminar (ObjectId de MongoDB)

**Ejemplo:**
```javascript
DELETE /inventarios/01/items/69461ccb667c6f5d36362356
```

**Response (200 OK):**
```json
{
  "message": "Item eliminado exitosamente",
  "item_id": "69461ccb667c6f5d36362356",
  "codigo": "PPPP1",
  "nombre": "Nombre del Producto",
  "deleted": true
}
```

**Errores posibles:**
- `400`: ID de item inválido
- `400`: El item pertenece a otra farmacia
- `404`: Item no encontrado
- `500`: Error del servidor

---

### 2. **DELETE `/inventarios/{inventario_id}/items/codigo/{codigo}`**

Elimina un item por su código (alternativo).

**Headers:**
```javascript
{
  "Authorization": "Bearer {token}"
}
```

**Parámetros de URL:**
- `inventario_id`: ID de la farmacia o inventario (puede estar vacío)
- `codigo`: Código del item a eliminar (case insensitive)

**Ejemplo:**
```javascript
DELETE /inventarios/01/items/codigo/PPPP1
```

**Response (200 OK):**
```json
{
  "message": "Item eliminado exitosamente",
  "item_id": "69461ccb667c6f5d36362356",
  "codigo": "PPPP1",
  "nombre": "Nombre del Producto",
  "deleted": true
}
```

**Errores posibles:**
- `400`: El item existe pero pertenece a otra farmacia
- `404`: Item con código no encontrado
- `500`: Error del servidor

---

## 🎨 Implementación en el Frontend

### **Ejemplo de Función de Eliminación**

```jsx
import { useState } from 'react';

const EliminarItemInventario = ({ item, farmacia }) => {
  const [eliminando, setEliminando] = useState(false);
  const [error, setError] = useState(null);

  const eliminarItem = async () => {
    if (!confirm(`¿Estás seguro de eliminar el item ${item.codigo}?`)) {
      return;
    }

    setEliminando(true);
    setError(null);

    try {
      // Intentar primero por ID
      let response;
      try {
        response = await fetch(
          `${API_URL}/inventarios/${farmacia}/items/${item.id}`,
          {
            method: 'DELETE',
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        );
      } catch (err) {
        // Si falla por ID, intentar por código
        console.log('Intentando eliminar por código...');
        response = await fetch(
          `${API_URL}/inventarios/${farmacia}/items/codigo/${item.codigo}`,
          {
            method: 'DELETE',
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        );
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error al eliminar item');
      }

      const data = await response.json();
      console.log('Item eliminado:', data);
      
      // Refrescar lista de items
      // ... tu lógica de refresco
      
    } catch (err) {
      console.error('Error eliminando item:', err);
      setError(err.message);
    } finally {
      setEliminando(false);
    }
  };

  return (
    <div>
      <button 
        onClick={eliminarItem}
        disabled={eliminando}
        className="btn-eliminar"
      >
        {eliminando ? 'Eliminando...' : 'Eliminar'}
      </button>
      {error && <div className="error">{error}</div>}
    </div>
  );
};
```

### **Función con Múltiples Intentos (Recomendado)**

```jsx
const eliminarItemConReintentos = async (item, farmacia) => {
  const metodos = [
    // Método 1: Por ID
    async () => {
      const response = await fetch(
        `${API_URL}/inventarios/${farmacia}/items/${item.id}`,
        {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    },
    
    // Método 2: Por código
    async () => {
      const response = await fetch(
        `${API_URL}/inventarios/${farmacia}/items/codigo/${item.codigo}`,
        {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    }
  ];

  // Intentar cada método hasta que uno funcione
  for (let i = 0; i < metodos.length; i++) {
    try {
      console.log(`Intentando método ${i + 1}...`);
      const resultado = await metodos[i]();
      console.log(`✅ Item eliminado exitosamente (método ${i + 1})`);
      return resultado;
    } catch (err) {
      console.log(`⚠️ Método ${i + 1} falló:`, err.message);
      if (i === metodos.length - 1) {
        // Si es el último método, lanzar el error
        throw err;
      }
    }
  }
};
```

---

## 🔍 Validaciones del Backend

### Validaciones Implementadas

1. **Validación de ID:**
   - Verifica que el ID sea un ObjectId válido de MongoDB
   - Retorna error 400 si el ID es inválido

2. **Validación de Existencia:**
   - Verifica que el item exista antes de eliminar
   - Retorna error 404 si no se encuentra

3. **Validación de Farmacia:**
   - Si se especifica `inventario_id`, verifica que el item pertenezca a esa farmacia
   - Retorna error 400 si pertenece a otra farmacia

4. **Búsqueda por Código:**
   - Búsqueda case insensitive (PPPP1, pppp1, Pppp1 funcionan igual)
   - Usa regex para coincidencia exacta

---

## 📊 Logs del Backend

El backend genera logs detallados:

```
🗑️ [INVENTARIOS] Eliminando item por ID: 69461ccb667c6f5d36362356 de inventario: '01'
   Item encontrado: PPPP1 - Nombre del Producto (Farmacia: 01)
✅ [INVENTARIOS] Item eliminado exitosamente: 69461ccb667c6f5d36362356 (PPPP1)
```

O por código:

```
🗑️ [INVENTARIOS] Eliminando item por código: PPPP1 de inventario: '01'
   Item encontrado: PPPP1 - Nombre del Producto (ID: 69461ccb667c6f5d36362356, Farmacia: 01)
✅ [INVENTARIOS] Item eliminado exitosamente por código: PPPP1 (ID: 69461ccb667c6f5d36362356)
```

---

## ⚠️ Manejo de Errores

### Error: Item No Encontrado

**Código:** 404

**Mensaje:** `"Item con ID {item_id} no encontrado"` o `"Item con código '{codigo}' no encontrado"`

**Solución:** Verificar que el item exista y que el ID/código sea correcto

### Error: Item en Otra Farmacia

**Código:** 400

**Mensaje:** `"El item pertenece a la farmacia '{farmacia_item}', no a '{farmacia_buscada}'"`

**Solución:** Usar el ID de farmacia correcto o eliminar sin especificar farmacia

### Error: ID Inválido

**Código:** 400

**Mensaje:** `"ID de item inválido: {item_id}"`

**Solución:** Verificar que el ID sea un ObjectId válido de MongoDB

---

## 🧪 Casos de Prueba

### Prueba 1: Eliminar por ID

**Request:**
```javascript
DELETE /inventarios/01/items/69461ccb667c6f5d36362356
```

**Resultado esperado:**
- ✅ Item eliminado exitosamente
- ✅ Response con datos del item eliminado
- ✅ Item ya no aparece en la lista

### Prueba 2: Eliminar por Código

**Request:**
```javascript
DELETE /inventarios/01/items/codigo/PPPP1
```

**Resultado esperado:**
- ✅ Item eliminado exitosamente
- ✅ Response con datos del item eliminado
- ✅ Item ya no aparece en la lista

### Prueba 3: Item No Encontrado

**Request:**
```javascript
DELETE /inventarios/01/items/000000000000000000000000
```

**Resultado esperado:**
- ❌ Error 404: Item no encontrado
- ✅ Mensaje de error claro

### Prueba 4: Item en Otra Farmacia

**Request:**
```javascript
DELETE /inventarios/02/items/codigo/PPPP1
// (Item PPPP1 pertenece a farmacia 01)
```

**Resultado esperado:**
- ❌ Error 400: Item pertenece a otra farmacia
- ✅ Mensaje indica la farmacia correcta

---

## 📝 Notas Importantes

### 1. Eliminación Permanente

⚠️ **IMPORTANTE:** La eliminación es **permanente**. El item se elimina completamente de la base de datos.

### 2. Sin Confirmación en el Backend

El backend no solicita confirmación. La confirmación debe manejarse en el frontend antes de hacer la petición DELETE.

### 3. Búsqueda Case Insensitive

El endpoint por código es case insensitive:
- `PPPP1` = `pppp1` = `Pppp1` = `PpPp1`

### 4. Inventario ID Opcional

El parámetro `inventario_id` puede estar vacío. Si está vacío, busca el item sin filtrar por farmacia.

---

## 🚀 Referencias

- **Endpoints:**
  - `DELETE /inventarios/{inventario_id}/items/{item_id}` - Eliminar por ID
  - `DELETE /inventarios/{inventario_id}/items/codigo/{codigo}` - Eliminar por código

- **Archivo backend:** `app/routes/auth.py`

- **Documentación relacionada:**
  - `INSTRUCCIONES_BACKEND_SINCRONIZAR_EXISTENCIA.md` - Sincronización de existencia

---

**Última actualización:** 2024-12-20  
**Estado:** ✅ Implementado  
**Prioridad:** 🚨 CRÍTICA

