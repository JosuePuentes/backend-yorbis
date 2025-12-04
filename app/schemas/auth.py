from pydantic import BaseModel
from typing import Optional, List

class LoginInput(BaseModel):
    correo: str
    contraseña: str

class PuntoVenta(BaseModel):
    banco: str
    puntoDebito: float
    puntoCredito: float

class Cuadre(BaseModel):
    dia: str
    cajaNumero: int
    tasa: float
    turno: str
    cajero: str
    cajeroId: Optional[str] = None
    totalCajaSistemaBs: float
    devolucionesBs: float
    recargaBs: float
    pagomovilBs: float
    puntosVenta: Optional[List[PuntoVenta]] = []
    efectivoBs: float
    totalBs: float
    totalBsEnUsd: float
    efectivoUsd: float
    zelleUsd: float
    totalGeneralUsd: float
    diferenciaUsd: float
    sobranteUsd: Optional[float] = 0
    faltanteUsd: Optional[float] = 0
    delete: Optional[bool] = False
    estado: Optional[str] = 'wait'
    nombreFarmacia: Optional[str] = None
    costoInventario: float  # Nuevo campo obligatorio
    fecha: Optional[str] = None  # Fecha (solo fecha)
    hora: Optional[str] = None   # Hora (solo hora)
    valesUsd: Optional[float] = 0  # Permitir decimales y valor por defecto 0
    imagenesCuadre: Optional[List[str]] = None  # Nombres de los objetos de imagen en R2 (hasta 3)
    # imagenCuadre: Optional[str] = None  # DEPRECATED: Usar imagenesCuadre