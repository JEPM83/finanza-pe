"""Backup diario de SQLite a Google Cloud Storage."""
import logging
import os
from datetime import datetime
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "finanza.db")


def realizar_backup():
    if not settings.gcs_bucket_name:
        logger.warning("GCS_BUCKET_NAME no configurado, backup omitido.")
        return

    if not os.path.exists(DB_PATH):
        logger.warning(f"Base de datos no encontrada en {DB_PATH}")
        return

    try:
        from google.cloud import storage
        client = storage.Client(project=settings.gcs_project_id)
        bucket = client.bucket(settings.gcs_bucket_name)

        fecha = datetime.now().strftime("%Y-%m-%d")
        blob_name = f"backups/finanza_{fecha}.db"
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(DB_PATH)

        size_mb = os.path.getsize(DB_PATH) / (1024 * 1024)
        logger.info(f"Backup exitoso: gs://{settings.gcs_bucket_name}/{blob_name} ({size_mb:.2f} MB)")
    except Exception as e:
        logger.error(f"Error en backup GCS: {e}")
