import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager

from app.database import engine
from app.models import *  # noqa: F401,F403

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import Base
    Base.metadata.create_all(bind=engine)

    from app.scheduler.jobs import iniciar_scheduler
    iniciar_scheduler()
    logger.info("Sistema finanza-pe iniciado.")

    yield

    from app.scheduler.jobs import detener_scheduler
    detener_scheduler()
    logger.info("Sistema finanza-pe detenido.")


app = FastAPI(
    title="Finanza PE",
    description="Monitor de finanzas personales",
    version="0.1.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="app/frontend/static"), name="static")
templates = Jinja2Templates(directory="app/frontend/templates")


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["Sistema"])
def health():
    return {"status": "ok"}


# ── Webhook WhatsApp (Green API) ──────────────────────────────────────────────
@app.post("/webhook/whatsapp", tags=["WhatsApp"])
async def webhook_whatsapp(request: Request):
    """
    Endpoint que recibe notificaciones de Green API.
    Configurar en Green API: Settings → Webhook URL → https://TU-VM/webhook/whatsapp
    """
    try:
        body = await request.json()
        from app.services.whatsapp_bot import extraer_texto_mensaje, enviar_mensaje
        from app.services.claude_nlp import procesar_mensaje

        notif = {"body": body, "receiptId": None}
        texto, _ = extraer_texto_mensaje(notif)

        if texto:
            logger.info(f"Webhook WhatsApp: {texto[:50]}")
            respuesta = procesar_mensaje(texto)
            enviar_mensaje(respuesta)

    except Exception as e:
        logger.error(f"Error en webhook WhatsApp: {e}")

    return {"status": "ok"}


# ── Endpoint de prueba WhatsApp ───────────────────────────────────────────────
@app.post("/test/whatsapp", tags=["Sistema"])
def test_whatsapp(mensaje: str = "Hola, prueba de conexión"):
    """Envía un mensaje de prueba a tu WhatsApp."""
    from app.services.whatsapp_bot import enviar_mensaje
    ok = enviar_mensaje(f"Prueba finanza-pe: {mensaje}")
    return {"enviado": ok}


@app.post("/test/nlp", tags=["Sistema"])
def test_nlp(pregunta: str = "balance"):
    """Prueba el NLP con Claude sin enviar a WhatsApp."""
    from app.services.claude_nlp import procesar_mensaje
    respuesta = procesar_mensaje(pregunta)
    return {"pregunta": pregunta, "respuesta": respuesta}


# ── Rutas API ─────────────────────────────────────────────────────────────────
from app.api.routes import cuentas, transacciones, categorias, reportes  # noqa: E402

app.include_router(cuentas.router,       prefix="/api/cuentas",       tags=["Cuentas"])
app.include_router(transacciones.router, prefix="/api/transacciones", tags=["Transacciones"])
app.include_router(categorias.router,    prefix="/api/categorias",    tags=["Categorías"])
app.include_router(reportes.router,      prefix="/api/reportes",      tags=["Reportes"])


# ── Portal web ────────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})
