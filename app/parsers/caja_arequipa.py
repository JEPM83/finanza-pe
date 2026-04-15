import re
from datetime import datetime
from app.parsers.base import BaseParser, EmailData, TransaccionParseada


class CajaArequipaParser(BaseParser):

    dominios = ["cajaarequipa.pe"]

    ASUNTOS_IGNORAR = [
        "bienvenido",
        "estado de cuenta",
    ]

    def puede_parsear(self, email: EmailData) -> bool:
        if not self._es_remitente_valido(email.remitente):
            return False
        if self._es_asunto_ignorable(email.asunto):
            return False
        asunto = email.asunto.lower()
        keywords = ["transferencia", "operaciones", "pago", "constancia"]
        return any(k in asunto for k in keywords)

    def parsear(self, email: EmailData) -> list[TransaccionParseada]:
        texto = self._html_a_texto(email.cuerpo_html) if email.cuerpo_html else email.cuerpo_texto
        asunto = email.asunto.lower()

        if "transferencia entre cuentas" in asunto:
            return self._parsear_transferencia_propia(texto, email.fecha_recibido)
        if "operaciones" in asunto:
            return self._parsear_notificacion(texto, email.fecha_recibido)

        return []

    def _parsear_transferencia_propia(self, texto: str, fecha_fallback: datetime) -> list[TransaccionParseada]:
        monto = self._extraer_monto(texto, [
            r"Importe de la transferencia\s+S/\s*([\d,]+\.?\d*)",
        ])
        if not monto:
            return []
        op = self._extraer_campo(texto, r"Número de Operación\s+(\w+)")
        fecha = self._extraer_fecha_ca(texto) or fecha_fallback
        return [TransaccionParseada(
            cuenta_nombre="Caja Arequipa Soles",
            fecha=fecha, monto=monto, moneda="PEN", tipo="cargo",
            descripcion="Transferencia entre cuentas Caja Arequipa",
            numero_operacion=op,
        )]

    def _parsear_notificacion(self, texto: str, fecha_fallback: datetime) -> list[TransaccionParseada]:
        # Formato: "ENVIO YAPE por S/.14.60 para Eder G Alanya C el 28/02"
        monto = self._extraer_monto(texto, [
            r"por\s+S/\.?\s*([\d,]+\.?\d*)",
            r"S/\s*([\d,]+\.?\d*)",
        ])
        if not monto:
            return []

        # Tipo de operación
        tipo_op = self._extraer_campo(texto, r"operación\s+([A-Z ]+?)\s+por")
        tipo = "cargo"
        descripcion = f"Operación Caja Arequipa: {tipo_op or 'Sin datos'}"

        destinatario = self._extraer_campo(texto, r"para\s+([^\n]+?)(?:\s+el\s+\d|$)")
        if destinatario:
            descripcion += f" a {destinatario}"

        fecha = self._extraer_fecha_ca(texto) or fecha_fallback

        return [TransaccionParseada(
            cuenta_nombre="Caja Arequipa Soles",
            fecha=fecha, monto=monto, moneda="PEN", tipo=tipo,
            descripcion=descripcion,
        )]

    def _extraer_fecha_ca(self, texto: str) -> datetime | None:
        # Formato: "26/03/26 - 11:34:38"
        patron = r"(\d{2}/\d{2}/\d{2,4})\s*[-–]\s*(\d{2}:\d{2})"
        m = re.search(patron, texto)
        if m:
            try:
                fecha_str = f"{m.group(1)} {m.group(2)}"
                fmt = "%d/%m/%y %H:%M" if len(m.group(1).split("/")[2]) == 2 else "%d/%m/%Y %H:%M"
                return datetime.strptime(fecha_str, fmt)
            except ValueError:
                pass
        return None

    @staticmethod
    def _extraer_campo(texto: str, patron: str) -> str | None:
        m = re.search(patron, texto, re.IGNORECASE)
        return m.group(1).strip() if m else None
