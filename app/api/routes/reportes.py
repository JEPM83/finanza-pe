from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date
from app.database import get_db
from app.models import Transaccion, Cuenta, TipoCambio

router = APIRouter()


@router.get("/resumen-mes")
def resumen_mes(
    anio: int = datetime.now().year,
    mes: int = datetime.now().month,
    db: Session = Depends(get_db),
):
    desde = datetime(anio, mes, 1)
    hasta = datetime(anio, mes + 1, 1) if mes < 12 else datetime(anio + 1, 1, 1)

    resultado = (
        db.query(
            Transaccion.tipo,
            Transaccion.moneda,
            func.sum(Transaccion.monto).label("total"),
            func.count(Transaccion.id).label("cantidad"),
        )
        .filter(Transaccion.fecha >= desde, Transaccion.fecha < hasta)
        .group_by(Transaccion.tipo, Transaccion.moneda)
        .all()
    )
    return [{"tipo": r.tipo, "moneda": r.moneda, "total": float(r.total), "cantidad": r.cantidad} for r in resultado]


@router.get("/gastos-por-categoria")
def gastos_por_categoria(
    anio: int = datetime.now().year,
    mes: int = datetime.now().month,
    db: Session = Depends(get_db),
):
    desde = datetime(anio, mes, 1)
    hasta = datetime(anio, mes + 1, 1) if mes < 12 else datetime(anio + 1, 1, 1)

    from app.models import Categoria
    resultado = (
        db.query(
            Categoria.nombre,
            Categoria.icono,
            Categoria.color,
            func.sum(Transaccion.monto).label("total"),
            func.count(Transaccion.id).label("cantidad"),
        )
        .join(Transaccion, Transaccion.categoria_id == Categoria.id)
        .filter(
            Transaccion.tipo == "cargo",
            Transaccion.moneda == "PEN",
            Transaccion.fecha >= desde,
            Transaccion.fecha < hasta,
        )
        .group_by(Categoria.id)
        .order_by(func.sum(Transaccion.monto).desc())
        .all()
    )
    return [
        {"categoria": r.nombre, "icono": r.icono, "color": r.color,
         "total": float(r.total), "cantidad": r.cantidad}
        for r in resultado
    ]
