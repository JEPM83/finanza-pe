from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.database import get_db
from app.models import Cuenta, Transaccion

router = APIRouter()


def _cuenta_dict(c: Cuenta, abonos: float, cargos: float) -> dict:
    return {
        "id": c.id,
        "nombre": c.nombre,
        "tipo": c.tipo,
        "moneda": c.moneda,
        "activa": c.activa,
        "numero_cuenta": c.numero_cuenta,
        "institucion_id": c.institucion_id,
        "institucion": c.institucion.nombre if c.institucion else None,
        "balance_calculado": round(abonos - cargos, 2),
        "total_abonos": round(abonos, 2),
        "total_cargos": round(cargos, 2),
    }


@router.get("/")
def listar_cuentas(solo_activas: bool = True, db: Session = Depends(get_db)):
    q = db.query(Cuenta).options(joinedload(Cuenta.institucion))
    if solo_activas:
        q = q.filter(Cuenta.activa == True)  # noqa: E712
    cuentas = q.all()

    result = []
    for c in cuentas:
        abonos = float(
            db.query(func.sum(Transaccion.monto))
            .filter(Transaccion.cuenta_id == c.id, Transaccion.tipo == "abono")
            .scalar() or 0
        )
        cargos = float(
            db.query(func.sum(Transaccion.monto))
            .filter(Transaccion.cuenta_id == c.id, Transaccion.tipo == "cargo")
            .scalar() or 0
        )
        result.append(_cuenta_dict(c, abonos, cargos))
    return result


@router.get("/{cuenta_id}")
def obtener_cuenta(cuenta_id: int, db: Session = Depends(get_db)):
    c = (
        db.query(Cuenta)
        .options(joinedload(Cuenta.institucion))
        .filter(Cuenta.id == cuenta_id)
        .first()
    )
    if not c:
        return {"error": "Cuenta no encontrada"}
    abonos = float(
        db.query(func.sum(Transaccion.monto))
        .filter(Transaccion.cuenta_id == c.id, Transaccion.tipo == "abono")
        .scalar() or 0
    )
    cargos = float(
        db.query(func.sum(Transaccion.monto))
        .filter(Transaccion.cuenta_id == c.id, Transaccion.tipo == "cargo")
        .scalar() or 0
    )
    return _cuenta_dict(c, abonos, cargos)
