from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date
import calendar
from app.database import get_db
from app.models import Transaccion, Cuenta, TipoCambio, Categoria

router = APIRouter()


def _mes_rango(anio: int, mes: int):
    """Retorna (inicio, fin) datetime para el mes dado."""
    inicio = datetime(anio, mes, 1)
    ultimo_dia = calendar.monthrange(anio, mes)[1]
    fin = datetime(anio, mes, ultimo_dia, 23, 59, 59)
    return inicio, fin


@router.get("/resumen-mes")
def resumen_mes(
    anio: int | None = None,
    mes: int | None = None,
    db: Session = Depends(get_db),
):
    if anio is None: anio = datetime.now().year
    if mes is None:  mes  = datetime.now().month
    inicio, fin = _mes_rango(anio, mes)
    resultado = (
        db.query(
            Transaccion.tipo,
            Transaccion.moneda,
            func.sum(Transaccion.monto).label("total"),
            func.count(Transaccion.id).label("cantidad"),
        )
        .filter(Transaccion.fecha >= inicio, Transaccion.fecha <= fin)
        .group_by(Transaccion.tipo, Transaccion.moneda)
        .all()
    )
    return [
        {"tipo": r.tipo, "moneda": r.moneda, "total": float(r.total), "cantidad": r.cantidad}
        for r in resultado
    ]


@router.get("/gastos-por-categoria")
def gastos_por_categoria(
    anio: int | None = None,
    mes: int | None = None,
    db: Session = Depends(get_db),
):
    if anio is None: anio = datetime.now().year
    if mes is None:  mes  = datetime.now().month
    inicio, fin = _mes_rango(anio, mes)
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
            Transaccion.fecha >= inicio,
            Transaccion.fecha <= fin,
        )
        .group_by(Categoria.id)
        .order_by(func.sum(Transaccion.monto).desc())
        .all()
    )
    return [
        {
            "categoria": r.nombre,
            "icono": r.icono,
            "color": r.color,
            "total": float(r.total),
            "cantidad": r.cantidad,
        }
        for r in resultado
    ]


@router.get("/evolucion-mensual")
def evolucion_mensual(meses: int = 6, db: Session = Depends(get_db)):
    hoy = date.today()
    resultado = []
    for i in range(meses - 1, -1, -1):
        # Retroceder i meses desde el mes actual
        mes_offset = hoy.month - 1 - i
        anio = hoy.year + mes_offset // 12
        mes = mes_offset % 12 + 1
        # Ajuste para valores negativos de mes_offset
        if mes_offset < 0:
            anio = hoy.year - ((-mes_offset + 11) // 12)
            mes = ((hoy.month - 1 - i) % 12) + 1

        inicio, fin = _mes_rango(anio, mes)

        gastos = float(
            db.query(func.sum(Transaccion.monto))
            .filter(
                Transaccion.tipo == "cargo",
                Transaccion.moneda == "PEN",
                Transaccion.fecha >= inicio,
                Transaccion.fecha <= fin,
            )
            .scalar() or 0
        )
        ingresos = float(
            db.query(func.sum(Transaccion.monto))
            .filter(
                Transaccion.tipo == "abono",
                Transaccion.moneda == "PEN",
                Transaccion.fecha >= inicio,
                Transaccion.fecha <= fin,
            )
            .scalar() or 0
        )

        meses_es = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        resultado.append({
            "mes": f"{meses_es[mes - 1]} {anio}",
            "anio": anio,
            "mes_num": mes,
            "gastos": gastos,
            "ingresos": ingresos,
        })
    return resultado


@router.get("/top-comercios")
def top_comercios(
    anio: int | None = None,
    mes: int | None = None,
    limite: int = 10,
    db: Session = Depends(get_db),
):
    if anio is None: anio = datetime.now().year
    if mes is None:  mes  = datetime.now().month
    inicio, fin = _mes_rango(anio, mes)
    resultado = (
        db.query(
            Transaccion.comercio,
            func.sum(Transaccion.monto).label("total"),
            func.count(Transaccion.id).label("cantidad"),
        )
        .filter(
            Transaccion.tipo == "cargo",
            Transaccion.moneda == "PEN",
            Transaccion.comercio.isnot(None),
            Transaccion.fecha >= inicio,
            Transaccion.fecha <= fin,
        )
        .group_by(Transaccion.comercio)
        .order_by(func.sum(Transaccion.monto).desc())
        .limit(limite)
        .all()
    )
    return [
        {"comercio": r.comercio, "total": float(r.total), "cantidad": r.cantidad}
        for r in resultado
    ]
