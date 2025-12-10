# Solución al Error 500 en Login

## Problema
Error 500 Internal Server Error al intentar hacer login desde el frontend.

## Causas Comunes

### 1. Variables de Entorno Faltantes en Render

El error 500 generalmente ocurre cuando faltan variables de entorno críticas. **VERIFICA EN RENDER** que tengas estas 4 variables configuradas:

#### Variables OBLIGATORIAS:

1. **MONGO_URI**
   - Valor: `mongodb+srv://rapifarma:w1Y7HoezUiMtfrWt@cluster0.9nirn5t.mongodb.net/?appName=Cluster0`

2. **DATABASE_NAME**
   - Valor: `ferreteria_los_puentes`

3. **SECRET_KEY**
   - Valor: `WC8jxnQ52ULWx_sQ5UtDreffTCwdLHNYH5SDF87JtHc`
   - ⚠️ **ESTA ES LA MÁS IMPORTANTE** - Sin ella, el login fallará

4. **ALGORITHM**
   - Valor: `HS256`

### 2. Cómo Verificar en Render

1. Ve a https://dashboard.render.com
2. Selecciona tu servicio `backend-yorbis`
3. Ve a la pestaña **"Environment"**
4. Verifica que las 4 variables estén presentes
5. Si falta alguna, haz clic en **"Add Environment Variable"** y agrega la que falte

### 3. Reiniciar el Servicio

Después de agregar/modificar variables de entorno:

1. Ve a tu servicio en Render
2. Haz clic en **"Manual Deploy"** → **"Deploy latest commit"**
3. Espera a que termine el deploy (2-5 minutos)
4. Revisa los logs para verificar que no hay errores

### 4. Verificar los Logs

Si el error persiste:

1. Ve a la pestaña **"Logs"** en Render
2. Busca errores que mencionen:
   - `SECRET_KEY`
   - `MONGO_URI`
   - `ValueError`
   - `JWTError`

### 5. Credenciales de Prueba

Usuario creado en la base de datos:
- **Correo:** `ferreterialospuentes@gmail.com`
- **Contraseña:** `admin123`

## Cambios Realizados

He mejorado el código para:
- ✅ Validar que las variables de entorno estén configuradas
- ✅ Mejor manejo de errores en el login
- ✅ Mensajes de error más descriptivos
- ✅ Verificar que el usuario existe antes de procesar

## Próximos Pasos

1. ✅ Verifica las variables de entorno en Render
2. ✅ Haz un nuevo deploy en Render
3. ✅ Prueba el login nuevamente
4. ✅ Si persiste el error, revisa los logs en Render


