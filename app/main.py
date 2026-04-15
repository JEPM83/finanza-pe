import logging
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager

from app.database import engine
from app.models import *  # noqa: F401,F403
from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


def _seed_admin():
    """Crea el usuario admin con clave 123 si no existe."""
    from passlib.context import CryptContext
    from app.database import SessionLocal
    from app.models.usuario import Usuario

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    db = SessionLocal()
    try:
        if not db.query(Usuario).filter(Usuario.username == "admin").first():
            db.add(Usuario(
                username="admin",
                password_hash=pwd_context.hash("123"),
            ))
            db.commit()
            logger.info("Usuario admin creado.")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import Base
    Base.metadata.create_all(bind=engine)
    _seed_admin()

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

app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
app.mount("/static", StaticFiles(directory="app/frontend/static"), name="static")
templates = Jinja2Templates(directory="app/frontend/templates")


def _login_requerido(request: Request):
    """Devuelve RedirectResponse si no hay sesión activa, None si está autenticado."""
    if not request.session.get("user_id"):
        return RedirectResponse("/login", status_code=302)
    return None


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["Sistema"])
def health():
    return {"status": "ok"}


# ── Webhook WhatsApp (Green API) ──────────────────────────────────────────────
@app.post("/webhook/whatsapp", tags=["WhatsApp"])
async def webhook_whatsapp(request: Request):
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


# ── Endpoints de prueba ───────────────────────────────────────────────────────
@app.post("/test/whatsapp", tags=["Sistema"])
def test_whatsapp(mensaje: str = "Hola, prueba de conexión"):
    from app.services.whatsapp_bot import enviar_mensaje
    ok = enviar_mensaje(f"Prueba finanza-pe: {mensaje}")
    return {"enviado": ok}


@app.post("/test/nlp", tags=["Sistema"])
def test_nlp(pregunta: str = "balance"):
    from app.services.claude_nlp import procesar_mensaje
    respuesta = procesar_mensaje(pregunta)
    return {"pregunta": pregunta, "respuesta": respuesta}


# ── Rutas API ─────────────────────────────────────────────────────────────────
from app.api.routes import cuentas, transacciones, categorias, reportes, admin  # noqa: E402
from app.api.routes import auth  # noqa: E402

app.include_router(auth.router,          tags=["Auth"])
app.include_router(cuentas.router,       prefix="/api/cuentas",       tags=["Cuentas"])
app.include_router(transacciones.router, prefix="/api/transacciones", tags=["Transacciones"])
app.include_router(categorias.router,    prefix="/api/categorias",    tags=["Categorías"])
app.include_router(reportes.router,      prefix="/api/reportes",      tags=["Reportes"])
app.include_router(admin.router,         prefix="/api/admin",         tags=["Admin"])


# ── Portal web (protegido) ────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def dashboard(request: Request):
    redir = _login_requerido(request)
    if redir:
        return redir
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/transacciones", include_in_schema=False)
def pagina_transacciones(request: Request):
    redir = _login_requerido(request)
    if redir:
        return redir
    return templates.TemplateResponse("transacciones.html", {"request": request})


@app.get("/cuentas", include_in_schema=False)
def pagina_cuentas(request: Request):
    redir = _login_requerido(request)
    if redir:
        return redir
    return templates.TemplateResponse("cuentas.html", {"request": request})


@app.get("/reportes", include_in_schema=False)
def pagina_reportes(request: Request):
    redir = _login_requerido(request)
    if redir:
        return redir
    return templates.TemplateResponse("reportes.html", {"request": request})


@app.get("/admin/instituciones", include_in_schema=False)
def pagina_admin_instituciones(request: Request):
    redir = _login_requerido(request)
    if redir:
        return redir
    return templates.TemplateResponse("admin_instituciones.html", {"request": request})


@app.get("/admin/cuentas", include_in_schema=False)
def pagina_admin_cuentas(request: Request):
    redir = _login_requerido(request)
    if redir:
        return redir
    return templates.TemplateResponse("admin_cuentas.html", {"request": request})


@app.get("/admin/usuarios", include_in_schema=False)
def pagina_admin_usuarios(request: Request):
    redir = _login_requerido(request)
    if redir:
        return redir
    return templates.TemplateResponse("admin_usuarios.html", {"request": request})
