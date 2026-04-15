from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager

from app.database import engine
from app.models import *  # noqa: F401,F403 — registra todos los modelos


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Arranque: crear tablas si no existen
    from app.database import Base
    Base.metadata.create_all(bind=engine)
    yield
    # Apagado: nada que limpiar por ahora


app = FastAPI(
    title="Finanza PE",
    description="Monitor de finanzas personales",
    version="0.1.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="app/frontend/static"), name="static")
templates = Jinja2Templates(directory="app/frontend/templates")


# --- Health check ---
@app.get("/health", tags=["Sistema"])
def health():
    return {"status": "ok"}


# --- Rutas de la API ---
from app.api.routes import cuentas, transacciones, categorias, reportes  # noqa: E402

app.include_router(cuentas.router,       prefix="/api/cuentas",       tags=["Cuentas"])
app.include_router(transacciones.router, prefix="/api/transacciones", tags=["Transacciones"])
app.include_router(categorias.router,    prefix="/api/categorias",    tags=["Categorías"])
app.include_router(reportes.router,      prefix="/api/reportes",      tags=["Reportes"])


# --- Portal web ---
from fastapi import Request  # noqa: E402

@app.get("/", include_in_schema=False)
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})
