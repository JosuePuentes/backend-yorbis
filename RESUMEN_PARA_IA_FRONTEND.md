# Resumen para IA del Frontend

## Información del Backend

**Base URL:** `https://backend-yorbis.onrender.com`

## Endpoints Disponibles

### 1. Autenticación
- `POST /auth/login` - Login (correo: ferreterialospuentes@gmail.com, contraseña: admin)
- `GET /auth/me` - Obtener usuario actual con permisos

### 2. Proveedores
- `GET /proveedores` - Listar todos
- `POST /proveedores` - Crear nuevo
- `GET /proveedores/{id}` - Obtener uno
- `PUT /proveedores/{id}` - Actualizar
- `DELETE /proveedores/{id}` - Eliminar

### 3. Compras (IMPORTANTE: Actualiza Inventario Automáticamente)
- `GET /compras` - Listar todas (filtros: farmacia, fecha_inicio, fecha_fin)
- `POST /compras` - Crear compra
- `GET /compras/{id}` - Obtener una
- `PUT /compras/{id}` - Actualizar
- `DELETE /compras/{id}` - Eliminar

**⚠️ COMPORTAMIENTO CRÍTICO:**
Cuando se crea una compra (`POST /compras`), los productos se suman AUTOMÁTICAMENTE al inventario.
- Si el producto existe → se suma la cantidad
- Si no existe → se crea nuevo registro

### 4. Inventario
- `GET /inventarios` - Listar todos
- `POST /inventarios` - Crear manualmente
- `PATCH /inventarios/{id}/estado` - Actualizar estado

## Estructura de Datos para Compras

```javascript
{
  "proveedorId": "string (ID del proveedor)",
  "proveedorNombre": "string (opcional)",
  "fecha": "YYYY-MM-DD",
  "farmacia": "01",  // ID de la farmacia
  "total": 1500.00,
  "numeroFactura": "string (opcional)",
  "observaciones": "string (opcional)",
  "productos": [
    {
      "nombre": "string (requerido)",
      "cantidad": 10,  // número (requerido)
      "precioUnitario": 15.00,  // número (requerido)
      "precioTotal": 150.00,  // número (requerido)
      "codigo": "string (opcional)",
      "productoId": "string (opcional)"
    }
  ]
}
```

## Headers Requeridos

```javascript
{
  "Content-Type": "application/json",
  "Authorization": "Bearer {token}"
}
```

## Manejo de Errores

- **401**: No autenticado (token inválido o faltante)
- **400**: Datos inválidos (campos faltantes o formato incorrecto)
- **404**: Recurso no encontrado
- **422**: Error de validación (estructura de datos incorrecta)
- **500**: Error del servidor

## Notas Importantes

1. **CORS**: Ya configurado para `https://frontend-yorbis.vercel.app`
2. **Token**: Guardar después del login y usar en todas las peticiones
3. **Inventario Automático**: Solo al crear compra, NO al actualizar/eliminar
4. **Farmacia**: Usar ID "01" para "Ferretería Los Puentes"

