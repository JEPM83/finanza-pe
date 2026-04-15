"""
Servicio de WhatsApp via Green API.
Maneja envío de notificaciones y recepción de mensajes.
"""
import logging
import httpx
from datetime import timezone, timedelta
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

BASE_URL = "https://api.green-api.com"


def _url(endpoint: str) -> str:
    return f"{BASE_URL}/waInstance{settings.green_api_instance}/{endpoint}/{settings.green_api_token}"


def _chat_id(numero: str) -> str:
    """Convierte número a formato Green API: 51999000000 → 51999000000@c.us"""
    numero = numero.replace("+", "").replace(" ", "")
    return f"{numero}@c.us"


def enviar_mensaje(texto: str, numero: str | None = None) -> bool:
    """Envía un mensaje de texto al número configurado (o al especificado)."""
    destino = numero or settings.whatsapp_number
    if not destino or not settings.green_api_instance:
        logger.warning("WhatsApp no configurado, mensaje no enviado.")
        return False
    try:
        resp = httpx.post(
            _url("sendMessage"),
            json={"chatId": _chat_id(destino), "message": texto},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Error enviando WhatsApp: {e}")
        return False


def notificar_transaccion(tx, cuenta_nombre: str, categoria_nombre: str | None) -> bool:
    """Formatea y envía notificación de una transacción nueva."""
    icono = "💳" if "credito" in cuenta_nombre.lower() or "visa" in cuenta_nombre.lower() else "🏦"
    if "yape" in cuenta_nombre.lower():
        icono = "📱"
    elif "efectivo" in cuenta_nombre.lower():
        icono = "💵"
    elif "ligo" in cuenta_nombre.lower():
        icono = "💜"

    tipo_texto = "Cargo" if tx.tipo == "cargo" else "Abono"
    simbolo = "$" if tx.moneda == "USD" else "S/"
    cat_texto = f"\nCategoría: {categoria_nombre}" if categoria_nombre else ""

    LIMA = timezone(timedelta(hours=-5))
    fecha_lima = tx.fecha.replace(tzinfo=timezone.utc).astimezone(LIMA)

    mensaje = (
        f"{icono} *{cuenta_nombre}*\n"
        f"{tipo_texto}: {simbolo} {tx.monto:,.2f}\n"
        f"{tx.descripcion}{cat_texto}\n"
        f"_{fecha_lima.strftime('%d %b %Y, %I:%M %p')}_"
    )
    return enviar_mensaje(mensaje)


def obtener_mensajes_pendientes() -> list[dict]:
    """
    Obtiene mensajes entrantes pendientes via polling Green API.
    Retorna lista de mensajes sin procesar.
    """
    if not settings.green_api_instance:
        return []
    try:
        resp = httpx.get(_url("receiveNotification"), timeout=25)  # Green API long-polls up to 20s
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return []
        return [data]  # Green API devuelve un mensaje por llamada
    except Exception as e:
        logger.error(f"Error obteniendo mensajes WhatsApp: {e}")
        return []


def confirmar_mensaje_recibido(receipt_id: int) -> bool:
    """Marca mensaje como procesado en Green API."""
    try:
        resp = httpx.delete(
            _url("deleteNotification") + f"/{receipt_id}",
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Error confirmando mensaje {receipt_id}: {e}")
        return False


def extraer_texto_mensaje(notificacion: dict) -> tuple[str | None, int | None]:
    """
    Extrae el texto y receiptId de una notificación Green API.
    Retorna (texto, receipt_id) o (None, receipt_id) si no es texto.
    """
    receipt_id = notificacion.get("receiptId")
    body = notificacion.get("body", {})

    if body.get("typeWebhook") != "incomingMessageReceived":
        return None, receipt_id

    msg_data = body.get("messageData", {})
    if msg_data.get("typeMessage") != "textMessage":
        return None, receipt_id

    texto = msg_data.get("textMessageData", {}).get("textMessage", "").strip()

    # Ignorar mensajes enviados por el propio bot (eco de mensajes salientes)
    sender = body.get("senderData", {}).get("sender", "")
    if body.get("senderData", {}).get("senderName") == "me" or \
       sender == _chat_id(settings.whatsapp_number):
        return None, receipt_id

    logger.info(f"Mensaje de {sender}: {texto[:40]}")
    return texto, receipt_id
