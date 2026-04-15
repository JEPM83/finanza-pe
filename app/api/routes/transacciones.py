from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from datetime import datetime
from app.database import get_db
from app.models import Transaccion, Cuenta, Categoria

router = APIRouter()


def _tx_dict(tx: Transaccion) -> dict:
    return {
        "id": tx.id,
        "fecha": tx.fecha.isoformat(),
        "monto": float(tx.monto),
        "moneda": tx.moneda,
        "tipo": tx.tipo,
        "descripcion": tx.descripcion,
        "comercio": tx.comercio,
        "numero_operacion": tx.numero_operacion,
        "categoria_manual": tx.categoria_manual,
        "notas": tx.notas,
        "cuenta_id": tx.cuenta_id,
        "cuenta_nombre": tx.cuenta.nombre if tx.cuenta else None,
        "categoria_id": tx.categoria_id,
        "categoria_nombre": tx.categoria.nombre if tx.categoria else None,
        "categoria_icono": tx.categoria.icono if tx.categoria else "📦",
        "categoria_color": tx.categoria.color if tx.categoria else "#6c757d",
    }


def _query_con_joins(db: Session):
    return db.query(Transaccion).options(
        joinedload(Transaccion.cuenta),
        joinedload(Transaccion.categoria),
    )


@router.get("/")
def listar_transacciones(
    cuenta_id: int | None = None,
    categoria_id: int | None = None,
    tipo: str | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    busqueda: str | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = _query_con_joins(db).order_by(Transaccion.fecha.desc())
    if cuenta_id:
        q = q.filter(Transaccion.cuenta_id == cuenta_id)
    if categoria_id:
        q = q.filter(Transaccion.categoria_id == categoria_id)
    if tipo:
        q = q.filter(Transaccion.tipo == tipo)
    if desde:
        q = q.filter(Transaccion.fecha >= desde)
    if hasta:
        q = q.filter(Transaccion.fecha <= hasta)
    if busqueda:
        term = f"%{busqueda}%"
        q = q.filter(
            Transaccion.descripcion.ilike(term) | Transaccion.comercio.ilike(term)
        )
    total = q.count()
    items = q.offset(offset).limit(limit).all()
    return {"total": total, "items": [_tx_dict(t) for t in items]}


@router.get("/recientes")
def transacciones_recientes(limite: int = 10, db: Session = Depends(get_db)):
    txs = (
        _query_con_joins(db)
        .order_by(Transaccion.fecha.desc())
        .limit(limite)
        .all()
    )
    return [_tx_dict(t) for t in txs]


@router.post("/efectivo")
def registrar_efectivo(
    tipo: str,
    monto: float,
    descripcion: str,
    categoria_nombre: str = "Otros",
    db: Session = Depends(get_db),
):
    cuenta = db.query(Cuenta).filter(Cuenta.nombre == "Efectivo Soles").first()
    if not cuenta:
        return {"error": "Cuenta Efectivo Soles no encontrada"}
    categoria = db.query(Categoria).filter(Categoria.nombre == categoria_nombre).first()
    if not categoria:
        categoria = db.query(Categoria).filter(Categoria.nombre == "Otros").first()

    tx = Transaccion(
        cuenta_id=cuenta.id,
        categoria_id=categoria.id if categoria else None,
        fecha=datetime.utcnow(),
        monto=monto,
        moneda="PEN",
        tipo=tipo,
        descripcion=descripcion,
        categoria_manual=True,
    )
    db.add(tx)
    db.commit()
    tx = _query_con_joins(db).filter(Transaccion.id == tx.id).first()
    return _tx_dict(tx)


@router.patch("/{tx_id}/categoria")
def actualizar_categoria(tx_id: int, categoria_id: int, db: Session = Depends(get_db)):
    tx = db.query(Transaccion).filter(Transaccion.id == tx_id).first()
    if not tx:
        return {"error": "Transacción no encontrada"}
    tx.categoria_id = categoria_id
    tx.categoria_manual = True
    db.commit()
    return {"ok": True}
