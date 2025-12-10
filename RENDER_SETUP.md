# Configuración para Render

## Configuración del Servicio Web

### Campos en Render:

1. **Name:** `backend-yorbis`

2. **Language:** `Python 3`

3. **Branch:** `main`

4. **Region:** `Virginia (US East)` (o la que prefieras)

5. **Root Directory:** 
   - Si tu repositorio tiene la estructura `backenddonaive-main/app/`, deja vacío
   - Si tu repositorio tiene la estructura `app/` directamente, deja vacío
   - Si el código está en una subcarpeta, especifica la ruta (ej: `backenddonaive-main`)

6. **Build Command:**
   ```
   pip install -r requirements.txt
   ```

7. **Start Command:**
   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

8. **Instance Type:** `Free` (o el que prefieras)

## Variables de Entorno

Agrega estas variables en la sección "Environment Variables":

- `MONGO_URI` = `mongodb+srv://rapifarma:w1Y7HoezUiMtfrWt@cluster0.9nirn5t.mongodb.net/?appName=Cluster0`
- `DATABASE_NAME` = `ferreteria_los_puentes`
- `SECRET_KEY` = `WC8jxnQ52ULWx_sQ5UtDreffTCwdLHNYH5SDF87JtHc`
- `ALGORITHM` = `HS256`

## Verificación

Después del despliegue, puedes verificar que funciona visitando:
- `https://tu-app.onrender.com/` - Debería mostrar `{"message": "Backend Yorbis API", "status": "running"}`
- `https://tu-app.onrender.com/health` - Debería mostrar `{"status": "healthy"}`

## Solución de Problemas

Si obtienes un 404:
1. Verifica que el **Start Command** sea exactamente: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
2. Verifica que el **Root Directory** esté correcto
3. Revisa los logs en Render para ver errores específicos
4. Asegúrate de que todos los archivos `__init__.py` estén presentes


