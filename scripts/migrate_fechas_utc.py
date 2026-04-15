"""
Migración: corrige fechas de transacciones a UTC usando internalDate de Gmail.

Para cada EmailProcesado en BD:
  1. Consulta Gmail API por el internalDate real (timestamp UTC)
  2. Actualiza fecha_recibido en EmailProcesado
  3. Actualiza fecha en todas sus Transacciones asociadas

Ejecutar una sola vez:
  python scripts/migrate_fechas_utc.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from app.database import SessionLocal
from app.models import EmailProcesado, Transaccion
from app.services.gmail_watcher import _obtener_credenciales
from googleapiclient.discovery import build


def main():
    creds = _obtener_credenciales()
    service = build("gmail", "v1", credentials=creds)
    db = SessionLocal()

    try:
        emails = db.query(EmailProcesado).all()
        print(f"Emails a procesar: {len(emails)}")

        actualizados = 0
        errores = 0

        for ep in emails:
            try:
                msg = service.users().messages().get(
                    userId="me",
                    id=ep.gmail_message_id,
                    format="minimal",
                ).execute()

                internal_ms = int(msg.get("internalDate", 0))
                if not internal_ms:
                    print(f"  SKIP {ep.gmail_message_id[:12]} -- sin internalDate")
                    continue

                fecha_utc = datetime.fromtimestamp(internal_ms / 1000, tz=timezone.utc).replace(tzinfo=None)

                # Actualizar todas las transacciones de este email
                txs = db.query(Transaccion).filter(
                    Transaccion.email_procesado_id == ep.id
                ).all()

                if not txs:
                    continue

                fecha_anterior = txs[0].fecha
                for tx in txs:
                    tx.fecha = fecha_utc

                actualizados += 1
                print(f"  OK  {ep.gmail_message_id[:12]} | {fecha_anterior} -> {fecha_utc} | {len(txs)} tx(s)")

            except Exception as e:
                errores += 1
                print(f"  ERR {ep.gmail_message_id[:12]} — {e}")

        db.commit()
        print(f"\nMigracion completada: {actualizados} emails actualizados, {errores} errores.")

    except Exception as e:
        db.rollback()
        print(f"Error fatal: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
