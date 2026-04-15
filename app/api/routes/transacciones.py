from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models import Transaccion

router = APIRouter()


@router.get("/")
def listar_transacciones(
    cuenta_id: int | None = None,
    categoria_id: int | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    limit: int = Query(default=50, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(Transaccion).order_by(Transaccion.fecha.desc())
    if cuenta_id:
        query = query.filter(Transaccion.cuenta_id == cuenta_id)
    if categoria_id:
        query = query.filter(Transaccion.categoria_id == categoria_id)
    if desde:
        query = query.filter(Transaccion.fecha >= desde)
    if hasta:
        query = query.filter(Transaccion.fecha <= hasta)
    return query.limit(limit).all()
