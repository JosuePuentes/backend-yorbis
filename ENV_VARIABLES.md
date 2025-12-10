# Variables de Entorno (Environment Variables)

Este documento lista todas las variables de entorno necesarias para el proyecto.

## Variables Requeridas

### MongoDB
```
MONGO_URI=mongodb+srv://rapifarma:w1Y7HoezUiMtfrWt@cluster0.9nirn5t.mongodb.net/?appName=Cluster0
DATABASE_NAME=ferreteria_los_puentes
```

### JWT (Autenticación)
```
SECRET_KEY=tu_secret_key_super_segura_aqui_minimo_32_caracteres
ALGORITHM=HS256
```

### Cloudflare R2 (Almacenamiento de archivos)
```
VITE_R2_BUCKET=nombre_de_tu_bucket
VITE_R2_ACCOUNT_ID=tu_account_id_de_cloudflare
VITE_R2_ACCESS_KEY_ID=tu_access_key_id
VITE_R2_SECRET_ACCESS_KEY=tu_secret_access_key
```

## Cómo configurarlas

### Opción 1: Archivo .env (Desarrollo Local)
Crea un archivo `.env` en la raíz del proyecto con las variables arriba.

### Opción 2: Variables de Entorno del Sistema (Producción)
Configura estas variables en tu plataforma de hosting (Vercel, Railway, Render, etc.)

## Notas Importantes

- **SECRET_KEY**: Debe ser una cadena aleatoria y segura. Puedes generar una con:
  ```python
  import secrets
  print(secrets.token_urlsafe(32))
  ```

- **MONGO_URI**: Reemplaza `<w1Y7HoezUiMtfrWt>` con tu contraseña real si tiene caracteres especiales.

- **DATABASE_NAME**: Actualmente configurado para `ferreteria_los_puentes`

- Las variables de R2 son opcionales si no usas almacenamiento de archivos.


