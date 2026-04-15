"""
API de administración: instituciones, cuentas, usuarios.
"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.database import get_db
from app.models import Cuenta, Institucion
from app.models.usuario import Usuario

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ══════════════════════════════════════════════════════
# INSTITUCIONES
# ══════════════════════════════════════════════════════

class InstitucionIn(BaseModel):
    nombre: str
    dominios_email: str = ""


@router.get("/instituciones")
def listar_instituciones(db: Session = Depends(get_db)):
    rows = db.query(Institucion).order_by(Institucion.nombre).all()
    return [
        {"id": i.id, "nombre": i.nombre, "dominios_email": i.dominios_email, "activa": i.activa}
        for i in rows
    ]


@router.post("/instituciones")
def crear_institucion(body: InstitucionIn, db: Session = Depends(get_db)):
    if db.query(Institucion).filter(Institucion.nombre == body.nombre).first():
        raise HTTPException(400, "Ya existe una institución con ese nombre")
    inst = Institucion(nombre=body.nombre, dominios_email=body.dominios_email)
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return {"id": inst.id, "nombre": inst.nombre, "dominios_email": inst.dominios_email, "activa": inst.activa}


@router.patch("/instituciones/{inst_id}")
def editar_institucion(inst_id: int, body: InstitucionIn, db: Session = Depends(get_db)):
    inst = db.get(Institucion, inst_id)
    if not inst:
        raise HTTPException(404, "Institución no encontrada")
    inst.nombre = body.nombre
    inst.dominios_email = body.dominios_email
    db.commit()
    return {"ok": True}


@router.patch("/instituciones/{inst_id}/toggle")
def toggle_institucion(inst_id: int, db: Session = Depends(get_db)):
    inst = db.get(Institucion, inst_id)
    if not inst:
        raise HTTPException(404, "Institución no encontrada")
    inst.activa = not inst.activa
    db.commit()
    return {"activa": inst.activa}


# ══════════════════════════════════════════════════════
# CUENTAS
# ══════════════════════════════════════════════════════

class CuentaIn(BaseModel):
    nombre: str
    institucion_id: int
    tipo: str
    moneda: str
    numero_cuenta: str = ""


@router.get("/cuentas")
def listar_cuentas_admin(db: Session = Depends(get_db)):
    rows = db.query(Cuenta).order_by(Cuenta.nombre).all()
    return [
        {
            "id": c.id,
            "nombre": c.nombre,
            "tipo": c.tipo,
            "moneda": c.moneda,
            "activa": c.activa,
            "numero_cuenta": c.numero_cuenta or "",
            "institucion_id": c.institucion_id,
            "institucion": c.institucion.nombre if c.institucion else "",
        }
        for c in rows
    ]


@router.post("/cuentas")
def crear_cuenta(body: CuentaIn, db: Session = Depends(get_db)):
    if db.query(Cuenta).filter(Cuenta.nombre == body.nombre).first():
        raise HTTPException(400, "Ya existe una cuenta con ese nombre")
    cuenta = Cuenta(
        nombre=body.nombre,
        institucion_id=body.institucion_id,
        tipo=body.tipo,
        moneda=body.moneda,
        numero_cuenta=body.numero_cuenta or None,
        activa=True,
        fecha_alta=date.today(),
    )
    db.add(cuenta)
    db.commit()
    db.refresh(cuenta)
    return {"id": cuenta.id, "nombre": cuenta.nombre}


@router.patch("/cuentas/{cuenta_id}")
def editar_cuenta(cuenta_id: int, body: CuentaIn, db: Session = Depends(get_db)):
    cuenta = db.get(Cuenta, cuenta_id)
    if not cuenta:
        raise HTTPException(404, "Cuenta no encontrada")
    cuenta.nombre = body.nombre
    cuenta.institucion_id = body.institucion_id
    cuenta.tipo = body.tipo
    cuenta.moneda = body.moneda
    cuenta.numero_cuenta = body.numero_cuenta or None
    db.commit()
    return {"ok": True}


@router.patch("/cuentas/{cuenta_id}/toggle")
def toggle_cuenta(cuenta_id: int, db: Session = Depends(get_db)):
    cuenta = db.get(Cuenta, cuenta_id)
    if not cuenta:
        raise HTTPException(404, "Cuenta no encontrada")
    cuenta.activa = not cuenta.activa
    if not cuenta.activa:
        cuenta.fecha_baja = date.today()
    else:
        cuenta.fecha_baja = None
    db.commit()
    return {"activa": cuenta.activa}


# ══════════════════════════════════════════════════════
# USUARIOS
# ══════════════════════════════════════════════════════

class UsuarioIn(BaseModel):
    username: str
    password: str


class PasswordIn(BaseModel):
    password: str


@router.get("/usuarios")
def listar_usuarios(db: Session = Depends(get_db)):
    rows = db.query(Usuario).order_by(Usuario.username).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "activo": u.activo,
            "creado_en": u.creado_en.strftime("%d/%m/%Y") if u.creado_en else "",
        }
        for u in rows
    ]


@router.post("/usuarios")
def crear_usuario(body: UsuarioIn, db: Session = Depends(get_db)):
    if db.query(Usuario).filter(Usuario.username == body.username).first():
        raise HTTPException(400, "Ya existe un usuario con ese nombre")
    if len(body.password) < 4:
        raise HTTPException(400, "La contraseña debe tener al menos 4 caracteres")
    u = Usuario(username=body.username, password_hash=pwd_context.hash(body.password))
    db.add(u)
    db.commit()
    return {"ok": True}


@router.patch("/usuarios/{user_id}/password")
def resetear_password(user_id: int, body: PasswordIn, db: Session = Depends(get_db)):
    u = db.get(Usuario, user_id)
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    if len(body.password) < 4:
        raise HTTPException(400, "La contraseña debe tener al menos 4 caracteres")
    u.password_hash = pwd_context.hash(body.password)
    db.commit()
    return {"ok": True}


@router.patch("/usuarios/{user_id}/toggle")
def toggle_usuario(user_id: int, db: Session = Depends(get_db)):
    u = db.get(Usuario, user_id)
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    u.activo = not u.activo
    db.commit()
    return {"activo": u.activo}
