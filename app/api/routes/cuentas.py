from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Cuenta

router = APIRouter()


@router.get("/")
def listar_cuentas(solo_activas: bool = True, db: Session = Depends(get_db)):
    query = db.query(Cuenta)
    if solo_activas:
        query = query.filter(Cuenta.activa == True)  # noqa: E712
    return query.all()


@router.get("/{cuenta_id}")
def obtener_cuenta(cuenta_id: int, db: Session = Depends(get_db)):
    return db.query(Cuenta).filter(Cuenta.id == cuenta_id).first()
