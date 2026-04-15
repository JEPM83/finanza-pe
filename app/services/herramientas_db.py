"""
Herramientas de base de datos para Claude Tool Use.
Cada función consulta SQLite y retorna datos estructurados.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

_LIMA = timezone(timedelta(hours=-5))

def _fmt_fecha(dt: datetime, con_hora: bool = True) -> str:
    """Convierte datetime UTC → hora Lima y formatea."""
    dt_lima = dt.replace(tzinfo=timezone.utc).astimezone(_LIMA)
    return dt_lima.strftime("%d/%m/%Y %H:%M") if con_hora else dt_lima.strftime("%d/%m/%Y")
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import SessionLocal
from app.models import Transaccion, Cuenta, Categoria, TipoCambio


def _db() -> Session:
    return SessionLocal()


def _tipo_cambio_vigente(db: Session) -> Decimal:
    tc = db.query(TipoCambio).order_by(TipoCambio.fecha.desc()).first()
    return tc.usd_a_pen if tc else Decimal("3.75")


def _rango_periodo(periodo: str) -> tuple[datetime, datetime]:
    hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if periodo == "hoy":
        return hoy, datetime.now()
    if periodo == "ayer":
        ayer = hoy - timedelta(days=1)
        return ayer, hoy
    if periodo == "esta_semana":
        inicio = hoy - timedelta(days=hoy.weekday())
        return inicio, datetime.now()
    if periodo == "este_mes":
        return hoy.replace(day=1), datetime.now()
    if periodo == "mes_pasado":
        primer_dia_mes = hoy.replace(day=1)
        ultimo_mes = primer_dia_mes - timedelta(days=1)
        return ultimo_mes.replace(day=1), primer_dia_mes
    if periodo == "esta_semana_pasada":
        inicio = hoy - timedelta(days=hoy.weekday() + 7)
        fin = inicio + timedelta(days=7)
        return inicio, fin
    # Último mes por defecto
    return hoy.replace(day=1), datetime.now()


# ─── HERRAMIENTAS ────────────────────────────────────────────────────────────

def obtener_balance() -> dict:
    """Retorna saldo actual de todas las cuentas activas con total consolidado en PEN."""
    db = _db()
    try:
        tc = _tipo_cambio_vigente(db)
        cuentas = db.query(Cuenta).filter(Cuenta.activa == True).all()  # noqa: E712

        resultado = []
        total_pen = Decimal("0")

        for cuenta in cuentas:
            # Calcular balance sumando abonos - cargos
            abonos = db.query(func.sum(Transaccion.monto)).filter(
                Transaccion.cuenta_id == cuenta.id,
                Transaccion.tipo == "abono",
            ).scalar() or Decimal("0")

            cargos = db.query(func.sum(Transaccion.monto)).filter(
                Transaccion.cuenta_id == cuenta.id,
                Transaccion.tipo == "cargo",
            ).scalar() or Decimal("0")

            balance = abonos - cargos
            balance_pen = balance * tc if cuenta.moneda == "USD" else balance

            if cuenta.tipo != "credito":
                total_pen += balance_pen

            resultado.append({
                "cuenta": cuenta.nombre,
                "tipo": cuenta.tipo,
                "moneda": cuenta.moneda,
                "balance": float(balance),
                "balance_pen": float(balance_pen),
            })

        return {
            "cuentas": resultado,
            "total_consolidado_pen": float(total_pen),
            "tipo_cambio": float(tc),
            "fecha": _fmt_fecha(datetime.now()),
        }
    finally:
        db.close()


def obtener_gastos_por_categoria(periodo: str = "este_mes") -> dict:
    """Retorna gastos agrupados por categoría para el período indicado."""
    db = _db()
    try:
        desde, hasta = _rango_periodo(periodo)
        rows = (
            db.query(
                Categoria.nombre,
                Categoria.icono,
                func.sum(Transaccion.monto).label("total"),
                func.count(Transaccion.id).label("cantidad"),
            )
            .join(Transaccion, Transaccion.categoria_id == Categoria.id)
            .filter(
                Transaccion.tipo == "cargo",
                Transaccion.moneda == "PEN",
                Transaccion.fecha >= desde,
                Transaccion.fecha <= hasta,
            )
            .group_by(Categoria.id)
            .order_by(func.sum(Transaccion.monto).desc())
            .all()
        )
        total = sum(float(r.total) for r in rows)
        categorias = [
            {
                "categoria": r.nombre,
                "icono": r.icono,
                "total": float(r.total),
                "cantidad": r.cantidad,
                "porcentaje": round(float(r.total) / total * 100, 1) if total > 0 else 0,
            }
            for r in rows
        ]
        return {
            "periodo": periodo,
            "desde": desde.strftime("%d/%m/%Y"),
            "hasta": hasta.strftime("%d/%m/%Y"),
            "categorias": categorias,
            "total_pen": total,
        }
    finally:
        db.close()


def obtener_transacciones_recientes(
    limite: int = 10,
    cuenta_nombre: str | None = None,
    tipo: str | None = None,
) -> dict:
    """Retorna las últimas N transacciones con filtros opcionales."""
    db = _db()
    try:
        query = db.query(Transaccion).order_by(Transaccion.fecha.desc())
        if cuenta_nombre:
            cuenta = db.query(Cuenta).filter(Cuenta.nombre.ilike(f"%{cuenta_nombre}%")).first()
            if cuenta:
                query = query.filter(Transaccion.cuenta_id == cuenta.id)
        if tipo:
            query = query.filter(Transaccion.tipo == tipo)

        txs = query.limit(min(limite, 20)).all()
        return {
            "transacciones": [
                {
                    "fecha": _fmt_fecha(tx.fecha),
                    "tipo": tx.tipo,
                    "monto": float(tx.monto),
                    "moneda": tx.moneda,
                    "descripcion": tx.descripcion,
                    "comercio": tx.comercio,
                    "cuenta": tx.cuenta.nombre if tx.cuenta else "",
                    "categoria": tx.categoria.nombre if tx.categoria else "Sin categoría",
                }
                for tx in txs
            ],
            "total_registros": len(txs),
        }
    finally:
        db.close()


def obtener_deuda_tarjetas() -> dict:
    """Retorna el saldo adeudado en cada tarjeta de crédito."""
    db = _db()
    try:
        tarjetas = db.query(Cuenta).filter(
            Cuenta.tipo == "credito",
            Cuenta.activa == True,  # noqa: E712
        ).all()

        resultado = []
        total_pen = Decimal("0")
        tc = _tipo_cambio_vigente(db)

        for tarjeta in tarjetas:
            cargos = db.query(func.sum(Transaccion.monto)).filter(
                Transaccion.cuenta_id == tarjeta.id,
                Transaccion.tipo == "cargo",
            ).scalar() or Decimal("0")

            abonos = db.query(func.sum(Transaccion.monto)).filter(
                Transaccion.cuenta_id == tarjeta.id,
                Transaccion.tipo == "abono",
            ).scalar() or Decimal("0")

            deuda = cargos - abonos
            deuda_pen = deuda * tc if tarjeta.moneda == "USD" else deuda
            total_pen += deuda_pen

            resultado.append({
                "tarjeta": tarjeta.nombre,
                "moneda": tarjeta.moneda,
                "deuda": float(deuda),
                "deuda_pen": float(deuda_pen),
            })

        return {
            "tarjetas": resultado,
            "total_deuda_pen": float(total_pen),
            "tipo_cambio": float(tc),
        }
    finally:
        db.close()


def obtener_resumen_periodo(periodo: str = "este_mes") -> dict:
    """Retorna resumen de ingresos, gastos y balance neto del período."""
    db = _db()
    try:
        desde, hasta = _rango_periodo(periodo)

        ingresos = db.query(func.sum(Transaccion.monto)).filter(
            Transaccion.tipo == "abono",
            Transaccion.moneda == "PEN",
            Transaccion.fecha >= desde,
            Transaccion.fecha <= hasta,
        ).scalar() or Decimal("0")

        gastos = db.query(func.sum(Transaccion.monto)).filter(
            Transaccion.tipo == "cargo",
            Transaccion.moneda == "PEN",
            Transaccion.fecha >= desde,
            Transaccion.fecha <= hasta,
        ).scalar() or Decimal("0")

        num_transacciones = db.query(func.count(Transaccion.id)).filter(
            Transaccion.fecha >= desde,
            Transaccion.fecha <= hasta,
        ).scalar() or 0

        return {
            "periodo": periodo,
            "desde": desde.strftime("%d/%m/%Y"),
            "hasta": hasta.strftime("%d/%m/%Y"),
            "ingresos_pen": float(ingresos),
            "gastos_pen": float(gastos),
            "balance_neto_pen": float(ingresos - gastos),
            "num_transacciones": num_transacciones,
        }
    finally:
        db.close()


def buscar_transacciones(busqueda: str, limite: int = 10) -> dict:
    """Busca transacciones por texto en descripción o comercio."""
    db = _db()
    try:
        txs = (
            db.query(Transaccion)
            .filter(
                Transaccion.descripcion.ilike(f"%{busqueda}%")
                | Transaccion.comercio.ilike(f"%{busqueda}%")
            )
            .order_by(Transaccion.fecha.desc())
            .limit(min(limite, 20))
            .all()
        )
        total_cargos = sum(float(tx.monto) for tx in txs if tx.tipo == "cargo" and tx.moneda == "PEN")
        return {
            "busqueda": busqueda,
            "transacciones": [
                {
                    "fecha": _fmt_fecha(tx.fecha),
                    "tipo": tx.tipo,
                    "monto": float(tx.monto),
                    "moneda": tx.moneda,
                    "descripcion": tx.descripcion,
                    "cuenta": tx.cuenta.nombre if tx.cuenta else "",
                }
                for tx in txs
            ],
            "total_encontradas": len(txs),
            "total_cargos_pen": total_cargos,
        }
    finally:
        db.close()


def registrar_transaccion_efectivo(
    tipo: str,
    monto: float,
    descripcion: str,
    categoria_nombre: str = "Otros",
) -> dict:
    """Registra un gasto o ingreso en efectivo manualmente."""
    db = _db()
    try:
        cuenta = db.query(Cuenta).filter(Cuenta.nombre == "Efectivo Soles").first()
        if not cuenta:
            return {"error": "Cuenta Efectivo Soles no encontrada"}

        categoria = db.query(Categoria).filter(
            Categoria.nombre.ilike(f"%{categoria_nombre}%")
        ).first()
        if not categoria:
            categoria = db.query(Categoria).filter(Categoria.nombre == "Otros").first()

        tx = Transaccion(
            cuenta_id=cuenta.id,
            categoria_id=categoria.id if categoria else None,
            fecha=datetime.now(),
            monto=Decimal(str(monto)),
            moneda="PEN",
            tipo=tipo,
            descripcion=descripcion,
            categoria_manual=True,
        )
        db.add(tx)
        db.commit()

        return {
            "exitoso": True,
            "tipo": tipo,
            "monto": monto,
            "descripcion": descripcion,
            "categoria": categoria.nombre if categoria else "Sin categoría",
            "fecha": _fmt_fecha(tx.fecha),
        }
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()
