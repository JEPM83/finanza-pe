"""
Servicio que monitorea Gmail y procesa emails bancarios automáticamente.
"""
import base64
import logging
import os
from datetime import datetime, timezone
from email import message_from_bytes
from email.policy import default as email_policy

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.database import SessionLocal
from app.models import EmailProcesado, Transaccion, Cuenta, Categoria, ReglaCategoria
from app.parsers.base import EmailData
from app.parsers.bcp import BCPParser
from app.parsers.yape import YapeParser
from app.parsers.interbank import InterbankParser
from app.parsers.pichincha import PichinchaParser
from app.parsers.caja_arequipa import CajaArequipaParser
from app.parsers.ligo import LigoParser

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Todos los dominios bancarios conocidos para el filtro Gmail
DOMINIOS_BANCARIOS = [
    "notificacionesbcp.com.pe",
    "yape.pe",
    "netinterbank.com.pe",
    "intercorp.com.pe",
    "pichincha.pe",
    "cajaarequipa.pe",
    "ligo.pe",
]

PARSERS = [
    BCPParser(),
    YapeParser(),
    InterbankParser(),
    PichinchaParser(),
    CajaArequipaParser(),
    LigoParser(),
]


def _construir_query_gmail() -> str:
    dominios = " OR ".join(f"from:*@{d}" for d in DOMINIOS_BANCARIOS)
    return f"({dominios}) newer_than:1d"


def _obtener_credenciales() -> Credentials:
    config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config")
    token_path = os.path.join(config_dir, "token.json")

    if not os.path.exists(token_path):
        raise FileNotFoundError(f"No se encontró token.json en {config_dir}. Ejecuta scripts/gmail_auth.py primero.")

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    return creds


def _decodificar_email(mensaje_raw: dict) -> EmailData | None:
    try:
        headers = {h["name"]: h["value"] for h in mensaje_raw["payload"]["headers"]}
        remitente = headers.get("From", "")
        asunto = headers.get("Subject", "")
        fecha_str = headers.get("Date", "")

        try:
            from email.utils import parsedate_to_datetime
            fecha = parsedate_to_datetime(fecha_str).replace(tzinfo=None)
        except Exception:
            fecha = datetime.utcnow()

        # Extraer cuerpo HTML y texto
        cuerpo_html = ""
        cuerpo_texto = ""
        payload = mensaje_raw["payload"]

        def extraer_cuerpo(parte):
            nonlocal cuerpo_html, cuerpo_texto
            mime = parte.get("mimeType", "")
            data = parte.get("body", {}).get("data", "")
            if data:
                contenido = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
                if mime == "text/html":
                    cuerpo_html = contenido
                elif mime == "text/plain":
                    cuerpo_texto = contenido
            for sub in parte.get("parts", []):
                extraer_cuerpo(sub)

        extraer_cuerpo(payload)

        return EmailData(
            message_id=mensaje_raw["id"],
            remitente=remitente,
            asunto=asunto,
            cuerpo_html=cuerpo_html,
            cuerpo_texto=cuerpo_texto,
            fecha_recibido=fecha,
        )
    except Exception as e:
        logger.error(f"Error decodificando email {mensaje_raw.get('id')}: {e}")
        return None


def _categorizar(descripcion: str, comercio: str | None, db) -> int | None:
    texto = f"{descripcion} {comercio or ''}".upper()
    reglas = db.query(ReglaCategoria).order_by(ReglaCategoria.prioridad).all()
    for regla in reglas:
        if regla.patron.upper() in texto:
            return regla.categoria_id
    # Categoría "Otros" como fallback
    otros = db.query(Categoria).filter(Categoria.nombre == "Otros").first()
    return otros.id if otros else None


def _resolver_cuenta_id(nombre_cuenta: str, db) -> int | None:
    cuenta = db.query(Cuenta).filter(
        Cuenta.nombre == nombre_cuenta,
        Cuenta.activa == True  # noqa: E712
    ).first()
    return cuenta.id if cuenta else None


def procesar_emails():
    """Job principal: lee emails nuevos y registra transacciones."""
    logger.info("Gmail Watcher: iniciando ciclo de revisión...")
    creds = _obtener_credenciales()
    service = build("gmail", "v1", credentials=creds)
    db = SessionLocal()

    try:
        query = _construir_query_gmail()
        resultado = service.users().messages().list(userId="me", q=query, maxResults=50).execute()
        mensajes = resultado.get("messages", [])

        nuevos = 0
        procesados = 0

        for msg_ref in mensajes:
            msg_id = msg_ref["id"]

            # Verificar si ya fue procesado
            ya_procesado = db.query(EmailProcesado).filter(
                EmailProcesado.gmail_message_id == msg_id
            ).first()
            if ya_procesado:
                continue

            nuevos += 1

            # Obtener email completo
            msg_full = service.users().messages().get(
                userId="me", id=msg_id, format="full"
            ).execute()

            email_data = _decodificar_email(msg_full)
            if not email_data:
                _registrar_email(db, msg_id, "desconocido", "desconocido", "error", "No se pudo decodificar")
                continue

            # Buscar parser adecuado
            parser = next((p for p in PARSERS if p.puede_parsear(email_data)), None)
            if not parser:
                _registrar_email(db, msg_id, email_data.remitente, email_data.asunto, "ignorado")
                db.commit()
                continue

            # Parsear transacciones
            try:
                transacciones = parser.parsear(email_data)
            except Exception as e:
                logger.error(f"Error parseando email {msg_id}: {e}")
                _registrar_email(db, msg_id, email_data.remitente, email_data.asunto, "error", str(e))
                db.commit()
                continue

            if not transacciones:
                _registrar_email(db, msg_id, email_data.remitente, email_data.asunto, "ignorado")
                db.commit()
                continue

            # Guardar email como procesado
            email_proc = _registrar_email(db, msg_id, email_data.remitente, email_data.asunto, "exitoso")
            db.flush()

            # Guardar cada transacción
            for tx in transacciones:
                cuenta_id = _resolver_cuenta_id(tx.cuenta_nombre, db)
                if not cuenta_id:
                    logger.warning(f"Cuenta no encontrada: {tx.cuenta_nombre}")
                    continue

                categoria_id = _categorizar(tx.descripcion, tx.comercio, db)

                nueva_tx = Transaccion(
                    cuenta_id=cuenta_id,
                    categoria_id=categoria_id,
                    email_procesado_id=email_proc.id,
                    fecha=tx.fecha,
                    monto=tx.monto,
                    moneda=tx.moneda,
                    tipo=tx.tipo,
                    descripcion=tx.descripcion,
                    comercio=tx.comercio,
                    numero_operacion=tx.numero_operacion,
                )
                db.add(nueva_tx)

            db.commit()
            procesados += 1
            logger.info(f"  [{email_data.remitente}] {email_data.asunto} → {len(transacciones)} transacción(es)")

        logger.info(f"Gmail Watcher: {nuevos} emails nuevos, {procesados} con transacciones registradas.")

    except Exception as e:
        logger.error(f"Error en Gmail Watcher: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def _registrar_email(db, msg_id: str, remitente: str, asunto: str,
                     resultado: str, error: str | None = None) -> EmailProcesado:
    ep = EmailProcesado(
        gmail_message_id=msg_id,
        remitente=remitente,
        asunto=asunto,
        resultado=resultado,
        error_detalle=error,
    )
    db.add(ep)
    return ep
