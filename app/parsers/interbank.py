import re
from datetime import datetime
from decimal import Decimal
from app.parsers.base import BaseParser, EmailData, TransaccionParseada


class InterbankParser(BaseParser):

    dominios = ["netinterbank.com.pe", "intercorp.com.pe"]

    ASUNTOS_IGNORAR = [
        "constancia de operaciones",
        "configuración",
        "activado",
        "desactivado",
        "bienvenido",
    ]

    def puede_parsear(self, email: EmailData) -> bool:
        if not self._es_remitente_valido(email.remitente):
            return False
        if self._es_asunto_ignorable(email.asunto):
            return False
        asunto = email.asunto.lower()
        keywords = ["consumo", "pago", "constancia de pago", "transferencia"]
        return any(k in asunto for k in keywords)

    def parsear(self, email: EmailData) -> list[TransaccionParseada]:
        texto = self._html_a_texto(email.cuerpo_html) if email.cuerpo_html else email.cuerpo_texto
        asunto = email.asunto.lower()

        if "consumo" in asunto:
            return self._parsear_consumo(texto, email.fecha_recibido)
        if "constancia de pago" in asunto or "pago" in asunto:
            return self._parsear_pago(texto, email.fecha_recibido)

        return []

    def _parsear_consumo(self, texto: str, fecha_fallback: datetime) -> list[TransaccionParseada]:
        # Formato: "Monto: S/. 12.00" o "Monto: S/ 12.00"
        monto = self._extraer_monto(texto, [
            r"Monto:\s+S/\.?\s*([\d,]+\.?\d*)",
        ])
        if not monto:
            return []
        comercio = self._extraer_campo(texto, r"Comercio:\s*([^\n]+?)(?:\s+Monto|$)")
        # Fecha formato: "29/03/2026"  Hora: "01:32 AM"
        fecha = self._extraer_fecha_interbank(texto) or fecha_fallback
        return [TransaccionParseada(
            cuenta_nombre="Visa Infiniti",
            fecha=fecha, monto=monto, moneda="PEN", tipo="cargo",
            descripcion=f"Consumo Visa Infinite: {comercio or 'Sin datos'}",
            comercio=comercio,
        )]

    def _parsear_pago(self, texto: str, fecha_fallback: datetime) -> list[TransaccionParseada]:
        # Formato: "Moneda y monto: S/ 600.00"
        monto = self._extraer_monto(texto, [
            r"Moneda y monto:\s+S/\s*([\d,]+\.?\d*)",
            r"monto:\s+S/\s*([\d,]+\.?\d*)",
        ])
        if not monto:
            return []
        op = self._extraer_campo(texto, r"Código de operación:\s*(\w+)")
        fecha = self._extraer_fecha_simple(
            texto, r"(\d{2}\s+\w+\s+\d{4}\s+\d{2}:\d{2}\s+[AP]M)", "%d %b %Y %I:%M %p"
        ) or fecha_fallback
        return [TransaccionParseada(
            cuenta_nombre="BCP Soles",  # el pago sale de la cuenta débito BCP
            fecha=fecha, monto=monto, moneda="PEN", tipo="cargo",
            descripcion="Pago Tarjeta Interbank Visa Infinite",
            numero_operacion=op,
        )]

    def _extraer_fecha_interbank(self, texto: str) -> datetime | None:
        # Formato: "29/03/2026" + "01:32 AM"
        patron = r"Fecha:\s*(\d{2}/\d{2}/\d{4}).*?Hora:\s*(\d{1,2}:\d{2}\s*[AP]M)"
        m = re.search(patron, texto, re.IGNORECASE | re.DOTALL)
        if m:
            try:
                fecha_str = f"{m.group(1)} {m.group(2).strip()}"
                return datetime.strptime(fecha_str, "%d/%m/%Y %I:%M %p")
            except ValueError:
                pass
        return None

    @staticmethod
    def _extraer_campo(texto: str, patron: str) -> str | None:
        m = re.search(patron, texto, re.IGNORECASE)
        return m.group(1).strip() if m else None
