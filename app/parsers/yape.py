import re
from datetime import datetime
from decimal import Decimal
from app.parsers.base import BaseParser, EmailData, TransaccionParseada


class YapeParser(BaseParser):

    dominios = ["yape.pe"]

    ASUNTOS_IGNORAR = [
        "cambios en monto",
        "tus compras por internet",
        "activadas",
        "desactivadas",
        "bienvenido",
    ]

    def puede_parsear(self, email: EmailData) -> bool:
        if not self._es_remitente_valido(email.remitente):
            return False
        if self._es_asunto_ignorable(email.asunto):
            return False
        asunto = email.asunto.lower()
        keywords = ["constancia", "confirmado", "exitosa", "exitoso", "recarga", "yapeo"]
        return any(k in asunto for k in keywords)

    def parsear(self, email: EmailData) -> list[TransaccionParseada]:
        texto = self._html_a_texto(email.cuerpo_html) if email.cuerpo_html else email.cuerpo_texto
        asunto = email.asunto.lower()

        if "recarga" in asunto:
            return self._parsear_recarga(texto, email.fecha_recibido)
        if "servicio" in asunto:
            return self._parsear_pago_servicio(texto, email.fecha_recibido)
        if "cinemark" in asunto or "promos" in texto.lower():
            return self._parsear_promo(texto, email.fecha_recibido)
        if "constancia de transferencia" in asunto:
            return self._parsear_promo(texto, email.fecha_recibido)

        return []

    def _parsear_recarga(self, texto: str, fecha_fallback: datetime) -> list[TransaccionParseada]:
        monto = self._extraer_monto(texto, [
            r"^S/\s*([\d,]+\.?\d*)",
            r"TOTAL\s*:\s*S/\s*([\d,]+\.?\d*)",
            r"RECARGA VIRTUAL\s*:\s*S/\s*([\d,]+\.?\d*)",
        ])
        if not monto:
            return []
        numero = self._extraer_campo(texto, r"Número recargado:\s*([\d ]+)")
        operadora = self._extraer_campo(texto, r"Operadora:\s*(\w+)")
        op = self._extraer_campo(texto, r"Nº de operación Yape:\s*(\w+)")
        fecha = self._extraer_fecha_yape(texto) or fecha_fallback
        return [TransaccionParseada(
            cuenta_nombre="Yape",
            fecha=fecha, monto=monto, moneda="PEN", tipo="cargo",
            descripcion=f"Recarga {operadora or ''} {numero or ''}".strip(),
            comercio=operadora, numero_operacion=op,
        )]

    def _parsear_pago_servicio(self, texto: str, fecha_fallback: datetime) -> list[TransaccionParseada]:
        monto = self._extraer_monto(texto, [r"Monto total\s+S/\s*([\d,]+\.?\d*)"])
        if not monto:
            return []
        empresa = self._extraer_campo(texto, r"Empresa:\s*([^\n]+?)(?:\s+Servicio|$)")
        op = self._extraer_campo(texto, r"Nº de operación Yape:\s*(\w+)")
        fecha = self._extraer_fecha_yape(texto) or fecha_fallback
        return [TransaccionParseada(
            cuenta_nombre="Yape",
            fecha=fecha, monto=monto, moneda="PEN", tipo="cargo",
            descripcion=f"Yapeo servicio: {empresa or 'Sin datos'}",
            comercio=empresa, numero_operacion=op,
        )]

    def _parsear_promo(self, texto: str, fecha_fallback: datetime) -> list[TransaccionParseada]:
        monto = self._extraer_monto(texto, [
            r"Monto total\s+S/\s*([\d,]+\.?\d*)",
            r"Monto total:\s*S/\s*([\d,]+\.?\d*)",
        ])
        if not monto:
            return []
        comercio = (
            self._extraer_campo(texto, r"Comercio:\s*([^\s][^\n]+?)(?:\s+Monto|\s+Cantidad|$)")
            or self._extraer_campo(texto, r"Compras\s+(\w+)")
            or "Yape Promos"
        )
        op = self._extraer_campo(texto, r"Número de operación Yape:\s*(\w+)")
        fecha = self._extraer_fecha_yape(texto) or fecha_fallback
        return [TransaccionParseada(
            cuenta_nombre="Yape",
            fecha=fecha, monto=monto, moneda="PEN", tipo="cargo",
            descripcion=f"Yape Promos: {comercio}",
            comercio=comercio, numero_operacion=op,
        )]

    def _extraer_fecha_yape(self, texto: str) -> datetime | None:
        # Formato: "08 Abr. 2026 - 02:46 pm" o "04 abr. 2026 - 09:14 p. m."
        meses = {
            "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
            "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12,
        }
        patron = r"(\d{1,2})\s+(\w{3})\.?\s+(\d{4})\s*[-–]\s*(\d{1,2}):(\d{2})\s*(a\.?\s*m\.?|p\.?\s*m\.?)"
        m = re.search(patron, texto, re.IGNORECASE)
        if m:
            dia, mes_str, anio, hora, minuto, ampm = m.groups()
            mes = meses.get(mes_str.lower()[:3])
            if mes:
                hora_int = int(hora)
                ampm_clean = ampm.replace(".", "").replace(" ", "").lower()
                if ampm_clean == "pm" and hora_int != 12:
                    hora_int += 12
                elif ampm_clean == "am" and hora_int == 12:
                    hora_int = 0
                return datetime(int(anio), mes, int(dia), hora_int, int(minuto))
        return None

    @staticmethod
    def _extraer_campo(texto: str, patron: str) -> str | None:
        m = re.search(patron, texto, re.IGNORECASE)
        return m.group(1).strip() if m else None
