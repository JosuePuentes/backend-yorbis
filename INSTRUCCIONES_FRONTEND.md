# Instrucciones para el Frontend

## Base URL
```
https://backend-yorbis.onrender.com
```

## Autenticación
Todos los endpoints (excepto login) requieren un token JWT en el header:
```
Authorization: Bearer {token}
```

---

## 🔐 Autenticación

### Login
```javascript
POST /auth/login
Content-Type: application/json

Body:
{
  "correo": "ferreterialospuentes@gmail.com",
  "contraseña": "admin"
}

Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "usuario": {
    "_id": "69320b68ce15ee162003c4d2",
    "correo": "ferreterialospuentes@gmail.com",
    "permisos": ["ver_inicio", "agregar_cuadre", ...],
    "farmacias": {"01": "Ferretería Los Puentes"}
  }
}
```

### Obtener Usuario Actual
```javascript
GET /auth/me
Authorization: Bearer {token}

Response:
{
  "_id": "69320b68ce15ee162003c4d2",
  "correo": "ferreterialospuentes@gmail.com",
  "permisos": [...],
  "farmacias": {...}
}
```

---

## 🏪 Proveedores

### Obtener Todos los Proveedores
```javascript
GET /proveedores
Authorization: Bearer {token}

Response: [
  {
    "_id": "...",
    "nombre": "Proveedor ABC",
    ...
  }
]
```

### Crear Proveedor
```javascript
POST /proveedores
Authorization: Bearer {token}
Content-Type: application/json

Body:
{
  "nombre": "Proveedor ABC",
  "telefono": "0412-1234567",
  "email": "proveedor@example.com",
  "direccion": "Calle Principal",
  "rif": "J-12345678-9"
}

Response:
{
  "message": "Proveedor creado exitosamente",
  "id": "...",
  "proveedor": {...}
}
```

### Obtener un Proveedor
```javascript
GET /proveedores/{proveedor_id}
Authorization: Bearer {token}
```

### Actualizar Proveedor
```javascript
PUT /proveedores/{proveedor_id}
Authorization: Bearer {token}
Content-Type: application/json

Body:
{
  "nombre": "Nuevo Nombre",
  "telefono": "0412-9876543"
}
```

### Eliminar Proveedor
```javascript
DELETE /proveedores/{proveedor_id}
Authorization: Bearer {token}
```

---

## 🛒 Compras

### ⚠️ IMPORTANTE: Actualización Automática de Inventario
**Cuando creas una compra, los productos se suman automáticamente al inventario.**

### Obtener Todas las Compras
```javascript
GET /compras
Authorization: Bearer {token}

// Con filtros opcionales:
GET /compras?farmacia=01
GET /compras?fecha_inicio=2025-01-01&fecha_fin=2025-12-31
GET /compras?farmacia=01&fecha_inicio=2025-01-01&fecha_fin=2025-12-31

Response: [
  {
    "_id": "...",
    "proveedorId": "...",
    "proveedorNombre": "Proveedor ABC",
    "fecha": "2025-12-05",
    "productos": [...],
    "total": 1500.00,
    "farmacia": "01"
  }
]
```

### Crear Compra (ACTUALIZA INVENTARIO AUTOMÁTICAMENTE)
```javascript
POST /compras
Authorization: Bearer {token}
Content-Type: application/json

Body:
{
  "proveedorId": "69320b68ce15ee162003c4d2",
  "proveedorNombre": "Proveedor ABC",  // Opcional
  "fecha": "2025-12-05",
  "farmacia": "01",
  "total": 1500.00,
  "numeroFactura": "FAC-001",  // Opcional
  "observaciones": "Compra de materiales",  // Opcional
  "productos": [
    {
      "nombre": "Martillo",
      "cantidad": 10,
      "precioUnitario": 15.00,
      "precioTotal": 150.00,
      "codigo": "MAR-001",  // Opcional
      "productoId": "..."  // Opcional
    },
    {
      "nombre": "Clavos",
      "cantidad": 5,
      "precioUnitario": 8.00,
      "precioTotal": 40.00
    }
  ]
}

Response:
{
  "message": "Compra creada exitosamente",
  "id": "...",
  "compra": {...},
  "inventario_actualizado": {
    "productos_actualizados": 2,
    "productos_con_error": 0,
    "detalle": {
      "exitosos": ["Martillo", "Clavos"],
      "errores": []
    }
  }
}
```

**Nota importante:** 
- Si el producto ya existe en el inventario, se **suma la cantidad** y se actualiza el costo promedio
- Si el producto no existe, se **crea un nuevo registro** en el inventario
- La actualización es automática, no necesitas hacer otra petición

