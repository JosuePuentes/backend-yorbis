from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.routes_example import router as example_router
from app.routes import auth, metas
from app.routes.pagoscpp import router as pagoscpp_router
from app.routes.cuadres import router as cuadres
from app.routes.proveedores import router as proveedores_router
from app.routes.compras import router as compras_router


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
