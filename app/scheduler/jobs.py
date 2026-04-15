"""
Jobs periódicos del sistema:
- Gmail watcher (cada 5 min)
- Procesador de mensajes WhatsApp (cada 15 seg)
- Backup a GCS (diario 2am)
- Tipo de cambio (diario 9am)
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
scheduler = BackgroundScheduler(timezone="America/Lima")


def job_gmail_watcher():
    try:
        from app.services.gmail_watcher import procesar_emails
        procesar_emails()
    except Exception as e:
        logger.error(f"Job gmail_watcher error: {e}")


def job_whatsapp_polling():
    """Revisa mensajes entrantes de WhatsApp y responde."""
    try:
        from app.services.whatsapp_bot import (
            obtener_mensajes_pendientes,
            confirmar_mensaje_recibido,
            extraer_texto_mensaje,
            enviar_mensaje,
        )
        from app.services.claude_nlp import procesar_mensaje

        notificaciones = obtener_mensajes_pendientes()
        for notif in notificaciones:
            receipt_id = notif.get("receiptId")
            texto, receipt_id = extraer_texto_mensaje(notif)

            if receipt_id:
                confirmar_mensaje_recibido(receipt_id)

            if texto:
                logger.info(f"WhatsApp mensaje recibido: {texto[:50]}")
                respuesta = procesar_mensaje(texto)
                enviar_mensaje(respuesta)

    except Exception as e:
        logger.error(f"Job whatsapp_polling error: {e}")


def job_backup_gcs():
    try:
        from app.services.backup_gcs import realizar_backup
        realizar_backup()
    except Exception as e:
        logger.error(f"Job backup_gcs error: {e}")


def job_tipo_cambio():
    try:
        from app.services.tipo_cambio import actualizar_tipo_cambio
        actualizar_tipo_cambio()
    except Exception as e:
        logger.error(f"Job tipo_cambio error: {e}")


def iniciar_scheduler():
    if scheduler.running:
        return

    # Gmail: cada N minutos (configurable en .env)
    scheduler.add_job(
        job_gmail_watcher,
        trigger=IntervalTrigger(minutes=settings.gmail_poll_interval_minutes),
        id="gmail_watcher",
        replace_existing=True,
        max_instances=1,
    )

    # WhatsApp polling: cada 15 segundos
    scheduler.add_job(
        job_whatsapp_polling,
        trigger=IntervalTrigger(seconds=15),
        id="whatsapp_polling",
        replace_existing=True,
        max_instances=1,
    )

    # Backup GCS: diario a las 2am hora Lima
    scheduler.add_job(
        job_backup_gcs,
        trigger=CronTrigger(hour=settings.backup_hour, minute=0, timezone="America/Lima"),
        id="backup_gcs",
        replace_existing=True,
    )

    # Tipo de cambio: diario a las 9am hora Lima
    scheduler.add_job(
        job_tipo_cambio,
        trigger=CronTrigger(hour=settings.tipo_cambio_hour, minute=0, timezone="America/Lima"),
        id="tipo_cambio",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler iniciado: gmail(5min), whatsapp(15s), backup(2am), tipo_cambio(9am)")


def detener_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
