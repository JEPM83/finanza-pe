"""Actualización diaria del tipo de cambio USD/PEN."""
import logging
import httpx
from datetime import date
from decimal import Decimal
from app.database import SessionLocal
from app.models import TipoCambio

logger = logging.getLogger(__name__)


def actualizar_tipo_cambio():
    """Obtiene el tipo de cambio del día desde la API del BCRP."""
    try:
        # API pública del Banco Central de Reserva del Perú
        resp = httpx.get(
            "https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PD04640PD/json/1/1",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        valor = Decimal(str(data["periods"][0]["values"][0]))
    except Exception:
        # Fallback: API alternativa de tipo de cambio
        try:
            resp = httpx.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=10)
            data = resp.json()
            valor = Decimal(str(data["rates"]["PEN"]))
        except Exception as e:
            logger.error(f"No se pudo obtener tipo de cambio: {e}")
            return

    db = SessionLocal()
    try:
        hoy = date.today()
        existente = db.query(TipoCambio).filter(TipoCambio.fecha == hoy).first()
        if existente:
            existente.usd_a_pen = valor
        else:
            db.add(TipoCambio(fecha=hoy, usd_a_pen=valor))
        db.commit()
        logger.info(f"Tipo de cambio actualizado: 1 USD = {valor} PEN")
    except Exception as e:
        db.rollback()
        logger.error(f"Error guardando tipo de cambio: {e}")
    finally:
        db.close()
