from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.api.v1.routes_example import router as example_router
from app.routes import auth, metas
from app.routes.pagoscpp import router as pagoscpp_router
from app.routes.cuadres import router as cuadres
from app.routes.proveedores import router as proveedores_router
from app.routes.compras import router as compras_router
from app.routes.productos import router as productos_router
from app.routes.punto_venta import router as punto_venta_router


app = FastAPI(
    title="Backend Yorbis API",
    description="API para Ferretería Los Puentes",
    version="1.0.0"
)

# CORS - Configuración mejorada
allowed_origins = [
    "https://frontend-yorbis.vercel.app",
    "https://frontend-yorbis.vercel.app/",
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Exception handler global para asegurar que CORS funcione incluso en errores
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Manejador global de excepciones que asegura que los headers CORS
    se envíen incluso cuando hay errores 500.
    """
    import traceback
    error_detail = str(exc)
    traceback.print_exc()
    
    # Determinar el código de estado
    status_code = 500
    if isinstance(exc, StarletteHTTPException):
        status_code = exc.status_code
    elif isinstance(exc, RequestValidationError):
        status_code = 422
    
    # Crear respuesta con headers CORS
    origin = request.headers.get("origin")
    headers = {}
    
    if origin in allowed_origins or any(origin.startswith(allowed) for allowed in allowed_origins if allowed.startswith("http://localhost")):
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
        headers["Access-Control-Allow-Headers"] = "*"
    
    return JSONResponse(
        status_code=status_code,
        content={"detail": error_detail},
        headers=headers
    )


@app.get("/")
async def root():
    return {"message": "Backend Yorbis API", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}


app.include_router(example_router, prefix="/api/v1")
app.include_router(auth.router)
app.include_router(pagoscpp_router)
app.include_router(metas.router, tags=["metas"])
app.include_router(cuadres, prefix="/api/cuadres", tags=["cuadres"])
app.include_router(proveedores_router, tags=["proveedores"])
app.include_router(compras_router, tags=["compras"])
app.include_router(productos_router, tags=["productos"])
app.include_router(punto_venta_router, tags=["punto-venta"])