### Obtener una Compra
```javascript
GET /compras/{compra_id}
Authorization: Bearer {token}
```

### Actualizar Compra
```javascript
PUT /compras/{compra_id}
Authorization: Bearer {token}
Content-Type: application/json

Body:
{
  "fecha": "2025-12-06",
  "total": 1600.00,
  "productos": [...]
}

// NOTA: Al actualizar, el inventario NO se actualiza automáticamente
```

### Eliminar Compra
```javascript
DELETE /compras/{compra_id}
Authorization: Bearer {token}

// NOTA: Al eliminar, el inventario NO se actualiza automáticamente
```

---

## 📦 Inventario

### Obtener Inventarios
```javascript
GET /inventarios
Authorization: Bearer {token}

Response: [
  {
    "_id": "...",
    "farmacia": "01",
    "nombre": "Martillo",
    "cantidad": 25,
    "costo": 15.00,
    "codigo": "MAR-001",
    "estado": "activo",
    "fecha": "2025-12-05"
  }
]
```

### Crear Inventario Manualmente
```javascript
POST /inventarios
Authorization: Bearer {token}
Content-Type: application/json

Body:
{
  "farmacia": "01",
  "nombre": "Producto Nuevo",
  "cantidad": 10,
  "costo": 20.00,
  "codigo": "PROD-001"  // Opcional
}
```

---

## 📋 Ejemplo de Flujo Completo

### 1. Login
```javascript
const loginResponse = await fetch('https://backend-yorbis.onrender.com/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    correo: 'ferreterialospuentes@gmail.com',
    contraseña: 'admin'
  })
});

const { access_token, usuario } = await loginResponse.json();
localStorage.setItem('token', access_token);
localStorage.setItem('usuario', JSON.stringify(usuario));
```

### 2. Crear Proveedor
```javascript
const token = localStorage.getItem('token');

const proveedorResponse = await fetch('https://backend-yorbis.onrender.com/proveedores', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    nombre: 'Proveedor ABC',
    telefono: '0412-1234567',
    email: 'proveedor@example.com'
  })
});

const proveedor = await proveedorResponse.json();
```

### 3. Crear Compra (Actualiza Inventario Automáticamente)
```javascript
const compraResponse = await fetch('https://backend-yorbis.onrender.com/compras', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    proveedorId: proveedor.id,
    proveedorNombre: 'Proveedor ABC',
    fecha: '2025-12-05',
    farmacia: '01',
    total: 1500.00,
    productos: [
      {
        nombre: 'Martillo',
        cantidad: 10,
        precioUnitario: 15.00,
        precioTotal: 150.00,
        codigo: 'MAR-001'
      }
    ]
  })
});

const compra = await compraResponse.json();
console.log('Inventario actualizado:', compra.inventario_actualizado);
```

---

## 🔧 Función Helper para Fetch con Auth

```javascript
async function fetchWithAuth(url, options = {}) {
  const token = localStorage.getItem('token');
  
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const response = await fetch(`https://backend-yorbis.onrender.com${url}`, {
    ...options,
    headers
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Error en la petición');
  }
  
  return response.json();
}

// Uso:
const proveedores = await fetchWithAuth('/proveedores');
const compra = await fetchWithAuth('/compras', {
  method: 'POST',
  body: JSON.stringify({...})
});
```

---

## ⚠️ Notas Importantes

1. **CORS**: Ya está configurado para aceptar peticiones desde `https://frontend-yorbis.vercel.app`

2. **Token**: Guarda el token después del login y úsalo en todas las peticiones

3. **Inventario Automático**: 
   - ✅ Al **crear** una compra → Inventario se actualiza automáticamente
   - ❌ Al **actualizar** una compra → Inventario NO se actualiza
   - ❌ Al **eliminar** una compra → Inventario NO se actualiza

4. **Estructura de Productos en Compra**:
   - `nombre` (requerido)
   - `cantidad` (requerido, número)
   - `precioUnitario` (requerido, número)
   - `precioTotal` (requerido, número)
   - `codigo` (opcional)
   - `productoId` (opcional)

5. **Farmacia**: Usa el ID de la farmacia (ej: "01" para "Ferretería Los Puentes")

---

## 🐛 Manejo de Errores

```javascript
try {
  const response = await fetchWithAuth('/compras', {
    method: 'POST',
    body: JSON.stringify(compraData)
  });
  
  if (response.inventario_actualizado.productos_con_error > 0) {
    console.warn('Algunos productos no se actualizaron:', 
      response.inventario_actualizado.detalle.errores);
  }
} catch (error) {
  console.error('Error:', error.message);
  // Manejar error (mostrar mensaje al usuario, etc.)
}
```

