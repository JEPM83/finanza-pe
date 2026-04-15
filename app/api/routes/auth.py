"""
Rutas de autenticación: login, logout, cambiar clave.
"""
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext

from app.database import SessionLocal
from app.models.usuario import Usuario

router = APIRouter()
templates = Jinja2Templates(directory="app/frontend/templates")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Login ─────────────────────────────────────────────────────────────────────

@router.get("/login", include_in_schema=False)
def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login", include_in_schema=False)
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    db = SessionLocal()
    try:
        user = db.query(Usuario).filter(
            Usuario.username == username,
            Usuario.activo == True,  # noqa: E712
        ).first()
        if not user or not pwd_context.verify(password, user.password_hash):
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error": "Usuario o contraseña incorrectos"},
            )
        request.session["user_id"] = user.id
        return RedirectResponse("/", status_code=302)
    finally:
        db.close()


# ── Logout ────────────────────────────────────────────────────────────────────

@router.get("/logout", include_in_schema=False)
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)


# ── Cambiar clave ─────────────────────────────────────────────────────────────

@router.get("/cambiar-clave", include_in_schema=False)
def cambiar_clave_page(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("cambiar_clave.html", {"request": request})


@router.post("/cambiar-clave", include_in_schema=False)
def cambiar_clave(
    request: Request,
    clave_actual:   str = Form(...),
    clave_nueva:    str = Form(...),
    clave_confirmar: str = Form(...),
):
    if not request.session.get("user_id"):
        return RedirectResponse("/login", status_code=302)

    db = SessionLocal()
    try:
        user = db.query(Usuario).filter(Usuario.id == request.session["user_id"]).first()

        if not pwd_context.verify(clave_actual, user.password_hash):
            return templates.TemplateResponse(
                "cambiar_clave.html",
                {"request": request, "error": "La clave actual es incorrecta"},
            )
        if clave_nueva != clave_confirmar:
            return templates.TemplateResponse(
                "cambiar_clave.html",
                {"request": request, "error": "Las claves nuevas no coinciden"},
            )
        if len(clave_nueva) < 4:
            return templates.TemplateResponse(
                "cambiar_clave.html",
                {"request": request, "error": "La clave debe tener al menos 4 caracteres"},
            )

        user.password_hash = pwd_context.hash(clave_nueva)
        db.commit()
        return templates.TemplateResponse(
            "cambiar_clave.html",
            {"request": request, "success": "Clave actualizada correctamente"},
        )
    finally:
        db.close()
