from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.routes_example import router as example_router
from app.routes import auth, metas
from app.routes.pagoscpp import router as pagoscpp_router
from app.routes.cuadres import router as cuadres


app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://frontend-yorbis.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
